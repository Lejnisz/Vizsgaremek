#!/usr/bin/env python3
"""Uroborosz Biztonság Kft. – hálózati konfiggenerátor.

inventory/network.yml + inventory/secrets.yml + templates/*.j2  →  out/<telephely>/<eszköz>.cfg

Használat:
    python generate.py                 # minden eszköz konfigja az out/ mappába
    python generate.py --device R-DEB  # egyetlen eszköz (kiírja a képernyőre is)
    python generate.py --list          # eszközlista
    python generate.py --check         # csak az inventory ellenőrzése, nem ír fájlt
"""
from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from pathlib import Path

import jinja2
import yaml

ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Segédek
# ---------------------------------------------------------------------------
def netmask(prefix: int) -> str:
    return str(ipaddress.ip_network(f"0.0.0.0/{prefix}").netmask)


def wildcard(prefix: int) -> str:
    return str(ipaddress.ip_network(f"0.0.0.0/{prefix}").hostmask)


def _with_masks(d: dict) -> dict:
    """prefix → mask + wildcard hozzáadása egy {ip/net, prefix} szótárhoz (másolatot ad)."""
    d = dict(d)
    if "prefix" in d:
        d["mask"] = netmask(d["prefix"])
        d["wildcard"] = wildcard(d["prefix"])
    return d


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Modell: nyers YAML → sablon-kontextusok
# ---------------------------------------------------------------------------
class Model:
    def __init__(self, inv: dict, secrets: dict):
        self.inv = inv
        self.secrets = secrets
        self.org = inv["org"]
        self.vlans = {int(k): v for k, v in inv["vlans"].items()}
        self.sites = inv["sites"]
        self._derive_sites()

    # -- telephelyek -------------------------------------------------------
    def _derive_sites(self) -> None:
        for key, s in self.sites.items():
            s["key"] = key
            s["wan"] = _with_masks(s["wan"])
            if "tunnel" in s:
                s["tunnel"] = _with_masks(s["tunnel"])
            if "serial" in s:
                s["serial"] = _with_masks(s["serial"])
            if "lan" in s:
                net = ipaddress.ip_network(s["lan"])
                s["lan_net"] = str(net.network_address)
                s["lan_wildcard"] = str(net.hostmask)
                base = ".".join(str(net.network_address).split(".")[:2])
                rows = []
                for v in s.get("vlans", []):
                    nb = f"{base}.{v['id']}"
                    rows.append({
                        "id": v["id"],
                        "name": self.vlans[v["id"]],
                        "net_base": nb,
                        "gw": f"{nb}.1",
                        "v6": f"2001:DB8:{s['n']}:{v['id']}::1/64",
                        "dhcp": v.get("dhcp"),
                    })
                s["vlan_rows"] = rows

    @property
    def remote_sites(self) -> list[dict]:
        return sorted((s for s in self.sites.values() if s["n"] > 1), key=lambda s: s["n"])

    # -- menedzsment ACL ---------------------------------------------------
    def mgmt_nets(self, site_key: str | None = None, extra: list | None = None) -> list[dict]:
        nets = list(self.org["mgmt_nets"])
        if site_key and site_key != "bp":
            for v in self.sites[site_key].get("vlan_rows", []):
                if v["id"] == 40:
                    nets.append({"net": f"{v['net_base']}.0", "wildcard": "0.0.0.255"})
        nets.extend(extra or [])
        return nets

    # -- eszközök ----------------------------------------------------------
    def devices(self) -> list[dict]:
        """Minden eszköz: {hostname, site, role, template, ctx}"""
        out: list[dict] = []
        inv = self.inv
        hq_wan = self.sites["bp"]["wan"]

        # ISP
        isp = dict(inv["isp"])
        isp["links"] = [_with_masks({**l, "netmask": netmask(l["prefix"])}) for l in isp["links"]]
        isp["routes"] = [{**r, "netmask": netmask(r["prefix"])} for r in isp["routes"]]
        out.append(self._dev(isp["hostname"], "isp", "isp", "isp.j2", {
            "isp": isp, "mgmt_nets": self.mgmt_nets(extra=isp.get("mgmt_extra"))}))

        # Központi router
        hq = dict(inv["hq_router"])
        hq["lan_if"] = _with_masks(hq["lan_if"])
        serial_key = hq["serial"]["peer_site"]
        hq["serial_site"] = self.sites[serial_key]
        vpn = dict(hq["remote_vpn"])
        out.append(self._dev(hq["hostname"], "bp", "router_hq", "router_hq.j2", {
            "hq": hq, "hq_wan": hq_wan, "vpn": vpn, "remote_sites": self.remote_sites,
            "mgmt_nets": self.mgmt_nets()}))

        # Telephelyi routerek
        for s in self.remote_sites:
            out.append(self._dev(s["router"], s["key"], "router_site", "router_site.j2", {
                "site": s, "hub_wan_ip": hq_wan["ip"], "hq_router": hq,
                "mgmt_nets": self.mgmt_nets(s["key"])}))

        # ASA
        asa = dict(inv["asa"])
        out.append(self._dev(asa["hostname"], "bp", "asa", "asa.j2", {"asa": asa}))

        # Core-ok
        for cd in inv["core"]["devices"]:
            out.append(self._core(cd))

        # Access switchek
        for sw in inv["switches"]:
            out.append(self._switch(sw))
        return out

    def _dev(self, hostname, site, role, template, ctx) -> dict:
        base_ctx = {"org": self.org, "secrets": self.secrets, "vlans": self.vlans}
        base_ctx.update(ctx)
        base_ctx.setdefault("dev", {"hostname": hostname})
        return {"hostname": hostname, "site": site, "role": role, "template": template, "ctx": base_ctx}

    def _core(self, cd: dict) -> dict:
        core = dict(self.inv["core"])
        core["portchannel"] = {**core["portchannel"], "name": f"Port-channel{core['portchannel']['id']}"}
        svis = []
        for sv in core["svi"]:
            vlan = sv["vlan"]
            base = sv.get("net_base", f"{core['net_prefix']}.{vlan}.0")
            net = ipaddress.ip_network(f"{base}/{sv['prefix']}")
            host = cd["host"]
            svis.append({
                "vlan": vlan,
                "name": self.vlans[vlan],
                "ip": str(net.network_address + host),
                "vip": str(net.network_address + 1),
                "mask": str(net.netmask),
                "v6": f"2001:DB8:1:{vlan}::{host}/64" if sv["prefix"] == 24 else f"2001:DB8:1:{vlan}::{host}/64",
                "helper": sv.get("helper", False),
                "owner": vlan in cd["owns"],
                **({"acl_in": sv["acl_in"]} if "acl_in" in sv else {}),
            })
        used = sorted({s["vlan"] for s in svis} | {core["trunk_native"]})
        dev = {
            "hostname": cd["hostname"],
            "svis": svis,
            "stp_owned": [s["vlan"] for s in svis if s["owner"]],
            "stp_other": [s["vlan"] for s in svis if not s["owner"]],
        }
        return self._dev(cd["hostname"], "bp", "core", "core.j2", {
            "dev": dev, "core": core, "mgmt_nets": self.mgmt_nets(),
            "vlan_defs": [{"id": v, "name": self.vlans[v]} for v in used]})

    def _switch(self, sw: dict) -> dict:
        site_key = sw["site"]
        site = self.sites[site_key]
        by_port = {p["port"]: p for p in sw["ports"]}
        rows = []
        for i in range(1, 25):
            port = f"FastEthernet0/{i}"
            p = by_port.get(port)
            if p:
                sec = {"host": 2, "ap": 10}.get(p["kind"])
                rows.append({"port": port, "vlan": p["vlan"], "shutdown": False, "port_security": sec})
            else:
                rows.append({"port": port, "vlan": 99, "shutdown": True, "port_security": None})
        used_vlans = {p["vlan"] for p in sw["ports"]} | {99}
        if "mgmt" in sw:
            used_vlans.add(sw["mgmt"]["vlan"])
        dev = dict(sw)
        dev.setdefault("snooping_vlans", [])
        dev.setdefault("uplinks", [])
        dev.setdefault("spare_uplinks", [])
        dev["port_rows"] = rows
        extra = None
        return self._dev(sw["hostname"], site_key, "access_switch", "access_switch.j2", {
            "dev": dev, "site_name": site["name"], "trunk_native": self.inv["core"]["trunk_native"],
            "parking_vlan": 99, "mgmt_nets": self.mgmt_nets(site_key, extra),
            "vlan_defs": [{"id": v, "name": self.vlans[v]} for v in sorted(used_vlans)]})


# ---------------------------------------------------------------------------
# Validálás
# ---------------------------------------------------------------------------
def validate(model: Model) -> list[str]:
    errs: list[str] = []
    inv = model.inv

    # hostname egyediség
    names = [d["hostname"] for d in model.devices()]
    for n in set(names):
        if names.count(n) > 1:
            errs.append(f"duplikált hostname: {n}")

    # VLAN hivatkozások
    def need_vlan(v, where):
        if v not in model.vlans:
            errs.append(f"ismeretlen VLAN {v} ({where})")

    for s in model.sites.values():
        for v in s.get("vlans", []):
            need_vlan(v["id"], f"telephely {s['key']}")
    for sw in inv["switches"]:
        for p in sw["ports"]:
            need_vlan(p["vlan"], f"{sw['hostname']} {p['port']}")
        if "mgmt" in sw:
            need_vlan(sw["mgmt"]["vlan"], f"{sw['hostname']} mgmt")
    for sv in inv["core"]["svi"]:
        need_vlan(sv["vlan"], "core SVI")

    # WAN és alagút címek ugyanabban az alhálózatban
    for s in model.remote_sites:
        w = s["wan"]
        net = ipaddress.ip_network(f"{w['ip']}/{w['prefix']}", strict=False)
        if ipaddress.ip_address(w["gw"]) not in net:
            errs.append(f"{s['key']}: a WAN gateway nincs a WAN alhálózatban")
        t = s["tunnel"]
        tnet = ipaddress.ip_network(f"{t['net']}/{t['prefix']}")
        for k in ("ip", "hub_ip"):
            if ipaddress.ip_address(t[k]) not in tnet:
                errs.append(f"{s['key']}: tunnel.{k} nincs a {tnet} hálózatban")
        if "serial" in s:
            sn = ipaddress.ip_network(f"{s['serial']['net']}/{s['serial']['prefix']}")
            for k in ("ip", "hub_ip"):
                if ipaddress.ip_address(s["serial"][k]) not in sn:
                    errs.append(f"{s['key']}: serial.{k} nincs a {sn} hálózatban")
        # az ISP megfelelő portja a WAN gateway címen áll
        if not any(l["ip"] == w["gw"] for l in inv["isp"]["links"]):
            errs.append(f"{s['key']}: az ISP-nek nincs {w['gw']} című portja")

    # ISMÉTLŐDŐ azonosítók a hub oldalon
    for field in ("hub_if", "hub_seq", "hub_acl"):
        vals = [s["tunnel"][field] for s in model.remote_sites]
        if len(set(vals)) != len(vals):
            errs.append(f"duplikált tunnel.{field}: {vals}")

    # IP-cím duplikáció (kontextusonként, a HSRP VIP-et külön kezelve)
    seen: dict[str, str] = {}

    def claim(ip, who):
        if ip in seen and seen[ip] != who:
            errs.append(f"duplikált IP {ip}: {seen[ip]} és {who}")
        seen[ip] = who

    for l in inv["isp"]["links"]:
        claim(l["ip"], f"ISP {l['port']}")
    for s in model.sites.values():
        claim(s["wan"]["ip"], f"{s['router']} WAN")
        if "tunnel" in s:
            claim(s["tunnel"]["ip"], f"{s['router']} tunnel")
            claim(s["tunnel"]["hub_ip"], f"hub tunnel {s['key']}")
        for v in s.get("vlan_rows", []):
            claim(v["gw"], f"{s['router']} vlan {v['id']}")

    # Core: SVI alhálózatok ne fedjék egymást, minden SVI-nak pontosan egy tulajdonosa legyen
    nets = []
    for sv in inv["core"]["svi"]:
        base = sv.get("net_base", f"{inv['core']['net_prefix']}.{sv['vlan']}.0")
        nets.append((sv["vlan"], ipaddress.ip_network(f"{base}/{sv['prefix']}")))
    for i, (v1, n1) in enumerate(nets):
        for v2, n2 in nets[i + 1:]:
            if n1.overlaps(n2):
                errs.append(f"core SVI átfedés: VLAN {v1} ({n1}) és VLAN {v2} ({n2})")
    svi_vlans = [sv["vlan"] for sv in inv["core"]["svi"]]
    owned = [v for d in inv["core"]["devices"] for v in d["owns"]]
    for v in svi_vlans:
        if owned.count(v) != 1:
            errs.append(f"core SVI VLAN {v}: {owned.count(v)} HSRP-tulajdonos (pontosan 1 kell)")

    # Switch portok ne ütközzenek
    for sw in inv["switches"]:
        ports = [p["port"] for p in sw["ports"]]
        if len(set(ports)) != len(ports):
            errs.append(f"{sw['hostname']}: duplikált port")

    # Jelszó mezők jelen vannak és nem placeholder
    for k in ("admin_user", "admin_password", "enable_secret", "ipsec_psk", "chap_password"):
        if not model.secrets.get(k):
            errs.append(f"secrets.{k} hiányzik")
        elif model.secrets[k] == "CHANGE_ME":
            errs.append(f"secrets.{k} még CHANGE_ME")
    return errs


# ---------------------------------------------------------------------------
# Renderelés
# ---------------------------------------------------------------------------
def make_env() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(ROOT / "templates")),
        undefined=jinja2.StrictUndefined,   # hiányzó adat → hiba, nem üres string
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def render(env: jinja2.Environment, dev: dict) -> str:
    text = env.get_template(dev["template"]).render(**dev["ctx"])
    # üres sorok összevonása, sor végi szóközök törlése
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventory", default=str(ROOT / "inventory" / "network.yml"))
    ap.add_argument("--secrets", default=str(ROOT / "inventory" / "secrets.yml"))
    ap.add_argument("--out", default=str(ROOT / "out"))
    ap.add_argument("--device", help="csak ez az eszköz (hostname)")
    ap.add_argument("--list", action="store_true", help="eszközlista")
    ap.add_argument("--check", action="store_true", help="csak ellenőrzés")
    args = ap.parse_args(argv)

    secrets_path = Path(args.secrets)
    if not secrets_path.exists():
        print(f"HIBA: nincs secrets fájl: {secrets_path} (másold a secrets.example.yml-t)", file=sys.stderr)
        return 2

    model = Model(load_yaml(Path(args.inventory)), load_yaml(secrets_path))
    errs = validate(model)
    if errs:
        print("Az inventory hibás:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 1

    devices = model.devices()
    if args.list:
        for d in devices:
            print(f"{d['hostname']:10} {d['site']:4} {d['role']}")
        return 0
    if args.check:
        print(f"OK: {len(devices)} eszköz, az inventory hibátlan")
        return 0

    env = make_env()
    out = Path(args.out)
    n = 0
    for d in devices:
        if args.device and d["hostname"] != args.device:
            continue
        text = render(env, d)
        path = out / d["site"] / f"{d['hostname']}.cfg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        n += 1
        if args.device:
            print(text)
    if args.device and n == 0:
        print(f"HIBA: nincs ilyen eszköz: {args.device}", file=sys.stderr)
        return 1
    print(f"{n} konfig kiírva: {out}", file=sys.stderr if args.device else sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

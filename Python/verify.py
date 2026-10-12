#!/usr/bin/env python3
"""A generált konfig összevetése egy eszközről lementett `show running-config` kimenettel.

    python verify.py R-DEB tests/fixtures/R-DEB.txt

A vizsgálat kontextusos és sorrendfüggetlen: minden generált parancsnak (a szülő
`interface ...` / `router ...` sorával együtt) szerepelnie kell a futó konfigban.
Visszatérési kód: 0 = egyezik, 1 = hiányzik valami a futó konfigból.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import generate

# A PT/IOS ezeket nem tükrözi a running-configban, vagy titkosítva/átalakítva írja ki.
IGNORE = [
    r"^end$", r"^write memory$", r"^no shutdown$", r"^crypto key generate",
    r"^logging buffered", r"^hostname ", r"^vlan \d+$", r"^name \S+$",
    r"^service password-encryption$", r"^ip routing$", r"^ip ssh version 2$",
    r"^no ip domain-lookup$", r"^no service pad$", r"^ssh timeout",
    r"^ipv6 unicast-routing$", r"^spanning-tree mode",
    r"^policy-map type inspect dns", r"^parameters$", r"^message-length",
]
# Ezeknél csak a „kulcsszó + felhasználó/azonosító" rész hasonlítható (a titok hash-elve van).
SECRET_PREFIXES = ("enable secret", "username ", "enable password", "banner motd")


def _expand_vty(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """`line vty 0 15` = `line vty 0 4` + `line vty 5 15` (a PT így bontja szét a running-configban)."""
    out: list[tuple[str, str]] = []
    for ctx, line in pairs:
        if ctx == "line vty 0 15" or line == "line vty 0 15":
            for rng in ("0 4", "5 15"):
                out.append(("" if line == "line vty 0 15" else f"line vty {rng}",
                            f"line vty {rng}" if line == "line vty 0 15" else line))
        else:
            out.append((ctx, line))
    return out


def _alias(line: str) -> str:
    """Az IOS a `logging host X` parancsot `logging X` alakban írja ki."""
    return re.sub(r"^logging host ", "logging ", line)


def normalize(text: str) -> list[tuple[str, str]]:
    return _expand_vty(_normalize(text))


def _normalize(text: str) -> list[tuple[str, str]]:
    """Sorok (kontextus, parancs) párokként. Kontextus = az utolsó nem behúzott sor."""
    out: list[tuple[str, str]] = []
    ctx = ""
    for raw in text.splitlines():
        if not raw.strip() or raw.strip() == "!" or raw.lstrip().startswith("!"):
            continue
        if raw.startswith(("Building", "Current configuration", ": ", "Cryptochecksum")):
            continue
        indented = raw[0] in " \t"
        line = _alias(" ".join(raw.split()))
        if not indented:
            if re.match(r"^(interface|router|line|ip dhcp pool|ip access-list|crypto map|crypto isakmp client|"
                        r"crypto dynamic-map|crypto isakmp policy|class-map|policy-map|vlan)\b", line):
                ctx = line
                out.append(("", line))
                continue
            ctx = ""
        out.append((ctx if indented else "", line))
    return out


def _secret_key(line: str) -> str:
    if line.startswith("banner motd"):
        return "banner motd"
    if line.startswith("enable"):
        return " ".join(line.split()[:2])
    if line.startswith("username "):
        return " ".join(line.split()[:2])
    return line


def compare(generated: str, running: str, strict: bool = False) -> list[str]:
    gen = normalize(generated)
    run = normalize(running)
    run_set = set(run)
    run_secret = {(c, _secret_key(l)) for c, l in run if l.startswith(SECRET_PREFIXES)}
    missing = []
    for ctx, line in gen:
        if any(re.search(p, line) for p in IGNORE) or (line.startswith("description ") and not strict):
            continue                       # a leírások csak kozmetikai többletet adnak
        if line.startswith(SECRET_PREFIXES):
            if (ctx, _secret_key(line)) not in run_secret:
                missing.append(f"[{ctx or 'global'}] {line.split(' secret')[0].split(' password')[0]}")
            continue
        if (ctx, line) in run_set:
            continue
        # IOS rövidítései: "permit ip 10.9.0.0 0.0.0.255 any" stb. ugyanúgy íródnak ki, ezért itt csak a
        # sorrendfüggetlen egyezést ismerjük el – minden más eltérés.
        missing.append(f"[{ctx or 'global'}] {line}")
    return missing


def to_commands(missing: list[str]) -> list[str]:
    """A compare() "[kontextus] parancs" sorait konfigurációs parancssorrá alakítja."""
    cmds = ["configure terminal"]
    cur = ""
    for m in missing:
        ctx, line = re.match(r"\[(.*?)\] (.*)", m).groups()
        ctx = "" if ctx == "global" else ctx
        if ctx != cur:
            if cur:
                cmds.append("exit")
            if ctx:
                cmds.append(ctx)
            cur = ctx
        cmds.append(line)
    if cur:
        cmds.append("exit")
    cmds += ["end", "write memory"]
    return [c for i, c in enumerate(cmds) if i == 0 or c != cmds[i - 1]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("device")
    ap.add_argument("running", help="a `show running-config` kimenet szövegfájlban")
    ap.add_argument("--inventory", default=str(generate.ROOT / "inventory" / "network.yml"))
    ap.add_argument("--secrets", default=str(generate.ROOT / "inventory" / "secrets.yml"))
    ap.add_argument("--strict", action="store_true", help="a leírásokat (description) és a `logging buffered` sort is ellenőrzi")
    ap.add_argument("--commands", action="store_true", help="JSON-ban kiírja a hiányzó sorok bevitelére szolgáló parancsokat")
    ap.add_argument("--show-extra", action="store_true", help="a futó konfig azon sorai is, amiket a generátor nem ír")
    args = ap.parse_args(argv)

    model = generate.Model(generate.load_yaml(Path(args.inventory)), generate.load_yaml(Path(args.secrets)))
    devs = {d["hostname"]: d for d in model.devices()}
    if args.device not in devs:
        print(f"nincs ilyen eszköz: {args.device}", file=sys.stderr)
        return 2
    gen_text = generate.render(generate.make_env(), devs[args.device])
    run_text = Path(args.running).read_text(encoding="utf-8")

    missing = compare(gen_text, run_text, strict=args.strict)
    if args.commands:
        import json
        print(json.dumps(to_commands(missing), ensure_ascii=False))
        return 1 if missing else 0
    if missing:
        print(f"{args.device}: {len(missing)} generált sor hiányzik a futó konfigból:")
        for m in missing:
            print("  -", m)
    else:
        print(f"{args.device}: a generált konfig minden sora megvan a futó konfigban")

    if args.show_extra:
        gen_set = set(normalize(gen_text))
        extra = [(c, l) for c, l in normalize(run_text) if (c, l) not in gen_set
                 and not any(re.search(p, l) for p in IGNORE)]
        print(f"\nA futó konfigban van, de a generátor nem írja ({len(extra)} sor):")
        for c, l in extra:
            print(f"  + [{c or 'global'}] {l}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())

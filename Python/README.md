# Uroborosz konfiggenerátor

Az `inventory/network.yml` (hálózati modell) és az `inventory/secrets.yml` (jelszavak)
alapján Jinja2 sablonokból előállítja mind a 14 eszköz IOS/ASA konfigját.

## Használat
    pip install pyyaml jinja2 pytest
    python generate.py --check            # inventory-ellenőrzés (IP-ütközés, VLAN-hivatkozás, titkok)
    python generate.py --list             # eszközök listája
    python generate.py                    # out/<telephely>/<eszköz>.cfg
    python generate.py --device R-BP      # egyetlen eszköz
    python verify.py R-DEB tests/fixtures/R-DEB.txt   # generált vs. futó konfig
    pytest                                # tesztek

## Felépítés
- `inventory/network.yml` – VLAN-ok, telephelyek, tunnelek, core, ASA, switchek
- `inventory/secrets.yml` – labor jelszavak (gitignore!); sablon: `secrets.example.yml`
- `templates/*.j2` – eszköztípusonként egy sablon + `_macros.j2`
- `verify.py` – sorrendfüggetlen összevetés `show running-config` mentéssel

## Új telephely
Új blokk a `sites:` alatt (wan, tunnel, vlans, ospf_router_id), a hub-oldali
`hub_if`/`hub_seq`/`hub_acl` egyedi legyen; `--check` jelzi az ütközést.
Megjegyzés: a `secrets.yml` a labor értékeit tartalmazza, éles használatra cserélendő.

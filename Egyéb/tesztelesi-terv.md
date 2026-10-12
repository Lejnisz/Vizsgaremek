# Uroborosz – tesztelési terv (labor, Packet Tracer 8.2.2)

Minden teszthez: **parancs → várt eredmény**. A `show` parancsok enable módban futnak (`enable`, jelszó: `Uro#Enable2026`).
Lépések a PC-ken: Desktop → Command Prompt (vagy `pt_pc_command`). A sikeres teszteket jelöld be a végén lévő összesítőben.

> A PC-k pontos címe a DHCP-től függ (pl. PC-SOC 10.1.10.x, PC-DEV 10.1.20.x). A web szerver neve a DNS-ben beállított név, ha nincs, használd a 10.1.100.10 címet.

## 0. Előkészítés
| # | Teszt | Parancs | Várt |
|---|---|---|---|
| 0.1 | Mentett konfig megvan | `show startup-config \| include hostname` | az eszköz neve |
| 0.2 | Minden interfész felállt | `show ip interface brief` | használt portok `up/up` |
| 0.3 | Idő/naplózás | `show logging \| include 10.1.30.20` | syslog host szerepel |

## 1. L1/L2 – kapcsolatok, VLAN, STP, EtherChannel
| # | Teszt | Eszköz | Parancs | Várt |
|---|---|---|---|---|
| 1.1 | VLAN-ok | SW-A1, Core-1 | `show vlan brief` | 10,20,30,40,50,60,99,254 megvan; használt portok a megfelelő VLAN-ban |
| 1.2 | Trönkök | Core-1 | `show interfaces trunk` | Gi1/0/1, 1/0/2, Po1 trönk, natív VLAN 99 |
| 1.3 | LACP | Core-1 | `show etherchannel summary` | Po1 `(SU)`, Gi1/0/23-24 `(P)` |
| 1.4 | STP root | Core-1 / Core-2 | `show spanning-tree summary` , `show spanning-tree vlan 10` | Core-1 root a 10,30,50,254 VLAN-okon; Core-2 a 20,40,60-on; mód: rapid-pvst |
| 1.5 | Port-security | SW-A1 | `show port-security interface fa0/1` | enabled, max 2, violation restrict |
| 1.6 | DHCP snooping | SW-A1 | `show ip dhcp snooping` | VLAN 10,20,50,60 engedélyezve; Gi0/1-2 trusted |
| 1.7 | Használaton kívüli portok | SW-A1 | `show interfaces status` | Fa0/5-24 `disabled`, VLAN 99 |

## 2. Gateway redundancia (HSRP)
| # | Teszt | Parancs | Várt |
|---|---|---|---|
| 2.1 | Állapot | Core-1: `show standby brief` | Active: VLAN 10,30,50,254; Standby: 20,40,60 |
| 2.2 | Állapot | Core-2: `show standby brief` | fordítva |
| 2.3 | **Failover** | PC-SOC: `ping -t 10.1.30.10`; Core-1-en `configure terminal` → `interface vlan 10` → `shutdown` | legfeljebb 1-3 kihagyott ping, utána újra válaszol (Core-2 átveszi) |
| 2.4 | Visszaállás | Core-1: `no shutdown` | Core-1 preempt miatt visszaveszi az Active szerepet |
| 2.5 | Core kiesés | Core-1 egyik uplinkjét/portját `shutdown` | a forgalom Core-2-n át megy (`tracert 10.1.30.10`) |

## 3. DHCP
| # | Teszt | Parancs | Várt |
|---|---|---|---|
| 3.1 | HQ kliens | PC-SOC: `ipconfig /renew` majd `ipconfig` | 10.1.10.21+ cím, GW 10.1.10.1, DNS 10.1.30.10 |
| 3.2 | DEV VLAN | PC-DEV: `ipconfig /renew` | 10.1.20.x |
| 3.3 | Vendég Wi-Fi | vendég kliens: `ipconfig` | 10.1.60.x, DNS 8.8.8.8 |
| 3.4 | Telephely | PC-DEB: `ipconfig /renew` | 10.2.40.21+ (R-DEB helyi pool; .1-.20 kizárva) |
| 3.5 | Relay | Core-1: `show running-config interface vlan 10` | `ip helper-address 10.1.30.10` |

## 4. Útválasztás (OSPF, statikus, IPv6)
| # | Teszt | Eszköz | Parancs | Várt |
|---|---|---|---|---|
| 4.1 | OSPF szomszédok | R-BP | `show ip ospf neighbor` | R-DEB, R-GYR, R-UGY `FULL` (Tunnel0/1/2 + Serial0/0/0 a DEB felé) |
| 4.2 | OSPF útvonalak | R-BP | `show ip route ospf` | 10.2.0.0/16, 10.3.0.0/16, 10.4.0.0/16 |
| 4.3 | Alapértelmezett út | R-DEB | `show ip route` | `S* 0.0.0.0/0 via 203.0.113.5` |
| 4.4 | Core alapút | Core-1 | `show ip route 0.0.0.0` | via 10.1.254.4 (ASA) |
| 4.5 | Telephely ↔ HQ | PC-DEB: `ping 10.1.30.10` | 0% veszteség |
| 4.6 | Telephely ↔ telephely | PC-DEB: `ping <PC-GYR IP>` | siker (HQ-n keresztül) |
| 4.7 | IPv6 | R-BP: `ping 2001:DB8:FFFF:2::2` , `show ipv6 route` | siker; ::/0 statikus |

## 5. Alagutak (GRE over IPsec)
| # | Teszt | Eszköz | Parancs | Várt |
|---|---|---|---|---|
| 5.1 | ISAKMP SA | R-BP | `show crypto isakmp sa` | 3 db `QM_IDLE` (203.0.113.6 / .10 / .14) |
| 5.2 | IPsec SA | R-BP | `show crypto ipsec sa \| include pkts` | titkosított/visszafejtett számlálók nőnek |
| 5.3 | Tunnel állapot | R-BP | `show interfaces tunnel 0` | `up, line protocol up` |
| 5.4 | Alagút ping | R-BP | `ping 172.16.0.2` , `ping 172.16.0.6` , `ping 172.16.0.10` | `!!!!!` |
| 5.5 | Forgalom titkosítva | R-BP | előtte `clear crypto isakmp`, majd PC-DEB ping, `show crypto ipsec sa` | `#pkts encrypt` nő |
| 5.6 | Elakadás javítása (ha kell) | WAN interfész | `no crypto map CM` → `crypto map CM` | SA újra felépül |

## 6. Tartalék kapcsolat (PPP/CHAP)
| # | Teszt | Parancs | Várt |
|---|---|---|---|
| 6.1 | Soros link | R-BP: `show interfaces serial0/0/0` | `Encapsulation PPP`, LCP Open, CHAP |
| 6.2 | Szomszéd | R-BP: `show ip ospf neighbor` | R-DEB `FULL` Serial0/0/0-n is |
| 6.3 | **Failover** | R-BP: `interface fa0/0` → `shutdown`, PC-DEB: `ping 10.1.30.10` | a ping a soros linken át él, `show ip route 10.2.0.0` → Serial0/0/0 |
| 6.4 | Visszaállás | R-BP: `no shutdown` | alagutak visszajönnek (szükség esetén 5.6) |
| 6.5 | CHAP hiba | R-DEB soros: jelszó átírása, majd `debug ppp authentication` | CHAP sikertelen; visszaírva helyreáll |

## 7. NAT
| # | Teszt | Parancs | Várt |
|---|---|---|---|
| 7.1 | PAT | PC-SOC: `ping 192.0.2.10` (INET-SRV), R-BP: `show ip nat translations` | 10.1.x → 203.0.113.2 (overload) |
| 7.2 | Vendég pool | vendég kliens → INET-SRV, `show ip nat translations` | 10.1.60.x → 198.51.100.3-6 |
| 7.3 | Statikus NAT | INET-SRV/PC-HOME: böngésző → `http://198.51.100.2` | DMZ web oldal betölt |
| 7.4 | Statisztika | R-BP: `show ip nat statistics` | hits/misses nőnek |

## 8. Tűzfal (ASA)
| # | Teszt | Parancs | Várt |
|---|---|---|---|
| 8.1 | Interfészek | ASA: `show interface ip brief` | outside 10.1.255.2, inside 10.1.254.4, dmz 10.1.100.1 |
| 8.2 | Inside → DMZ | PC-SOC böngésző: `http://10.1.100.10` | betölt |
| 8.3 | DMZ → inside tiltva | DMZ szerverről `ping 10.1.10.21` | **nincs válasz** (DMZ-IN deny) |
| 8.4 | Kívülről a web | PC-HOME: `http://198.51.100.2` | betölt (443/80 engedélyezve) |
| 8.5 | Kívülről belső tiltva | INET-SRV: `ping 10.1.30.10` | nincs válasz |
| 8.6 | Hitcount | ASA: `show access-list OUTSIDE-IN` , `show access-list DMZ-IN` | számlálók nőnek a fenti tesztekre |
| 8.7 | Inspect | ASA: `show service-policy` | icmp, dns, ftp, tftp |
| 8.8 | SSH | PC a 10.1.40.0/24-ből: `ssh -l admin 10.1.254.4` | belép; másik hálózatból nem |

## 9. Távmunkás VPN
| # | Teszt | Parancs | Várt |
|---|---|---|---|
| 9.1 | Kapcsolódás | PC-HOME → Desktop → VPN: cím 203.0.113.2, csoport `UROVPN`, kulcs `UroVpn#Remote2026`, felhasználó `vpnuser` / `Uro#Vpn2026` | „VPN is running”, IP a 10.9.0.10-50 közül |
| 9.2 | Szerverhálózat | PC-HOME: `ping 10.1.30.10` | siker |
| 9.3 | Munkamenet | R-BP: `show crypto isakmp sa` , `show crypto session` | a dinamikus (DYN) munkamenet látszik |
| 9.4 | Rossz jelszó | VPN rossz jelszóval | elutasítva |

## 10. Biztonság és menedzsment
| # | Teszt | Parancs | Várt |
|---|---|---|---|
| 10.1 | SSH engedett | Menedzsment PC (10.1.40.0/24): `ssh -l admin 10.1.254.2` | belép (`Uro#Admin2026`) |
| 10.2 | SSH tiltott | PC-SOC: `ssh -l admin 10.1.254.2` | kapcsolat elutasítva (MGMT-ACL) |
| 10.3 | Telnet tiltva | menedzsment PC: `telnet 10.1.254.2` | elutasítva |
| 10.4 | Enable jelszó | konzol: `enable` | kér jelszót (`Uro#Enable2026`) |
| 10.5 | Titkosított jelszavak | `show running-config \| include secret` | `secret 5 ...`, nem olvasható szöveg |
| 10.6 | Banner | bejelentkezéskor | „Uroborosz Biztonsag Kft. - csak jogosult hasznalat” |
| 10.7 | Block-for | R-BP: 5 rossz SSH belépés 60 mp-en belül | 120 mp-re tilt (`show login`) |
| 10.8 | WAN-IN ACL | R-DEB: `show ip access-lists WAN-IN` | spoofing (RFC1918 forrás) hitcount |
| 10.9 | Vendég elszigetelés | vendég kliens: `ping 10.1.30.10` | nincs válasz (GUEST-IN) |
| 10.10 | Port-security | SW-A1 Fa0/1-re 3. MAC csatlakoztatása | `show port-security interface fa0/1` → violation count nő, a port nem áll le (restrict) |
| 10.11 | BPDU guard | access portra switch csatlakoztatása | port err-disabled |
| 10.12 | DHCP snooping | hamis DHCP szerver access porton | `show ip dhcp snooping binding` , a kliens nem kap tőle címet |

## 11. DNS és szolgáltatások
| # | Teszt | Parancs | Várt |
|---|---|---|---|
| 11.1 | Névfeloldás | PC-SOC: `nslookup <web neve>` | 10.1.100.10 |
| 11.2 | Weboldal névvel | böngésző `http://<web neve>` | betölt |
| 11.3 | Syslog | bármely eszközön konfigváltozás, majd a syslog szerveren (10.1.30.20) | üzenet érkezik |

## 12. Végső ellenőrzés és mentés
| # | Teszt | Parancs | Várt |
|---|---|---|---|
| 12.1 | Teljes mentés | minden eszközön `write memory` | `[OK]` |
| 12.2 | Konfig egyezés | `python verify.py <ESZKÖZ> <mentés.txt>` | „minden sora megvan” |
| 12.3 | Topológia mentése | PT: File → Save | `uroborosz-v1.pkt` |
| 12.4 | Újraindítás | egy router `reload`, majd 4.1, 5.1 | konfig visszajön, OSPF/IPsec felépül |

## Összesítő
| Terület | Tesztek | Eredmény |
|---|---|---|
| L2 (1) | 7 | ☐ |
| HSRP (2) | 5 | ☐ |
| DHCP (3) | 5 | ☐ |
| Routing (4) | 7 | ☐ |
| Alagutak (5) | 6 | ☐ |
| PPP/CHAP (6) | 5 | ☐ |
| NAT (7) | 4 | ☐ |
| ASA (8) | 8 | ☐ |
| Távmunkás VPN (9) | 4 | ☐ |
| Biztonság (10) | 12 | ☐ |
| DNS/Syslog (11) | 3 | ☐ |
| Mentés (12) | 4 | ☐ |

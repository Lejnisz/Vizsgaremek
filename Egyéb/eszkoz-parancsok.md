# Uroborosz – eszközparancsok (labor, Packet Tracer 8.2.2)

Eszközönként a teljes, bemásolható parancssor a konfig-generátor kimenetéből (`python generate.py`); ez egyezik az eszközökön futó,
`verify.py`-jal ellenőrzött konfiggal. Jelszavakat tartalmaz – csak laborban használd.

## Használat
1. Konzolon: `enable` → `configure terminal`, majd az eszköz blokkját másold be (egy-egy blokk teljes egészében).
2. A blokk végén van a `write memory`.
3. Ajánlott sorrend: ISP → R-BP → ASA-BP → Core-1/2 → SW-FW → SW-A1/A2 → R-DEB/R-GYR/R-UGY → telephelyi switchek.
   Az alagutak (GRE/IPsec) csak akkor jönnek fel, ha mindkét végük kész.

## Packet Tracer 8.2.2 sajátosságok
- ASA: `crypto key generate rsa` yes/no kérdésére válaszolj; `ssh version 2`, `line N`, `log` ACL-ben nem támogatott; a visszatérő ping-hez kell az `inspect icmp`.
- Alagút-elakadás módosítás után: `no crypto map CM` / `crypto map CM` a WAN interfészen.
- A WAN-IN ACL a visszafejtett forgalomra is vonatkozik, ezért a VPN-pool (10.9.0.0/24) engedélye az RFC1918 tiltás elé kerül.
- `login block-for` 2960-on nem támogatott; `no ip source-route`, `no service pad`, `no ip redirects/unreachables` PT-ben ismeretlen.
- `aaa new-model` után a konzol bejelentkezést kér: `aaa authentication login CONSOLE none` + `line con 0` / `login authentication CONSOLE`.
- Modul behelyezés (HWIC-2T) újraindítja az eszközt; soros kábelnél a topológia-eszköznek `cable: serial` kell.
- A `show running-config | include` csak enable módban működik.
- Tunnel interfészre a `description` nem támogatott; a `logging buffered` elfogadott, de nem jelenik meg a running-configban.


---

## ISP – szolgáltató (3650)

```
! ============================================================
! ISP – szolgáltató (3650-24PS, routed portok)
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname ISP
service password-encryption
no ip domain-lookup
ip domain-name isp.local
ip ssh version 2
enable secret Uro#Enable2026
username admin privilege 15 secret Uro#Admin2026
login block-for 120 attempts 5 within 60
banner motd #Uroborosz Biztonsag Kft. - csak jogosult hasznalat#
ip routing
ipv6 unicast-routing
spanning-tree mode pvst
logging buffered 16384
logging host 10.1.30.20
!
interface GigabitEthernet1/0/1
 description R-BP
 no switchport
 ip address 203.0.113.1 255.255.255.252
 ipv6 address 2001:DB8:FFFF:1::1/64
 no shutdown
interface GigabitEthernet1/0/2
 description R-DEB
 no switchport
 ip address 203.0.113.5 255.255.255.252
 ipv6 address 2001:DB8:FFFF:2::1/64
 no shutdown
interface GigabitEthernet1/0/3
 description R-GYR
 no switchport
 ip address 203.0.113.9 255.255.255.252
 ipv6 address 2001:DB8:FFFF:3::1/64
 no shutdown
interface GigabitEthernet1/0/4
 description R-UGY
 no switchport
 ip address 203.0.113.13 255.255.255.252
 ipv6 address 2001:DB8:FFFF:4::1/64
 no shutdown
interface GigabitEthernet1/0/5
 description INET-SRV
 no switchport
 ip address 192.0.2.1 255.255.255.0
 ipv6 address 2001:DB8:FFFF:5::1/64
 no shutdown
interface GigabitEthernet1/0/6
 description Tavmunkas (PC-HOME)
 no switchport
 ip address 198.18.0.1 255.255.255.0
 no shutdown
!
ip route 198.51.100.0 255.255.255.248 203.0.113.2
ipv6 route 2001:DB8:1::/48 2001:DB8:FFFF:1::2
ipv6 route 2001:DB8:2::/48 2001:DB8:FFFF:2::2
ipv6 route 2001:DB8:3::/48 2001:DB8:FFFF:3::2
ipv6 route 2001:DB8:4::/48 2001:DB8:FFFF:4::2
!
ip access-list standard MGMT-ACL
 permit 10.1.40.0 0.0.0.255
 permit 10.1.254.0 0.0.0.7
 permit 172.16.0.0 0.0.255.255
 permit 203.0.113.0 0.0.0.15

!
crypto key generate rsa modulus 1024
line vty 0 15
 access-class MGMT-ACL in
 login local
 transport input ssh
end
write memory
```

---

## R-BP – HQ router (2811)

```
! ============================================================
! R-BP – központi (Budapest) router: alagút-hub, NAT, távmunkás VPN
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname R-BP
service password-encryption
no ip domain-lookup
ip domain-name uroborosz.local
ip ssh version 2
enable secret Uro#Enable2026
username admin privilege 15 secret Uro#Admin2026
login block-for 120 attempts 5 within 60
banner motd #Uroborosz Biztonsag Kft. - csak jogosult hasznalat#
ipv6 unicast-routing
spanning-tree mode pvst
logging buffered 16384
logging host 10.1.30.20
!
! --- AAA: konzol belépés nélkül (fizikai hozzáférés), VTY helyi felhasználóval, VPN helyi adatbázissal ---
aaa new-model
aaa authentication login default local
aaa authentication login CONSOLE none
aaa authentication login VPN-AUTHN local
aaa authorization network VPN-AUTHZ local
username vpnuser secret Uro#Vpn2026
username R-DEB secret Uro#Chap2026
!
! --- IPsec: GRE-alagutak a telephelyekhez + Easy VPN szerver a távmunkásoknak ---
crypto isakmp policy 10
 encr aes 256
 authentication pre-share
 group 5
crypto isakmp key UroVpn#2026 address 203.0.113.6
crypto isakmp key UroVpn#2026 address 203.0.113.10
crypto isakmp key UroVpn#2026 address 203.0.113.14
crypto isakmp client configuration group UROVPN
 key UroVpn#Remote2026
 pool VPN-POOL
crypto ipsec transform-set TS esp-aes 256 esp-sha-hmac
crypto dynamic-map DYN 10
 set transform-set TS
 reverse-route
crypto map CM client authentication list VPN-AUTHN
crypto map CM isakmp authorization list VPN-AUTHZ
crypto map CM client configuration address respond
access-list 101 permit gre host 203.0.113.2 host 203.0.113.6
crypto map CM 10 ipsec-isakmp
 set peer 203.0.113.6
 set transform-set TS
 match address 101
access-list 102 permit gre host 203.0.113.2 host 203.0.113.10
crypto map CM 20 ipsec-isakmp
 set peer 203.0.113.10
 set transform-set TS
 match address 102
access-list 103 permit gre host 203.0.113.2 host 203.0.113.14
crypto map CM 30 ipsec-isakmp
 set peer 203.0.113.14
 set transform-set TS
 match address 103
crypto map CM 100 ipsec-isakmp dynamic DYN
ip local pool VPN-POOL 10.9.0.10 10.9.0.50
!
interface Tunnel0
 ip address 172.16.0.1 255.255.255.252
 mtu 1476
 tunnel source FastEthernet0/0
 tunnel destination 203.0.113.6
interface Tunnel1
 ip address 172.16.0.5 255.255.255.252
 mtu 1476
 tunnel source FastEthernet0/0
 tunnel destination 203.0.113.10
interface Tunnel2
 ip address 172.16.0.9 255.255.255.252
 mtu 1476
 tunnel source FastEthernet0/0
 tunnel destination 203.0.113.14
!
interface FastEthernet0/0
 description WAN (ISP)
 ip address 203.0.113.2 255.255.255.252
 ipv6 address 2001:DB8:FFFF:1::2/64
 no ip proxy-arp
 no cdp enable
 ip nat outside
 ip access-group WAN-IN in
 crypto map CM
!
interface FastEthernet0/1
 description ASA outside
 ip address 10.1.255.1 255.255.255.252
 ipv6 address 2001:DB8:1:FF::1/64
 ip nat inside
!
interface Serial0/0/0
 description PPP-CHAP backup link to R-DEB
 bandwidth 64
 ip address 172.16.1.1 255.255.255.252
 encapsulation ppp
 ppp authentication chap
 clock rate 64000
 no shutdown
!
router ospf 1
 router-id 1.1.1.1
 log-adjacency-changes
 redistribute static subnets
 network 172.16.0.0 0.0.0.255 area 0
 network 172.16.1.0 0.0.0.3 area 0
!
! --- NAT: statikus (DMZ web), dinamikus pool (vendég Wi-Fi), PAT (belső hálók) ---
ip nat inside source static 10.1.100.10 198.51.100.2
ip nat pool GUEST 198.51.100.3 198.51.100.6 netmask 255.255.255.248
ip nat inside source list 60 pool GUEST
ip nat inside source list 50 interface FastEthernet0/0 overload
access-list 60 permit 10.1.60.0 0.0.0.255
access-list 50 deny 10.1.60.0 0.0.0.255
access-list 50 permit 10.1.0.0 0.0.255.255
!
ip route 0.0.0.0 0.0.0.0 203.0.113.1
ip route 10.1.0.0 255.255.0.0 10.1.255.2
ipv6 route ::/0 2001:DB8:FFFF:1::1
ipv6 route 2001:DB8:1::/48 2001:DB8:1:FF::2
!
ip access-list extended WAN-IN
 permit ip 10.9.0.0 0.0.0.255 any
 deny ip 10.0.0.0 0.255.255.255 any
 deny ip 172.16.0.0 0.15.255.255 any
 deny ip 192.168.0.0 0.0.255.255 any
 deny ip 127.0.0.0 0.255.255.255 any
 permit ip any any
ip access-list extended VPN-SPLIT
 permit ip 10.1.30.0 0.0.0.255 any
 permit ip 10.1.100.0 0.0.0.255 any
ip access-list standard MGMT-ACL
 permit 10.1.40.0 0.0.0.255
 permit 10.1.254.0 0.0.0.7
 permit 172.16.0.0 0.0.255.255

!
crypto key generate rsa modulus 1024
line con 0
 login authentication CONSOLE
line vty 0 15
 access-class MGMT-ACL in
 transport input ssh
end
write memory
```

---

## ASA-BP – tűzfal (5506-X)

```
! ============================================================
! ASA-BP – ASA 5506-X (PT 8.2.2 / ASA 9.6(1) CLI)
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname ASA-BP
domain-name uroborosz.local
enable password Uro#Enable2026
!
interface GigabitEthernet1/1
 nameif outside
 security-level 0
 ip address 10.1.255.2 255.255.255.252
 ipv6 address 2001:DB8:1:FF::2/64
 no shutdown
interface GigabitEthernet1/2
 nameif inside
 security-level 100
 ip address 10.1.254.4 255.255.255.248
 ipv6 address 2001:DB8:1:254::4/64
 no shutdown
interface GigabitEthernet1/3
 nameif dmz
 security-level 50
 ip address 10.1.100.1 255.255.255.0
 ipv6 address 2001:DB8:1:100::1/64
 no shutdown
interface GigabitEthernet1/4
 no nameif
 no security-level
 no ip address
 shutdown
interface GigabitEthernet1/5
 no nameif
 no security-level
 no ip address
 shutdown
interface GigabitEthernet1/6
 no nameif
 no security-level
 no ip address
 shutdown
interface GigabitEthernet1/7
 no nameif
 no security-level
 no ip address
 shutdown
interface GigabitEthernet1/8
 no nameif
 no security-level
 no ip address
 shutdown
interface Management1/1
 management-only
 no nameif
 no security-level
 no ip address
 shutdown
!
route outside 0.0.0.0 0.0.0.0 10.1.255.1 1
route inside 10.1.0.0 255.255.0.0 10.1.254.1 1
route outside 10.2.0.0 255.254.0.0 10.1.255.1 1
route outside 10.4.0.0 255.255.0.0 10.1.255.1 1
ipv6 route outside ::/0 2001:DB8:1:FF::1
ipv6 route inside 2001:DB8:1::/48 2001:DB8:1:254::2
!
access-list OUTSIDE-IN extended permit tcp any host 10.1.100.10 eq 443
access-list OUTSIDE-IN extended permit tcp any host 10.1.100.10 eq www
access-list OUTSIDE-IN extended permit ip 10.2.0.0 255.254.0.0 10.1.0.0 255.255.0.0
access-list OUTSIDE-IN extended permit ip 10.4.0.0 255.255.0.0 10.1.0.0 255.255.0.0
access-list OUTSIDE-IN extended permit icmp any host 10.1.100.10 echo
access-list OUTSIDE-IN extended permit ip 10.9.0.0 255.255.255.0 10.1.30.0 255.255.255.0
access-list DMZ-IN extended permit icmp host 10.1.100.10 10.1.0.0 255.255.0.0 echo-reply
access-list DMZ-IN extended permit tcp host 10.1.100.10 eq www 10.1.0.0 255.255.0.0
access-list DMZ-IN extended permit tcp host 10.1.100.10 eq 443 10.1.0.0 255.255.0.0
access-list DMZ-IN extended deny ip 10.1.100.0 255.255.255.0 10.1.0.0 255.255.0.0
access-list DMZ-IN extended permit ip any any
access-group OUTSIDE-IN in interface outside
access-group DMZ-IN in interface dmz
!
! --- Állapottartó vizsgálat (a PT-ASA ICMP válaszokat csak inspect icmp mellett enged vissza) ---
policy-map type inspect dns preset_dns_map
 parameters
  message-length maximum 512
policy-map global_policy
 class inspection_default
  inspect dns preset_dns_map
  inspect ftp
  inspect icmp
  inspect tftp
service-policy global_policy global
!
! --- Menedzsment: SSH csak a menedzsment hálóról, helyi felhasználóval ---
username admin password Uro#Admin2026
aaa authentication ssh console LOCAL
ssh 10.1.40.0 255.255.255.0 inside
ssh timeout 5
! A kulcsgenerálás interaktív (yes/no kérdést adhat): crypto key generate rsa modulus 1024
end
write memory
```

---

## Core-1 (3650)

```
! ============================================================
! Core-1 – HQ core (3650-24PS): HSRP v2, Rapid-PVST, LACP Port-channel1
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname Core-1
service password-encryption
no ip domain-lookup
ip domain-name uroborosz.local
ip ssh version 2
enable secret Uro#Enable2026
username admin privilege 15 secret Uro#Admin2026
login block-for 120 attempts 5 within 60
banner motd #Uroborosz Biztonsag Kft. - csak jogosult hasznalat#
ip routing
ipv6 unicast-routing
logging buffered 16384
logging host 10.1.30.20
!
vlan 10
 name SOC
vlan 20
 name DEV
vlan 30
 name SERVERS
vlan 40
 name MGMT
vlan 50
 name WIFI-STAFF
vlan 60
 name WIFI-GUEST
vlan 99
 name PARKING
vlan 254
 name TRANSIT
!
spanning-tree mode rapid-pvst
spanning-tree vlan 10,30,50,254 priority 24576
spanning-tree vlan 20,40,60 priority 28672
!
interface Port-channel1
 description Core-Core
 switchport trunk native vlan 99
 switchport mode trunk
interface GigabitEthernet1/0/23
 description Core-Core LACP
 switchport trunk native vlan 99
 switchport mode trunk
 channel-group 1 mode active
interface GigabitEthernet1/0/24
 description Core-Core LACP
 switchport trunk native vlan 99
 switchport mode trunk
 channel-group 1 mode active
interface GigabitEthernet1/0/1
 description SW-A1
 switchport trunk native vlan 99
 switchport mode trunk
interface GigabitEthernet1/0/2
 description SW-A2
 switchport trunk native vlan 99
 switchport mode trunk
interface GigabitEthernet1/0/3
 description SW-FW
 switchport access vlan 254
 switchport mode access
!
interface Vlan10
 description SOC
 ip address 10.1.10.2 255.255.255.0
 ip helper-address 10.1.30.10
 ipv6 address 2001:DB8:1:10::2/64
 standby version 2
 standby 10 ip 10.1.10.1
 standby 10 priority 110
 standby 10 preempt
interface Vlan20
 description DEV
 ip address 10.1.20.2 255.255.255.0
 ip helper-address 10.1.30.10
 ipv6 address 2001:DB8:1:20::2/64
 standby version 2
 standby 20 ip 10.1.20.1
 standby 20 preempt
interface Vlan30
 description SERVERS
 ip address 10.1.30.2 255.255.255.0
 ipv6 address 2001:DB8:1:30::2/64
 standby version 2
 standby 30 ip 10.1.30.1
 standby 30 priority 110
 standby 30 preempt
interface Vlan40
 description MGMT
 ip address 10.1.40.2 255.255.255.0
 ip helper-address 10.1.30.10
 ipv6 address 2001:DB8:1:40::2/64
 standby version 2
 standby 40 ip 10.1.40.1
 standby 40 preempt
interface Vlan50
 description WIFI-STAFF
 ip address 10.1.50.2 255.255.255.0
 ip helper-address 10.1.30.10
 ipv6 address 2001:DB8:1:50::2/64
 standby version 2
 standby 50 ip 10.1.50.1
 standby 50 priority 110
 standby 50 preempt
interface Vlan60
 description WIFI-GUEST
 ip address 10.1.60.2 255.255.255.0
 ip helper-address 10.1.30.10
 ip access-group GUEST-IN in
 ipv6 address 2001:DB8:1:60::2/64
 standby version 2
 standby 60 ip 10.1.60.1
 standby 60 preempt
interface Vlan254
 description TRANSIT
 ip address 10.1.254.2 255.255.255.248
 ipv6 address 2001:DB8:1:254::2/64
 standby version 2
 standby 254 ip 10.1.254.1
 standby 254 priority 110
 standby 254 preempt
!
ip route 0.0.0.0 0.0.0.0 10.1.254.4
ipv6 route ::/0 2001:DB8:1:254::4
!
ip access-list extended GUEST-IN
 deny ip 10.1.60.0 0.0.0.255 10.0.0.0 0.255.255.255
 permit ip any any
ip access-list standard MGMT-ACL
 permit 10.1.40.0 0.0.0.255
 permit 10.1.254.0 0.0.0.7
 permit 172.16.0.0 0.0.255.255

!
crypto key generate rsa modulus 1024
line vty 0 15
 access-class MGMT-ACL in
 login local
 transport input ssh
end
write memory
```

---

## Core-2 (3650)

```
! ============================================================
! Core-2 – HQ core (3650-24PS): HSRP v2, Rapid-PVST, LACP Port-channel1
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname Core-2
service password-encryption
no ip domain-lookup
ip domain-name uroborosz.local
ip ssh version 2
enable secret Uro#Enable2026
username admin privilege 15 secret Uro#Admin2026
login block-for 120 attempts 5 within 60
banner motd #Uroborosz Biztonsag Kft. - csak jogosult hasznalat#
ip routing
ipv6 unicast-routing
logging buffered 16384
logging host 10.1.30.20
!
vlan 10
 name SOC
vlan 20
 name DEV
vlan 30
 name SERVERS
vlan 40
 name MGMT
vlan 50
 name WIFI-STAFF
vlan 60
 name WIFI-GUEST
vlan 99
 name PARKING
vlan 254
 name TRANSIT
!
spanning-tree mode rapid-pvst
spanning-tree vlan 20,40,60 priority 24576
spanning-tree vlan 10,30,50,254 priority 28672
!
interface Port-channel1
 description Core-Core
 switchport trunk native vlan 99
 switchport mode trunk
interface GigabitEthernet1/0/23
 description Core-Core LACP
 switchport trunk native vlan 99
 switchport mode trunk
 channel-group 1 mode active
interface GigabitEthernet1/0/24
 description Core-Core LACP
 switchport trunk native vlan 99
 switchport mode trunk
 channel-group 1 mode active
interface GigabitEthernet1/0/1
 description SW-A1
 switchport trunk native vlan 99
 switchport mode trunk
interface GigabitEthernet1/0/2
 description SW-A2
 switchport trunk native vlan 99
 switchport mode trunk
interface GigabitEthernet1/0/3
 description SW-FW
 switchport access vlan 254
 switchport mode access
!
interface Vlan10
 description SOC
 ip address 10.1.10.3 255.255.255.0
 ip helper-address 10.1.30.10
 ipv6 address 2001:DB8:1:10::3/64
 standby version 2
 standby 10 ip 10.1.10.1
 standby 10 preempt
interface Vlan20
 description DEV
 ip address 10.1.20.3 255.255.255.0
 ip helper-address 10.1.30.10
 ipv6 address 2001:DB8:1:20::3/64
 standby version 2
 standby 20 ip 10.1.20.1
 standby 20 priority 110
 standby 20 preempt
interface Vlan30
 description SERVERS
 ip address 10.1.30.3 255.255.255.0
 ipv6 address 2001:DB8:1:30::3/64
 standby version 2
 standby 30 ip 10.1.30.1
 standby 30 preempt
interface Vlan40
 description MGMT
 ip address 10.1.40.3 255.255.255.0
 ip helper-address 10.1.30.10
 ipv6 address 2001:DB8:1:40::3/64
 standby version 2
 standby 40 ip 10.1.40.1
 standby 40 priority 110
 standby 40 preempt
interface Vlan50
 description WIFI-STAFF
 ip address 10.1.50.3 255.255.255.0
 ip helper-address 10.1.30.10
 ipv6 address 2001:DB8:1:50::3/64
 standby version 2
 standby 50 ip 10.1.50.1
 standby 50 preempt
interface Vlan60
 description WIFI-GUEST
 ip address 10.1.60.3 255.255.255.0
 ip helper-address 10.1.30.10
 ip access-group GUEST-IN in
 ipv6 address 2001:DB8:1:60::3/64
 standby version 2
 standby 60 ip 10.1.60.1
 standby 60 priority 110
 standby 60 preempt
interface Vlan254
 description TRANSIT
 ip address 10.1.254.3 255.255.255.248
 ipv6 address 2001:DB8:1:254::3/64
 standby version 2
 standby 254 ip 10.1.254.1
 standby 254 preempt
!
ip route 0.0.0.0 0.0.0.0 10.1.254.4
ipv6 route ::/0 2001:DB8:1:254::4
!
ip access-list extended GUEST-IN
 deny ip 10.1.60.0 0.0.0.255 10.0.0.0 0.255.255.255
 permit ip any any
ip access-list standard MGMT-ACL
 permit 10.1.40.0 0.0.0.255
 permit 10.1.254.0 0.0.0.7
 permit 172.16.0.0 0.0.255.255

!
crypto key generate rsa modulus 1024
line vty 0 15
 access-class MGMT-ACL in
 login local
 transport input ssh
end
write memory
```

---

## SW-FW (2960)

```
! ============================================================
! SW-FW – access switch (2960-24TT), Budapest (központ)
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname SW-FW
service password-encryption
no ip domain-lookup
ip domain-name uroborosz.local
ip ssh version 2
enable secret Uro#Enable2026
username admin privilege 15 secret Uro#Admin2026
banner motd #Uroborosz Biztonsag Kft. - csak jogosult hasznalat#
logging buffered 16384
logging host 10.1.30.20
!
vlan 99
 name PARKING
vlan 254
 name TRANSIT
!
spanning-tree mode pvst
!
interface FastEthernet0/1
 switchport access vlan 254
 switchport mode access
 spanning-tree portfast
interface FastEthernet0/2
 switchport access vlan 254
 switchport mode access
 spanning-tree portfast
interface FastEthernet0/3
 switchport access vlan 254
 switchport mode access
 spanning-tree portfast
interface FastEthernet0/4
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/5
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/6
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/7
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/8
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/9
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/10
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/11
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/12
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/13
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/14
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/15
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/16
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/17
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/18
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/19
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/20
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/21
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/22
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/23
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/24
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
!
!
ip access-list standard MGMT-ACL
 permit 10.1.40.0 0.0.0.255
 permit 10.1.254.0 0.0.0.7
 permit 172.16.0.0 0.0.255.255

!
crypto key generate rsa modulus 1024
line vty 0 15
 access-class MGMT-ACL in
 login local
 transport input ssh
end
write memory
```

---

## SW-A1 (2960)

```
! ============================================================
! SW-A1 – access switch (2960-24TT), Budapest (központ)
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname SW-A1
service password-encryption
no ip domain-lookup
ip domain-name uroborosz.local
ip ssh version 2
enable secret Uro#Enable2026
username admin privilege 15 secret Uro#Admin2026
banner motd #Uroborosz Biztonsag Kft. - csak jogosult hasznalat#
logging buffered 16384
logging host 10.1.30.20
!
vlan 10
 name SOC
vlan 20
 name DEV
vlan 40
 name MGMT
vlan 50
 name WIFI-STAFF
vlan 60
 name WIFI-GUEST
vlan 99
 name PARKING
!
spanning-tree mode rapid-pvst
ip dhcp snooping vlan 10,20,50,60
no ip dhcp snooping information option
ip dhcp snooping
!
interface FastEthernet0/1
 switchport access vlan 10
 switchport mode access
 switchport port-security
 switchport port-security maximum 2
 switchport port-security violation restrict
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/2
 switchport access vlan 20
 switchport mode access
 switchport port-security
 switchport port-security maximum 2
 switchport port-security violation restrict
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/3
 switchport access vlan 50
 switchport mode access
 switchport port-security
 switchport port-security maximum 10
 switchport port-security violation restrict
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/4
 switchport access vlan 60
 switchport mode access
 switchport port-security
 switchport port-security maximum 10
 switchport port-security violation restrict
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/5
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/6
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/7
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/8
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/9
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/10
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/11
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/12
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/13
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/14
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/15
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/16
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/17
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/18
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/19
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/20
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/21
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/22
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/23
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/24
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
!
interface GigabitEthernet0/1
 description trunk
 switchport trunk native vlan 99
 switchport mode trunk
 ip dhcp snooping trust
interface GigabitEthernet0/2
 description trunk
 switchport trunk native vlan 99
 switchport mode trunk
 ip dhcp snooping trust
!
interface Vlan40
 ip address 10.1.40.11 255.255.255.0
 no shutdown
ip default-gateway 10.1.40.1
ip access-list standard MGMT-ACL
 permit 10.1.40.0 0.0.0.255
 permit 10.1.254.0 0.0.0.7
 permit 172.16.0.0 0.0.255.255

!
crypto key generate rsa modulus 1024
line vty 0 15
 access-class MGMT-ACL in
 login local
 transport input ssh
end
write memory
```

---

## SW-A2 (2960)

```
! ============================================================
! SW-A2 – access switch (2960-24TT), Budapest (központ)
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname SW-A2
service password-encryption
no ip domain-lookup
ip domain-name uroborosz.local
ip ssh version 2
enable secret Uro#Enable2026
username admin privilege 15 secret Uro#Admin2026
banner motd #Uroborosz Biztonsag Kft. - csak jogosult hasznalat#
logging buffered 16384
logging host 10.1.30.20
!
vlan 30
 name SERVERS
vlan 40
 name MGMT
vlan 99
 name PARKING
!
spanning-tree mode rapid-pvst
!
interface FastEthernet0/1
 switchport access vlan 30
 switchport mode access
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/2
 switchport access vlan 30
 switchport mode access
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/3
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/4
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/5
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/6
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/7
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/8
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/9
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/10
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/11
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/12
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/13
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/14
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/15
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/16
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/17
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/18
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/19
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/20
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/21
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/22
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/23
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/24
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
!
interface GigabitEthernet0/1
 description trunk
 switchport trunk native vlan 99
 switchport mode trunk
interface GigabitEthernet0/2
 description trunk
 switchport trunk native vlan 99
 switchport mode trunk
!
interface Vlan40
 ip address 10.1.40.12 255.255.255.0
 no shutdown
ip default-gateway 10.1.40.1
ip access-list standard MGMT-ACL
 permit 10.1.40.0 0.0.0.255
 permit 10.1.254.0 0.0.0.7
 permit 172.16.0.0 0.0.255.255

!
crypto key generate rsa modulus 1024
line vty 0 15
 access-class MGMT-ACL in
 login local
 transport input ssh
end
write memory
```

---

## R-DEB – Debrecen router

```
! ============================================================
! R-DEB – Debrecen telephely router (Cisco 2811)
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname R-DEB
service password-encryption
no ip domain-lookup
ip domain-name uroborosz.local
ip ssh version 2
enable secret Uro#Enable2026
username admin privilege 15 secret Uro#Admin2026
login block-for 120 attempts 5 within 60
banner motd #Uroborosz Biztonsag Kft. - csak jogosult hasznalat#
ipv6 unicast-routing
spanning-tree mode pvst
logging buffered 16384
logging host 10.1.30.20
!
! --- DHCP (helyi pool-ok) ---
ip dhcp excluded-address 10.2.40.1 10.2.40.20
ip dhcp excluded-address 10.2.50.1 10.2.50.20
ip dhcp pool MGMT
 network 10.2.40.0 255.255.255.0
 default-router 10.2.40.1
 dns-server 10.1.30.10
ip dhcp pool WIFI
 network 10.2.50.0 255.255.255.0
 default-router 10.2.50.1
 dns-server 10.1.30.10
!
! --- IPsec (GRE-over-IPsec a központ felé; PT 8.2.2: crypto map a fizikai WAN porton) ---
crypto isakmp policy 10
 encr aes 256
 authentication pre-share
 group 5
crypto isakmp key UroVpn#2026 address 203.0.113.2
crypto ipsec transform-set TS esp-aes 256 esp-sha-hmac
access-list 101 permit gre host 203.0.113.6 host 203.0.113.2
crypto map CM 10 ipsec-isakmp
 set peer 203.0.113.2
 set transform-set TS
 match address 101
!
interface Tunnel0
 ip address 172.16.0.2 255.255.255.252
 mtu 1476
 tunnel source FastEthernet0/0
 tunnel destination 203.0.113.2
!
interface FastEthernet0/0
 description WAN (ISP)
 ip address 203.0.113.6 255.255.255.252
 ipv6 address 2001:DB8:FFFF:2::2/64
 no ip proxy-arp
 no cdp enable
 ip access-group WAN-IN in
 crypto map CM
!
interface FastEthernet0/1
 description LAN trunk (SW-DEB)
 no ip address
 no shutdown
interface FastEthernet0/1.30
 description SERVERS
 encapsulation dot1Q 30
 ip address 10.2.30.1 255.255.255.0
 ipv6 address 2001:DB8:2:30::1/64
interface FastEthernet0/1.40
 description MGMT
 encapsulation dot1Q 40
 ip address 10.2.40.1 255.255.255.0
 ipv6 address 2001:DB8:2:40::1/64
interface FastEthernet0/1.50
 description WIFI-STAFF
 encapsulation dot1Q 50
 ip address 10.2.50.1 255.255.255.0
 ipv6 address 2001:DB8:2:50::1/64
!
! --- PPP/CHAP tartalék soros link a központ felé ---
username R-BP secret Uro#Chap2026
interface Serial0/0/0
 description PPP-CHAP backup link to R-BP
 bandwidth 64
 ip address 172.16.1.2 255.255.255.252
 encapsulation ppp
 ppp authentication chap
 no shutdown
!
router ospf 1
 router-id 2.2.2.2
 log-adjacency-changes
 passive-interface FastEthernet0/1.30
 passive-interface FastEthernet0/1.40
 passive-interface FastEthernet0/1.50
 network 172.16.0.0 0.0.0.3 area 0
 network 10.2.0.0 0.0.255.255 area 0
 network 172.16.1.0 0.0.0.3 area 0
!
ip route 0.0.0.0 0.0.0.0 203.0.113.5
ipv6 route ::/0 2001:DB8:FFFF:2::1
!
ip access-list extended WAN-IN
 deny ip 10.0.0.0 0.255.255.255 any
 deny ip 172.16.0.0 0.15.255.255 any
 deny ip 192.168.0.0 0.0.255.255 any
 deny ip 127.0.0.0 0.255.255.255 any
 permit ip any any
ip access-list standard MGMT-ACL
 permit 10.1.40.0 0.0.0.255
 permit 10.1.254.0 0.0.0.7
 permit 172.16.0.0 0.0.255.255
 permit 10.2.40.0 0.0.0.255

!
crypto key generate rsa modulus 1024
line vty 0 15
 access-class MGMT-ACL in
 login local
 transport input ssh
end
write memory
```

---

## SW-DEB

```
! ============================================================
! SW-DEB – access switch (2960-24TT), Debrecen
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname SW-DEB
service password-encryption
no ip domain-lookup
ip domain-name uroborosz.local
ip ssh version 2
enable secret Uro#Enable2026
username admin privilege 15 secret Uro#Admin2026
banner motd #Uroborosz Biztonsag Kft. - csak jogosult hasznalat#
logging buffered 16384
logging host 10.1.30.20
!
vlan 30
 name SERVERS
vlan 40
 name MGMT
vlan 50
 name WIFI-STAFF
vlan 99
 name PARKING
!
spanning-tree mode rapid-pvst
!
interface FastEthernet0/1
 switchport access vlan 30
 switchport mode access
 switchport port-security
 switchport port-security maximum 2
 switchport port-security violation restrict
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/2
 switchport access vlan 40
 switchport mode access
 switchport port-security
 switchport port-security maximum 2
 switchport port-security violation restrict
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/3
 switchport access vlan 50
 switchport mode access
 switchport port-security
 switchport port-security maximum 10
 switchport port-security violation restrict
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/4
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/5
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/6
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/7
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/8
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/9
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/10
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/11
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/12
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/13
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/14
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/15
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/16
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/17
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/18
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/19
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/20
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/21
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/22
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/23
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/24
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
!
interface GigabitEthernet0/1
 description trunk
 switchport trunk native vlan 99
 switchport mode trunk
interface GigabitEthernet0/2
 description PARKING (tartalek uplink)
 switchport access vlan 99
 shutdown
!
ip access-list standard MGMT-ACL
 permit 10.1.40.0 0.0.0.255
 permit 10.1.254.0 0.0.0.7
 permit 172.16.0.0 0.0.255.255
 permit 10.2.40.0 0.0.0.255

!
crypto key generate rsa modulus 1024
line vty 0 15
 access-class MGMT-ACL in
 login local
 transport input ssh
end
write memory
```

---

## R-GYR – Győr router

```
! ============================================================
! R-GYR – Győr telephely router (Cisco 2811)
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname R-GYR
service password-encryption
no ip domain-lookup
ip domain-name uroborosz.local
ip ssh version 2
enable secret Uro#Enable2026
username admin privilege 15 secret Uro#Admin2026
login block-for 120 attempts 5 within 60
banner motd #Uroborosz Biztonsag Kft. - csak jogosult hasznalat#
ipv6 unicast-routing
spanning-tree mode pvst
logging buffered 16384
logging host 10.1.30.20
!
! --- DHCP (helyi pool-ok) ---
ip dhcp excluded-address 10.3.40.1 10.3.40.20
ip dhcp excluded-address 10.3.50.1 10.3.50.20
ip dhcp pool MGMT
 network 10.3.40.0 255.255.255.0
 default-router 10.3.40.1
 dns-server 10.1.30.10
ip dhcp pool WIFI
 network 10.3.50.0 255.255.255.0
 default-router 10.3.50.1
 dns-server 10.1.30.10
!
! --- IPsec (GRE-over-IPsec a központ felé; PT 8.2.2: crypto map a fizikai WAN porton) ---
crypto isakmp policy 10
 encr aes 256
 authentication pre-share
 group 5
crypto isakmp key UroVpn#2026 address 203.0.113.2
crypto ipsec transform-set TS esp-aes 256 esp-sha-hmac
access-list 101 permit gre host 203.0.113.10 host 203.0.113.2
crypto map CM 10 ipsec-isakmp
 set peer 203.0.113.2
 set transform-set TS
 match address 101
!
interface Tunnel0
 ip address 172.16.0.6 255.255.255.252
 mtu 1476
 tunnel source FastEthernet0/0
 tunnel destination 203.0.113.2
!
interface FastEthernet0/0
 description WAN (ISP)
 ip address 203.0.113.10 255.255.255.252
 ipv6 address 2001:DB8:FFFF:3::2/64
 no ip proxy-arp
 no cdp enable
 ip access-group WAN-IN in
 crypto map CM
!
interface FastEthernet0/1
 description LAN trunk (SW-GYR)
 no ip address
 no shutdown
interface FastEthernet0/1.40
 description MGMT
 encapsulation dot1Q 40
 ip address 10.3.40.1 255.255.255.0
 ipv6 address 2001:DB8:3:40::1/64
interface FastEthernet0/1.50
 description WIFI-STAFF
 encapsulation dot1Q 50
 ip address 10.3.50.1 255.255.255.0
 ipv6 address 2001:DB8:3:50::1/64
!
router ospf 1
 router-id 3.3.3.3
 log-adjacency-changes
 passive-interface FastEthernet0/1.40
 passive-interface FastEthernet0/1.50
 network 172.16.0.4 0.0.0.3 area 0
 network 10.3.0.0 0.0.255.255 area 0
!
ip route 0.0.0.0 0.0.0.0 203.0.113.9
ipv6 route ::/0 2001:DB8:FFFF:3::1
!
ip access-list extended WAN-IN
 deny ip 10.0.0.0 0.255.255.255 any
 deny ip 172.16.0.0 0.15.255.255 any
 deny ip 192.168.0.0 0.0.255.255 any
 deny ip 127.0.0.0 0.255.255.255 any
 permit ip any any
ip access-list standard MGMT-ACL
 permit 10.1.40.0 0.0.0.255
 permit 10.1.254.0 0.0.0.7
 permit 172.16.0.0 0.0.255.255
 permit 10.3.40.0 0.0.0.255

!
crypto key generate rsa modulus 1024
line vty 0 15
 access-class MGMT-ACL in
 login local
 transport input ssh
end
write memory
```

---

## SW-GYR

```
! ============================================================
! SW-GYR – access switch (2960-24TT), Győr
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname SW-GYR
service password-encryption
no ip domain-lookup
ip domain-name uroborosz.local
ip ssh version 2
enable secret Uro#Enable2026
username admin privilege 15 secret Uro#Admin2026
banner motd #Uroborosz Biztonsag Kft. - csak jogosult hasznalat#
logging buffered 16384
logging host 10.1.30.20
!
vlan 40
 name MGMT
vlan 50
 name WIFI-STAFF
vlan 99
 name PARKING
!
spanning-tree mode rapid-pvst
!
interface FastEthernet0/1
 switchport access vlan 40
 switchport mode access
 switchport port-security
 switchport port-security maximum 2
 switchport port-security violation restrict
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/2
 switchport access vlan 50
 switchport mode access
 switchport port-security
 switchport port-security maximum 10
 switchport port-security violation restrict
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/3
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/4
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/5
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/6
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/7
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/8
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/9
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/10
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/11
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/12
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/13
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/14
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/15
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/16
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/17
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/18
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/19
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/20
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/21
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/22
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/23
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/24
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
!
interface GigabitEthernet0/1
 description trunk
 switchport trunk native vlan 99
 switchport mode trunk
interface GigabitEthernet0/2
 description PARKING (tartalek uplink)
 switchport access vlan 99
 shutdown
!
ip access-list standard MGMT-ACL
 permit 10.1.40.0 0.0.0.255
 permit 10.1.254.0 0.0.0.7
 permit 172.16.0.0 0.0.255.255
 permit 10.3.40.0 0.0.0.255

!
crypto key generate rsa modulus 1024
line vty 0 15
 access-class MGMT-ACL in
 login local
 transport input ssh
end
write memory
```

---

## R-UGY – Ügyfél router

```
! ============================================================
! R-UGY – Ügyfél (mintaügyfél) telephely router (Cisco 2811)
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname R-UGY
service password-encryption
no ip domain-lookup
ip domain-name uroborosz.local
ip ssh version 2
enable secret Uro#Enable2026
username admin privilege 15 secret Uro#Admin2026
login block-for 120 attempts 5 within 60
banner motd #Uroborosz Biztonsag Kft. - csak jogosult hasznalat#
ipv6 unicast-routing
spanning-tree mode pvst
logging buffered 16384
logging host 10.1.30.20
!
! --- DHCP (helyi pool-ok) ---
ip dhcp excluded-address 10.4.40.1 10.4.40.20
ip dhcp excluded-address 10.4.70.1 10.4.70.20
ip dhcp pool MGMT
 network 10.4.40.0 255.255.255.0
 default-router 10.4.40.1
 dns-server 10.1.30.10
ip dhcp pool IOT
 network 10.4.70.0 255.255.255.0
 default-router 10.4.70.1
 dns-server 10.1.30.10
!
! --- IPsec (GRE-over-IPsec a központ felé; PT 8.2.2: crypto map a fizikai WAN porton) ---
crypto isakmp policy 10
 encr aes 256
 authentication pre-share
 group 5
crypto isakmp key UroVpn#2026 address 203.0.113.2
crypto ipsec transform-set TS esp-aes 256 esp-sha-hmac
access-list 101 permit gre host 203.0.113.14 host 203.0.113.2
crypto map CM 10 ipsec-isakmp
 set peer 203.0.113.2
 set transform-set TS
 match address 101
!
interface Tunnel0
 ip address 172.16.0.10 255.255.255.252
 mtu 1476
 tunnel source FastEthernet0/0
 tunnel destination 203.0.113.2
!
interface FastEthernet0/0
 description WAN (ISP)
 ip address 203.0.113.14 255.255.255.252
 ipv6 address 2001:DB8:FFFF:4::2/64
 no ip proxy-arp
 no cdp enable
 ip access-group WAN-IN in
 crypto map CM
!
interface FastEthernet0/1
 description LAN trunk (SW-UGY)
 no ip address
 no shutdown
interface FastEthernet0/1.40
 description MGMT
 encapsulation dot1Q 40
 ip address 10.4.40.1 255.255.255.0
 ipv6 address 2001:DB8:4:40::1/64
interface FastEthernet0/1.70
 description IOT
 encapsulation dot1Q 70
 ip address 10.4.70.1 255.255.255.0
 ipv6 address 2001:DB8:4:70::1/64
!
router ospf 1
 router-id 4.4.4.4
 log-adjacency-changes
 passive-interface FastEthernet0/1.40
 passive-interface FastEthernet0/1.70
 network 172.16.0.8 0.0.0.3 area 0
 network 10.4.0.0 0.0.255.255 area 0
!
ip route 0.0.0.0 0.0.0.0 203.0.113.13
ipv6 route ::/0 2001:DB8:FFFF:4::1
!
ip access-list extended WAN-IN
 deny ip 10.0.0.0 0.255.255.255 any
 deny ip 172.16.0.0 0.15.255.255 any
 deny ip 192.168.0.0 0.0.255.255 any
 deny ip 127.0.0.0 0.255.255.255 any
 permit ip any any
ip access-list standard MGMT-ACL
 permit 10.1.40.0 0.0.0.255
 permit 10.1.254.0 0.0.0.7
 permit 172.16.0.0 0.0.255.255
 permit 10.4.40.0 0.0.0.255

!
crypto key generate rsa modulus 1024
line vty 0 15
 access-class MGMT-ACL in
 login local
 transport input ssh
end
write memory
```

---

## SW-UGY

```
! ============================================================
! SW-UGY – access switch (2960-24TT), Ügyfél (mintaügyfél)
! Generálva az inventory-ból – kézzel ne szerkeszd.
! ============================================================
hostname SW-UGY
service password-encryption
no ip domain-lookup
ip domain-name uroborosz.local
ip ssh version 2
enable secret Uro#Enable2026
username admin privilege 15 secret Uro#Admin2026
banner motd #Uroborosz Biztonsag Kft. - csak jogosult hasznalat#
logging buffered 16384
logging host 10.1.30.20
!
vlan 40
 name MGMT
vlan 70
 name IOT
vlan 99
 name PARKING
!
spanning-tree mode rapid-pvst
!
interface FastEthernet0/1
 switchport access vlan 40
 switchport mode access
 switchport port-security
 switchport port-security maximum 2
 switchport port-security violation restrict
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/2
 switchport access vlan 70
 switchport mode access
 switchport port-security
 switchport port-security maximum 2
 switchport port-security violation restrict
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/3
 switchport access vlan 70
 switchport mode access
 switchport port-security
 switchport port-security maximum 2
 switchport port-security violation restrict
 spanning-tree portfast
 spanning-tree bpduguard enable
interface FastEthernet0/4
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/5
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/6
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/7
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/8
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/9
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/10
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/11
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/12
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/13
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/14
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/15
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/16
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/17
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/18
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/19
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/20
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/21
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/22
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/23
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
interface FastEthernet0/24
 description PARKING (nem hasznalt port)
 switchport access vlan 99
 switchport mode access
 shutdown
!
interface GigabitEthernet0/1
 description trunk
 switchport trunk native vlan 99
 switchport mode trunk
interface GigabitEthernet0/2
 description PARKING (tartalek uplink)
 switchport access vlan 99
 shutdown
!
ip access-list standard MGMT-ACL
 permit 10.1.40.0 0.0.0.255
 permit 10.1.254.0 0.0.0.7
 permit 172.16.0.0 0.0.255.255
 permit 10.4.40.0 0.0.0.255

!
crypto key generate rsa modulus 1024
line vty 0 15
 access-class MGMT-ACL in
 login local
 transport input ssh
end
write memory
```

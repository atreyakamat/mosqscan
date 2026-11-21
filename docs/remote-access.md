# Vectora AI 2.2 — Remote Field Access and Secure VPN Architecture

## 1. Security Policy Regarding Remote Access

> [!CAUTION]
> **PROHIBITION OF PUBLIC PORT FORWARDING**
> Never forward port 8000 or any internal service ports (5432, 6379) through router NAT to the public internet.
> Public exposure subjects the development machine and database to automated vulnerability scans, brute-force attacks, and unauthenticated denial-of-service threats.

All remote field communication from Android devices outside the local Wi-Fi network must route exclusively through an encrypted **WireGuard Virtual Private Network (VPN)** tunnel.

---

## 2. WireGuard Topology Overview

```
Field Device (Android Tablet/Phone)
  IP: 10.8.0.2/24 (wg0 interface)
  Vectora App Base URL: http://10.8.0.1:8000/
          │
          │ [Encrypted WireGuard UDP Tunnel via Public IP/DDNS:51820]
          ▼
Home / Lab Router (UDP 51820 forwarded to Workstation)
          │
          ▼
Development Workstation (Omarchy Linux)
  Host Physical IP: 192.168.1.120
  WireGuard Server Interface (wg0): 10.8.0.1/24
  Docker Bridge Interface: 172.18.0.1
          │
          ▼
Docker Container: vectora-backend (port 8000)
```

---

## 3. Server Configuration (Workstation)

### 3.1 Install WireGuard
```bash
sudo pacman -S wireguard-tools
```

### 3.2 Key Generation
```bash
umask 077
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
wg genkey | tee /etc/wireguard/client1_private.key | wg pubkey > /etc/wireguard/client1_public.key
```

### 3.3 Server Configuration File (`/etc/wireguard/wg0.conf`)
```ini
[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = <SERVER_PRIVATE_KEY_CONTENT>

# Restrict client traffic strictly to API port 8000
PostUp = iptables -A FORWARD -i wg0 -p tcp --dport 8000 -j ACCEPT; iptables -A FORWARD -i wg0 -j DROP
PostDown = iptables -D FORWARD -i wg0 -p tcp --dport 8000 -j ACCEPT; iptables -D FORWARD -i wg0 -j DROP

# Remote Android Field Device
[Peer]
PublicKey = <CLIENT1_PUBLIC_KEY_CONTENT>
AllowedIPs = 10.8.0.2/32
```

### 3.4 Enable and Start Interface
```bash
sudo systemctl enable --now wg-quick@wg0
```

---

## 4. Client Configuration (Android Device)

### 4.1 Install Android WireGuard Client
Install the official **WireGuard** client from Google Play Store or F-Droid (`com.wireguard.android`).

### 4.2 Client Profile (`vectora-remote.conf`)
```ini
[Interface]
PrivateKey = <CLIENT1_PRIVATE_KEY_CONTENT>
Address = 10.8.0.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = <SERVER_PUBLIC_KEY_CONTENT>
Endpoint = your-home-public-domain-or-ip.com:51820
AllowedIPs = 10.8.0.1/32
PersistentKeepalive = 25
```

> [!NOTE]
> `AllowedIPs = 10.8.0.1/32` configures split tunneling.
> Only traffic destined for the Vectora development server is routed across the VPN; standard internet traffic on the mobile device is unaffected.

---

## 5. Mobile App Configuration

Once the WireGuard tunnel is active:
1. Open **Vectora AI** on the Android device.
2. Navigate to **Settings** (`/settings`).
3. Set **Server Base URL** to:
   ```
   http://10.8.0.1:8000/
   ```
4. Tap **Test Connection**.
5. The status displays `Connected (HTTP 200)`.

---

## 6. Security Guarantees

1. **State-of-the-Art Cryptography**:
   WireGuard utilizes ChaCha20 for symmetric encryption, Poly1305 for authentication, Curve25519 for ECDH key exchange, and BLAKE2s for hashing.
2. **Stealth and Silence**:
   WireGuard does not respond to unauthenticated packets. Port scanners find port 51820 completely closed.
3. **Database and Cache Isolation**:
   The internal Docker PostgreSQL (5432) and Redis (6379) services do not publish host ports and cannot be accessed even across the VPN tunnel.

# Vectora AI 2.2 — Local Area Network (LAN) Deployment Guide

## 1. Architecture and Addressing

Vectora AI 2.2 serves inferences across the local development network.
The development workstation hosts the Dockerized FastAPI backend, and mobile devices connect directly through Wi-Fi.

- **Host Workstation IP**: `192.168.1.120`
- **Subnet**: `192.168.1.0/24`
- **Service Port**: `8000` (FastAPI / Uvicorn)
- **Base Endpoint URL**: `http://192.168.1.120:8000/`

---

## 2. Router DHCP Reservation (Static IP)

To prevent IP churn when the host workstation reboots:
1. Access the local Wi-Fi router administration page (typically `http://192.168.1.1`).
2. Navigate to **DHCP Server** -> **Address Reservation** / **Static Lease**.
3. Identify the development machine MAC address:
   ```bash
   ip link show
   ```
4. Bind the MAC address to fixed IP address `192.168.1.120`.
5. Apply and save the router configuration.

---

## 3. Docker Service Port Isolation

The root `docker-compose.yml` configures service exposure to ensure security on the LAN:

- **Backend API**:
  ```yaml
  ports:
    - "${VECTORa_API_BIND:-0.0.0.0:8000}:8000"
  ```
  Listens on all network interfaces (`0.0.0.0:8000`) so connected LAN devices can reach the REST API.
- **Database (PostgreSQL)**:
  Exposes no host ports (`ports` block removed).
  PostgreSQL communicates exclusively over the internal bridge network `vectora-network` on port 5432.
- **Cache (Redis)**:
  Exposes no host ports (`ports` block removed).
  Redis communicates exclusively over the internal bridge network `vectora-network` on port 6379.

This configuration prevents unauthorized database and cache access from untrusted devices on the local Wi-Fi network.

---

## 4. Host Linux Firewall Configuration

On Linux distributions using `ufw` or `iptables`:

### UFW Configuration
```bash
# Allow API access only from local subnet 192.168.1.0/24
sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp comment 'Vectora AI API'

# Deny external access to internal database/cache ports
sudo ufw deny 5432/tcp
sudo ufw deny 6379/tcp
sudo ufw reload
```

### Verification
```bash
sudo ufw status verbose
```

---

## 5. Android Network Security Configuration

Android 9 (API 28) and higher block unencrypted cleartext HTTP traffic by default.
To allow development and field LAN testing over `http://192.168.1.120:8000` without compromising production security, a strict network security policy is enforced in `android/app/src/main/res/xml/network_security_config.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <!-- Default policy: Strictly require HTTPS for all external traffic -->
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>

    <!-- Specific private development exceptions -->
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="false">192.168.1.120</domain>
        <domain includeSubdomains="false">10.0.2.2</domain>
        <domain includeSubdomains="false">localhost</domain>
        <domain includeSubdomains="false">127.0.0.1</domain>
    </domain-config>
</network-security-config>
```

In `android/app/src/main/AndroidManifest.xml`:
- Linked policy: `android:networkSecurityConfig="@xml/network_security_config"`.
- Removed global `android:usesCleartextTraffic="true"`.

---

## 6. Android Dynamic Endpoint Configuration

The Android client does not hardcode server addresses into compiled code.
In `SettingsScreen.kt` and `ServerClientManager.kt`:
1. Users can view and modify the current **Server Base URL**.
2. The default value is `http://192.168.1.120:8000/`.
3. Changes persist immediately in encrypted SharedPreferences.
4. Two diagnostic controls allow instant verification:
   - **Test Connection**: Calls `GET /health` to confirm HTTP reachability.
   - **Check Model Health**: Calls `GET /api/v1/models/info` to confirm model loading, checksum integrity, and model name.

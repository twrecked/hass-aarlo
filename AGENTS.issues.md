# PyArlo & Hass-Aarlo Issue Cache & Troubleshooting Knowledge Base

This file serves as a persistent diagnostic cache and troubleshooting knowledge base for both human maintainers and AI agents working in `pyaarlo` and `hass-aarlo`. It documents known error signatures, root causes, diagnostic verification steps, and proven resolutions based on historical issues.

---

## Quick Navigation

1. [Authentication & 2FA](#1-authentication--2fa)
   - [1.1 Gmail IMAP 2FA ("Application-specific password required")](#11-gmail-imap-2fa-application-specific-password-required)
   - [1.2 Error 9306: "Mfa disabled by service"](#12-error-9306-mfa-disabled-by-service)
   - [1.3 Error 9261: "Invalid factor data" / Stale Factor Cache](#13-error-9261-invalid-factor-data--stale-factor-cache)
   - [1.4 Token Expiration & Periodic HTTP 401 / Meta 9204 Errors](#14-token-expiration--periodic-http-401--meta-9204-errors)
   - [1.5 Cloudflare Bot Challenge / HTTP 403 Forbidden](#15-cloudflare-bot-challenge--http-403-forbidden)
2. [Device Discovery & Missing Hardware](#2-device-discovery--missing-hardware)
   - [2.1 "No devices returned" or "No locations returned" (ReadTimeout)](#21-no-devices-returned-or-no-locations-returned-readtimeout)
   - [2.2 Wi-Fi Direct Camera Battery & Properties Stale (Base Station Twin)](#22-wi-fi-direct-camera-battery--properties-stale-base-station-twin)
   - [2.3 Valid Cameras Filtered Out Due to "Deactivated" / "Parking" State](#23-valid-cameras-filtered-out-due-to-deactivated--parking-state)
   - [2.4 Essential Pan & Tilt Searching Continually for Base Station](#24-essential-pan--tilt-searching-continually-for-base-station)
   - [2.5 SmartHub (VMB4540/VMB5000) Connected Camera Discovery Issues](#25-smarthub-vmb4540vmb5000-connected-camera-discovery-issues)
3. [Arming & Modes (V1/V2 vs. Modern V3 Architecture)](#3-arming--modes-v1v2-vs-modern-v3-architecture)
   - [3.1 V3 Mode Desynchronization (Permanent Divergence after Stream Outage)](#31-v3-mode-desynchronization-permanent-divergence-after-stream-outage)
   - [3.2 Custom Modes Missing on Migrated V3 Accounts](#32-custom-modes-missing-on-migrated-v3-accounts)
   - [3.3 Multi-Location Account Mode Routing](#33-multi-location-account-mode-routing)
4. [Live Streaming, Snapshots, & Media](#4-live-streaming-snapshots--media)
   - [4.1 Stream Works Once, Then Fails / Permission 2016 ("No Such Permissions")](#41-stream-works-once-then-fails--permission-2016-no-such-permissions)
   - [4.2 Snapshot Fails with Error 2503 Due to Active Stream Contention](#42-snapshot-fails-with-error-2503-due-to-active-stream-contention)
   - [4.3 RTSPS vs. DASH Session Negotiation Failures (AVD2001A / AVD4001A)](#43-rtsps-vs-dash-session-negotiation-failures-avd2001a--avd4001a)
   - [4.4 SmartHub Direct Local Storage Access (RaTLS) Port Failure](#44-smarthub-direct-local-storage-access-ratls-port-failure)
5. [Configuration & Home Assistant OS Environment](#5-configuration--home-assistant-os-environment)
   - [5.1 Fragile Host & Broker Overrides in `aarlo.yaml` (`host`, `auth_host`, `mqtt_host`)](#51-fragile-host--broker-overrides-in-aarloyaml-host-auth_host-mqtt_host)
   - [5.2 Entity IDs with Special Characters (Umlauts, Accents, Hyphens)](#52-entity-ids-with-special-characters-umlauts-accents-hyphens)
   - [5.3 Temporary Directory Restrictions on Modern Home Assistant OS (`/tmp`)](#53-temporary-directory-restrictions-on-modern-home-assistant-os-tmp)
   - [5.4 Deprecated Services & Entity Attributes (`ATTR_COLOR_TEMP`, `reconnect_every`)](#54-deprecated-services--entity-attributes-attr_color_temp-reconnect_every)

---

## 1. Authentication & 2FA

### 1.1 Gmail IMAP 2FA ("Application-specific password required")
* **Symptoms & Signatures**:
  * `[ALERT] Application-specific password required: https://support.google.com/accounts/answer/185833`
  * `imaplib.IMAP4.error: b'[AUTHENTICATIONFAILED] Invalid credentials (Failure)'`
  * 2FA startup fails during startup in Home Assistant or `pyaarlo login`.
* **Root Cause**: Google accounts with 2FA enabled disallow standard login passwords over IMAP. A dedicated Google App Password must be generated.
* **Diagnostic Verification**:
  ```bash
  pyaarlo login --status
  pyaarlo login --tfa email:imap --tfa-host imap.gmail.com --tfa-user user@gmail.com --tfa-pass 'xxxx xxxx xxxx xxxx'
  ```
* **Resolution**:
  1. Enable 2-Step Verification on the Google account.
  2. Navigate to Google Account -> Security -> App Passwords.
  3. Generate a 16-character App Password for "Mail" / "Home Assistant".
  4. Supply the 16-character password in `aarlo.yaml` or through the integration UI config flow.
* **Related Issues**: `#1176`, `#1123`, `#1118`, `#1110`, `#1108`

---

### 1.2 Error 9306: "Mfa disabled by service"
* **Symptoms & Signatures**:
  * JSON error response: `{"data": {"error": "9306", "message": "Mfa disabled by service"}}`
  * `TypeError: 'NoneType' object is not subscriptable` at `backend.py` inside `_auth_get_factors()`.
* **Root Cause**: Arlo's backend returned error 9306 when MFA had been disabled on the account or service level, returning `None` instead of a list of factor items.
* **Diagnostic Verification**:
  Run `pyaarlo login` and inspect the factor retrieval response.
* **Resolution**:
  * Fixed in `pyaarlo >= 0.8.0.24` / `v0.9.0-alpha.1`: Code now checks `meta.code == 0` and safely handles missing or null factor objects, gracefully proceeding with standard non-MFA login.
* **Related Issues**: `#1163`

---

### 1.3 Error 9261: "Invalid factor data" / Stale Factor Cache
* **Symptoms & Signatures**:
  * Arlo returns `meta: {"code": 9261, "message": "Invalid factor data"}` during 2FA start/finish.
  * Integration worked previously, then fails abruptly without password changes.
* **Root Cause**: Arlo occasionally invalidates registered 2FA factor IDs or device registrations on their servers. When `pyaarlo` attempts to reuse the cached factor ID saved in local storage, Arlo rejects it.
* **Diagnostic Verification**:
  ```bash
  pyaarlo login --force
  ```
* **Resolution**:
  1. Clear cached session and factor files in `~/.cache/pyaarlo/` (or `/config/.aarlo/`).
  2. Run `pyaarlo login --force` to regenerate fresh factor pairings and device trust tokens.
* **Related Issues**: `#203`, `#1110`

---

### 1.4 Token Expiration & Periodic HTTP 401 / Meta 9204 Errors
* **Symptoms & Signatures**:
  * Devices and cameras operate normally for ~2 to 4 hours, after which mode changes, snapshots, or commands fail silently or raise `401 Unauthorized` / `meta: 9204`.
  * Integration requires Home Assistant restart to regain control.
* **Root Cause**: Arlo OAuth tokens have a finite lifetime (~14 days maximum, but subject to silent revocation or 2-hour sliding expirations). Older versions relied on a fixed `reconnect_every` interval that was often missed or desynced.
* **Diagnostic Verification**:
  Check `pyaarlo login --status` to view exact expiration timestamps and time remaining.
* **Resolution**:
  * Implemented in `v0.9.0-alpha.2+`:
    * Strict dynamic token renewal scheduled `expires_in - 300` seconds in advance.
    * Automatic transparent 401 catch-and-relogin in `ArloSession.request_tuple()` with `_login_lock` serialization.
    * HTTP request draining (`drain_in_flight`) and stream transaction draining (`drain_transactions`) before token rotation.
* **Related Issues**: `#1170`, `#1127`, `#37f13c5`

---

### 1.5 Cloudflare Bot Challenge / HTTP 403 Forbidden
* **Symptoms & Signatures**:
  * `403 Forbidden` on `https://ocapi-app.arlo.com/api/auth` or `https://myapi.arlo.com`.
  * HTML response containing Cloudflare Turnstile / Captcha challenge.
* **Root Cause**: Cloudflare detects Python `requests` TLS fingerprint.
* **Resolution**:
  * `pyaarlo` defaults to `curl_cffi` (impersonating modern Chrome TLS fingerprints) to seamlessly pass Cloudflare bot detection.
  * Ensure `curl_cffi` is installed in the virtual environment. In `aarlo.yaml` or config flow, keep `http_backend: curl_cffi`.
* **Related Issues**: `#0.8.0.21`, `#0.9.0-alpha.1`

---

## 2. Device Discovery & Missing Hardware

### 2.1 "No devices returned" or "No locations returned" (ReadTimeout)
* **Symptoms & Signatures**:
  * `requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='myapi.arlo.com', port=443): Read timed out.`
  * Log message: `backend: no devices returned` or `_refresh_locations: no locations returned`.
  * Integration starts with 0 devices discovered.
* **Root Cause**: Arlo cloud API occasionally takes >15-30 seconds to query multi-camera device lists during maintenance or high load. When the timeout expires, discovery fails completely and an empty list is parsed.
* **Diagnostic Verification**:
  ```bash
  pyaarlo -vv list devices --ignore-cache
  ```
* **Resolution**:
  1. In `v0.9+`, `pyaarlo` automatically persists a local catalog in cache storage. When initial live queries time out, `pyaarlo` falls back to the saved device catalog to keep entities alive until the next background refresh.
  2. If running on slow connections, increase `request_timeout` in configuration (default: 15s).
* **Related Issues**: `#1175`, `#1132`, `#1134`

---

### 2.2 Wi-Fi Direct Camera Battery & Properties Stale (Base Station Twin)
* **Symptoms & Signatures**:
  * Standalone Wi-Fi cameras (e.g. Arlo Essential Indoor, Essential Outdoor Gen 2, Pro 4) have frozen battery levels, stale signal strength, or un-updated charging state.
* **Root Cause**: For direct-to-cloud cameras without a SmartHub, Arlo creates two device entries sharing the same device ID: an `ArloBaseStation` twin representing the cloud gateway, and an `ArloCamera` representing the physical camera. In older versions, `_refresh_devices()` matched the first device dictionary entry (the base twin), leaving the camera's properties stale.
* **Resolution**:
  * Resolved in `pyaarlo v0.9.0-alpha.2`: `_refresh_devices()` now iterates over all registered objects matching the device ID, ensuring both the base twin and the camera object receive updated properties.
* **Related Issues**: `pyaarlo#219`, `pyaarlo#211`

---

### 2.3 Valid Cameras Filtered Out Due to "Deactivated" / "Parking" State
* **Symptoms & Signatures**:
  * Camera is present in the official Arlo mobile app and fully functional, but missing entirely in Home Assistant and `pyaarlo list devices`.
* **Root Cause**: In Arlo's backend JSON, the camera reports `state: "deactivated"` or `"parking"` (which Arlo uses for unmounted or sleep-mode cameras), but `pyaarlo` was strictly filtering for `state in ("provisioned", "synced")`.
* **Resolution**:
  * `pyaarlo` discovery was updated to include cameras reporting `deactivated` states if they possess valid streaming resources and device IDs.
* **Related Issues**: `pyaarlo#199`

---

### 2.4 Essential Pan & Tilt Searching Continually for Base Station
* **Symptoms & Signatures**:
  * Log flood: `Searching for basestation for <deviceId>` repeatedly.
* **Root Cause**: Pan & Tilt and Essential Gen 2 cameras communicate directly with the cloud and do not connect to physical SmartHubs. Pyaarlo's parent-child resolution logic was aggressively polling for parent hub devices.
* **Resolution**:
  * Standalone Wi-Fi direct cameras are flagged as self-parented cloud gateways; base station searches are bypassed.
* **Related Issues**: `#1145`

---

### 2.5 SmartHub (VMB4540/VMB5000) Connected Camera Discovery Issues
* **Symptoms & Signatures**:
  * Cameras paired to a SmartHub appear as offline or missing attributes on initial startup.
* **Root Cause**: SmartHubs report children as subordinate devices. If the base station's initial `/hmsweb/users/devices` packet has not completed parsing before child entities are instantiated, child devices miss their parent credentials (`xcloudId`).
* **Resolution**:
  * In `v0.9+`, initialization separates discovery into a multi-pass dependency graph: hubs and locations are instantiated and mapped first, and children bind to their parent `xcloudId` cleanly before platform entity creation.
* **Related Issues**: `#1109`, `#1114`

---

## 3. Arming & Modes (V1/V2 vs. Modern V3 Architecture)

### 3.1 V3 Mode Desynchronization (Permanent Divergence after Stream Outage)
* **Symptoms & Signatures**:
  * Changing mode in Home Assistant or through an automation shows the panel as "Armed Away", but the official Arlo app remains "Standby".
  * Base station state is desynchronized from the location mode.
* **Root Cause**:
  * In V3, Arlo accounts are location-based (`location.mode`), not base-station-based.
  * If an MQTT/SSE stream drop occurs right when a mode change is issued, the local optimistic state update marks the entity as armed. Because `base_station.set_mode()` checked `if self.mode == mode_name: return`, subsequent sync attempts were ignored because the entity believed it was already in the desired mode.
* **Resolution**:
  * Implemented in `v0.9.0-alpha.2+`:
    * When setting location mode, changes are forcefully propagated to all associated base stations with `force=True`, bypassing the "no mode change needed" guard.
    * Base station reconnect sequences trigger `location.update_mode()` to ensure local state reconciles with true cloud state.
* **Related Issues**: `#1162`, `#1146`, `#1150`

---

### 3.2 Custom Modes Missing on Migrated V3 Accounts
* **Symptoms & Signatures**:
  * Only default modes ("Arm Away", "Arm Home", "Standby") appear; custom modes created in the old app or V1/V2 accounts are missing or unswitchable.
  * Errors when attempting to call `alarm_control_panel.alarm_arm_custom_bypass`.
* **Root Cause**:
  * Arlo's modern app (API V3) eliminated traditional custom mode lists on base stations. In V3, custom scenarios are implemented as "Automations" / "Rules" tied to schedules or geolocation.
* **Resolution**:
  * Basic modes (`arm_away`, `arm_home`, `disarm` / `standby`) map directly to V3 `privacyState` and `experience`.
  * For custom automation triggers, reverse-engineered V3 custom automation schemas are available under `location.set_custom_mode()`.
* **Related Issues**: `#1138`, `#1137`, `#1131`, `#1124`, `pyaarlo#195`

---

### 3.3 Multi-Location Account Mode Routing
* **Symptoms & Signatures**:
  * Mode change on one base station arms or disarms the wrong home/building, or commands fail silently.
* **Root Cause**:
  * Accounts with multiple physical locations (e.g. Home and Office) have separate location IDs. Calling mode commands without specifying the location target routed to the first discovered location ID.
* **Resolution**:
  * Use the `-l / --location` parameter in CLI:
    ```bash
    pyaarlo location set-mode "arm_away" --location "Beach House"
    ```
  * In Home Assistant, ensure each location has its corresponding `alarm_control_panel` entity mapped to its specific location ID.
* **Related Issues**: `#1140`

---

## 4. Live Streaming, Snapshots, & Media

### 4.1 Stream Works Once, Then Fails / Permission 2016 ("No Such Permissions")
* **Symptoms & Signatures**:
  * Camera live stream works on the first attempt after HA restart. Subsequent attempts display a black screen or spinning wheel.
  * Logs show `error: 2016, message: "No Such Permissions"` when attempting to stop activity.
  * Snapshots fail with error `2503`.
* **Root Cause**:
  * When a live stream is stopped, `pyaarlo` sends `stop_activity` to Arlo Cloud.
  * If Arlo Cloud returns error 2016 (indicating the cloud session was already terminated on Arlo's end) or if the `idle` event over MQTT is dropped, `pyaarlo` kept the camera internally marked as `streaming`.
  * Subsequent stream calls reused the old, expired `rtsps://` URL because `pyaarlo` believed a local stream was already running.
* **Resolution**:
  * In `v0.9+`, `async_stop_activity()` unconditionally resets the internal stream URL cache and clears `user_requests` even if `stop_activity` returns 2016 or times out.
  * A dead stream cannot poison subsequent stream requests.
* **Related Issues**: `#1168`, `#1165`, `#1125`, `pyaarlo#207`

---

### 4.2 Snapshot Fails with Error 2503 Due to Active Stream Contention
* **Symptoms & Signatures**:
  * Log error: `status: 2503` or `Snapshot request returned false`.
* **Root Cause**: Arlo hardware cannot take a full-frame idle snapshot while the video pipeline is actively encoding a live stream or recording a clip.
* **Resolution**:
  * If streaming is active, `pyaarlo` uses `_take_streaming_snapshot()` instead of `_take_idle_snapshot()`.
  * Ensure automations do not request full-frame snapshots while live WebRTC/HLS streaming is active.
* **Related Issues**: `pyaarlo#207`, `#1158`

---

### 4.3 RTSPS vs. DASH Session Negotiation Failures (AVD2001A / AVD4001A)
* **Symptoms & Signatures**:
  * Video doorbell live feed fails to load in Home Assistant; ffmpeg logs show connection refused or undecodable stream.
* **Root Cause**: Certain newer doorbells and firmware versions reject or throttle RTSPS stream negotiation while responding reliably to MPEG-DASH streams (or vice versa).
* **Resolution**:
  * `pyaarlo` stream negotiation requests both stream formats from `/hmsweb/users/devices/startStream` and falls back dynamically to DASH if RTSPS negotiation fails.
* **Related Issues**: `#1156`, `#1174`, `#1141`

---

### 4.4 SmartHub Direct Local Storage Access (RaTLS) Port Failure
* **Symptoms & Signatures**:
  * `Failed to open ratls port: None`
  * Cannot access or download local SD card / USB recordings from VMB4540/VMB5000 SmartHubs.
* **Root Cause**: RaTLS requires a temporary authenticated port lease granted via an Arlo notification packet (`action: "open", resource: "storage/ratls"`). If the event stream is disconnected, the response is never received.
* **Resolution**:
  * `pyaarlo local-media` commands and the RaTLS client now ensure the event stream is connected before sending the notify request, and wait for the transaction response over MQTT.
* **Related Issues**: `pyaarlo#191`

---

## 5. Configuration & Home Assistant OS Environment

### 5.1 Fragile Host & Broker Overrides in `aarlo.yaml` (`host`, `auth_host`, `mqtt_host`)
* **Symptoms & Signatures**:
  * Connection failure on startup: 403 Forbidden, 404 Not Found, or MQTT connection rejected (`rc=5`).
* **Root Cause**:
  * Legacy forum posts and documentation often suggested adding `host: https://myapi.arlo.com` or `mqtt_host: mqtt-cluster.arloxcld.com` into `aarlo.yaml`.
  * Hardcoding these endpoints overrides modern dynamic discovery: Arlo frequently rotates API hosts and dynamically provisions the MQTT broker hostname per-session in the V3 session packet (e.g. `mqtt-cluster-v2-z2-1.arloxcld.com`).
* **Resolution**:
  * Remove `host`, `auth_host`, `mqtt_host`, and `mqtt_port` from `/config/aarlo.yaml`.
  * In `v0.9.0-alpha.3+`, both `pyaarlo` and `hass-aarlo` detect these overrides and emit explicit warnings in the log.
* **Related Issues**: `#1170`, `#466a8db`, `#cc3f36d`

---

### 5.2 Entity IDs with Special Characters (Umlauts, Accents, Hyphens)
* **Symptoms & Signatures**:
  * Warning in Home Assistant core: `Entity ID contains invalid characters; this will break in HA 2027.2.0`.
  * Camera named `Haustür` generating entity `camera.aarlo_haustur` or failing slugification.
* **Root Cause**: Strict entity ID validation in modern Home Assistant releases rejects raw non-ASCII unicode characters and irregular separator symbols.
* **Resolution**:
  * `pyaarlo` uses `python-slugify` and `unidecode` to normalize entity names into valid Home Assistant identifiers (`haustur`, `front_door`).
  * If preferred, enable `serial_ids: true` in configuration to identify entities by hardware serial number instead of display names.
* **Related Issues**: `#1147`, `#1119`, `#1120`

---

### 5.3 Temporary Directory Restrictions on Modern Home Assistant OS (`/tmp`)
* **Symptoms & Signatures**:
  * `PermissionError: [Errno 13] Permission denied: '/tmp/...'`
  * Missing snapshot images or video download failures in Home Assistant.
* **Root Cause**: Home Assistant OS container security restricts or sandboxes access to root `/tmp/`. Integrations must use Home Assistant's managed temporary directory (`hass.config.config_dir` or `tempfile.gettempdir()`).
* **Resolution**:
  * Hardcoded `/tmp/` paths in `camera.py` and `media.py` were replaced with `hass.config.path(".aarlo")` and managed tempfile directories.
* **Related Issues**: `#1135`

---

### 5.4 Deprecated Services & Entity Attributes (`ATTR_COLOR_TEMP`, `reconnect_every`)
* **Symptoms & Signatures**:
  * Warnings on integration startup: `reconnect_every in aarlo configuration is deprecated and ignored`.
  * Light entity errors regarding `ATTR_COLOR_TEMP` or color temperature conversion.
* **Root Cause**:
  * `reconnect_every` was deprecated in favor of automated dynamic pre-expiration renewal.
  * Home Assistant core deprecated `ATTR_COLOR_TEMP` in favor of `color_temp_kelvin`.
* **Resolution**:
  * Remove `reconnect_every` from `aarlo.yaml`.
  * Light platform supports modern Home Assistant color modes and kelvin-based color temperatures.
* **Related Issues**: `#1136`, `#9d558fa`

# **An Arlo Home Assistant Integration**

_Aarlo_ is a custom component for [Home Assistant](https://www.home-assistant.io/), providing asynchronous access to the [Arlo](https://www.arlo.com/en-us/) camera and security ecosystem.

_Aarlo_ provides, amongst other things:
- Access to cameras, base stations, sirens, doorbells, and lights.
- Asynchronous, real-time notification of motion, sound, and doorbell press events via MQTT/WebSockets.
- Media playback, snapshots, and direct camera streaming in Home Assistant.
- Environmental sensors (temperature, humidity, air quality) from supported base stations.
- Dedicated switches for alarms, camera snapshots, and doorbell muting.
- Native async service calls and non-blocking integration lifecycle.

---

> ### ⚠️ Major Rewrite Notice (`v0.9.0-alpha.1`)
>
> **Aarlo v0.9 is a major rewrite transitioning the integration and underlying `pyaarlo` library to native Python `asyncio`.**
>
> **This is an active alpha release — please expect bugs, edge cases, and evolving improvements.**
>
> *Note on Hardware Testing:* The maintainer does not own or have access to every Arlo hardware model (such as all generations of cameras, floodlights, doorbells, chimes, and SmartHubs) and cannot test every permutation. Community testing and feedback are essential to stabilizing this release!
>
> If you encounter issues, regressions, or unexpected behavior with your hardware, please [open a GitHub issue](https://github.com/twrecked/hass-aarlo/issues). Please include your Home Assistant version, Arlo device models, and relevant logs.
>
> If you need the legacy v0.8 documentation, it is archived in [README_v8.md](README_v8.md).

---

# Table Of Contents

- [Introduction](#introduction)
- [Requirements](#requirements)
- [What's New & Changed Defaults in v0.9](#whats-new--changed-defaults-in-v09)
- [Installing the Integration](#installing-the-integration)
  - [HACS](#hacs)
  - [Manual Installation](#manual-installation)
- [Adding and Configuring the Integration](#adding-and-configuring-the-integration)
  - [Two-Factor Authentication (2FA)](#two-factor-authentication-2fa)
  - [Options & Configuration Flow](#options--configuration-flow)
- [Event Stream Backends (MQTT vs. SSE)](#event-stream-backends-mqtt-vs-sse)
- [Cloudflare & Network Resiliency](#cloudflare--network-resiliency)
- [Diagnostics & Bug Reports](#diagnostics--bug-reports)
  - [Configuring Logging](#configuring-logging)
  - [Capturing a Network Archive (.har)](#capturing-a-network-archive-har)
  - [Encrypting Diagnostic Output](#encrypting-diagnostic-output)
- [FAQ](#faq)
- [Supported Devices](#supported-devices)
- [Known Limitations](#known-limitations)

---

# Introduction

_Aarlo_ interacts with the [Arlo Web APIs](https://my.arlo.com/#/home) to provide full Home Assistant entity support.

With v0.9, all network requests, event listeners, streaming handoffs, and entity controls run asynchronously on Home Assistant's event loop with zero thread-blocking calls.

For advanced configurations (such as customizing video download directories or raw entity naming), see [README-advanced.md](README-advanced.md).

---

# Requirements

- **Dedicated Arlo Account:**
  _Aarlo_ requires a dedicated Arlo account. If you attempt to reuse the same account you use on your mobile phone, the phone app and Home Assistant will constantly disconnect each other.
- **Admin Access Rights:**
  Grant the secondary account `Allow Access Rights` (Admin privileges) in your primary Arlo app settings (*Settings -> Grant Access*). This is required to control base station modes and receive battery/signal updates.
- **Two-Factor Authentication (2FA):**
  Arlo mandates two-factor authentication. We strongly recommend configuring an **Email** 2FA factor using **IMAP**.

---

# What's New & Changed Defaults in v0.9

In v0.9, the integration has been streamlined so that **`/config/aarlo.yaml` is no longer needed for normal setups**. Sane, automated defaults now handle operation out of the box:

1. **`http_backend: curl_cffi` (Default)**:
   - Uses real browser TLS fingerprints (`chrome131`) to reliably pass Cloudflare anti-bot verification.
   - `cloudscraper` remains available as a manual fallback option if needed.
2. **Automated Token Expiry Renewal**:
   - Reconnects and token renewals are now automatically scheduled to fire **5 minutes before the session token expires**.
   - Manual periodic reconnect workarounds (e.g. `reconnect_every: 15`) are no longer needed.
3. **`recent_time: 60` (Default)**:
   - The camera "recently active" status window defaults to 60 seconds (1 minute), rather than the legacy 60-minute default.
4. **`media_retry: []` (Default)**:
   - Recordings now rely on real-time MQTT push events (`mediaUploadNotification`) rather than firing multiple duplicate HTTP polling requests for every video.
5. **Modern Sub-Logger (`pyaarlo.packet`)**:
   - High-volume packet and protocol tracing is routed through the `pyaarlo.packet` logger.
   - The legacy `verbose_debug: true` setting in `aarlo.yaml` is deprecated.
6. **UI Configuration for Backend & Media**:
   - Event stream protocol (`auto`, `mqtt`, `sse`), HTTP client (`curl_cffi`, `cloudscraper`), and local recording download templates (`save_media_to`) can now be managed directly in Home Assistant via **Configure**.
   - Any existing settings in `/config/aarlo.yaml` are automatically imported on startup.

---

# Installing the Integration

### HACS (Recommended)

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

_Aarlo_ is part of the default HACS store. Search for "Aarlo" under Integrations and download the latest release.

### Manual Installation

Copy the `custom_components/aarlo` directory into your Home Assistant `/config/custom_components/` directory and restart Home Assistant.

---

# Adding and Configuring the Integration

From the Home Assistant UI:
1. Navigate to **Settings -> Devices & Services**.
2. Click **Add Integration** and search for **Aarlo**.
3. Enter your dedicated Arlo account credentials and 2FA settings:

![Integration Setup](/images/config-flow-01.png?raw=true)

| Field | Description |
|---|---|
| **Username** | Your dedicated Arlo account email address |
| **Password** | Your dedicated Arlo account password |
| **Two Factor Mechanism** | Select **IMAP** (recommended), **PUSH**, or **NONE** |
| **TFA Username** | Your IMAP email username |
| **TFA Password** | Your IMAP email password or app-specific password |
| **TFA Host** | Your IMAP server hostname (e.g. `imap.gmail.com`) |

---

## Two-Factor Authentication (2FA)

Arlo requires two-step verification. Three methods are supported:

### 1. IMAP (`email:imap`) — Strongly Recommended
Automates two-factor authentication headlessly. When Arlo sends an email with a 6-digit code, _Aarlo_ checks your inbox over IMAP, extracts the code, and completes login without manual intervention.

- **App Passwords Required:**
  Webmail providers like Gmail and Yahoo require an **Application Specific Password** (not your regular account password) when accessing via IMAP:
  - [Google App Passwords Guide](https://support.google.com/mail/answer/185833?hl=en)
  - [Yahoo App Passwords Guide](https://help.yahoo.com/kb/SLN15241.html)

- **Common IMAP Hostnames:**
  - Gmail: `imap.gmail.com`
  - Yahoo: `imap.mail.yahoo.com`
  - Outlook / Office 365: `outlook.office365.com`

### 2. Push (`push`)
Arlo sends a push notification to your phone. You must open the official Arlo app and approve the login request when Home Assistant restarts.

### 3. SMS (`sms`)
Requires manual verification code entry.

---

## Options & Configuration Flow

From the Integration page, click **Configure** on Aarlo to customize integration settings and entities:

- **Backend & Media Settings Screen (New):**
  - **Event Stream Backend:** Select `auto` (MQTT WebSocket, recommended), `mqtt`, or `sse`.
  - **HTTP Client Backend:** Select `curl_cffi` (Chrome TLS fingerprinting, recommended), `cloudscraper`, or `requests`.
  - **Save Media Path Template:** Specify a directory template to download MP4 video recordings locally (e.g. `/config/media/${SN}/${Y}/${m}/${d}/${T}`). Leave blank to stream on demand without saving files to disk.
  - *Automatic Import:* If you have existing settings in `/config/aarlo.yaml`, they are automatically imported into this screen on startup.
- **Alarm Setting Screen:** Customize home/away/night mode names, disarm codes, and siren trigger duration.
- **Binary Sensors Screen:** Enable or disable motion, sound, doorbell press, cry, contact, light, and leak sensors.
- **Sensors Screen:** Enable battery level, signal strength, capture history, and environmental sensors.
- **Switches Screen:** Add switches to trip sirens, request snapshots, or silence doorbell chimes.

---

# Event Stream Backends (MQTT vs. SSE)

Arlo supports two streaming protocols for pushing real-time events to Home Assistant:

1. **`auto` / MQTT over WebSockets (Default):**
   - The modern protocol used by Arlo's official web and mobile apps.
   - Lightweight and supports concurrent connections.
   - The broker URL is dynamically assigned by Arlo during authentication.
2. **`sse` (Fallback):**
   - HTTP Server-Sent Events stream (`/subscribe`).
   - Retained as a fallback if your account or devices do not push events over MQTT.
   - *Limitation:* Arlo restricts SSE to a single connection per account.

To change or override the backend, click **Configure** on the Aarlo integration in Home Assistant and select your preferred backend on the first screen (or optionally specify `backend:` in `/config/aarlo.yaml`).

---

# Cloudflare & Network Resiliency

Arlo protects its login endpoints with Cloudflare anti-bot checks.

- In v0.9, _Aarlo_ defaults to **`curl_cffi`**, which impersonates authentic browser TLS fingerprints (`chrome131`) to pass Cloudflare verification cleanly.
- To switch the HTTP backend (e.g. to `cloudscraper` or `requests`), click **Configure** on the Aarlo integration in Home Assistant and adjust the **HTTP Client Backend** dropdown on the first screen (or optionally specify `http_backend:` in `/config/aarlo.yaml`).

---

# Diagnostics & Bug Reports

### Configuring Logging

Standard logging in `configuration.yaml` allows granular control over log output:

```yaml
logger:
  default: info
  logs:
    # Standard integration logs (device states, mode changes, connections)
    pyaarlo: debug
    custom_components.aarlo: debug

    # Optional: Enable raw packet tracing (replaces verbose_debug)
    pyaarlo.packet: debug
```

> **Tip:** You can toggle `pyaarlo.packet: debug` on and off dynamically without restarting Home Assistant via Developer Tools -> Actions -> `logger.set_level`.

### Capturing a Network Archive (.har)

If reporting an issue with an unsupported device or an unhandled packet:
1. Open [my.arlo.com](https://my.arlo.com) in Chrome, Firefox, or Edge.
2. Open Developer Tools (`F12`), go to the **Network** tab, and check **Preserve log**.
3. Perform the action (e.g. view stream, arm device, toggle light).
4. Right-click any network request and select **Save all as HAR with content**.

### Encrypting Diagnostic Output

`.har` files and raw packet traces contain session tokens and device identifiers:
- Anonymize and encrypt the file using the [encryption page](https://pyaarlo-tfa.appspot.com/) or via the `pyaarlo` CLI:
  ```bash
  cat trace.log | pyaarlo-utils anonymize | pyaarlo-utils encrypt > trace.log.enc
  ```
- Attach the encrypted output to a [GitHub Issue](https://github.com/twrecked/hass-aarlo/issues). Only maintainers holding the private key can decrypt it.

---

# FAQ

### Can I share an account with my mobile app?
No. Arlo's servers do not support simultaneous logins on the same credentials. Create a free second Arlo account, grant it Admin access to your devices, and use those credentials in Home Assistant.

### Why do live streams take a few seconds to start?
Arlo cameras are battery-optimized and stay in deep sleep until an event or stream is requested. Initiating a stream requires communicating through the cloud to wake the camera and establish an RTSP/HLS stream back to Home Assistant.

### Do I need an Arlo Smart subscription?
No subscription is needed for live viewing, motion events, snapshots, or local RTSP streaming. Arlo requires a subscription to access cloud-stored video recordings.

---

# Supported Devices

Most Arlo devices are supported, including:
- **Cameras:** Arlo HD (VMC3030), Pro (VMC4030), Pro 2/3/4/5 (VMC4040/VMC4041/VMC4060), Ultra (VMC5040), Essential & Essential 2 (VMC2030/VMC2040/VMC3060), Go & Go 2 (VML4030/VML2030), Arlo Baby (ABC1000).
- **Doorbells:** Audio Doorbell (AAD1001), Video Doorbell Wired & Wireless (AVD1001, AVD2001, AVD3001, AVD4001).
- **Lights:** Arlo Light (AL1101), Pro 3 Floodlight (FB1001).
- **Sensors & Base Stations:** All-in-One Sensor (MS1001), Base Station (VMB3000/VMB4000/VMB4500/VMB5000).

---

# Known Limitations

- **Cloud Dependency:** All authentication and stream negotiation routes through Arlo's cloud infrastructure.
- **Cloudflare Verification:** Arlo periodically changes anti-bot challenges; `curl_cffi` keeps these working reliably.
- **Hardware Permutations:** With dozens of camera models and firmware variations, unexpected packets occasionally appear. Please report unhandled events with debug logs so they can be incorporated.

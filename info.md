# Asynchronous Arlo Component for Home Assistant (v0.9)

An asynchronous Home Assistant custom integration providing full access to the [Arlo](https://www.arlo.com/) camera and security system.

> **Note on v0.9:** Aarlo v0.9 is a major rewrite transitioning the integration and underlying `pyaarlo` library to native Python `asyncio`.

## Features

- **Asynchronous & Non-Blocking:** All entity operations, streaming handoffs, and background event loops run natively on Home Assistant's event loop.
- **Full Device Support:** Cameras, base stations, sirens, doorbells, lights, and environmental sensors.
- **Instant Event Notifications:** Real-time push updates for motion, audio, and doorbell press events via MQTT over WebSockets.
- **Media & Streaming:** Live camera streaming, snapshot requests, and optional local recording storage.
- **Zero-Config Defaults:** Optimized Cloudflare TLS fingerprinting (`curl_cffi`), automatic session token renewals, and in-UI options configuration.

For full setup instructions, two-factor authentication configuration, and troubleshooting guides, please visit the [README](https://github.com/twrecked/hass-aarlo/blob/master/README.md).

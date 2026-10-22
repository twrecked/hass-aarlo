# 🚀 Aarlo v0.9.0-alpha.1 — Native Async Refactor & Modernization

> ### ⚠️ Alpha Release & Community Testing Notice
> **Aarlo v0.9 is a ground-up modernization refactoring the integration and the underlying `pyaarlo` library to native Python `asyncio`.**
>
> This is an active pre-release. While the core architecture is significantly faster and non-blocking, Arlo has dozens of camera generations, floodlights, doorbells, chimes, and SmartHub firmware variants. We cannot test every hardware permutation alone.
>
> **Community testing and feedback are essential!** If you encounter bugs, regressions, or unhandled device packets, please [open a GitHub issue](https://github.com/twrecked/hass-aarlo/issues) with your hardware models and diagnostic logs.
>
> *(Legacy v0.8 documentation is archived in [README_v8.md](README_v8.md)).*

---

## 🌟 Highlights

### 1. Fully Asynchronous & Non-Blocking Core
- **`PyArlo.create()` on Event Loop:** Integration setup, authentication, and platform forwarding run natively on Home Assistant's event loop without blocking executor threads or using `time.sleep()`.
- **Async Entity Controls:** All device actions across Cameras, Alarm Control Panels, Lights, Sirens, Switches, and Media Players now execute as native asynchronous coroutines (`async_turn_on`, `async_turn_off`, `async_alarm_arm_*`, `async_media_*`, `async_camera_image`, `stream_source`, etc.).
- **Async Services:** All component services (`camera_snapshot`, `camera_stop_activity`, `siren_on`, `sirens_on`, `siren_off`, `sirens_off`, `restart_device`, `inject_response`) run non-blockingly.
- **Clean Unload:** Direct `await arlo.stop(logout=True)` ensures prompt, reliable integration reloads and restarts.

### 2. Sane Defaults & "Zero-Config" Operation
In v0.9, **`/config/aarlo.yaml` is no longer required** for standard operation:
- **`http_backend: curl_cffi` (Default):** Uses real browser TLS fingerprints (`chrome131`) to pass Cloudflare anti-bot challenges reliably out of the box, eliminating the need for `cloudscraper`.
- **Dynamic Session Token Renewal:** Automatically calculates token expiration and re-authenticates 5 minutes before the session expires. Brute-force periodic reconnect workarounds (`reconnect_every: 15`) are obsolete.
- **`recent_time: 60`:** Camera "recently active" status resets after 60 seconds (1 minute), replacing the legacy 60-minute default.
- **`media_retry: []`:** Eliminated redundant 3-polling cloud request bursts (`[5, 15, 25]`); recordings now sync cleanly via real-time MQTT push events.

### 3. In-UI Options Flow for Backend & Media
- Added a new **Backend & Media Settings** screen as the very first step in Home Assistant's **Configure** options flow:
  - Choose Event Stream Backend (`auto` / MQTT WebSocket, `mqtt`, or `sse`).
  - Choose HTTP Client Backend (`curl_cffi`, `cloudscraper`, or `requests`).
  - Configure the local recording download template (`save_media_to`).
- **Automated Migration from `aarlo.yaml`:** If you have existing settings in `/config/aarlo.yaml`, Home Assistant automatically imports them into the integration's configuration entry on startup.

### 4. Concurrency & Performance Enhancements
- **Parallel Multi-Siren Dispatch:** "All Sirens" commands now fire across all targeted devices simultaneously using `asyncio.gather` rather than waiting for each siren in series.
- **Batched Nightlight Updates:** Turning on `ArloNightLight` with brightness, color, and mode now batches into a single network request instead of 4 separate HTTP calls.

### 5. Diagnostics & Logging Overhaul
- **Dedicated Sub-Logger (`pyaarlo.packet`):** Raw MQTT/SSE packet dumps and internal protocol traces are separated from normal debug logs.
- Standard debug (`pyaarlo: debug`, `custom_components.aarlo: debug`) stays clean and readable.
- You can toggle raw packet dumps on/off dynamically in the Home Assistant GUI (**Developer Tools -> Actions -> `logger.set_level`**) without restarting:
  ```yaml
  action: logger.set_level
  data:
    pyaarlo.packet: debug  # set to 'info' to turn off
  ```
- Deprecated `verbose_debug: true` in `aarlo.yaml`.

---

## 🛠️ Home Assistant Standards Compliance
- Added `"integration_type": "hub"` to `manifest.json`.
- Updated `ArloSensor` to inherit from `SensorEntity` using `_attr_native_value` and `_attr_native_unit_of_measurement`.
- Fixed `signal_strength` device class and `MediaPlayerEntity` volume/mute property mappings.
- Bumped minimum Home Assistant version in `hacs.json` to `2025.1.0`.

---

## 📋 Migration & Upgrade Notes

1. **Remove Legacy YAML Platform Sections:**
   If your `configuration.yaml` still has old platform entries like `camera: - platform: aarlo` or `sensor: - platform: aarlo`, remove them. The integration automatically loads all platforms via its config entry.
2. **Slim Down `aarlo.yaml`:**
   Unless you use custom local media download paths (`save_media_to`), you can safely delete or empty `/config/aarlo.yaml`.
3. **Targeting `pyaarlo`:**
   Integration manifest points to `pyaarlo` on the `v0.9-async-refactor` branch.

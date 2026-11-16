# 🚀 Aarlo v0.9.0-beta.1 — Release Notes

> Version `0.9.0-beta.1` marks the first official beta release of the modernized **Aarlo v0.9 integration**. This milestone transitions the integration to PyArlo's async-first architecture, moves configuration from `aarlo.yaml` into Home Assistant UI, consolidates location-level alarms, retires legacy siren switches in favor of native Home Assistant sirens, introduces native WebRTC live camera streaming, and adopts modern entity naming conventions.

---

## ⚠️ Breaking Changes & Upgrading from v0.8.x

If you are upgrading from Aarlo `v0.8.x` or earlier, please review the following changes:

### 1. Configuration Moved from `aarlo.yaml` to Home Assistant UI
* **UI Config & Options Flow:** Settings previously configured in `aarlo.yaml` (such as event stream backend, HTTP client backend, local media recording path, retention period, and entity naming preferences) are now managed directly in the Home Assistant UI via **Settings → Devices & Services → Aarlo → Configure**.
* **Seamless YAML Import:** Existing YAML configurations are imported into Home Assistant's configuration entries automatically.

### 2. Retired Legacy Siren Switches in Favor of Native Sirens
* **Switches Removed:** Duplicate `switch.aarlo_*_siren` and `switch.aarlo_all_sirens` entities have been retired.
* **Native Siren Entities:** All siren operations are now handled exclusively by dedicated Home Assistant `siren` entities (`siren.aarlo_*`), which support native volume levels, sound durations, and on/off controls.
* **Backwards Compatibility:** Legacy siren options in `aarlo.yaml` or storage entries are safely ignored and will not cause schema validation errors.

### 3. Consolidated Location Alarms
* **Location-Level Modes:** Modern Arlo Secure accounts set security modes per-location rather than per-device. Individual camera/base alarm panels are now suppressed by default (`hide_base_station_alarms = True`) to prevent non-functional, out-of-sync entities.
* **Clean Friendly Names:** Location alarm entities and devices are cleanly named (e.g., **User Location Home** and **Location Home**).
* **Configurable Override:** If you prefer to expose individual base station alarm panels alongside the location alarm, you can uncheck `hide_base_station_alarms` in the Options Flow.

### 4. Modern Entity Naming Architecture (`_attr_has_entity_name = True`)
* **Clean Device Pages:** Child entities display functional names only (e.g. **Battery Level**, **Motion**, **Spotlight**, **Snapshot**, **Siren**) on their Home Assistant device page, eliminating repetitive names (no more "Front Front Motion").
* **Upfront Naming Choice:** Fresh installations let you choose your naming format (`<device>_<function>` vs `<function>_<device>`) directly on the initial setup screen alongside the `aarlo_` prefix toggle.
* **Existing Setups:** Existing installations retain their current `unique_id` mappings across upgrades to ensure zero broken automations or dashboards.

---

## 🌟 What's New in v0.9.0-beta.1

### 1. Native WebRTC Camera Streaming (`ArloSipCam`)
* Cameras supporting Arlo's SIP protocol now stream using native Home Assistant WebRTC.
* Media flows directly peer-to-peer between your browser and Arlo with sub-second latency and zero transcode overhead.
* Automated retrieval and refresh of Arlo STUN/TURN ICE servers passed through to the browser.
* Non-SIP cameras automatically maintain standard RTSP/HLS operation for full backwards compatibility.

### 2. Unified Light Platform (`pyaarlo::ArloLight`)
* Consumes first-class light objects directly from PyArlo for standalone lights (AL1101), camera spotlights, and camera floodlights.
* Natively supports percentage brightness adjustment and on/off controls.
* Automatically prevents duplicate battery, motion, and connectivity sensors for child lights.

### 3. Device Removal from Home Assistant UI
* Implemented `async_remove_config_entry_device()`, allowing retired or replaced Arlo hardware to be deleted directly from **Settings → Devices**.
* Protects active devices from accidental deletion while allowing clean removal of orphaned hardware.

### 4. Configurable Integration Name on Install
* You can now specify a custom title during setup (e.g., `Arlo at Home`) instead of being restricted to `Aarlo for <username>`.

### 5. Requirements & Dependency Update
* Pinned requirement to the official `pyaarlo==0.9.0-beta.1` release tag.

---

## 📦 Upgrading via HACS

To update to this beta release via HACS:
1. Open **HACS → Integrations → Aarlo**.
2. Select the three dots menu in the top right and choose **Redownload**.
3. Toggle **Show beta versions** on and select **v0.9.0-beta.1**.
4. Restart Home Assistant.

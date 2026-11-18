# 🚀 Aarlo v0.9.0-beta.2 — Release Notes

> Version `0.9.0-beta.2` is a targeted update for the **Aarlo v0.9 integration**, delivering real-time contact sensor state updates for Arlo Security Systems (Keypad Sensor Hub SH1001) and upgrading the underlying `pyaarlo` dependency to `v0.9.0-beta.2`.

---

## 🌟 What's New in v0.9.0-beta.2

### 1. MS1001 Real-Time Contact State on Keypad Sensor Hubs ([#1190](https://github.com/twrecked/hass-aarlo/issues/1190))
* **Live Open/Close Updates:** Systems running Arlo's Keypad Sensor Hub (`SH1001`) with All-in-One Sensors (`MS1001`) now report door and window contact state changes in real time.
* **Stream Exception Decoding:** Consumes location-level `automation/exceptionSensors` event streams via `pyaarlo 0.9.0-beta.2`, eliminating the issue where contact entities only updated on integration reload.

### 2. Upstream Dependency Update (`pyaarlo==0.9.0-beta.2`)
* Pinned the integration's library requirement to `pyaarlo==0.9.0-beta.2`.
* Includes CLI enhancements (`--hass` flag and `--hass-dir` options) for external scripting and monitoring diagnostics.

---

## 📦 Upgrading via HACS

To update to this beta release via HACS:
1. Open **HACS → Integrations → Aarlo**.
2. Select the three dots menu in the top right and choose **Redownload**.
3. Toggle **Show beta versions** on and select **v0.9.0-beta.2**.
4. Restart Home Assistant.

# 🚀 Aarlo v0.9.0-alpha.3 — Release Notes

> ### ⚠️ Alpha Pre-Release & Community Testing Notice
> This is the third alpha pre-release for the **Aarlo v0.9 native `asyncio` rewrite**.
>
> Version `0.9.0-alpha.3` focuses on **discouraged configuration warnings**, **preventing hardcoded host overrides from breaking cloud connectivity**, and **updating the underlying `pyaarlo` requirement to `v0.9.0-alpha.3`**.
>
> **Community testing and feedback are essential!** If you encounter bugs, regressions, or unhandled device packets, please [open a GitHub issue](https://github.com/twrecked/hass-aarlo/issues) with your hardware models and diagnostic logs.

---

## 🌟 What's New in v0.9.0-alpha.3

### 1. Discouraged Configuration Warnings
- **Host & Broker Override Warnings:** Overriding fragile network settings (`host`, `auth_host`, `mqtt_host`, `mqtt_port`) in `/config/aarlo.yaml` or YAML configuration is a common cause of complete connection failures when endpoints rotate. Aarlo now detects these settings in options and emits a clear warning in Home Assistant logs.
- **Removed Artificial Schema Defaults:** Removed default values for `host` and `auth_host` from `AARLO_SCHEMA`. This prevents default endpoints from being injected into configuration options unnecessarily and allows `pyaarlo` to manage connection endpoints dynamically.

### 2. Under-the-Hood `pyaarlo` Improvements (`v0.9.0-alpha.3`)
Inherits the latest stability updates from `pyaarlo` v0.9.0-alpha.3:
- **Transaction Draining & Co-Location:** Stream transactions are co-located in `ArloSession` alongside HTTP in-flight tracking, ensuring pending notify transactions finish gracefully during token renewal and re-login sequences.
- **Defensive Cache Directory Auto-Creation:** Automatically ensures parent directories exist when saving session state and cookies, preventing startup crashes on clean installations.
- **Co-Located Log Encrypter:** The Google App Engine log encrypter service (`https://aarlo-dot-twrecked-tools.nn.r.appspot.com`) is now maintained alongside `pyaarlo`.

---

## 📋 Upgrading

To install or update to this pre-release via HACS, make sure **Show beta versions** is enabled under the Aarlo integration options, or point to the `v0.9.0-alpha.3` release.

# 🚀 Aarlo v0.9.0-alpha.4 — Release Notes

> ### ⚠️ Alpha Pre-Release & Community Testing Notice
> This is the fourth alpha pre-release for the **Aarlo v0.9 native `asyncio` rewrite**.
>
> Version `0.9.0-alpha.4` focuses on **push 2FA rate-limit protection**, **troubleshooting documentation**, and **updating the underlying `pyaarlo` requirement to `v0.9.0-alpha.4`**.
>
> **Community testing and feedback are essential!** If you encounter bugs, regressions, or unhandled device packets, please [open a GitHub issue](https://github.com/twrecked/hass-aarlo/issues) with your hardware models and diagnostic logs.

---

## 🌟 What's New in v0.9.0-alpha.4

### 1. Push 2FA Rate-Limit Protection (via `pyaarlo v0.9.0-alpha.4`)
- **Early Exit on Lockout:** When Arlo returns `"Too many requests"`, polling `/api/finishAuth` terminates immediately on attempt #1 rather than burning through all 10 retries. Continuing to poll when rate-limited resets and extends Arlo's ~24-hour lockout window; aborting immediately prevents extending the ban.
- **Early Exit on Expiration:** Aborts immediately if the push prompt expires on Arlo's servers (`"Maximum permitted time for authentication exceeded"`).
- **Clear Guidance:** Logs an actionable error message advising the user that the account is rate-limited and to wait 24 hours before retrying.

### 2. Dropped `aiofiles` Dependency & Atomic Config Writes
- **Native Home Assistant Executor:** Eliminated the third-party `aiofiles` requirement from `manifest.json`. Reading and writing `/config/aarlo.yaml` now uses Home Assistant's native executor (`hass.async_add_executor_job`) with standard `pathlib.Path`.
- **Atomic File Writes:** Saving configuration writes to a `.tmp` file before atomically replacing the target, protecting `aarlo.yaml` against corruption during sudden restarts or power loss.

### 3. Troubleshooting Knowledge Base (`AGENTS.issues.md`)
- Added a comprehensive diagnostic issue cache and troubleshooting lookup table in `AGENTS.issues.md`.
- Synthesizes 1 year of historical issues across 5 core categories:
  1. Authentication & 2FA (Gmail app passwords, error 9306, error 9261, 401 token renewal).
  2. Device Discovery (ReadTimeouts, Wi-Fi direct camera twins, deactivated camera states).
  3. V3 Modes & Arming (desync bypass, location-to-hub propagation, custom mode automations).
  4. Live Streaming & Snapshots (stale RTSPS URLs, error 2016, snapshot error 2503).
  5. Configuration & Environment (`aarlo.yaml` overrides, entity ID naming, `/tmp` restrictions).

---

## 📋 Upgrading

To install or update to this pre-release via HACS, make sure **Show beta versions** is enabled under the Aarlo integration options, or point to the `v0.9.0-alpha.4` release tag.

# 🚀 Aarlo v0.9.0-alpha.2 — Release Notes

> ### ⚠️ Alpha Pre-Release & Community Testing Notice
> This is the second alpha pre-release for the **Aarlo v0.9 native `asyncio` rewrite**.
>
> Version `0.9.0-alpha.2` focuses on **session rotation stability**, **eliminating transient 401 errors**, **fixing modern V3 mode synchronization**, and **aligning entity controls with normalized `pyaarlo` APIs**.
>
> **Community testing and feedback are essential!** If you encounter bugs, regressions, or unhandled device packets, please [open a GitHub issue](https://github.com/twrecked/hass-aarlo/issues) with your hardware models and diagnostic logs.

---

## 🌟 What's New in v0.9.0-alpha.2

### 1. Zero-Collision Token Renewal & Session Stability
Inheriting the session rotation overhaul in `pyaarlo`:
- **No More Re-Auth Collisions:** All token refreshes and re-logins are strictly serialized. Non-auth API requests arriving while renewal is occurring now pause and resume with the new token.
- **In-Flight Draining:** Active HTTP requests and stream transactions are gracefully drained before tokens expire and sessions rotate.
- **Eliminated False 401s:** Prevents entity updates or snapshot requests from colliding with token refreshes.

### 2. Modern V3 Mode Alignment (Fixes Issue #1162)
For users on the modern Arlo experience (V3 Location/Arming modes):
- Mode changes triggered from Home Assistant or external apps now immediately propagate across all base stations and SmartHubs associated with the location.
- Desynced base stations force their mode updates through, preventing commands from being ignored when out-of-sync.
- Base station refresh cycles automatically reconcile modes with the location's current state upon stream reconnects.

### 3. Entity Platform & API Normalization
- **Spotlight & Floodlight Symmetry:** Entity controls now use normalized `pyaarlo` actions (`spotlight_on()`, `spotlight_off()`).
- **Stream Teardown:** Streamlined `async_stop_activity()` with direct non-blocking coroutine execution.
- **Recent Activity Accuracy:** Resolved false-triggering of `recentActivity` caused by periodic status broadcasts, and deduplicated successive state callbacks.

### 4. Configuration & Logging Cleanups
- **Deprecated `reconnect_every`:** Deprecated and ignored `reconnect_every` in configuration, relying entirely on modern dynamic token renewal.
- **Faster Recovery:** Lowered default request timeout from 60s to 15s for faster failure recovery.
- **Quieter Logs:** Periodic base station capability checks (`pingCapability`, `sirenState`) have been demoted to verbose packet debug (`vdebug`), drastically reducing debug log clutter.
- **Documentation Cleanup:** Moved legacy documentation, guides, and release notes into the `docs/` directory.

---

## 📋 Upgrading

To install or update to this pre-release via HACS, make sure **Show beta versions** is enabled under the Aarlo integration options, or point to the `v0.9.0-alpha.2` release tag.

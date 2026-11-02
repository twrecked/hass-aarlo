# 🚀 Aarlo v0.9.0-alpha.6 — Release Notes

> ### ⚠️ Alpha Pre-Release & Community Testing Notice
> This is the sixth alpha pre-release for the **Aarlo v0.9 native `asyncio` rewrite**.
>
> Version `0.9.0-alpha.6` focuses on **defensive configuration handling**, preventing **NoneType errors when loading empty or comment-only YAML configurations**, and **preserving default options across partial configuration entry updates** (resolving [PR #1179](https://github.com/twrecked/hass-aarlo/pull/1179) by [@mtthsbrd](https://github.com/mtthsbrd)).
>
> **Community testing and feedback are essential!** If you encounter bugs, regressions, or unhandled device packets, please [open a GitHub issue](https://github.com/twrecked/hass-aarlo/issues) with your hardware models and diagnostic logs.

---

## 🌟 What's New in v0.9.0-alpha.6

### 1. Defensive YAML Loading (PR #1179)
Resolves crashes during startup when `aarlo.yaml` or `configuration.yaml` contains an empty `aarlo:` block or a file containing only comments:
- **NoneType Protection:** Replaced direct `.get()` on the parsed YAML result with `(config or {}).get(COMPONENT_DOMAIN) or {}`.
- **Prevents Startup Failure:** Avoids `AttributeError: 'NoneType' object has no attribute 'get'` (when the YAML document parses to `None`) and `TypeError: 'NoneType' object is not iterable` (when `aarlo:` is present without sub-keys).
- **Smooth Transition for v0.9:** Since v0.9 encourages UI configuration and no longer requires `aarlo.yaml`, users migrating from legacy setups who cleared or commented out their YAML files will no longer experience crashes.

### 2. Default Options Preservation on Partial Updates (PR #1179)
Fixes secondary entity registration when editing configuration entries:
- **Default Overlay:** In `_merge()`, options are now initialized with `{**DEFAULT_OPTIONS, **(options or {})}` instead of only applying `DEFAULT_OPTIONS` when `options` was completely empty.
- **Entity Retention:** Prevents secondary entities (`binary_sensor_*`, `sensor_*`, and `switch_*`) from disappearing or becoming `unavailable` when only a subset of configuration keys (such as `backend`, `http_backend`, or `save_media_to`) are present in `entry.options`.

Special thanks to **[@mtthsbrd](https://github.com/mtthsbrd)** for identifying the issues and contributing the fix!

### 3. UI Re-authentication & Reconfiguration Support (Resolves Issue #1178)
Addresses credential updates and locked accounts when passwords change:
- **Automatic Re-authentication (`reauth`):** When Arlo rejects account credentials (such as Error `9015: Password not correct`), Aarlo now raises `ConfigEntryAuthFailed`. Home Assistant immediately prompts the user with an **"Attention Required: Reauthenticate"** banner on the dashboard, allowing them to enter the corrected password directly in the UI without modifying `.storage/core.config_entries` or deleting the integration.
- **Fast Auth Failure:** Bypasses futile connection retry loops when passwords are explicitly rejected by Arlo's cloud authentication service, preventing account lockouts and IP throttling.
- **Voluntary Reconfiguration (`reconfigure`):** Users can now click the three dots on the Aarlo integration card and select **"Reconfigure"** at any time to modify their Arlo username, password, or Two-Factor Authentication (2FA) mechanism and settings.

---

## 📋 Upgrading

To install or update to this pre-release via HACS, make sure **Show beta versions** is enabled under the Aarlo integration options, or point to the `v0.9.0-alpha.6` release tag.

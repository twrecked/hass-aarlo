# 🚀 Aarlo v0.9.0-alpha.7 — Release Notes

> ### ⚠️ Alpha Pre-Release & Community Testing Notice
> This is the seventh alpha pre-release for the **v0.9 native `asyncio` rewrite**.
> 
> Version `0.9.0-alpha.7` introduces **automated local media retention policies and disk space management**, preventing local disks from filling up with accumulated recordings, and bumps the underlying `pyaarlo` requirement to `v0.9.0-alpha.7`.
> 
> Feedback from users with diverse Arlo hardware remains vital! Please report any regressions or unhandled events on [GitHub Issues](https://github.com/twrecked/hass-aarlo/issues).

---

## 🌟 What's New in v0.9.0-alpha.7

### 1. Automated Media Retention (`media_retention_days`)
- **Configurable Retention Policy:** Users can now specify a retention period in days (e.g. `30`) to control how long locally downloaded recordings are kept on disk.
- **Manageable via UI & YAML:**
  - In the Home Assistant UI: **Settings** → **Devices & Services** → **Aarlo** → **Configure** → **General** settings.
  - In YAML configuration:
    ```yaml
    aarlo:
      save_media_to: "/config/media/${SN}/${Y}/${m}/${d}/${T}"
      media_retention_days: 30
    ```
- **Non-Blocking Daily Pruning:** Filesystem scanning and deletion run inside background worker threads (`loop.run_in_executor`), ensuring Home Assistant's event loop remains completely responsive.
- **Orphan Directory Pruning:** When old recordings are purged, empty date subdirectories (`YYYY/MM/DD/`) are pruned bottom-up without touching the base media folder.

### 2. Dependency Update
- Bumped `pyaarlo` requirement to `v0.9.0-alpha.7`.

---

## 📦 Upgrading to v0.9.0-alpha.7

To install or update to this pre-release via HACS, make sure **Show beta versions** is enabled under the Aarlo integration options, or point to the `v0.9.0-alpha.7` release tag.

Restart Home Assistant after updating.

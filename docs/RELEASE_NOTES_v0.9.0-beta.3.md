# 🚀 Aarlo v0.9.0-beta.3 — Release Notes

> Version `0.9.0-beta.3` adds diagnostics for shared Arlo accounts with restricted permissions and updates the underlying `pyaarlo` dependency to `v0.9.0-beta.3`.

---

## 🌟 What's New in v0.9.0-beta.3

### 1. Restricted Shared Access Detection & Repairs Issue
* **Permission Diagnostics:** Detects devices shared from a primary Arlo account that lack administrative privileges (`userRole != "ADMIN"`, typically `GUEST`).
* **Home Assistant Repairs Integration:** When restricted shared devices are detected during startup, Aarlo creates a Home Assistant **Repairs** issue explaining that control features, capabilities, and streaming will be restricted, with actionable instructions to enable "Allow Access Rights" in the primary Arlo app under **Settings → Access Control / Grant Access**.
* **Automatic Resolution:** Once access rights are granted in the Arlo mobile app and the integration is reloaded or restarted, the Repairs issue automatically resolves and clears.
* **Translations:** Provided localized Repairs issue titles and descriptions in both English and French.

### 2. Upstream Dependency Update (`pyaarlo==0.9.0-beta.3`)
* Pinned the integration's library requirement to `pyaarlo==0.9.0-beta.3`.
* Consumes upstream `is_shared`, `has_access_rights`, and `owner_id` device properties and startup diagnostic logging.

---

## 📦 Upgrading via HACS

To update to this beta release via HACS:
1. Open **HACS → Integrations → Aarlo**.
2. Select the three dots menu in the top right and choose **Redownload**.
3. Toggle **Show beta versions** on and select **v0.9.0-beta.3**.
4. Restart Home Assistant.

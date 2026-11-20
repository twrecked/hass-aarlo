# Aarlo v0.9.0-beta.6 — Release Notes

## Breaking change: Recent Activity

Recent Activity is now a Home Assistant binary sensor. It turns `on` when the camera detects activity and `off` when the recent-activity timer expires.

- Update dashboard, script, and automation references from `sensor.aarlo_<camera>_recent_activity` to `binary_sensor.aarlo_<camera>_recent_activity`. Check the entity registry for the exact new ID if you use a different naming scheme.
- Update state triggers and conditions to use `on` and `off` (`"on"` and `"off"` in YAML).
- Your enable/disable setting and the camera's `recent_activity` attribute are unchanged. After updating references, you can remove the old unavailable sensor entries. No reinstall is required.

PyArlo remains pinned to `v0.9.0-beta.5`. See the [v0.9 upgrade notes](../README.md#breaking-changes-when-upgrading-to-v09) for other changes.

## Upgrading via HACS

Back up Home Assistant. Open **HACS → Aarlo → Redownload**, enable beta versions, select `v0.9.0-beta.6`, and restart Home Assistant.

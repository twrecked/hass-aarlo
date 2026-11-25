# Aarlo v0.9.0-beta.8 — Release Notes

## WebRTC live view

Home Assistant now installs `pyaarlo==0.9.0b6` from PyPI without requiring Git. PyArlo uses its built-in SIP streaming model list when Arlo omits the capability, while still honoring explicit boolean values and recognizing SIP configuration objects.

This lets Aarlo select WebRTC, when enabled, for supported doorbells such as the AVD2001A and AVD4001A that previously fell back to HLS. If you reported pixelation in [#1156](https://github.com/twrecked/hass-aarlo/issues/1156), please retest live view; selecting WebRTC doesn't guarantee the pixelation is resolved.

## Upgrading via HACS

Back up Home Assistant. Open **HACS → Aarlo → Redownload**, enable beta versions, select `v0.9.0-beta.8`, and restart Home Assistant.

# Aarlo v0.9.0-beta.7 — Release Notes

## Installation fix

Home Assistant now installs `pyaarlo==0.9.0b5` from PyPI instead of cloning it from Git. This keeps the same PyArlo beta and bypasses the Git error reported on an older Synology Docker host in [#1156](https://github.com/twrecked/hass-aarlo/issues/1156). There are no streaming changes in this release.

## Upgrading via HACS

Back up Home Assistant. Open **HACS → Aarlo → Redownload**, enable beta versions, select `v0.9.0-beta.7`, and restart Home Assistant.

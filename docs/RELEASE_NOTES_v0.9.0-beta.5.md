# Aarlo v0.9.0-beta.5 — Release Notes

## Doorbell startup fix

- Update PyArlo to [v0.9.0-beta.5](https://github.com/twrecked/pyaarlo/releases/tag/v0.9.0-beta.5). Video doorbells that advertise only `Melody`, such as the `AVD2001A`, are no longer set up as media players. This avoids the unsupported `audioPlayback` request that returned `4000: Resource not found` at startup.
- Arlo Baby playback and devices that explicitly advertise `AudioPlayback` are unchanged.

## Upgrading via HACS

Open **HACS → Aarlo → Redownload**, enable beta versions, select `v0.9.0-beta.5`, and restart Home Assistant.

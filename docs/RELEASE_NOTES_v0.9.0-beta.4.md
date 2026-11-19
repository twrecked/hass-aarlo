# Aarlo v0.9.0-beta.4 — Release Notes

## Cloud recording

- `aarlo.camera_start_recording` now uses FFmpeg to keep the stream open without writing a temporary MP4. This avoids the `/tmp` path restriction reported in [#1135](https://github.com/twrecked/hass-aarlo/issues/1135) and avoids local MP4 timestamp errors.
- The integration pins `pyaarlo` to `v0.9.0-beta.4`. PyArlo checks the camera, base station, and matched Arlo location for the recording time zone. If none provides it, Aarlo uses Home Assistant's configured time zone.
- Recordings still appear in the Arlo library. Local media downloads and `save_media_to` are unchanged.

## Upgrading via HACS

Open **HACS → Aarlo → Redownload**, enable beta versions, select `v0.9.0-beta.4`, and restart Home Assistant.

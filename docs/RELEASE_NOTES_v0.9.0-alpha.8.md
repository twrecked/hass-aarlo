# 🚀 Aarlo v0.9.0-alpha.8 — Release Notes

> Version `0.9.0-alpha.8` introduces **native WebRTC camera streaming**, delivering sub-second live view startup, zero transcode overhead, peer-to-peer browser streaming, a global fallback switch, and updates the `pyaarlo` requirement to `v0.9.0-alpha.8`.
>
> **Special Thanks:** This release is based on reverse engineering, design, and foundational work ([PR #1153](https://github.com/twrecked/hass-aarlo/pull/1153) and [pyaarlo PR #210](https://github.com/twrecked/pyaarlo/pull/210)) by **Edwin Anne ([@edwin-anne](https://github.com/edwin-anne))**.

---

## 🌟 What's New in v0.9.0-alpha.8

### 1. Native Home Assistant WebRTC Streaming (`ArloSipCam`)
Arlo official applications negotiate live video over WebRTC signaled through SIP in a WebSocket:
* **Zero Transcoding**: Media flows directly peer-to-peer between your browser and Arlo Cloud/TURN servers. Home Assistant does not run `ffmpeg` or handle video packets on this path.
* **Instant Startup**: Live streams negotiate and establish in hundreds of milliseconds without buffering HLS segments.
* **Zero Configuration**: Aarlo queries Arlo Cloud capability documents during entity setup and automatically registers capable cameras as native WebRTC entities.
* **Trickle-ICE Splicing**: Buffers trickled browser ICE candidates and injects them directly into the offer SDP, ensuring compatibility with Arlo's SIP proxy.
* **STUN/TURN Integration**: Automatically acquires and refreshes Arlo STUN and TURN server credentials, passing them to the browser for reliable traversal through NAT and firewalls.

### 2. Full Backwards Compatibility & Reversion Switch
* **RTSP/HLS Preserved**: Older camera models that do not support SIP streaming remain standard `ArloCam` entities (RTSPS/HLS).
* **Global Fallback Toggle**: If you need to revert all cameras to the traditional RTSP/HLS stream relay, you can disable WebRTC in `aarlo.yaml`:
  ```yaml
  aarlo:
    webrtc: False
  ```

### 3. Requirements & Dependencies
* Updated `pyaarlo` dependency to `v0.9.0-alpha.8` featuring native `asyncio` SIP-over-WebSocket signaling.

---

## 📦 Upgrading to v0.9.0-alpha.8

To install or update to this pre-release via HACS, ensure **Show beta versions** is enabled under the Aarlo integration options, or point to the `v0.9.0-alpha.8` release tag.

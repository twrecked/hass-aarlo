# 🚀 Aarlo v0.9.0-alpha.5 — Release Notes

> ### ⚠️ Alpha Pre-Release & Community Testing Notice
> This is the fifth alpha pre-release for the **Aarlo v0.9 native `asyncio` rewrite**.
>
> Version `0.9.0-alpha.5` focuses on fixing **Server-Sent Events (SSE) event stream connectivity**, **chunk iteration**, and **clean stream teardown** with the default `curl_cffi` backend (resolving [Issue #1177](https://github.com/twrecked/hass-aarlo/issues/1177)), and updating the underlying `pyaarlo` requirement to `v0.9.0-alpha.5`.
>
> **Community testing and feedback are essential!** If you encounter bugs, regressions, or unhandled device packets, please [open a GitHub issue](https://github.com/twrecked/hass-aarlo/issues) with your hardware models and diagnostic logs.

---

## 🌟 What's New in v0.9.0-alpha.5

### 1. Fix SSE Stream Never Connecting (Fixes Issue #1177)
Resolves a bug where users running with `backend: sse` experienced perpetual connection failures (`connect failed 400`) followed by an `AttributeError` exception loop:
- **Host Header Normalization:** Removed `host: None` and `Content-Type: None` header assignments. In `curl_cffi`, assigning `None` told `libcurl` to strip the `Host:` header, causing Arlo's cloud edge servers to reject every SSE connection with `400 Bad Request`.
- **Native Async Generator Streaming:** Switched `AsyncSession` chunk iteration from `iter_content()` (synchronous generator) to `aiter_content()` (asynchronous generator), fixing `AttributeError: 'generator' object has no attribute '__anext__'`.
- **Clean Stream Teardown & Handle Safety:** Cleanly cancels the background streaming task and unblocks the chunk queue on integration reload or restart, preventing shutdown hangs.

### 2. Under-the-Hood `pyaarlo` Improvements (`v0.9.0-alpha.5`)
Inherits all stability updates from `pyaarlo` v0.9.0-alpha.5.

---

## 📋 Upgrading

To install or update to this pre-release via HACS, make sure **Show beta versions** is enabled under the Aarlo integration options, or point to the `v0.9.0-alpha.5` release tag.

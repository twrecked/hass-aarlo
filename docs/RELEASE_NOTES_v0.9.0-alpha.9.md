# 🚀 Aarlo v0.9.0-alpha.9 — Release Notes

> Version `0.9.0-alpha.9` modernizes entity naming across all platforms with `_attr_has_entity_name = True`, introduces dynamic 2FA factor selection during setup and re-authentication (PR #1184 by Edwin ANNE), unifies camera spotlights and floodlights directly from PyArlo, adds Home Assistant Device Registry device removal support, and updates the `pyaarlo` requirement to `v0.9.0-alpha.9`.
>
> **Special Thanks:** Dynamic 2FA factor selection, resumable setup flow, and translations contributed by **Edwin ANNE ([@edwin-anne](https://github.com/edwin-anne))** in [PR #1184](https://github.com/twrecked/hass-aarlo/pull/1184).

---

## 🌟 What's New in v0.9.0-alpha.9

### 1. Modern Entity Naming Architecture (`_attr_has_entity_name = True`)
Entities across all platforms (`camera`, `light`, `siren`, `sensor`, `binary_sensor`, `switch`, `alarm_control_panel`, `media_player`) now adhere to modern Home Assistant entity naming standards:
* **Clean Device Pages**: Child and functional entities are given functional names only (e.g., `"Battery Level"`, `"Motion"`, `"Spotlight"`, `"Siren"`, `"Snapshot"`), eliminating redundant device names under device cards (no more `"Battery Level Car Port Light"` under `"Car Port Light"`).
* **Primary Device Entities**: Cameras, standalone lights, alarm control panels, and media players set `_attr_name = None`, letting Home Assistant automatically name the primary entity after the device.
* **Preserved `aarlo_` Entity ID Prefix**: All generated entity IDs preserve the clean `aarlo_` prefix (`sensor.aarlo_car_port_light_battery_level`, `light.aarlo_car_port_light`, `light.aarlo_driveway_spotlight`) using `suggested_object_id`.
* **Zero Automation / Dashboard Breakage**: Existing installations retain their current `entity_id` mappings across upgrades thanks to stable `unique_id` definitions.

### 2. Interactive 2FA Factor Selection During Setup & Reauth (PR #1184)
*Contributed by [Edwin ANNE](https://github.com/edwin-anne) (@edwin-anne).*
* **Zero Guesswork**: The setup wizard no longer asks users to guess a 2FA mechanism up front. It takes your credentials, logs in via PyArlo's `ArloLogin`, and dynamically displays the 2FA methods actually configured on your Arlo account (e.g., `"Pixel 9 (Arlo app)"`, `"home@example.com (Email)"`).
* **In-UI Push Approval**: Selecting the Arlo app displays a progress spinner while you approve the prompt on your phone (waiting up to 5 minutes, stopping immediately on denial).
* **Email & SMS Code Entry**: Entering an incorrect code prompts for an inline retry without starting over.
* **Trusted Browser Session**: Options and paired user agents match the runtime, ensuring the session and cookies saved during setup are reused across restarts without prompting for 2FA again.
* **Manual Setup Fallback**: A checkbox allows configuring automated IMAP mailbox code retrieval if preferred.
* **Localization**: Full English (`en`) and French (`fr`) translations.

### 3. Unified Light Platform (`pyaarlo::ArloLight`)
* `custom_components/aarlo/light.py` directly consumes `pyaarlo::ArloLight` objects from `arlo.lights`, cleanly mapping standalone smart lights, camera spotlights, and camera floodlights.
* Spotlight and floodlight controls natively call `turn_on()` and `turn_off()` with percentage brightness scaling.
* Automatically prevents generating duplicate battery, motion, and connectivity sensors for camera child lights in `sensor.py` and `binary_sensor.py`.

### 4. Device Registry Device Removal (`async_remove_config_entry_device`)
* Allows users to remove retired or orphaned Arlo devices directly from Home Assistant's **Settings -> Devices** interface.
* Verifies against active Arlo Cloud hardware before allowing deletion, preventing accidental removal of live devices while cleanly purging old ones.

### 5. Requirements & Dependencies
* Updated `pyaarlo` requirement to `v0.9.0-alpha.9` featuring dynamic cloud capability document resolution and unified camera lights.

---

## 📦 Upgrading to v0.9.0-alpha.9

To install or update to this pre-release via HACS, ensure **Show beta versions** is enabled under the Aarlo integration options, or point to the `v0.9.0-alpha.9` release tag.

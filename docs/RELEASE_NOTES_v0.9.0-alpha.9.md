# 🚀 Aarlo v0.9.0-alpha.9 — Release Notes

> Version `0.9.0-alpha.9` modernizes entity naming across all platforms with `_attr_has_entity_name = True`, unifies camera spotlights and floodlights directly from PyArlo, adds Home Assistant Device Registry device removal support, and updates the `pyaarlo` requirement to `v0.9.0-alpha.9`.

---

## 🌟 What's New in v0.9.0-alpha.9

### 1. Modern Entity Naming Architecture (`_attr_has_entity_name = True`)
Entities across all platforms (`camera`, `light`, `siren`, `sensor`, `binary_sensor`, `switch`, `alarm_control_panel`, `media_player`) now adhere to modern Home Assistant entity naming standards:
* **Clean Device Pages**: Child and functional entities are given functional names only (e.g., `"Battery Level"`, `"Motion"`, `"Spotlight"`, `"Siren"`, `"Snapshot"`), eliminating redundant device names under device cards (no more `"Battery Level Car Port Light"` under `"Car Port Light"`).
* **Primary Device Entities**: Cameras, standalone lights, alarm control panels, and media players set `_attr_name = None`, letting Home Assistant automatically name the primary entity after the device.
* **Preserved `aarlo_` Entity ID Prefix**: All generated entity IDs preserve the clean `aarlo_` prefix (`sensor.aarlo_car_port_light_battery_level`, `light.aarlo_car_port_light`, `light.aarlo_driveway_spotlight`) using `suggested_object_id`.
* **Zero Automation / Dashboard Breakage**: Existing installations retain their current `entity_id` mappings across upgrades thanks to stable `unique_id` definitions.

### 2. Unified Light Platform (`pyaarlo::ArloLight`)
* `custom_components/aarlo/light.py` directly consumes `pyaarlo::ArloLight` objects from `arlo.lights`, cleanly mapping standalone smart lights, camera spotlights, and camera floodlights.
* Spotlight and floodlight controls natively call `turn_on()` and `turn_off()` with percentage brightness scaling.
* Automatically prevents generating duplicate battery, motion, and connectivity sensors for camera child lights in `sensor.py` and `binary_sensor.py`.

### 3. Device Registry Device Removal (`async_remove_config_entry_device`)
* Allows users to remove retired or orphaned Arlo devices directly from Home Assistant's **Settings -> Devices** interface.
* Verifies against active Arlo Cloud hardware before allowing deletion, preventing accidental removal of live devices while cleanly purging old ones.

### 4. Lifecycle Session Cleanup (`async_remove_entry`)
* Automatically removes `.session`, `.cookies`, and cache files from `.aarlo/` when the integration is deleted from Home Assistant, ensuring clean re-adds.

### 5. Requirements & Dependencies
* Updated `pyaarlo` requirement to `v0.9.0-alpha.9` featuring dynamic cloud capability document resolution and unified camera lights.

---

## 📦 Upgrading to v0.9.0-alpha.9

To install or update to this pre-release via HACS, ensure **Show beta versions** is enabled under the Aarlo integration options, or point to the `v0.9.0-alpha.9` release tag.

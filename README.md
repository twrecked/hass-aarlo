# hass-aarlo
Asynchronous Arlo Component for Home Assistant

Copy all directories into the `custom_component` directory.

Replace all instance of the `arlo` platform with `aalro` in your home assistant configuration files - for example

```
aarlo:
  username: !secret arlo_username
  password: !secret arlo_password
  scan_interval: 300
  
camera:
  - platform: aarlo
    ffmpeg_arguments: '-pred 1 -q:v 2'

alarm_control_panel:
  - platform: aarlo
    home_mode_name: Home
    away_mode_name: Armed
    
- platform: aarlo
  monitored_conditions:
  - motion
  - sound
  
- platform: aarlo
  monitored_conditions:
  - last_capture
  - total_cameras
  - battery_level
  - captured_today
  - signal_strength
```

Restart your home assistant system.

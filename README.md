# hass-aarlo

## Table of Contents
- [Introduction](#introduction)
   - [Supported Features](#supported-features)
   - [Notes](#notes)
   - [Thanks](#thanks)
- [Installation](#installation)
   - [HACS](#hacs)
   - [Manually](#manually)
   - [From Script](#from-script)
- [Configuration](#configuration)
   - [Moving from Arlo](#moving-from-arlo)
   - [Main Configuration](#main-configuration)
   - [Alarm Configuration](#alarm-configuration)
   - [Camera Configuration](#camera-configuration)
   - [Binary Sensor Configuration](#binary-sensor-configuration)
   - [Sensor Configuration](#sensor-configuration)
   - [Light Configuration](#light-configuration)
   - [Switch Configuration](#switch-configuration)
   - [Media Player Configuration](#media-player-configuration)
   - [Custom Lovelace Card Configuration](#custom-lovelace-card-configuration)
- [Other](#other)
   - [Best Practises and Known Limitations](#best-practices-and-known-limitations)
   - [Debugging](#debugging)
- [Advanced Use](#advanced)
   - [All Parameters](#all-parameters)
   - [Services](#services)
   - [Automations](#automations)
      - [Update camera snapshot 3 seconds after a recording event happens](#update-camera-snapshot-3-seconds-after-a-recording-event-happens)
      - [Begin recording when an entity changes state](#begin-recording-when-an-entity-changes-state)
   - [Web Sockets](#web-sockets)
   - [Streaming](#streaming)
- [To Do](#to-do)

## Introduction
This is the Asynchronous Arlo component for [Home Assistant](https://www.home-assistant.io/).

The component is based on the original [Arlo component](https://www.home-assistant.io/integrations/arlo/) and it can operate as replacement with minimal configuration changes.

The component uses the same API as the [Arlo Website](https://my.arlo.com/#/cameras). The component will login to the backend, open an evenstream and provide realtime information on the state of your Arlo devices.

The component support base stations, cameras, lights and doorbells.

### Supported Features
* Base station mode changes
* Camera motion detection
* Camera audio detection
* Door bell motion detection
* Door bell button press
* Current Camera status
* Saving of state across restarts
* Camera on/off
* Request camera thumbnail updates
* Start / stop camera recording
* Direct video streaming from Arlo where possible
* Siren when triggering an alarm
* Live Streaming
* Pseudo Switches for activing sirens and taking snapshots
* Lights
* Arlo Baby media player

### Notes
This document assumes you are familiar with Home Assistant setup and configuration.

Wherever you see `/config` in this README it refers to your Home Assistant configuration directory. For example, for my installation it's `/home/steve/ha` which is mapped to `/config` in my docker container.

### Thanks
Many thanks to:
* [Pyarlo](https://github.com/tchellomello/python-arlo) and [Arlo](https://github.com/jeffreydwalter/arlo) for doing all the hard work figuring the API out and the free Python lesson!
* [sseclient](https://github.com/btubbs/sseclient) for reading from the event stream
* [Button Card](https://github.com/kuuji/button-card/blob/master/button-card.js) for a working lovelace card I could understand
* [![JetBrains](/images/jetbrains.svg)](https://www.jetbrains.com/?from=hass-aarlo) for the excellent **PyCharm IDE** and providing me with an open source license to speed up the project development.


## Installation

### HACS
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
Aarlo is part of the default HACS store. If you're not interested in development branches this is the easiest way to install.

### Manually
Copy the `aarlo` directory into your `/config/custom_components` directory.

### From Script
Run the install script. Run it once to make sure the operations look sane and run it a second time with the `go` paramater to do the actual work. If you update just rerun the script, it will overwrite all installed files.

```sh
install /config
# check output looks good
install go /config
```

## Configuration

### Moving From Arlo
Start by replacing all instances of `arlo` with `aarlo` in your Home Assistant configuration files.

To support motion and audio capture add `aarlo` as a platform to the `binary_sensor` list. To support viewing library recordings look at [Aarlo Lovelace Card](https://github.com/twrecked/lovelace-hass-aarlo).

### Creating a Login
Aarlo needs a dedicated Aarlo login. If you try to reuse an existing login - for example, the login from the Arlo app on your phone - the app and this component will constantly fight to login.

When you have created the Aarlo login, share the devices you want to share and give the Aarlo user admin access.

### Main Configuration
The following configuration is the minimim needed.

```yaml
aarlo:
  username: !secret arlo_username
  password: !secret arlo_password
```

The following configuration adds some connection keep alive mechanisms to try to work around limitations in using the Arlo web API.

```yaml
aarlo:
  username: !secret arlo_username
  password: !secret arlo_password
  refresh_devices_every: 2
  stream_timeout: 120
```

* `refresh_devices_every` tells the code to reload the device list every 2 hours.
* `stream_timeout` tells the event stream to restart after 2 minutes of inactivity.

If you still struggle with connectivity you can add the following:

```yaml
  reconnect_every: 90
```

* `reconnect_every` force the system to logout and log back in, in this case every 90 minutes.

### Alarm Configuration

The following enables and configures the base stations.

```yaml
alarm_control_panel:
  - platform: aarlo
    home_mode_name: home
    away_mode_name: armed
    night_mode_name: night
    trigger_time: 30
    alarm_volume: 8
```

* Arlo does not have a built in `away`, `home` or `night` mode. Use `away_mode_name`, `home_mode_name` and `night_mode_name` to map them to one of your custom Arlo modes. By default `away_mode_name` maps to `Armed`. If you don't map all your modes in there is a possibility the alarm panel will appear blank. Names are case insensitive.
* `trigger_time` determines how long, in seconds, the triggered alarm will sound
* `alarm_volume` determine how loud, from 1 to 8, the triggered alarm will sound

See [here](https://www.home-assistant.io/components/arlo/#alarm) for more information on mode names. 

### Camera Configuration

The following enables any cameras.

```yaml
camera:
  - platform: aarlo
```

### Binary Sensor Configuration

The following enables and configures the binary sensors.

```yaml
binary_sensor:
  - platform: aarlo
    monitored_conditions:
    - motion
    - sound
    - ding
```

Items on the `monitored_conditions` can be one or more of the following:

* `motion` fires when a camera, doorbell or light detects motion.
* `sound` fires when a camera detects a sound.
* `ding` fires when a doorbell is pressed.

The Arlo backend sends the notifications on the event stream so they are (almost) real time.

### Sensor Configuration

The following enables and configures the sensors.

```yaml
sensor:
  - platform: aarlo
    monitored_conditions:
    - total_cameras
    - last_capture
    - recent_activity
    - captured_today
    - battery_level
    - signal_strength
    - temperature
    - humidity
    - air_quality
```

Items on the `monitored_conditions` can be one or more of the following:

* `total_cameras` is a global sensor showing the number of cameras detected.

The rest of the sensors appear per camera.

* `last_capture` The last time an event was captured by this camera.
* `recent_activity` Is `on` if activity was recently seen on the camera.
* `captured_today` The number of events captured by the camera today.
* `battery_level` The percentage of battery remaining.
* `signal_strength` The WiFi signal strength of the camera.
* `temperature` The temperature in the room where the camera is, if supported.
* `humidity` The humidity in the room where the camera is, if supported.
* `air_quality` The air quality in the room where the camera is, if supported.

### Light Configuration

The following enables any lights:

```yaml
light:
  - platform: aarlo
```

### Switch Configuration

The following enables and configures some pseudo switches:

```yaml
switch:
  - platform: aarlo
    siren: True
    all_sirens: True
    snapshot: True
    siren_volume: 1
    siren_duration: 10
```

* `siren` If `True`, will create a switch for each siren device that allows your to turn it on or off.
* `all_sirens` If `True`, will create a switch for all the siren devices that allows you to turn them all on and off.
* `snapshot` If `True`, will create a switch for each camera to allow you to take a snapshot.

`siren_volume` and `siren_duration` controls how loud, from 1 to 10, the siren is and how long, in seconds, it sounds.

### Media Player Configuration

The following enables media player for supported devices:

```yaml
media_player:
  - platform: aarlo
```

### Custom Lovelace Card Configuration

A custom Lovelace card which is based on the `picture-glance` can be found here: https://github.com/twrecked/lovelace-hass-aarlo

The custom Lovelace card allows access to the video recordings library and presents customizable camera information on the camera feed. It was influenced by the Arlo web interface camera view.

*This piece is optional, `aarlo` will work with the standard Lovelace cards.*


## Other

### Supported Features
* Base station mode changes
* Camera motion detection
* Camera audio detection
* Camera on/off
* Current Camera status
* Request camera thumbnail updates
* Start / stop camera recording
* Door bell motion detection
* Door bell button press
* Direct video streaming from Arlo where possible
* Siren when triggering an alarm
* Live Streaming
* Pseudo Switches for activing sirens and taking snapshots
* Lights on/off
* Light motion detection
* Arlo Baby media player
* Saving of state across restarts

### Naming
Entity ID naming follows this pattern `component-type.aarlo_lower_case_name_with_underscores`.

For example, a camera called "Front Door" will have an entity id of `camera.aarlo_front_door`.

### Best Practises and Known Limitations
The component uses the Arlo webapi.
* There is no documentation so the API has been reverse engineered using browser debug tools.
* There is no support for smart features, you only get motion detection notifications, not what caused the notification. (Although, you can pipe a snapshot into deepstack...)
* Streaming times out after 30 minutes.
* The webapi doesn't seem like it was really designed for permanent connections so the system will sometimes appear to lock up. Various work arounds are in the code and can be configured at the `arlo` component level. See next paragraph.

If you do find the component locks up after a while (I've seen reports of hours, days or weeks), you can add the following to the main configuration. Start from the top and work down:
* `refresh_devices_every`, tell Aarlo to request the device list every so often. This will sometimes prevent the back end from aging you out. The value is in hours and a good starting point is 3.
* `stream_timeout`, tell Aarlo to close and reopen the event stream after a certain period of inactivity. Aarlo will send keep alive every minute so a good starting point is 180 seconds.
* `reconnect_every`, tell Aarlo to logout and back in every so often. This establishes a new session at the risk of losing an event notification. The value is minutes and a good starting point is 90.
* `request_timout`, the amount of time to allow for a http request to work. A good starting point is 120 seconds.

Unify your alarm mode names across all your base stations. There is no way to specify different mode names for each device.

Alro will allow shared accounts to give cameras their own name. If you find cameras appearing with unexpected names (or not appearing at all), log into the Arlo web interface with your Home Assistant account and make sure the camera names are correct.

### Debugging

## Advanced Use

### All Parameters
The following additional parameters can be specified against the aarlo platform for more granular control:

| Field  | Type | Default | Description |
| ------ | ---- | ------- | ----------- |
| `db_motion_time`        | integer  | `30` (s)                | Duration of doorbell motion. (Arlo doorbell only indicates motion is present not that it stops) |
| `db_ding_time`          | integer  | `60` (s)                | Duration of doorbell press. (Arlo doorbell only indicates doorbell was pressed, not that it was released) |
| `recent_time`           | integer  | `600` (s)               | Used to hold the cameras in a recent activity state after a recording or streaming event. (Streaming & recording can be over in a few seconds, without this the camera will revert to idle, possibly looking like nothing has happened.) |
| `last_format`           | strftime | `'%m-%d %H:%M'`         | Display format of last captured time  |
| `http_connections`      | integer  | `5`                     | Adjust the number http connections pools to cache |
| `http_max_size`         | integer  | `10`                    | Adjust the maximum number connects to save in the pool |
| `request_timeout`       | time period  | `60`                | Timeout for requests sent to Arlo server. 0 means no timeout. |
| `stream_timeout`        | time period  | `0`                 | Timeout for inactivity on the Arlo event stream. 0 means no timeout. Used to help with Arlo components becoming unresponsive. |
| `reconnect_every`       | integer  | `0` (minutes)           | If not 0 then force a logout every `reconect_entry` time period. Used to help with Arlo components becoming unresponsive.|
| `refresh_devices_every` | integer  | `0` (hours)             | Used to force a refresh every x hours. 0 = no refreshing. Used to resolve issue with mode changes failing after several days of use |
| `packet_dump`           | boolean  | `False`                 | Causes aarlo to store all the packets it sees in `/config/.aarlo/packets.dump` file. Only really needed for debugging and reverse engineering the API. |
| `conf_dir`              | string   | `'/config/.aarlo'`      | Location to store component state. (The default is fine for hass.io, docker, and virtualenv systems - don't set this value unless asked to.) |
| `host`                  | string   | `https://my.arlo.com`   | Sets the host aarlo will connect to |
| `no_media_upload`       | boolean  | `False`                 | Used as a workaround for Arlo issues where the camera never gets a media upload notification. (Not needed in most cases.) |
| `mode_api`              | string   | `auto`                  | available options: [`v1`, `v2`] You can override this by setting this option to  v1 or v2 to use the old or new version exclusively. The default is  auto, choose based on device |

### Camera Statuses

The following camera statuses are reported:
  * `Idle` camera is doing nothing
  * `Turned Off` user has turned the camera off
  * `Recording` camera has detected something and is recording
  * `Streaming` camera is streaming live video to another other login
  * `Taking Snapshot` camers is updating the thumbnail
  * `Recently Active` camera has seen activity within the last few minutes
  * `Too Cold!` the camera is shutdown until it warms up

### Services

The component provides the following services:

| Service | Parameters | Description |
|---------|------------|-------------|
| `camera.aarlo_request_snapshot` | `entity_id` - camera to get snapshot from | This requests a snapshot be taken. Camera will move from  taking_snapshot state when finished |
| `camera.aarlo_request_snapshot_to_file` | `entity_id` - camera to get snapshot from<br/>`filename` - where to save snapshot | This requests a snapshot be taken and written to the passed file. Camera will move from  taking_snapshot state when finished |
| `camera.aarlo_stop_activity` | `entity_id` - camera to get snapshot from | This moves the camera into the idle state. Can be used to stop streaming |
| `camera.start_recording` | `entity_id` - camera to start recording<br>`duration` - amount of time in seconds to record | Begins video capture from the specified camera |
| `camera.stop_recording` | `entity_id` - camera to stop recording | Ends video capture from the specified camera |
| `alarm_control_panel.aarlo_set_mode` | `entity_id` - camera to get snapshot from<br/>`mode` - custom mode to change to | Set the alarm to a custom mode |

### Automations

#### Update camera snapshot 3 seconds after a recording event happens

```yaml
- id: 'automation-0100'
  alias: Camera Snapshot
  trigger:
  - entity_id: camera.aarlo_camera1,camera.aarlo_camera2
    for: 00:00:03
    from: 'idle'
    platform: state
    to: 'recording'
  - entity_id: camera.aarlo_camera1,camera.aarlo_camera2
    for: 00:00:03
    from: 'recently active'
    platform: state
    to: 'recording'
  condition: []
  action:
  - data_template:
      entity_id: "{{ trigger.entity_id }}"
    service: camera.aarlo_request_snapshot
```

#### Begin recording when an entity changes state

```yaml
- id: 'automation-0101'
  alias: Record video when garage opens
  description: ''
  trigger:
  - entity_id: cover.garage_door
    platform: state
    to: open
  condition: []
  action:
  - data:
      duration: 300
      entity_id: camera.aarlo_garage
    service: camera.aarlo_start_recording
```

### Web Sockets

The component provides the following extra web sockets:

| Service | Parameters | Description |
|---------|------------|-------------|
| aarlo_video_url | <ul><li>`entity_id` - camera to get details from</li><ul> | Request details of the last recorded video. Returns: <ul><li>`url` - video url</li><li>`url_type` - video type</li><li>`thumbnail` - thumbnail image url</li><li>`thumbnail_type` - thumbnail image type</li></ul> |
| aarlo_library | <ul><li>`at-most` - return at most this number of entries</li><ul> | Request up the details of `at-most` recently recorded videos. Returns an array of:<ul><li>`created_at`: unix time stamp</li><li>`created_at_pretty`: pretty version of the create time</li><li>`url`: URL of the video</li><li>`url_type`: video type</li><li>`thumbnail`: URL of the thumbnail</li><li>`thumbnail_type`: thumbnail type</li><li>`object`: object in the video that triggered the capture</li><li>`object_region`: region in the video that triggered the capture</li></ul> |
| aarlo_stream_url | <ul><li>`entity_id` -  camera to get snapshot from</li><li>`filename` - where to save snapshot | Ask the camera to start streaming. Returns:<ul><li>`url` - URL of the video stream</li></ul> |
| aarlo_snapshot_image | <ul><li>`entity_id` -  camera to get snapshot from</li></ul> | Request a snapshot. Returns image details: <ul><li>`content_type`: the image type</li><li>`content`: the image</li></ul> |
| aarlo_stop_activity | <ul><li>`entity_id` - camera to stop activity on</li></ul> | Stop all the activity in the camera. Returns: <ul><li>`stopped`: True if stop request went in</li></ul> |

### Streaming

Streaming now works "out of the box" for HassOS and Docker installs. To get streaming working in `virtualenv` you still need to make sure a couple of libraries are installed. For `ubuntu` the following works:
```
source your-env/bin/activate
sudo apt install libavformat-dev
sudo apt install libavdevice-dev
pip install av==6.1.2
```

Set `image_click` to `play` on the aarlo glance card.

If you are still having issues please read these 3 posts:
   * https://github.com/twrecked/hass-aarlo/issues/55
   * https://community.home-assistant.io/t/arlo-replacement-pyarlo-module/93511/293
   * https://community.home-assistant.io/t/arlo-replacement-pyarlo-module/93511/431?u=sherrell

## To Do

* coloured lights
* custom mode - like SmartThings to better control motion detection
* use asyncio loop internally


# hass-aarlo

## 2FA Support

This release contains beta 2FA support. It works by requesting an email with the
one-time code and then making an IMAP connection to your email provider and
reading the code from the email Arlo sends.

There is a **lot** that can go wrong with this - for starters, I've only tested
it in English - but to get it working add the following configuration (with the
correct values obviously) - to `aarlo:`

```yaml
  tfa_host: imap.gmail.com
  tfa_username: your.email.account@gmail.com
  tfa_password: roygbiv

```

For gmail users, the following
[help](https://support.google.com/accounts/answer/185833?hl=en) is useful.

Finally, if you haven't enabled 2FA you don't need to do this.


## Notice of Future Breaking Changes

### The custom services are moving into the `aarlo` domain.

This release moves all the component services in the `aarlo` domain. This is
their correct location and allows Home Assistant to use the component's
`services.yaml` file to provide help with the services.

To allow you to transition and test your scripts the old, incorrectly located,
services will remain for a while. My plan is to remove them in a few months. If
you move all your code over to the new services you can add the
`hide_deprecated_services` option to your configuration to hide these old
services.

See [Services](#advanced-services) for more information.


## Table of Contents
- [Introduction](#introduction)
- [Installation](#installation)
- [Configuration](#configuration)
   - [Moving from Arlo](#configuration-moving)
   - [Creating a Login](#configuration-login)
   - [Main Configuration](#configuration-main)
   - [Alarm Configuration](#configuration-alarm)
   - [Camera Configuration](#configuration-camera)
   - [Binary Sensor Configuration](#configuration-binary)
   - [Sensor Configuration](#configuration-sensor)
   - [Light Configuration](#configuration-light)
   - [Switch Configuration](#configuration-switch)
   - [Media Player Configuration](#configuration-media)
   - [Custom Lovelace Card Configuration](#configuration-lovelace)
- [Other](#other)
   - [Naming](#other-naming)
   - [Best Practises and Known Limitations](#other-best)
   - [Debugging](#other-debugging)
   - [Hiding Sensitive Data](#other-sensitive)
   - [Adding Devices](#other-adding)
- [Advanced Use](#advanced)
   - [All Parameters](#advanced-parameters)
   - [Camera Statuses](#advanced-statuses)
   - [Services](#advanced-services)
   - [Web Sockets](#advanced-websockets)
   - [Automation Examples](#advanced-automations)
   - [Streaming](#advanced-streaming)
- [2 Factor Authentication](#2fa)
   - [IMAP](#2fa-automatic)
   - [REST API](#sfa-rest-api)
- [To Do](#to-do)


<a name="introduction"></a>
## Introduction
Aarlo is an Asynchronous Arlo component for [Home
Assistant](https://www.home-assistant.io/), it uses the [Arlo
Website](https://my.arlo.com/#/cameras) APIs and supports base stations,
cameras, lights and doorbells.

Aarlo is based on the original [Arlo
component](https://www.home-assistant.io/integrations/arlo/) and it can operate
as replacement with minimal configuration changes.

Aarlo also provides a custom [Lovelace
Card](https://github.com/twrecked/lovelace-hass-aarlo), which overlays a
camera's last snapshot with its current status and allows access to the cameras
recording library and live streaming.

<a name="introduction-features"></a>
#### Features

Aarlo provides:
- Access to cameras, base stations, sirens, doorbells and lights.
- Asynchronous, almost immediate, notification of motion, sound and button press events.
- Ability to view library recordings, take snapshots and direct stream from cameras.
- Tracking of environmental stats from certain base station types.
- Special switches to trip alarms and take snapshots from cameras.
- Enhanced state notifications.
- Media player support for select devices.

<a name="introduction-notes"></a>
#### Notes
This document assumes you are familiar with Home Assistant setup and configuration.

Wherever you see `/config` in this documenent it refers to your Home Assistant
configuration directory. For example, for my installation it's `/home/steve/ha`
which is mapped to `/config` by my docker container.

<a name="introduction-thanks"></a>
#### Thanks
Many thanks to:
* [Pyarlo](https://github.com/tchellomello/python-arlo) and
  [Arlo](https://github.com/jeffreydwalter/arlo) for doing all the hard work
  figuring the API out and the free Python lesson!
* [sseclient](https://github.com/btubbs/sseclient) for reading from the event
  stream
* [Button Card](https://github.com/kuuji/button-card/blob/master/button-card.js)
  for a working lovelace card I could understand
* [JetBrains](https://www.jetbrains.com/?from=hass-aarlo) for the excellent
  **PyCharm IDE** and providing me with an open source license to speed up the
  project development.
  
  [![JetBrains](/images/jetbrains.svg)](https://www.jetbrains.com/?from=hass-aarlo)


<a name="installation"></a>
## Installation

<a name="installation-hacs"></a>
#### HACS
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

Aarlo is part of the default HACS store. If you're not interested in development
branches this is the easiest way to install.

<a name="installation-manually"></a>
#### Manually
Copy the `aarlo` directory into your `/config/custom_components` directory.

<a name="installation-from-script"></a>
#### From Script
Run the install script. Run it once to make sure the operations look sane and run it a
second time with the `go` paramater to do the actual work. If you update just rerun the
script, it will overwrite all installed files.

```sh
install /config
# check output looks good
install go /config
```

<a name="configuration"></a>
## Configuration

<a name="configuration-moving"></a>
### Moving From Arlo
You can replace all instances of `arlo` with `aarlo` in your Home Assistant configuration
files to start using Aarlo. The following sections detail new configuration items you can
use to add extra functionality to your new Aarlo component.

You can also run Arlo and Aarlo side by side but you will need to create an Aarlo specific
login.

<a name="configuration-login"></a>
### Creating a Login
_If you are replacing the original Arlo component you don't need to do this step._

Aarlo needs a dedicated Aarlo login. If you try to reuse an existing login - for example,
the login from the Arlo app on your phone - the app and this component will constantly
fight to login.

When you have created the Aarlo login, from your original Arlo account grant access to any
devices you want to share and give the Aarlo user admin access.

<a name="configuration-main"></a>
### Main Configuration
The following configuration is the minimim needed.

```yaml
aarlo:
  username: !secret arlo_username
  password: !secret arlo_password
```

The following configuration adds some connection keep alive mechanisms to try to work
around limitations in using the Arlo web API.

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

<a name="configuration-alarm"></a>
### Alarm Configuration

The following enables and configures the base stations.

```yaml
alarm_control_panel:
  - platform: aarlo
    away_mode_name: armed
    home_mode_name: home
    night_mode_name: night
    trigger_time: 30
    alarm_volume: 8
```

* `away_mode_name` Arlo mode to use when setting alarm to `Armed Away`. Default value is
  `armed` which maps to Arlo's default `Armed` mode.
* `home_mode_name` Arlo mode to use when setting alarm to `Armed Home`. Default value
  `home`.
* `night_mode_name` Arlo mode to use when setting alarm to `Armed Night`. Default value
  `night`.
* `trigger_time` determines how long, in seconds, the triggered alarm will sound
* `alarm_volume` determine how loud, from 1 to 8, the triggered alarm will sound

Arlo does not have a built in `home` or `night` mode. If you need them create a custom
mode in Arlo and `home_mode_name` and `night_mode_name` to map to them. You don't need to
map all modes - I don't use `night_mode`. Names are case insensitive. Using duplicate
names will cause problems, for example, mapping both `away` and `night` mode to `armed`
will work when setting the mode from Home Assistant but might not show the correct mode if
you change it in the Arlo app. 

See [here](https://www.home-assistant.io/components/arlo/#alarm) for more information on
mode names. 


<a name="configuration-camera"></a>
### Camera Configuration

The following enables any cameras.

```yaml
camera:
  - platform: aarlo
```

<a name="configuration-binary"></a>
### Binary Sensor Configuration

The following enables and configures the binary sensors.

```yaml
binary_sensor:
  - platform: aarlo
    monitored_conditions:
    - motion
    - sound
    - ding
    - cry
    - connectivity
```

Items on the `monitored_conditions` can be one or more of the following:

* `motion` fires when a camera, doorbell or light detects motion.
* `sound` fires when a camera detects a sound.
* `ding` fires when a doorbell is pressed.
* `cry` fires when crying is detected (ArloBaby only)
* `connectivty` is true when Arlo a device is connected

The Arlo backend sends the notifications on the event stream so they are (almost) real
time.

<a name="configuration-sensor"></a>
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

<a name="configuration-light"></a>
### Light Configuration

The following enables any lights:

```yaml
light:
  - platform: aarlo
```
The component supports the standard Arlo lights, Arlo Baby lights and Arlo Pro 3
Floodlight. There is one noticable quirk, you can adjust the brightness of a light while
it is on but the change will not happen until you turn the light off and back on again.
This how the official web interface works. 

This does not apply to the Pro 3 Floodlight as the brightness 
can be changed while it is turned on.
 
<a name="configuration-switch"></a>
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

* `siren` If `True`, will create a switch for each siren device that allows your to turn
  it on or off.
* `all_sirens` If `True`, will create a switch for all the siren devices that allows you
  to turn them all on and off.
* `snapshot` If `True`, will create a switch for each camera to allow you to take a
  snapshot.

`siren_volume` and `siren_duration` controls how loud, from 1 to 10, the siren is and how
long, in seconds, it sounds.

<a name="configuration-media"></a>
### Media Player Configuration

The following enables media player for supported devices:

```yaml
media_player:
  - platform: aarlo
```

<a name="configuration-lovelace"></a>
### Custom Lovelace Card Configuration

A custom Lovelace card which is based on the `picture-glance` can be found here:
https://github.com/twrecked/lovelace-hass-aarlo

The custom Lovelace card allows access to the video recordings library and presents
customizable camera information on the camera feed. It was influenced by the Arlo web
interface camera view.

*This piece is optional, `aarlo` will work with the standard Lovelace cards.*


<a name="other"></a>
## Other

<a name="other-naming"></a>
### Naming
Entity ID naming follows this pattern
`component-type.aarlo_lower_case_name_with_underscores`.

For example, a camera called "Front Door" will have an entity id of
`camera.aarlo_front_door`.

<a name="other-best"></a>
### Best Practises and Known Limitations
The component uses the Arlo webapi.
* There is no documentation so the API has been reverse engineered using browser debug
  tools.
* There is no support for smart features, you only get motion detection notifications, not
  what caused the notification. (Although, you can pipe a snapshot into deepstack...)
* Streaming times out after 30 minutes.
* The webapi doesn't seem like it was really designed for permanent connections so the
  system will sometimes appear to lock up. Various work arounds are in the code and can be
  configured at the `arlo` component level. See next paragraph.

If you do find the component locks up after a while (I've seen reports of hours, days or
weeks), you can add the following to the main configuration. Start from the top and work
down:
* `refresh_devices_every`, tell Aarlo to request the device list every so often. This will
  sometimes prevent the back end from aging you out. The value is in hours and a good
  starting point is 3.
* `stream_timeout`, tell Aarlo to close and reopen the event stream after a certain period
  of inactivity. Aarlo will send keep alive every minute so a good starting point is 180
  seconds.
* `reconnect_every`, tell Aarlo to logout and back in every so often. This establishes a
  new session at the risk of losing an event notification. The value is minutes and a good
  starting point is 90.
* `request_timeout`, the amount of time to allow for a http request to work. A good
  starting point is 120 seconds.

Unify your alarm mode names across all your base stations. There is no way to specify
different mode names for each device.

Alro will allow shared accounts to give cameras their own name. If you find cameras
appearing with unexpected names (or not appearing at all), log into the Arlo web interface
with your Home Assistant account and make sure the camera names are correct.

You can change the brightness on the light but not while it's turned on. You need to turn
it off and back on again for the change to take. This is how the web interface does it.

<a name="other-debugging"></a>
### Debugging
If you run into problems there please provide the following in the bug report to help
debugging.
* Version of software running.
* Make of cameras and base stations you have.

I might also ask you to turn on component logging and event logging. The follow paragraphs
show you how, it's safe to leave these running if you fancy pokeing around and trying to
find out what it going wrong.

* Component logging. You can turn this on by adding the following to your
  `configuration.yaml` file.
```yaml
logger:
  default: info
  logs:
    custom_components.aarlo: debug
    custom_components.aarlo.alarm_control_panel: debug
    custom_components.aarlo.binary_sensor: debug
    custom_components.aarlo.camera: debug
    custom_components.aarlo.light: debug
    custom_components.aarlo.media_player: debug
    custom_components.aarlo.sensor: debug
    custom_components.aarlo.switch: debug
    pyaarlo: debug
```

	If, for example, you suspect the problem is just with your lights you can remove
	unneeded debug:
```yaml
logger:
  default: info
  logs:
    custom_components.aarlo: debug
    custom_components.aarlo.light: debug
    pyaarlo: debug
```

	Home assistant logs everything to `/config/home-assistant.log`, a typical piece of
	debug from Aarlo looks like this.
```
2020-01-21 11:44:48 DEBUG (ArloBackgroundWorker) [pyaarlo] fast refresh
2020-01-21 11:44:48 DEBUG (ArloBackgroundWorker) [pyaarlo] day testing with 2020-01-21!
2020-01-21 11:44:50 DEBUG (ArloEventStream) [pyaarlo] async ping response subscriptions/XXXXXX-XXX-XXXXXXX_web
```
	If you fancy diving in, and please do, searching for exceptions and any reference to
	`traceBack` is a good place to start.


* Event logging. You can look at what events Arlo is sending you by turning on event
  stream dumping. Add the following to your `configuration.yaml` file and Aarlo will dump
  events into `/config/.aarlo/packets.dump`:
```yaml
aarlo:
    # current config here
    packet_dump: True
```

   This file will built up from a constant trickle of packets from Arlo. The following
   exerpt shows a login confirmation and a subscription check response.
```
{'status': 'connected'}
{ 'action': 'is',
    'from': 'XXXXXXXXXXXXX',
    'resource': 'subscriptions/XXXXXX-XXX-XXXXXXX_web',
    'to': 'XXXXXX-XXX-XXXXXXX_web',
    'transId': 'web!38a29262-1ce0-4c4d-8f75-fafec2c34332'}
```

	Another example, if Arlo detects motion you will see a packet with the following field
	in it:
```
'properties': {'motionDetected': True},
```

<a name="other-sensitive"></a>
### Hiding Sensitive Data

If you paste any debug logs into github it's a good idea to encrypt them before uploading
them. You can do this using the [pyaarlo](https://github.com/twrecked/pyaarlo) component.
The easiest way to install it is in a virtual environment. The following steps will
install Pyaarlo.

```bash
$ virtualenv -p /usr/bin/python3.6 pyaarlo
$ source pyaarlo/bin/activate
(pyaarlo) $ pip install git+https://github.com/twrecked/pyaarlo
(pyaarlo) $ pyaarlo --help
```

To encrypt your logs save the output to a file and do the following:

```bash
(pyaarlo)$ cat your-log-file | pyaarlo encrypt
```

The output will look like this - only longer! Paste everything, including the BEGIN and
END lines into your bug report.

```
-----BEGIN PYAARLO DUMP-----
gAN9cQAoWAEAAABucQFCAAEAAJJ7SWmo+vX28ycatrCV2s1o0wiIo3SPVOaRkHBf6xVup2D/cdZI
nvim30f/oTNwkuspbwYTwOzXHZJygnsi/9vX4+5g65te+bJczzVl6hoBM+2uaNfFi63iL0blMv32
zwTZHPj7TxwcJbdOGuP+A+yqEpxPbIsI/8nUP9CLvE01cxje+a7swgUdidoPTAAPSjjteGWl/h+V
DMX8UcDPtN+fdYOyEVlVOoFPQC4u/xXjN0qusfW0yNqpKHzD82Vkz0Igc5USXCRsbAs1YNgnZgXt
KWwDrH5v31jNd6zppaF5EtgfnyDsUohzqYy0bciXfD0HAQS/6sbT+sSaRf39q7pxAlgBAAAAb3ED
QyDC4o3xjAKAA4pGGxzZ7zyUP7nU6QgiqDD1aYi7C6SzcnEEdS4=
-----END PYAARLO DUMP-----
```

#### Notes
Data isn't anonymised internally... I will be adding that functionality.

You don't need to keep re-installing pyaarlo, just re-activate the virtualenv.
```bash
$ cd where-you-where-before
$ source pyaarlo/bin/activate
(pyaarlo) $ pyaarlo --help
```

When you're finished with pyaarlo deactive the virtualenv.
```bash
(pyaarlo) $ deactivate
$
```


<a name="other-adding"></a>
### Adding Devices

*Coming soon...*

<a name="advanced"></a>
## Advanced Use

<a name="advanced-parameters"></a>
### All Parameters
The following additional parameters can be specified against the aarlo platform for more
granular control:

| Field                      | Type        | Default                      | Description                                                                                                                                                                                                                              |
| ------                     | ----        | -------                      | -----------                                                                                                                                                                                                                              |
| `db_motion_time`           | integer     | `30` (s)                     | Duration of doorbell motion. (Arlo doorbell only indicates motion is present not that it stops)                                                                                                                                          |
| `db_ding_time`             | integer     | `60` (s)                     | Duration of doorbell press. (Arlo doorbell only indicates doorbell was pressed, not that it was released)                                                                                                                                |
| `recent_time`              | integer     | `600` (s)                    | Used to hold the cameras in a recent activity state after a recording or streaming event. (Streaming & recording can be over in a few seconds, without this the camera will revert to idle, possibly looking like nothing has happened.) |
| `last_format`              | strftime    | `'%m-%d %H:%M'`              | Display format of last captured time                                                                                                                                                                                                     |
| `http_connections`         | integer     | `5`                          | Adjust the number http connections pools to cache                                                                                                                                                                                        |
| `serial_ids`               | boolean     | False                        | Use device IDS for the entity names.                                                                                                                                                                                                     |
| `http_max_size`            | integer     | `10`                         | Adjust the maximum number connects to save in the pool                                                                                                                                                                                   |
| `request_timeout`          | time period | `60`                         | Timeout for requests sent to Arlo server. 0 means no timeout.                                                                                                                                                                            |
| `stream_timeout`           | time period | `0`                          | Timeout for inactivity on the Arlo event stream. 0 means no timeout. Used to help with Arlo components becoming unresponsive.                                                                                                            |
| `reconnect_every`          | integer     | `0` (minutes)                | If not 0 then force a logout every `reconect_entry` time period. Used to help with Arlo components becoming unresponsive.                                                                                                                |
| `refresh_devices_every`    | integer     | `0` (hours)                  | Used to force a refresh every x hours. 0 = no refreshing. Used to resolve issue with mode changes failing after several days of use                                                                                                      |
| `packet_dump`              | boolean     | `False`                      | Causes aarlo to store all the packets it sees in `/config/.aarlo/packets.dump` file. Only really needed for debugging and reverse engineering the API.                                                                                   |
| `conf_dir`                 | string      | `'/config/.aarlo'`           | Location to store component state. (The default is fine for hass.io, docker, and virtualenv systems - don't set this value unless asked to.)                                                                                             |
| `host`                     | string      | `https://my.arlo.com`        | Sets the host aarlo will connect to                                                                                                                                                                                                      |
| `auth_host`                | string      | `https://ocapi-app.arlo.com` | Sets the authentication host aarlo will connect to                                                                                                                                                                                       |
| `no_media_upload`          | boolean     | `False`                      | Used as a workaround for Arlo issues where the camera never gets a media upload notification. (Not needed in most cases.) *Deprecated, prefer `media_retry`.                                                                             |
| `media_retry`              | list(ints)  | list(time_outs)              | Used as a workaround for Arlo issues where the camera never gets a media upload notification. (Not needed in most cases.)                                                                                                                |
| `mode_api`                 | string      | `auto`                       | available options: [`v1`, `v2`] You can override this by setting this option to  v1 or v2 to use the old or new version exclusively. The default is  auto, choose based on device                                                        |
| `verbose_debug`            | boolean     | `False`                      | Turn on extra debug. This extra information is usually not needed!                                                                                                                                                                       |
| `hide_deprecated_services` | boolean     | `False`                      | If `True` only show services on the `aarlo` domain.                                                                                                                                                                                      |
| `library_days`             | integer     | `30` (days)                  | Change the number of days of video the component downloads from Arlo.                                                                                                                                                                    |
| `injection_service`        | boolean     | `False`                      | If `True` enable the packet injection service.                                                                                                                                                                                           |

<a name="advanced-statuses"></a>
### Camera Statuses

The following camera statuses are reported:
  * `Idle` camera is doing nothing
  * `Turned Off` user has turned the camera off
  * `Recording` camera has detected something and is recording
  * `Streaming` camera is streaming live video to another other login
  * `Taking Snapshot` camers is updating the thumbnail
  * `Recently Active` camera has seen activity within the last few minutes
  * `Too Cold!` the camera is shutdown until it warms up

<a name="advanced-services"></a>
### Services

The component provides the following services:

| Service                                 | Parameters                                                                                                                         | Description                                                                                                                    |
|-----------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| `aarlo.camera_request_snapshot`         | `entity_id` - name(s) of entities to use                                                                                           | This requests a snapshot be taken. Camera will move from `taking_snapshot` state when finished                                 |
| `aarlo.camera_request_snapshot_to_file` | `entity_id` - name(s) of entities to use <br/>`filename` - where to save snapshot                                                  | This requests a snapshot be taken and written to the passed file. Camera will move from  `taking_snapshot` state when finished |
| `aarlo.camera_start_recording`          | `entity_id` - name(s) of entities to use <br>`duration` - amount of time in seconds to record                                      | Begins video capture from the specified camera                                                                                 |
| `aarlo.camera_request_video_to_file`    | `entity_id` - name(s) of entities to use <br/>`filename` - where to save video                                                     | This requests a video be taken and written to the passed file. Camera will move from `recording` state when finished           |
| `aarlo.camera_stop_activity`            | `entity_id` - name(s) of entities to use                                                                                           | This moves the camera into the idle state. Can be used to stop streaming or recording.                                         |
| `aarlo.alarm_set_mode`                  | `entity_id` - name(s) of entities to use <br/>`mode` - custom mode to change to                                                    | Set the alarm to a custom mode                                                                                                 |
| `aarlo.siren_on`                        | `duration` - amount of time in seconds to record<br/>`volume` - how loud to set siren                                              | Turn a siren on.                                                                                                               |
| `aarlo.sirens_on`                       | `entity_id` - name(s) of entities to use <br>`duration` - amount of time in seconds to record<br/>`volume` - how loud to set siren | Turns all sirens on.                                                                                                           |
| `aarlo.siren_off`                       | `entity_id` - name(s) of entities to use                                                                                           | Turns a siren off.                                                                                                             |
| `aarlo.sirens_off`                      |                                                                                                                                    | Turns all sirens off.                                                                                                          |
| `aarlo.inject_response`                 | `filename` - file to read packet from                                                                                              | Inject a packet into the event stream.                                                                                         |

For recordings longer than 30 seconds you will need to whitelist the /tmp
directory. This is because we have to keep a stream to Arlo open to prevent them
from stopping the recording after 30 seconds. And we write this stream to the
/tmp directory.

These services are deprecated and will be going away. By moving services under the aarlo
domain it allows Home Assistant to use the `services.yaml` descriptions.

| Service                                 | Parameters                                                                                  | Description                                                                                                                  |
|-----------------------------------------|---------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| `camera.aarlo_request_snapshot`         | `entity_id` - camera to get snapshot from                                                   | This requests a snapshot be taken. Camera will move from  taking_snapshot state when finished                                |
| `camera.aarlo_request_snapshot_to_file` | `entity_id` - camera to get snapshot from<br/>`filename` - where to save snapshot           | This requests a snapshot be taken and written to the passed file. Camera will move from  taking_snapshot state when finished |
| `camera.aarlo_stop_activity`            | `entity_id` - camera to get snapshot from                                                   | This moves the camera into the idle state. Can be used to stop streaming                                                     |
| `camera.start_recording`                | `entity_id` - camera to start recording<br>`duration` - amount of time in seconds to record | Begins video capture from the specified camera                                                                               |
| `camera.stop_recording`                 | `entity_id` - camera to stop recording                                                      | Ends video capture from the specified camera                                                                                 |
| `alarm_control_panel.aarlo_set_mode`    | `entity_id` - camera to get snapshot from<br/>`mode` - custom mode to change to             | Set the alarm to a custom mode                                                                                               |

<a name="advanced-events"></a>
### Events

The following events can fire:

| Event                  | Description                                                |
|------------------------|------------------------------------------------------------|
| aarlo_image_updated    | The image updated                                          |
| aarlo_snapshot_updated | The image updated, and it was caused by a snapshot.        |
| aarlo_image_updated    | The image updated, and it was caused by an Arlo recording. |

The following events are deprecated:

| Event                | Description          |
|----------------------|----------------------|
| aarlo_snapshot_ready | The image is updated |


<a name="advanced-websockets"></a>
### Web Sockets

The component provides the following extra web sockets:

| Service              | Parameters                                                                                     | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|----------------------|------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| aarlo_video_url      | <ul><li>`entity_id` - camera to get details from</li><ul>                                      | Request details of the last recorded video. Returns: <ul><li>`url` - video url</li><li>`url_type` - video type</li><li>`thumbnail` - thumbnail image url</li><li>`thumbnail_type` - thumbnail image type</li></ul>                                                                                                                                                                                                                                                                          |
| aarlo_library        | <ul><li>`at-most` - return at most this number of entries</li><ul>                             | Request up the details of `at-most` recently recorded videos. Returns an array of:<ul><li>`created_at`: unix time stamp</li><li>`created_at_pretty`: pretty version of the create time</li><li>`url`: URL of the video</li><li>`url_type`: video type</li><li>`thumbnail`: URL of the thumbnail</li><li>`thumbnail_type`: thumbnail type</li><li>`object`: object in the video that triggered the capture</li><li>`object_region`: region in the video that triggered the capture</li></ul> |
| aarlo_stream_url     | <ul><li>`entity_id` -  camera to get snapshot from</li><li>`filename` - where to save snapshot | Ask the camera to start streaming. Returns:<ul><li>`url` - URL of the video stream</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                |
| aarlo_snapshot_image | <ul><li>`entity_id` -  camera to get snapshot from</li></ul>                                   | Request a snapshot. Returns image details: <ul><li>`content_type`: the image type</li><li>`content`: the image</li></ul>                                                                                                                                                                                                                                                                                                                                                                    |
| aarlo_stop_activity  | <ul><li>`entity_id` - camera to stop activity on</li></ul>                                     | Stop all the activity in the camera. Returns: <ul><li>`stopped`: True if stop request went in</li></ul>                                                                                                                                                                                                                                                                                                                                                                                     |

<a name="advanced-automations"></a>
### Automation Examples

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

<a name="advanced-streaming"></a>
### Streaming

Streaming now works "out of the box" for HassOS and Docker installs. To get streaming
working in `virtualenv` you still need to make sure a couple of libraries are installed.
For `ubuntu` the following works:
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

<a name="2fa"></a>
## 2FA

Aarlo supports 2 factor authentication.

<a name="2fa-automatic"></a>
#### IMAP

For IMAP 2FA Arlo needs to access and your email account form where it reads the token
Arlo sent.

```yaml
aarlo:
  tfa_source: imap
  tfa_type: email
  tfa_host: imap.host.com
  tfa_username: your-user-name
  tfa_password: your-imap-password
```

It's working well with my gmail account, see
[here](https://support.google.com/mail/answer/185833?hl=en) for help setting up single app
passwords.

<a name="2fa-rest-api"></a>
#### Rest API

This mechanism allows you to use any suitably configured/programmed website. When you
start authenticating Arlo makes a `clear` request and repeated `look-up` requests to a
website to retrieve your TFA code. The format of these requests and their reponses are
well defined but the host Arlo uses is configurable.

```yaml
aarlo:
  tfa_source: rest-api
  tfa_type: SMS
  tfa_host: custom-host
  tfa_username: test@test.com
  tfa_password: 1234567890
```

* Pyaarlo will clear the current code with this HTTP GET request:
```http request
https://custom-host/clear?email=test@test.com&token=1234567890
``` 

* And the server will respond with this on success:
```json
{ "meta": { "code": 200 },
  "data": { "success": true, "email": "test@test.com" } }
```

* Aarlo will look up the current code with this HTTP GET request:
```http request
https://custom-host/get?email=test@test.com&token=1234567890
``` 

* And the server will respond with this on success:
```json
{ "meta": { "code": 200 },
  "data": { "success": true, "email": "test@test.com", "code": "123456", "timestamp": "123445666" } }
```

* Failures always have `code` value of anything other than 200.
```json
{ "meta": { "code": 400 },
  "data": { "success": false, "error": "permission denied" }}
```

Aarlo doesn't care how you get the codes into the system only that they are there. Feel
free to roll your own server or...

##### Using My Server

I have a website running at https://pyaarlo-tfa.appspot.com that can provide this service.
It's provided as-is, it's running as a Google app so it should be pretty reliable and the
only information I have access to is your email address, access token for my website and
whatever your last code was. (_Note:_ if you're not planning on using email forwarding the
`email` value isn't strictly enforced, a unique ID is sufficient.)

_If you don't trust me and my server - and I won't be offended - you can get the source
from [here](https://github.com/twrecked/pyaarlo-tfa-helper) and set up your own._

To use the REST API with my website do the following:

* Register with my website. You only need to do this once and I'm sorry for the crappy
  interface. Go to [registration page](https://pyaarlo-tfa.appspot.com/register) and enter
  your email address (or unique ID). The website will reply with a json document
  containing your _token_, keep this _token_ and use it in all REST API interactions.
```json
{"email":"testing@testing.com",
 "fwd-to":"pyaarlo@thewardrobe.ca",
 "success":true,
 "token":"4f529ea4dd20ca65e102e743e7f18914bcf8e596b909c02d"}
```

* To add a code send the following HTTP GET request:
```http request
https://custom-host/add?email=test@test.com&token=4f529ea4dd20ca65e102e743e7f18914bcf8e596b909c02d&code=123456
```

You can replace `code` with `msg` and the server will try and parse the code out value of
`msg`, use it for picking apart SMS messages.

##### Using IFTTT

You have your server set up or are using mine, one way to send codes is to use
[IFTTT](https://ifttt.com/) to forward SMS messages to the server. I have an Android phone
so use the `New SMS received from phone number` trigger and match to the Arlo number
sending me SMS codes. (I couldn't get the match message to work, maybe somebody else will
have better luck.)

I pair this with `Make a web request` action to forward the SMS code into my server, I use
the following recipe. Modify the email and token as necessary.
```
URL: https://pyaarlo-tfa.appspot.com/add?email=test@test.com&token=4f529ea4dd20ca65e102e743e7f18914bcf8e596b909c02d&msg={{Text}}
Method: GET
Content Type: text/plain
```

Make sure to configure Aarlo to request a token over SMS with `tfa_type='SMS`. Now, when
you login in, Arlo will send an SMS to your phone, the IFTTT app will forward this to the
server and Aarlo will read it from the server.

##### Using EMAIL

If you run your own `postfix` server you can use [this
script](https://github.com/twrecked/pyaarlo-tfa-helper/blob/master/postfix/pyaarlo-fwd.in)
to set up an email forwarding alias. Use an alias like this:
```text
pyaarlo:  "|/home/test/bin/pyaarlo-fwd"
```

Make sure to configure Aarlo to request a token over EMAIL with `tfa_type='EMAIL`. Then
set up your email service to forward Arlo code message to your email forwarding alias.


<a name="to-do"></a>
## To Do

* smarter light brightness...
* coloured lights
* custom mode - like SmartThings to better control motion detection
* use asyncio loop internally

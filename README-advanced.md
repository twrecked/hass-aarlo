# Table of Contents

<!-- TOC -->
* [Table of Contents](#table-of-contents)
* [Introduction](#introduction)
* [Entity Naming](#entity-naming)
  * [Configuration](#configuration)
* [Saving Media](#saving-media)
* [Streaming](#streaming)
  * [Direct Streaming](#direct-streaming)
  * [Further Help](#further-help)
* [Snapshots](#snapshots)
  * [Other](#other)
* [User Agents](#user-agents)
* [All Parameters](#all-parameters)
* [Camera Statuses](#camera-statuses)
* [Services](#services)
* [Events](#events)
* [Web Sockets](#web-sockets)
* [Automation Examples](#automation-examples)
    * [Update camera snapshot 3 seconds after a recording event happens](#update-camera-snapshot-3-seconds-after-a-recording-event-happens)
    * [Begin recording when an entity changes state](#begin-recording-when-an-entity-changes-state)
<!-- TOC -->

# Introduction

This is where I put all the advanced bits of the original README file.

_I need to revisit this document._

# Entity Naming

Pre *0.8* versions of the integration named entities like this:

```
component-type.aarlo_lower_case_name_with_underscores
```

For example, a camera called "Front Door" could have entity IDs that look like this:

```
camera.aarlo_front_door
binary_sensor.aarlo_motion_front_door
```

In *0.8* you can still get this behaviour by checking the `Use aarlo prefix for entries` when adding the installation. And from *0.8* an on you can change the entity names as much as _Home Assistant_ supports it. If you don't check the box the names will look like this:

```
camera.front_door
binary_sensor.motion_front_door
```

## Configuration

_Aarlo_ will decode Unicode characters, this means a camera called `Haustür` will be called `component-type.aarlo_haustur`. If you do not want this behaviour - and be warned, this may cause problems using certain _Home Assistant_ services - add this to `/config/aarlo.yaml`.

```yaml
aarlo:
  # existing config...
  no_unicode_squash: True
```

You can ask _Arlo_ to use serial numbers not names for entity ids. Add this to `/config/aarlo.yaml`.

```yaml
aarlo:
  # existing config...
  serial_ids: True
```

# Saving Media

You can use `save_media_to` option to specify a file naming scheme. If you do _Aarlo_ will use that to save all media - videos and snapshots - locally. You can use the following substitutions:

- `SN`; the device serial number
- `N`; the device name
- `Y`; the year of the recording, include century
- `m`; the month of the year as a number (range 01 to 12)
- `d`; the day of the month as a number (range 01 to 31)
- `H`; the hour of the day (range 00 to 23)
- `M`; the minute of the hour (range 00 to 59)
- `S`; the seconds of the minute (range 00 to 59)
- `F`; a shortcut for `Y-m-d`
- `T`; a shortcut for `H:M:S`
- `t`; a shortcut for `H-M-S`
- `s`; the number of seconds since the epoch

You specify the substitution by prefixing it with a `$` in the format string. You can optionally use curly brackets to remove any ambiguity. For example, the following configuration in `/config/arlo.yaml` will save all media under `/config/media`organised by serial number and then by date. The code will add the correct file extension.

```yaml
aarlo:
  # existing config...
  save_media_to: "/config/media/${SN}/${Y}/${m}/${d}/${T}"
```

The first time you configure `save_media_to` the system can take several minutes to download all the currently available media. The download is throttled to not overload _Home Assistant_ or _Arlo_. Once the initial download is completed updates should happen a lot faster.

The code doesn't provide any management of the downloads, it will keep downloading them until your device is full. It also doesn't provide a _NAS_ interface, you need to mount the _NAS_ device and point `save_media_to` at it.

# Streaming

You need to use the custom `aarlo-glance` card. And you need to do one or both of these:

- add `stream` to the `image_click` options of the card
- add `stream` to the `image_top` or `image_bottom` options of the card

Streaming works with _Home Assistant_ and, for most people, will just work. But there are still some things to be wary of.

## Direct Streaming

_Arlo_ recently upgraded their streaming servers to support `mpeg-dash`. You can stream this directly to your browser without going through your _Home Assistant_ install.

One of the biggest advantages of direct streaming was audio support but that has been added to non-direct streaming in recent _Home Assistant_ releases. Direct streaming still offloads the conversion from your _Home Assistant_ server and reduces the bandwidth usage of your home network, this is especially true
if streaming from outside your home network.

You can not stream directly to Apple devices, they don't support `mpeg-dash`.

Internally the code will use non-direct streaming as needed. For example, to save recording into the _Arlo_ library of longer than 30 seconds the code must open a stream to the _Arlo_ servers, it can only do this in non-direct mode because the stream component doesn't support `mpeg-dash`.

To use it on your `aarlo-glance` card you need to add `direct` to the `image_view` options of the card. You can mix direct and non-direct cards on the UI.

## Further Help

If you are still having issues please read these 3 posts:

* https://github.com/twrecked/hass-aarlo/issues/55
* https://community.home-assistant.io/t/arlo-replacement-pyarlo-module/93511/293
* https://community.home-assistant.io/t/arlo-replacement-pyarlo-module/93511/431?u=sherrell

# Snapshots

Snapshots can be tricky.

The initial implementation would issue a `fullFrameSnapshot` request and _Arlo_ would return a snapshot. The problem was it wasn't very consistent, I have 2 identical cameras where snapshot will work on one and not the other. _Arlo_ uses this implementation to allow you to position the camera and I've seen it not work on their web interface and app.

The next implementation would start a stream and issues a snapshot command - mimicking the camera button show on the live stream on the web interface. Again, this mostly worked but some cameras would steadfastly refuse to send back a snapshot.

The latest version adds to the previous stream version by allowing the updated thumbnail from the stream to be used as the snapshot image. This method works best but there are still some pieces of configuration you can tweak to make it better.

* `stream_snapshot`; set to `True` to turn on stream snapshots, default `False`.
* `stream_snapshot_stop`; a positive integer, the number of seconds to stop the stream after starting it for a snapshot, default 10. This can help speed up cameras that won't send a snapshot on request. Setting it to 0 will let  _Arlo_ stop the stream when it thinks it has become idle.
* `snapshot_checks`; an integer array, default values 1 and 5. Force _Aarlo_ to do a media library check to see if the snapshot has appeared. Useful when systems fail to send `mediaUploadNotifications`.
* `snapshot_timeout`; a positive integer, default 60. How long to give the snapshot to appear before stopping everything.

## Other

This is a summary of possible snapshot sizes:

| camera | user_agent | stream_snapshot | worked    | size      |
|--------|------------|-----------------|-----------|-----------|
| street | linux      | yes             | yes       | 640x352   |
| street | linux      | no              | sometimes |           |
| front  | linux      | yes             | yes       | 1920x1072 |
| front  | linux      | no              | yes       |           |
| street | apple      | yes             | no*       |           |
| street | apple      | no              | sometimes | 1280x720  |
| front  | apple      | yes             | yes       |           |
| front  | apple      | no              | yes       | 1920x1072 |

_street_ is an 1st gen _Arlo_ (VMC3030)
_front_ is an _Arlo Pro_ (VMC4030P)

# User Agents

The following user agents are available:
- `arlo`; the original `netgear` use agent, this is the default and will get `rtsps` streams from the _Arlo_ servers.
- `linux`; a newer `Chrome` user agent, this will get `mpeg-dash` streams from the _Arlo_ servers.
- `apple`, `ipad`, `iphone`, `mac`, `firefox`; these simulate these devices or  browsers and, for now, these return `mpeg_dash` streams.

As you can see, the user agent you supply to _Arlo_ determines what streaming format is used. I used to think that the agent you used to log in had to be the same as the agent you use to start a stream. After some testing I find this is not the case.

What this means is _Aarlo_ can select the best user agent for the task.

- The `camera.record` service will use `arlo` agent so _Home Assistant_ can save the stream as `mp4`.
- The `camera.play_stream` service will use `arlo` agent so _Home Assistant_ can convert the stream to `hls`.
- The `arlo_stream_url` web service will use the `linux` agent to return a URL to an `mpeg-dash` stream.

Those `camera.play_stream` and `arlo_stream_url` changes are important, they allow the `aarlo-glance` Lovelace card to choose direct or non-direct streams regardless of the default user agent provided.

The default user agent is used in all other cases. This means, for example, the one you set if picked for snapshot operations.


# All Parameters

The following additional parameters can be specified in `/config/aarlo.yaml` for more granular control:

| Field                   | Type        | Default                      | Description                                                                                                                                                                                                                              |
|-------------------------|-------------|------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `db_motion_time`        | integer     | `30` (s)                     | Duration of doorbell motion. (Arlo doorbell only indicates motion is present not that it stops)                                                                                                                                          |
| `db_ding_time`          | integer     | `60` (s)                     | Duration of doorbell press. (Arlo doorbell only indicates doorbell was pressed, not that it was released)                                                                                                                                |
| `recent_time`           | integer     | `60` (s)                     | Used to hold the cameras in a recent activity state after a recording or streaming event. (Streaming & recording can be over in a few seconds, without this the camera will revert to idle, possibly looking like nothing has happened.) |
| `last_format`           | strftime    | `'%m-%d %H:%M'`              | Display format of last captured time                                                                                                                                                                                                     |
| `serial_ids`            | boolean     | False                        | Use device IDS for the entity names.  **BE CAREFUL, WILL RENAME ALL YOUR ENTITIES**                                                                                                                                                      |
| `request_timeout`       | time period | `60`                         | Timeout for requests sent to Arlo server. 0 means no timeout.                                                                                                                                                                            |
| `stream_timeout`        | time period | `120`                        | Timeout for inactivity on the Arlo event stream. 0 means no timeout. Used to help with Arlo components becoming unresponsive.                                                                                                            |
| `reconnect_every`       | integer     | `0` (minutes)                | If not 0 then force a logout every `reconect_entry` time period. Used to help with Arlo components becoming unresponsive.                                                                                                                |
| `refresh_devices_every` | integer     | `2` (hours)                  | Used to force a device refresh every x hours. 0 = no refreshing. Used to resolve issue with mode changes failing after several days of use.                                                                                              |
| `refresh_modes_every`   | integer     | `0` (minutes)                | Used to force a mode refresh every x minutes. 0 = no refreshing. Used to resolve issue with mode changes failing after several days of use.                                                                                              |
| `packet_dump`           | boolean     | `False`                      | Causes aarlo to store all the packets it sees in `/config/.aarlo/packets.dump` file. Only really needed for debugging and reverse engineering the API.                                                                                   |
| `conf_dir`              | string      | `'/config/.aarlo'`           | Location to store component state. (The default is fine for hass.io, docker, and virtualenv systems - don't set this value unless asked to.)                                                                                             |
| `host`                  | string      | `https://my.arlo.com`        | Sets the host aarlo will connect to                                                                                                                                                                                                      |
| `auth_host`             | string      | `https://ocapi-app.arlo.com` | Sets the authentication host aarlo will connect to                                                                                                                                                                                       |
| `backend`               | string      | `mqtt`                       | Use mqtt or sse backend                                                                                                                                                                                                                  |
| `no_media_upload`       | boolean     | `False`                      | Used as a workaround for Arlo issues where the camera never gets a media upload notification. (Not needed in most cases.) *Deprecated, prefer `media_retry`.                                                                             |
| `media_retry`           | list(ints)  | 5, 15, 25                    | Used as a workaround for Arlo issues where the camera never gets a media upload notification. (Not needed in most cases.)                                                                                                                |
| `mode_api`              | string      | `auto`                       | available options: [`v1`, `v2`, `v3`] You can override this by setting this option to  v1 or v2 to use the old or new version exclusively. The default is  auto, choose based on device                                                  |
| `save_updates_to`       | string      | ''                           | A directory to automatically save updated camera images to. Has format `$save_updates_to/$unique_id.jpg`                                                                                                                                 |
| `save_media_to`         | string      | ''                           | A string describing where to save new media files. This include both video and snapshots. See the "Save Media" section.                                                                                                                  |
| `verbose_debug`         | boolean     | `False`                      | Turn on extra debug. This extra information is usually not needed!                                                                                                                                                                       |
| `library_days`          | integer     | `27` (days)                  | Change the number of days of video the component downloads from Arlo.                                                                                                                                                                    |
| `injection_service`     | boolean     | `False`                      | If `True` enable the packet injection service.                                                                                                                                                                                           |
| `user_agent`            | string      | `arlo`                       | Tells the system which user agent to pass to Arlo.                                                                                                                                                                                       |
| `stream_snapshot`       | boolean     | `False`                      | If `True` will always try to start a stream before taking a snapshot. If `False` will take and idle or streaming snapshot depending on the camera state.                                                                                 |
| `stream_snapshot_stop`  | integer     | `10` (seconds)               | How long to wait before stopping the snapshot stream, 0 means let Arlo do it.                                                                                                                                                            |
| `snapshot_checks`       | list(ints)  | 1 and 5 (seconds)            | Force Aarlo to check for a snapshot before `mediaUploadNotification` appears.                                                                                                                                                            |
| `snapshot_timeout`      | integer     | 65 (seconds)                 | How long to wait before abandoning snapshot attempt                                                                                                                                                                                      |

# Camera Statuses

The following camera statuses are reported:
* `Idle` camera is doing nothing
* `Turned Off` user has turned the camera off
* `Recording` camera has detected something and is recording
* `Streaming` camera is streaming live video to another other login
* `Taking Snapshot` cameras is updating the thumbnail
* `Recently Active` camera has seen activity within the last few minutes
* `Too Cold!` the camera is shutdown until it warms up

# Services

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
| `aarlo.restart_device`                  | `entity_id` - name(s) of entities to reboot                                                                                        | Restarts a base station. You need admin access to do this.                                                                     |
| `aarlo.inject_response`                 | `filename` - file to read packet from                                                                                              | Inject a packet into the event stream.                                                                                         |

For recordings longer than 30 seconds you will need to white list the `/tmp` directory. This is because we have to keep a stream to _Arlo_ open to prevent them from stopping the recording after 30 seconds. And we write this stream to the `/tmp` directory.

For `restart_device` you need to log in with the main account.

# Events

The following events can fire:

| Event                  | Description                                                |
|------------------------|------------------------------------------------------------|
| aarlo_image_updated    | The image updated                                          |
| aarlo_snapshot_updated | The image updated, and it was caused by a snapshot.        |
| aarlo_capture_updated  | The image updated, and it was caused by an Arlo recording. |

# Web Sockets

The component provides the following extra web sockets:

| Service              | Parameters                                                                                     | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|----------------------|------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| aarlo_video_url      | <ul><li>`entity_id` - camera to get details from</li><ul>                                      | Request details of the last recorded video. Returns: <ul><li>`url` - video url</li><li>`url_type` - video type</li><li>`thumbnail` - thumbnail image url</li><li>`thumbnail_type` - thumbnail image type</li></ul>                                                                                                                                                                                                                                                                          |
| aarlo_library        | <ul><li>`at-most` - return at most this number of entries</li><ul>                             | Request up the details of `at-most` recently recorded videos. Returns an array of:<ul><li>`created_at`: unix time stamp</li><li>`created_at_pretty`: pretty version of the create time</li><li>`url`: URL of the video</li><li>`url_type`: video type</li><li>`thumbnail`: URL of the thumbnail</li><li>`thumbnail_type`: thumbnail type</li><li>`object`: object in the video that triggered the capture</li><li>`object_region`: region in the video that triggered the capture</li></ul> |
| aarlo_stream_url     | <ul><li>`entity_id` -  camera to get snapshot from</li><li>`filename` - where to save snapshot | Ask the camera to start streaming. Returns:<ul><li>`url` - URL of the video stream</li></ul>                                                                                                                                                                                                                                                                                                                                                                                                |
| aarlo_snapshot_image | <ul><li>`entity_id` -  camera to get snapshot from</li></ul>                                   | Request a snapshot. Returns image details: <ul><li>`content_type`: the image type</li><li>`content`: the image</li></ul>                                                                                                                                                                                                                                                                                                                                                                    |
| aarlo_stop_activity  | <ul><li>`entity_id` - camera to stop activity on</li></ul>                                     | Stop all the activity in the camera. Returns: <ul><li>`stopped`: True if stop request went in</li></ul>                                                                                                                                                                                                                                                                                                                                                                                     |

# Automation Examples

### Update camera snapshot 3 seconds after a recording event happens

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

### Begin recording when an entity changes state

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


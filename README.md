# hass-aarlo

### Asynchronous Arlo Component for Home Assistant.

The component operates in a similar way to the [Arlo](https://arlo.netgear.com/#/cameras) web site - it opens a single event stream to the Arlo backend and monitors events and state changes for all base stations, cameras and doorbells in a system. Currently it only lets you set base station modes.

## Table of Contents
* Supported features
* Notes
* Installation
  * Migrating from Old Layout
  * Manually
  * From Script
* Component Configuration
  * Sample Configuration
  * Additional Parameters
* Lovelace Card Configuration

## Supported Features:
* Base station mode changes
* Camera motion detection
* Camera audio detection
* Door bell motion detection
* Door bell button press
* Camera status
  * `Idle` camera is doing nothing
  * `Turned Off` user has turned the camera off
  * `Recording` camera has detected something and is recording
  * `Streaming` camera is streaming live video other login
  * `Taking Snapshot` camers is updating the thumbnail
  * `Recently Active` camera has seen activity within the last few minutes
  * `Too Cold!` the camera is shutdown until it warms up
* Saving of state across restarts
* Camera on/off
* Requesting thumbnail updates
* Direct video streaming from arlo where possible
* Siren when triggering an alarm
* Streaming (**Note**: in virtualenv installation only)

It provides a custom lovelace resource that is a specialised version of a picture-glance that allows you to see the last snapshot taken and give quick access to clip counts, the last recorded video and signal and battery levels.

**This is an alpha release - it's working great for me - 3 base stations, 11 cameras, 2 doorbells - but I haven't had chance to test it against many different configurations!**
**If I had to say where stuff might blow up I'd guess at the resource card, I've only really tested it on Chrome!**

## Notes
Wherever you see `/config` in this README it refers to your home-assistant configuration directory. For me, for example, it's `/home/steve/ha` that is mapped to `/config` inside my docker container.

Many thanks to:
* [Pyarlo](https://github.com/tchellomello/python-arlo) and [Arlo](https://github.com/jeffreydwalter/arlo) for doing all the hard work figuring the API out and the free Python lesson!
* [sseclient](https://github.com/btubbs/sseclient) for reading from the event stream
* [Button Card](https://github.com/kuuji/button-card/blob/master/button-card.js) for a working lovelace card I could understand

## Installation

### Migrating from Old Layout
**This only needs to be done once and only if you installed an older version of `hass-aarlo`.** 

Home Assitant moved to a new layout for custom components, running the `remove_old` script will show a list of commands needed to remove the old installation. You will need to enter these commands manually. After running the command and, if they are empty, it's safe to remove the `alarm_control_panel`, `binary_sensor`, `sensor` and `camera` directories from your `/config/custom_components` directory

### Manually
Copy the `aarlo`directory into your `/config/custom_components` directory.

Copy the `www` directory into you `/config` directory.

### Script
Run the install script. Run it once to make sure the operations look sane and run it a second time with the `go` paramater to do the actual work. If you update just rerun the script, it will overwrite all installed files.

```sh
install /config
# check output looks good
install go /config
```

## Component Configuration
For the simplest use replace all instances of the `arlo` with `aarlo` in your home-assistant configuration files. To support motion and audio capture add `aarlo` as a platform to the `binary_sensor` list.

The following is an example configuration:

```yaml
aarlo:
  username: !secret arlo_username
  password: !secret arlo_password

camera:
  - platform: aarlo
    ffmpeg_arguments: '-pred 1 -q:v 2'

alarm_control_panel:
  - platform: aarlo
    home_mode_name: home
    away_mode_name: armed
    trigger_time: 30
    alarm_volume: 8

binary_sensor:
  - platform: aarlo
    monitored_conditions:
    - motion
    - sound
    - ding

sensor:
  - platform: aarlo
    monitored_conditions:
    - last_capture
    - total_cameras
    - battery_level
    - captured_today
    - signal_strength
```
The `alarm_control_panel` can be triggered and a siren, if present, will sound.

The following additional parameters can be specified against the aarlo platform:

```yaml
aarlo:
  username: !secret arlo_username
  password: !secret arlo_password
  packet_dump: True
  db_motion_time: 30
  db_ding_time: 10
  recent_time: 10
  last_format: '%m-%d %H:%M'
  conf_dir: /config/.aarlo
  no_media_upload: True
  mode_api: auto
  refresh_devices_every: 0
  http_connections: 5
  http_max_size: 10
```
| Field                 | Type     | Default          | Description                                                                                                                                                                                                                               |
|-----------------------|----------|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| packet_dump           | boolean  | `False`          | Causes aarlo to store all the packets it sees in `/config/.aarlo/packets.dump` file.                                                                                                                                                      |
| db_motion_time        | integer  | 30 (s)           | Duration of doorbell motion. (Arlo doorbell only indicates motion is present not that it stops.)                                                                                                                                          |
| db_ding_time          | integer  | 60 (s)           | Duration of doorbell press. (Arlo doorbell only indicates doorbell was pressed, not that it was released.)                                                                                                                                |
| recent_time           | integer  | 600 (s)          | Used to hold the cameras in a  recent activity state after a recording or streaming event. (Streaming & recording can be over in a few seconds, without this the camera will revert to idle, possibly looking like nothing has happened.) |
| last_format           | strftime | '%m-%d %H:%M'    | Display format of last captured time                                                                                                                                                                                                      |
| conf_dir              | string   | '/config/.aarlo' | Location to store component state. (The default is fine for hass.io, docker, and virtualenv systems. You shouldn't have to change this.)                                                                                                  |
| no_media_upload       | boolean  | False            | Used as a workaround for Arlo issues where the camera never gets a media upload notification. (Not needed in most cases.)                                                                                                                 |
| mode_api              | string   | 'auto'           | available options: ['v1', 'v2'] You can override this by setting this option to  v1 or v2 to use the old or new version exclusively. The default is  auto, choose based on device.                                                        |
| refresh_devices_every | integer  | 0 (hours)        | Used to force a refresh every x hours. 0 = no refreshing. Used to resolve issue with mode changes failing after several days of use.                                                                                                      |
| http_connections      | integer  | 5                | Adjust the number http connections pools to cache.                                                                                                                                                                                        |
| http_max_size         | integer  | 10               | Adjust the maximum number connects to save in the pool.                                                                                                                                                                                   |


For `alarm_control_panel` you only need to specify the modes if you have custom mode names, see [here](https://www.home-assistant.io/components/arlo/#alarm) for more information. Names are case insensitive.

## Custom Lovelace Card Configuration

*This piece is optional, `aarlo` will work with the standard Lovelace cards.*

The new resource `aarlo-glance` is based on `picture-glance` but tailored for the Arlo component to simplify the configuration. 

### Resource Configuration
Add the following to the top of your UI configuration file.

```yaml
resources:
  - type: module
    url: /local/aarlo-glance.js
```

## Card configuration

| Name | Type | Default | Supported options | Description |
|-------------|-------------|--------------|---------------------------------------------------------------------------------------|-----------------------------------------|
| type | string | **required** | `custom:aarlo-glance` |  |
| entity | string | **required** | camera entity_id |  |
| name | string |  | Display Name |  |
| show | string list | **required** | [motion, sound, snapshot, battery_level, signal_strength, captured_today, image_date] | all items are optional but you must provide at least 1 |
| top_title | boolean | false |  | Show the title at the top of the card |
| top_status | boolean | false |  | Show the status at the top of the card |
| top_date | boolean | false |  | Show the date at the top of the card |
| image_click | string |  | ['play'] | Action to perform when image is clicked. Remove attribute to play last recorded video when image is clicked. |
| door | string | entity_id |  | Useful if the camera is pointed at a door. |
| door_lock | string | entity_id |  |  |
| door_bell | string | entity_id |  |  |
| door2 | string | entity_id |  | Useful if the camera is pointed at a door. |
| door2_lock | string | entity_id |  |  |
| door2_bell | string | entity_id |  |  |

### Example
```yaml
type: 'custom:aarlo-glance'
entity: camera.aarlo_front_door_camera
name: Front Door
show:
  - motion
  - sound
  - snapshot
  - battery_level
  - signal_strength
  - captured_today
  - image_date
top_title: false
top_status: false
top_date: false
image_click: play
door: binary_switch.front_door
door_lock: lock.front_door_lock
door_bell: binary_switch.aarlo_ding_front_door_bell
door2: binary_switch.front_door
door2_lock: lock.front_door_lock
door2_bell: binary_switch.aarlo_ding_front_door_bell
```

You don't need to reboot to see the GUI changes, a reload is sufficient. And if all goes will see a card that looks like this:

![Aarlo Glance](/images/aarlo-glance-02.png)

Reading from left to right you have the camera name, motion detection indicator, captured clip indicator, battery levels, signal level and current state. If you click the image the last captured clip will play, if you click the last captured icon you will be show the video library thumbnails - see below. Clicking the camera icon (not shown) will take a snapshot and replace the current thumbnail. (See supported features for list of camera statuses)

Clicking on the last captured clip will display thumbnail mode. Clicking on a thumbnail starts the appropiate video.  You can currently only see the last 99 videos. If you move your mouse over a thumbnail it will show you time of capture and, if you have a Smart subscription, a reason for the capture. **>** takes you to the next page, **<** to the previous and **X** closes the window.

![Aarlo Thumbnails](/images/thumbnails.png)

See the [Lovelace Custom Card](https://developers.home-assistant.io/docs/en/lovelace_custom_card.html) page for further information.

## Streaming

The support for stream is experimental and works but with a couple of caveats.
* virtualenv only - this is because `ffmpeg` doesn't support rtsps streams in docker or hassio.
* the stream only stops if you use the aarlo-glance card

Do get streaming working in `virtualenv` you still need to make sure a couple of libraries are installed. For `ubuntu` the following works:
```
source your-env/bin/activate
sudo apt install libavformat-dev
sudo apt install libavdevice-dev
pip install av==6.1.2
```
Set `image_click` to `play` on the aarlo glance card.

For further information on getting streaming working please read these 2 posts:
   * https://github.com/twrecked/hass-aarlo/issues/55
   * https://community.home-assistant.io/t/arlo-replacement-pyarlo-module/93511/293
   * https://community.home-assistant.io/t/arlo-replacement-pyarlo-module/93511/431?u=sherrell

## Other Lovelace Options

Using the conditional card you can have badges of cameras appear after activity or if they go off line. I use the following to get quick updates on an overview view.

```yaml
cards:
type: vertical-stack
  - card:
      show_state: false
      type: glance
    entities:
      - entity: camera.aarlo_front_door_camera
        name: Front Door
      - entity: camera.aarlo_front_camera
        name: Front
      - entity: camera.aarlo_driveway_camera
        name: Driveway
      - entity: camera.aarlo_back_door_camera
        name: Back Door
    show_empty: false
    state_filter:
      - recently active
      - streaming
      - recording
    type: entity-filter
  - card:
      show_state: true
      type: glance
    entities:
      - entity: camera.aarlo_front_door_camera
        name: Front Door
      - entity: camera.aarlo_front_camera
        name: Front
      - entity: camera.aarlo_driveway_camera
        name: Driveway
      - entity: camera.aarlo_back_door_camera
        name: Back Door
    show_empty: false
    state_filter:
      - 'offline, too cold'
      - turned off
    type: entity-filter
```
When things happen it will look something like:

![Recent Activity](/images/activity.png)

## Automations

The following example automation will update the image 3 seconds after a recording event happens.

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

## Services

The component provides the following services:

| Service | Parameters | Description |
|---------------------------------------|-------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| camera.aarlo_request_snapshot | `entity_id` - camera to get snapshot from | This requests a snapshot be taken. Camera will move from  taking_snapshot state when finished. |
| camera.aarlo_request_snapshot_to_file | `entity_id` - camera to get snapshot from<br>`filename` - where to save snapshot | This requests a snapshot be taken and written to the passed file. Camera will move from  taking_snapshot state when finished. |
| camera.aarlo_stop_activity | `entity_id` -  camera to get snapshot from | This moves the camera into the idle state. Can be used to stop streaming. |
| alarm_control_panel.aarlo_set_mode | `entity_id` -  camera to get snapshot from<br>`mode` - custom mode to change to | Set the alarm to a custom mode. |

## Web Sockets

The component provides the following extra web sockets:

| Service | Parameters | Description |
|---------------------------------------|-------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| aarlo_video_url | `entity_id` - camera to get details from | Request details of the last recorded video. Returns:<br>`url` - video url<br>`url_type` - video type<br>`thumbnail` - thumbnail image url<br>`thumbnail_type` - thumbnail image type |
| aarlo_library | `at-most` - return at most this number of entries | Request up the details of `at-most` recently recorded videos. Returns an array of:<br>`created_at`: unix time stamp<br> `created_at_pretty`: pretty version of the create time<br> `url`: URL of the video<br> `url_type`: video type<br> `thumbnail`: URL of the thumbnail<br> `thumbnail_type`: thumbnail type<br> `object`: object in the video that triggered the capture<br> `object_region`: region in the video that triggered the capture|
| aarlo_stream_url | `entity_id` -  camera to get snapshot from<br>`filename` - where to save snapshot | Ask the camera to start streaming. Returns:<br>`url` - URL of the video stream |
| aarlo_snapshot_image | `entity_id` -  camera to get snapshot from | Request a snapshot. Returns image details: <br>`content_type`: the image type<br>`content`: the image |
| aarlo_stop_activity | `entity_id` - camera to stop activity on | Stop all the activity in the camera. Returns: <br>`stopped`: True if stop request went in |

## To Do

* custom mode - like SmartThings to better control motion detection
* enhance live streaming
* use asyncio loop internally
* setup pypi

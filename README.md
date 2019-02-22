# hass-aarlo

Asynchronous Arlo Component for Home Assistant.

The component operates in a similar way to the [Arlo](https://arlo.netgear.com/#/cameras) web site - it opens a single event stream to the Arlo backend and monitors events and state changes for all base stations, cameras and doorbells in a system. Currently it only lets you set base station modes.

The component supports:
* base station mode changes
* camera motion detection
* camera audio detection
* door bell motion detection
* door bell button press
* on the Lovelace UI it will report camera streaming state on the picture entity - ie, a clip is being recorded or somebody is view a stream on the Arlo app or if the camera is too cold to operate
* saving of state across restarts
* camera on/off
* request thumbnail updates

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
For the simplest use replace all instances of the `arlo` with `aalro` in your home-assistant configuration files. To support motion and audio capture add `aarlo` as a platform to the `binary_sensor` list.

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
    home_mode_name: Home
    away_mode_name: armed

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

The following new parameters can be specified against the aarlo platform:

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
```
* If `packet_dump` is True `aarlo` will store all the packets it sees in `/config/.aarlo/packets.dump` file.
* `db_motion_time` sets how long a doorbell motion will last. Arlo doorbell only indicates motion is present not that it stops. You can adjust the stop time out here.
* `db_ding_time` sets how long a doorbell button press will last. As with motion Arlo doorbell only tells us it's pressed not released.
* `recent_time` is used to hold the cameras in a `recent activity` state after a recording or streaming event. The actually streaming or recording can be over in a few seconds and without this the camera will revert back to idle possible looking like nothing has happend.
* `last_format` is a `strftime` compatible string indicating how you want the last captured time displayed
* `config_dir` is where the component stores its state. The default is fine for hassio, docker system and virtualenv systems. You shoudn't have to change this.

For `alarm_control_panel` you only need to specify the modes if you have custom mode names, see [here](https://www.home-assistant.io/components/arlo/#alarm) for more information.

Now restart your home assistant system.

## Resource Configuration

*This piece is optional, `aarlo` will work with the standard Lovelace cards.*

The new resource `aarlo-glance` is based on `picture-glance` but tailored for the Arlo component to simplify the configuration. To enable it add the following to the top of your UI configuration file.

```yaml
resources:
  - type: module
    url: /local/aarlo-glance.js
```
You configure a camera with the following yaml. The `show` parameters are optional but you must have atleast one.

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
```

You don't need to reoboot to see the GUI changes, a reload is sufficient. And if all goes will see a card that looks like this:

![Aarlo Glance](/images/aarlo-glance-02.png)

Reading from left to right you have the camera name, motion detection indicator, captured clip indicator, battery levels, signal level and current state. If you click the image the last captured clip will play, if you click the last captured icon up to the last 9 videos will be show as thumbnails on the card. Clicking on a thumbnail starts the appropiate video. (The video streams directly from Arlo which solves some weird speed issues I was seeing.) Click the camers (not shown) will take a snapshot and replace the current thumbnail.
The states are:
* `Idle` camera is doing nothing
* `Turned Off` user has turned the camera off
* `Recording` camera has detected something and is recording
* `Streaming` camera is streaming live video other login
* `Taking Snapshot` camers is updating the thumbnail
* `Recently Active` camera has seen activity within the last few minutes
* `Too Cold!` the camera is shutdown until it warms up

See the [Lovelace Custom Card](https://developers.home-assistant.io/docs/en/lovelace_custom_card.html) page for further information.

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

## To Do

* custom mode - like SmartThings to better control motion detection
* live streaming???
* arlo q cameras


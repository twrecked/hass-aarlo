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

**This is an alpha release - it's working great for me - 3 base stations, 11 cameras, 2 doorbells - but I haven't had chance to test it against many different configurations!**

## Installation

### Manually
Copy all directories into your home-assistant `custom_components` directory.

### Script
Run the install script. Run it once to make sure the operations look sane and run it a second time with the `go` paramater to do the actual work. If you update just rerun the script, it will overwrite all installed files.

```sh
install /path/to/your/custom_components
# check output looks good
install go /path/to/your/custom_components
```

## Configuration

For the simplest use replace all instances of the `arlo` with `aalro` in your home-assistant configuration files. To support motion and audio capture add `aarlo` as a platform to the binary_sensor list.

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
    away_mode_name: Armed

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
```
* If `packet_dump` is True `aarlo` will store all the packets it sees in `/config/.aarlo/packets.dump` file.
* `db_motion_time` sets how long a doorbell motion will last. Arlo doorbell only indicates motion is present not that it stops. You can adjust the stop time out here.
* `db_ding_time` sets how long a doorbell button press will last. As with motion Arlo doorbell only tells us it's pressed not released.

Now restart your home assistant system.

## To Do

* turn cameras on/off
* custom mode - like SmartThings to better control motion detection
* caching of last video to speed up showing of it
* live streaming???




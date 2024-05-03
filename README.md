# **An Arlo Home Assistant Integration**

_Aarlo_ is a custom component for [Home  Assistant](https://www.home-assistant.io/), that provides access to  the [Arlo](https://www.arlo.com/en-us/) system.

_Aarlo_ provides, amongst other things:
- Access to cameras, base stations, sirens, doorbells and lights.
- Asynchronous, almost immediate, notification of motion, sound and button press events.
- Ability to view library recordings, take snapshots and direct stream from cameras.
- Tracking of environmental stats from certain base station types.
- Special switches to trip alarms and take snapshots from cameras.
- Enhanced state notifications.
- Media player support for select devices.

# Table Of Contents

<!-- TOC -->
* [**An Arlo Home Assistant Integration**](#an-arlo-home-assistant-integration)
* [Table Of Contents](#table-of-contents)
* [Introduction](#introduction)
  * [Notes](#notes)
  * [Thanks](#thanks)
  * [See Also](#see-also)
* [Requirements](#requirements)
* [Installing the Integration](#installing-the-integration)
  * [HACS](#hacs)
  * [Manually](#manually)
  * [From Script](#from-script)
* [Adding and Configuring the Integration](#adding-and-configuring-the-integration)
  * [Further Configuration](#further-configuration)
    * [Alarm Setting Screen](#alarm-setting-screen)
    * [Binary Sensors Screen](#binary-sensors-screen)
    * [Sensors Screen](#sensors-screen)
    * [Switches Screen](#switches-screen)
* [Coming From Earlier Versions](#coming-from-earlier-versions)
* [Advanced Configuration](#advanced-configuration)
  * [Back Ends](#back-ends)
    * [How it Works](#how-it-works)
    * [Configuration](#configuration)
  * [Cloud Flare](#cloud-flare)
    * [How We Work Around This](#how-we-work-around-this)
    * [Configuration](#configuration-1)
  * [Two Factor Authentication](#two-factor-authentication)
    * [IMAP](#imap)
      * [Application Passwords](#application-passwords)
      * [IMAP Servers](#imap-servers)
    * [PUSH](#push)
  * [Configuration](#configuration-2)
* [Bug Reports](#bug-reports)
  * [What to Include](#what-to-include)
  * [Enabling Debug](#enabling-debug)
  * [Encrypting the Output](#encrypting-the-output)
* [Reverse Engineering](#reverse-engineering)
  * [Figuring out what Aarlo Needs to Do](#figuring-out-what-aarlo-needs-to-do)
  * [MQTT Stream](#mqtt-stream)
  * [SSE Stream](#sse-stream)
  * [Supporting New Features](#supporting-new-features)
* [FAQ](#faq)
* [Supported Devices](#supported-devices)
* [Known Limitations](#known-limitations)
<!-- TOC -->

# Introduction

_Aarlo_ is a custom component for [Home  Assistant](https://www.home-assistant.io/), that provides access to  the [Arlo](https://www.arlo.com/en-us/) system.

The integration uses the _APIs_ provided by the [Arlo Camera Website](https://my.arlo.com/#/home) and there are several limitations to this. See the [Known Limitations](#known-limitatons) section for further details.

If you encounter an issue then look at the [FAQ](#faq) section to see if it has a known problem and has a workaround or fix. If not, look at the [Bug Report](#bug-reports) section for information on how to generate debug logs and create a debug report.

The old _README_ is still available [here](https://github.com/twrecked/hass-aarlo/blob/doc-updates/README-202405.md).

## Notes

This document assumes you are familiar with _Home Assistant_ setup and configuration.

Wherever you see `/config` in this document it refers to your _Home Assistant_ configuration directory. For example, for my installation it's `/home/steve/ha` which is mapped to `/config` by my docker container.

Wherever you see _Arlo_ it refers to any piece of the _Arlo_ system.

Wherever you see _Aarlo_ I'm referring to this component.

## Thanks

Many thanks to:
- [Pyarlo](https://github.com/tchellomello/python-arlo) and  [Arlo](https://github.com/jeffreydwalter/arlo) for doing all the hard work figuring the API out and the free Python lesson!
- [sseclient](https://github.com/btubbs/sseclient) for reading from the event stream
- [Button Card](https://github.com/kuuji/button-card/blob/master/button-card.js) for a working Lovelace card I could understand
- [JetBrains](https://www.jetbrains.com/?from=hass-aarlo) for the excellent **PyCharm IDE** and providing me with an open source licence to speed up the project development.

[![JetBrains](images/jetbrains.svg)](https://www.jetbrains.com/?from=hass-aarlo)

## See Also

_Aarlo_ also provides a custom [_Lovelace Card_](https://github.com/twrecked/lovelace-hass-aarlo), which overlays a camera's last snapshot with its current status and allows access to the cameras recording library and live-streaming.

If you aren't familiar with _Home Assistant_ I recommend visiting the  [Community Website](https://community.home-assistant.io/). It's full of helpful people and there is always someone who's encountered the problem you are trying to fix.

# Requirements

_Aarlo_ needs a dedicated _Arlo_ account. If you try to reuse an existing account, for example, the one you use on the _Arlo_ app on your phone, the app and this integration will constantly fight to log in. This is an _Arlo_ limitation.

The dedicated _Aarlo_ account needs admin access to set the alarm levels and read certain status values.

See [the _Arlo_ documentation](https://kb.arlo.com/000062933/How-do-I-add-friends-on-my-Arlo-Secure-app-Arlo-Secure-4-0#:~:text=To%20add%20a%20friend%20to%20your%20Arlo%20account%3A&text=Tap%20or%20click%20to%20add,grant%20the%20user%20additional%20privileges.) for further instructions.

You need to enable two factor authentication. Set up an email address to receive the verification code. _Aarlo_ supports other _TFA_ mechanisms but email is the easiest to use. See the [Two Factor Authentication](#two-factor-authentication) section later for more details.

# Installing the Integration

**You only need to use one of these installation mechanisms. I recommend HACS.**

## HACS

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

_Aarlo is part of the default HACS store. If you're not interested in using development branches this is the easiest way to install._

## Manually

Copy the `aarlo` directory into your `/config/custom_components` directory.

## From Script

Run the installation script. Run it once to make sure the operations look sane and run it a second time with the `go` parameter to do the actual work. If you update just rerun the script, it will overwrite all installed files.

```sh  
install /config # check output looks good  
install go /config
```

# Adding and Configuring the Integration

However you install the source code you know need to add the integration into _Home Assistant_. From the home page select `Settings -> Devices & Services`, from here click `ADD INTEGRATION` and search for `Aarlo`. On the first screen enter your account details.

![The Image View](/images/config-flow-01.png?raw=true)

| Field                | Value                                    |
| ---                  | ---                                      |
| Username             | Your _Arlo_ account username             |
| Password             | Your _Arlo_ account password             |
| Two Factor Mechanism | Select IMAP                              |
| TFA Username         | The email account you registered for TFA |
| TFA Password         | The email account password               |
| TFA Host             | The IMAP server to look for the email on |

If you leave `Use aarlo prefix` checked all your devices will be of the format `type.aarlo_*`.

Click `SUBMIT`. The integration will log into _Arlo_ and retrieve the list of devices associated with it. If it all works you will be able to assign the devices to rooms on the the next screen.

![The Image View](/images/config-flow-02.png?raw=true)

## Further Configuration

You can fine tune the settings further. From the Integration page click `CONFIGURE`.

### Alarm Setting Screen

Fine tune the alarm settings:

![The Image View](/images/config-flow-03.png?raw=true)


| Field                | Value                                                    |
| ---                  | ---                                                      |
| Alarm/disarm Code    | Enter a code if needed, otherwise leave as default       |
| Disarmed mode name   | Change if your Arlo account has a custom disarmed name   |
| Home mode name       | Change if your Arlo account has a custom home mode name  |
| Away mode name       | Change if your Arlo account has a custom away mode name  |
| Night mode name      | Change if your Arlo account has a custom night mode name |
| Arm code required    | Select if Alarm/disarm code is needed to arm             |
| Disarm code required | Select if Alarm/disarm code is needed to disarm          |
| Trigger time         | How long to wait when arming                             |
| Alarm volume         | Default volume for the alarm sirens                      |

_Night Mode_; _Arlo_ will not have one of these unless you create it


### Binary Sensors Screen

Determine which binary sensors are available:

![The Image View](/images/config-flow-04.png?raw=true)

| Field               | Value                                   |
| ---                 | ---                                     |
| Sound detection     | Enable microphones on cameras           |
| Motion detection    | Enable motion detection on cameras      |
| Doorbell presses    | Enable doorbell buttons                 |
| Cry detection       | For Arlo baby, enable cry detection     |
| Device connectivity | Be notified when a device disconnects   |
| Open/Close sensors  | Enable door and window sensors          |
| Brightness sensors  | Enable light detection                  |
| Tamper detection    | Enable notification if device is opened |
| Leak detection      | Enable leak monitoring devices          |

Not all sensors are available on all devices.

### Sensors Screen

![The Image View](/images/config-flow-05.png?raw=true)

Determine which sensors are available:

| Field                                     | Value                                                           |
| ---                                       | ---                                                             |
| Last capture time                         | A per camera sensor indicating when the last recording was made |
| Total number of cameras detected          | Integer value of camera count                                   |
| Recent activity detected                  | Was the camera recently active                                  |
| Number of videos/snapshots captured today | Integer value of recording made today                           |
| Device battery level                      | Percentage of battery left                                      |
| WiFi signal strength                      | WiFi strength, has a range of 1 to 5                            |
| Room temperature                          | Room conditions                                                 |
| Room humidity                             | Room conditions                                                 |
| Air quality                               | Room conditions                                                 |

Not all sensors are available on all devices.  And _recent activity_ should probably be a _binary_sensor_.

### Switches Screen

Enable miscellaneous switches:

![The Image View](/images/config-flow-06.png?raw=true)

| Field                                       | Value                                                |
| ---                                         | ---                                                  |
| Switches to turn sirens on                  | Provide a switch to turn individual sirens on        |
| A switch turn all sirens on                 | Provide a switch to turn all sirens on               |
| Allow sirens to be turned off               | Allow sirens to be turned off by switch              |
| Siren switch volume                         | Default volume level, from 1 to 10                   |
| Siren Switch duration                       | Default time to run the alarm                        |
| Switches to request cameras take a snapshot | Provide a switch to take a camera snapshot           |
| Camera snapshot timeout                     | How long to wait for badly behaved cameras to finish |
| Switches to silence doorbell chimes         | Provide a switch to silence doorbells.               |

# Coming From Earlier Versions

If you are coming from an early there are several things to note:

- Your configuration will be imported into the `config flow` mechanism. All your devices will appear on the integration page.
- You will not be able to change your login or TFA settings without deleting the Intergration.
- You will be able to fine tune with the [Further Configuration](#further-configuration) settings.
- You can comment out the original `yaml` entries.
- The import enables the `prefix with _aarlo` to keep the naming identical.
- All component services are now in the `aarlo` domain.
- The `pyaarlo` component is now installed via `pip` and not included with the Integration.

I wasn't willing to move some of the more esoteric configuration items into the `config flow` mechanisms, if you had any configured they will appear in the `/config/aarlo.yaml` file.

# Advanced Configuration

## Back Ends

_Arlo_ will use either [SSE](https://en.wikipedia.org/wiki/Server-sent_events) or [MQTT](https://en.wikipedia.org/wiki/MQTT) to signal events to _Aarlo_. I'm not fully sure of the mechanism which determines which gets chosen but I know adding or removing a `user_agent` will switch between the two.

### How it Works

_Arlo_ recently updated the response they send to the `session/v3` API requests to indicate which back end to choose. _Aarlo_ will parse that out when using `auto`.

```yaml
# This is the MQTT backend. We use the host and port.
'mqttUrl': 'ssl://mqtt-cluster-z1.arloxcld.com:8883'

# This is the SSE backend. We use a fixed host and port.
'mqttUrl': 'wss://mqtt-cluster-z1.arloxcld.com:8084'
```

If you enable verbose debugging your should be able to find this value in the _Home Assistant_ logs.

### Configuration

Starting with the `0.8` release _Aarlo_ should be smart enough to work out which back end to use. But if you find yourself running into problems, like missing motion detection events or missing sensor value updates you can manually override the setting. Change this setting in `/config/aarlo.yaml`.

```yaml
aarlo:
  # This forces the SSE backend
  backend: sse
```

```yaml
aarlo:
  # This forces the MQTT backend
  backend: mqtt
  # These might also be needed
  mqtt_hostname_check: false
  mqtt_host: mqtt-cluster-z1.arloxcld.com
```

```yaml
aarlo:
  # This forces Aarlo to choose
  backend: auto
```

Note, removing the setting is equivalent to `auto`.

## Cloud Flare

_Arlo_ uses _Cloud Flare_ anti-bot protection to the _Arlo_ website login. This service doesn't work well with the _Python Requests_ package (or how _Aarlo_ uses those requests, I'm not too sure).

If you see the following errors you are running into _Cloud Flare_ issues.

```  
2021-06-03 13:28:32 WARNING (SyncWorker_4) [pyaarlo] request-error=CloudflareChallengeError  
```  

This problem affects me, and I'm constantly trying to refine the code.

### How We Work Around This

_Aarlo_ does several things to work around this:

- It uses the [cloudscraper](https://pypi.org/project/cloudscraper/) module to wrap the login requests to _Arlo_. After the login is complete _cloudscraper_ is not needed.
- It mimics the official website requests as closely as possible, down to the `Header` level.
- It will cache successful login credentials for up to 2 weeks so when you restart _Home Assistant_ _Aarlo_ won't need to login again.

### Configuration

But, if you are still seeing login issues there are several configuration items you can try.

You can try a different user agent. This is configured in `/config/aarlo.yaml`:

```yaml
aarlo:
  # Change the user agent. It can be either arlo, iphone, ipad, mac, firefox or linux
  #  or random. random will change it each time it tries to login
  user_agent: linux

  # Or use a custom user agent, everything after the ! will be used
  user_agent: !this-is-a-custom-user-agent
```

You can add a `Source` header along with the login request. I have one site that needs this and one that doesn't. _I think it might be user agent related._

```yaml
aarlo:
  # This adds the following header "Source: arloCamWeb"
  send_source: true
```

You can disable session caching with the following:

```yaml
aarlo:
  # This will force a full login on every restart
  save_session: false

```

You can select different _ecdh_ curves to use. This topic is out of the scope of this document, see [here](https://github.com/venomous/cloudscraper#cryptography) for an explanation.

```yaml
aarlo:
  # Make this curve the first choice. You can only enter 1 choice.
  ecdh_curve: secp384r1
```

You can modify `/etc/hosts` to point to a specific _Arlo_ web server

```
# Remove the # to force the request to go to a particular cloudflare server
#104.18.30.98 ocapi-app.arlo.com  
#104.18.31.98 ocapi-app.arlo.com  
```

## Two Factor Authentication

_Arlo_ calls this _Two-step Verification_. You are going to need to enable this for your _Home Assistant_ specific account. _Aarlo_ support _IMAP_ and _PUSH_ mechanisms but I recommend using _IMAP_, with _PUSH_ you need to manually respond to the login request.

You will find instructions for setting up two factor authentication here [Arlo provide here](https://kb.arlo.com/000062289/How-do-I-edit-Arlo-two-step-verification-settings)

You enter two factor authentication when you add the integration.

### IMAP

Follow the two factor authentication instructions and add and set up an _Email_ verification method. You can test this by logging into the [main Arlo web page](https://my.arlo.com/#/home) and making sure it sends you an email.

#### Application Passwords

For _Gmail_ and _Yahoo_ (and other web based email client) you can't log in with your usual password, you will have to create an application specific password. Explaining why this is necessary is out of the scope of this document so see the following pages.

- [Gmail App Password](https://support.google.com/mail/answer/185833?hl=en)
- [Yahoo App Password](https://help.yahoo.com/kb/SLN15241.html)

If you find you can't log in to your _IMAP_ account check the application password requirement.

#### IMAP Servers

The following servers are known to work:

| Service | Host Name           |
| ---     | ---                 |
| Gmail   | imap.gmail.com      |
| Yahoo!  | imap.mail.yahoo.com |

### PUSH

Follow the two factor authentication instructions and add and set up a _PUSH_ verification method.

## Configuration

If you need to change the cipher list passed to the IMAP client you specify it with the following option. You shouldn't need to do this. see [the openssl man page](https://www.openssl.org/docs/man1.1.1/man1/ciphers.html) for more information.

```yaml
aarlo:
  # specify cipher list to use
  cipher_list: "HIGH:!DH:!aNULL"

  # Use DEFAULT for the cipher list
  default_ciphers: True
```

# Bug Reports

## What to Include

If you run into problems please create a [bug report](https://github.com/twrecked/hass-aarlo/issues), include the following information in the bug report to help debugging. If you don't I'll just pester you until you do.

- The version of _Home Assistant_ you are running.
- The version of _Aarlo_ you are running, just saying _latest_ isn't adequate.
- Make of cameras or device you are having problems.
- What you were doing or expecting.
- Include debug logs if available.

## Enabling Debug

You turn on basic  _Aarlo_ debugging by changing the logging setting in `configuration.yaml`.

```yaml
logger:
  default: info
  logs:
    pyaarlo: debug
    custom_components.aarlo: debug
```

You can turn on verbose debugging by enabling logging and adding the following to `/config/aarlo.yaml` as well. Verbose debug will generate a lot of logs so it's best to enable only while needed.

```yaml
aarlo:
  verbose_debug: true
```

## Encrypting the Output

Before you send me the debug you should encrypt it.  You can encrypt your output on this [web page](https://pyaarlo-tfa.appspot.com/). You can upload the file or copy and paste it into the buffer then press `Submit`.

**This page doesn't forward automatically the output to me, so you will have to copy and paste it into a file and attach it to the bug report.**

This page will obscure the logs so only I can read them, I'm the sole possessor of the private key to decrypt it, but be wary, along with serial number it might include your account and password information. You can obscure those before encrypting, I never need them.

# Reverse Engineering

## Figuring out what Aarlo Needs to Do

I don't own every piece _Arlo_ of equipment so sometimes, when things go wrong or new equipment is released, I need to see what _Arlo_ actually expects this code to send and what this code can expect back from _Arlo_. _Aarlo_ simulates a web browser connection so you can find out what is expected by using the browser _Developer Tools_.

_This instructions are for Chrome but most browsers (I hope!) have similar functionality._

- Open your browser.
- Go to [the Arlo camera website](https://my.arlo.com/#/home).
- With the _Arlo_ website open enable you browser's developer tools. On Chrome you click the three dots in the upper right corner, then select `More Tools` and finally select `Developer Tools`. You can also use the shortcut `CTRL+SHIFT+I`.
- Select the `Network` tab in the newly opened window.
- Now log in to the _Arlo_ website.

When you log in the data passed between the browser and _Arlo_ website will start to appear, and keep appearing, in this tab. If you click on an entry under `Name` you can examine the packets in more detail.

- The `Headers` tab shows you what was sent in the headers of the request.
- The `Payload` tabs shows you what was sent in the body of the request
- The `Preview` tab shows the reply sent back from _Arlo_.

![Network TAB](images/chrome-2.png)

If you hover over the field under `name` a pop up will display the full URL the request was sent to.

## MQTT Stream

_I need to document this._

## SSE Stream

Look for a URL containing the word `subscribe`, this will be the even stream _Arlo_ sends back to the web page. As you click buttons on the web page more items will appear in this list. I can use this information to determine how to parse response packets for cases I don't yet handle.

## Supporting New Features

For example, _Arlo_ creates a new device with a `WOOHOO` button, I don't posses such a device but you'd like the `WOOHOO` functionality implementing in _Aarlo_. What I need is the sequence of packets and their replies when you press the button. The only real way to do this is to press the button and see what new packets appear in the `Name` tab.

You will then need to copy and paste them into a bug report on _GitHub_. See [the previous section](#encrypting-the-output) on how to hide sensitive data.

# FAQ

_I need to fill this out_

# Supported Devices

This is a list of devices that are known to work. Most _Arlo_ devices will work even if not explicitly mentioned in this list although they might have limited functionality.

| Model   | Name                     | Notes |
| ---     | ---                      | ---   |
| ABC1000 | Baby                     |       |
| AVD1001 | Wired Video Doorbell     |       |
| AVD2001 | Essential Video Doorbell |       |
| AVD3001 | Wired Video Doorbell HD  |       |
| AVD4001 | Wired Video Doorbell 2K  |       |
| FB1001  | Pro 3 Floodlight         |       |
| MS1001  | All in 1 Sensor          |       |
| VMB3010 | Base Station             |       |
| VMB4000 | Base Station 2           |       |
| VMC2030 | Essential                |       |
| VMC2040 | Essential Indoor         |       |
| VMC3030 | HD                       |       |
| VMC3052 | Essential XL             |       |
| VMC4030 | Pro 2                    |       |
| VMC4040 | Pro 3                    |       |
| VMC4041 | Pro 4                    |       |
| VMC4060 | Pro 5                    |       |
| VMC5040 | Ultra                    |       |
| VML2030 | Go 2                     |       |
| VML4030 | Go                       |       |

# Known Limitations
This component was written by reverse engineering the _APIs_ used on the [Arlo Camera](https://my.arlo.com/#/home) web page.

These are general limitations:
- _There is no Documentation_; I, and others, have had to reverse engineer the protocol, and for the most part this is easy enough once I get the packets...
- _but I don't have access to all the equipment_; so I rely on users to provide the device information and packets for me. The _Reverse Engineering_ section gives you instructions on how to get these packets. Or, if you are feeling brave, you can temporarily share the device with me.
- _and Arlo likes to Change Things_; this all becomes more problematic when _Arlo_ decides to change how things work, one minute things work and the next minute things break, unfortunately it has to break before I can fix it.

These are limitations verses the website:
- _Cloud Flare_; _Aarlo_ has to bypass the 'not-a-robot' checks of _Cloud Flare_ to login, this works most of the time but _Arlo_ will change their back-end occasionally and break it. There are settings in the _advanced configuration_ you can change to help with this. *And yes, this can be a pain to get working*.

These are limitations versus the mobile application:
- _Object Detection_; the mobile application will let you know almost immediately what triggered the motion event, this is not possible with the website _APIs_.
- _Timeouts_; the website doesn't feel like it was designed for persistent connections so _Aarlo_ has a lot of code inside to try to mitigate this. But occasionally you might miss an event. There are settings in the _advanced configuration_ you can change to help with this.

The last two can be summed up as `if the WEB API doesn't support it, neither can the component.` Bear that in mine when asking for new feature requests.

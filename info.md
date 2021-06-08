# Asynchronous Arlo Component for Home Assistant.

An (almost) drop in replacement for the standard
[Arlo](https://my.arlo.com/#/cameras) package.

Please visit the
[Readme](https://github.com/twrecked/hass-aarlo/blob/master/README.md) for more
details.

{% if prerelease %}

## NB!: This is an Alpha version!

## New Features in 0.8

### Split Out Pyaarlo
The code now uses `pyaalo` by installing it via `pip` rather than maintaining 
its own version.

### Authentication Caching
The code will retry authorization tokens for as long as they are valid. This 
means a reduction in authentication attempts and 2FA requests. If this 
does not work for you send me some logs and add`save_session: False` to your 
configuration.

## Breaking Changes in 0.8
The following options have been removed:
- `hide_deprecated_services`; all component services are now in the `aarlo` 
  domain.
- `http_connections`; no longer used after `cloudscraper` was needed
- `http_max_size`; no longer used after `cloudscraper` was needed

{% endif %}

## Features

Aarlo provides:

- Access to cameras, base stations, sirens, doorbells and lights.
- Asynchronous, almost immediate, notification of motion and sound events.
- Ability to view library recordings, take snapshots and direct stream from cameras.
- Tracking of environmental stats from certain base station types.
- Special switches to trip alarms and take snapshots from cameras.
- Enhanced state notifications.
- Media player support for select devices.

There is also a resource
[`aarlo-glance`](https://github.com/twrecked/lovelace-hass-aarlo) which is based
on `picture-glance` but tailored for the Arlo component.

## Example

![Aarlo Glance](https://github.com/twrecked/hass-aarlo/blob/master/images/aarlo-glance-02.png)

## Documentation

Please visit the
[Readme](https://github.com/twrecked/hass-aarlo/blob/master/README.md) for full
documentation.

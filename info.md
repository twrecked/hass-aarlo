# Asynchronous Arlo Component for Home Assistant.

An (almost) drop in replacement for the standard [Arlo](https://my.arlo.com/#/cameras) package.

Please visit the [Readme](https://github.com/twrecked/hass-aarlo/blob/master/README.md) for more details.

## 2FA Support

This release contains beta 2FA support. It works by requesting an email with the one-time code and then making an IMAP connection to your email provider and reading the code from the email Arlo sends.

There is a **lot** that can go wrong with this - for starters, I've only tested it in English - but to get it working add the following configuration (with the correct values obviously) - to `aarlo:`

```yaml
  imap_host: 'imap.gmail.com'
  imap_username: 'your.email.account@gmail.com'
  imap_password: 'roygbiv'

```

For gmail users, the following [help](https://support.google.com/accounts/answer/185833?hl=en) is useful.

Finally, if you haven't enabled 2FA you don't need to do this.

## Notice of Future Breaking Changes

### The custom services are moving into the `aarlo` domain.

This release moves all the component services in the `aarlo` domain. This is their correct location and allows Home Assistant to use the component's `services.yaml` file to provide help with the services.

To allow you to transition and test your scripts the old, incorrectly located, services will remain for a while. My plan is to remove them in a few months. If you move all your code over to the new services you can add the `hide_deprecated_services` option to your configuration to hide these old services.

See [Services](#advanced-services) for more information.


## Features

Aarlo provides:

- Access to cameras, base stations, sirens, doorbells and lights.
- Asynchronous, almost immediate, notification of motion and sound events.
- Ability to view library recordings, take snapshots and direct stream from cameras.
- Tracking of environmental stats from certain base station types.
- Special switches to trip alarms and take snapshots from cameras.
- Enhanced state notifications.
- Media player support for select devices.

There is also a resource [`aarlo-glance`](https://github.com/twrecked/lovelace-hass-aarlo) which is based on `picture-glance` but tailored for the Arlo component.

## Example

![Aarlo Glance](https://github.com/twrecked/hass-aarlo/blob/master/images/aarlo-glance-02.png)

## Documentation

Please visit the [Readme](https://github.com/twrecked/hass-aarlo/blob/master/README.md) for full documentation.

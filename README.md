# Home Assistant Multizone Media Player Controller

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
<br><a href="https://www.buymeacoffee.com/Petro31" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-black.png" width="150px" height="35px" alt="Buy Me A Coffee" style="height: 35px !important;width: 150px !important;" ></a>

_Multizone Media Player Controller app for AppDaemon._

This creates a sensor that represents the current media_player zone that is under control.

e.g. You have a reciever with 3 zones.  When brought into Home Assistant, you get 3 separate Zones.  You'd like to turn the volume up for all the zones that are on, or optionally just turn on one.

* The created sensors current state will represent which zones are on.  e.g. `All Zones`, `Zone 1`, `Zone 2`, `Zone 1`, `Zone 1,2`, `off`.
* The sensor will contain a list of available media_players (All players that are currently on).
* The sensor will contain a list of active media_players (All players that will be affected by the events).

## Installation

Download the `multizone_media_control` directory from inside the `apps` directory to your local `apps` directory, then add the configuration to enable the `hacs` module.

## Example App configuration

#### Basic
```yaml
# Creates a controller that will cycle between Zone 1, Zone 2, and All Zones (when all are on).
zone1_volume:
  module: convert_media_volume
  class: ConvertMediaVolume
  media_players:
  - media_player.yamaha_receiver
  - media_player.yamaha_receiver_zone_2
```

#### Advanced 
```yaml
# Creates a controller that will cycle between Zone 1, Zone 2, and All Zones (when all are on).
# The volume will only increase and decrease on every 0.05 level.
multizone_controller:
  module: multizone_media_control
  class: MultiZoneController
  media_players:
  - media_player.yamaha_receiver
  - media_player.yamaha_receiver_zone_2
  snap_volume: true
  volume_increment: 0.05
  volume_max: 1.0
  volume_min: 0.2
```

#### App Configuration
key | optional | type | default | description
-- | -- | -- | -- | --
`module` | False | string | multizone_media_control | The module name of the app.
`class` | False | string | MultiZoneController | The name of the Class.
`media_players` | False | list | | list of media_player entity_ids.
`name` | True | str | `Active Media Player` | Friendly name of the Sensor.
`volume_max`| True | float | 1.0 | A maximum volume that the controller can go to.  range(0.51 - 1.25)
`volume_min`| True | float | 0.0 | A minimum volume that the controller can go to.  range(0.0 - 0.5)
`volume_increment`| True | float | 0.01 | The amount of volume that moves up and down when a volume_up/down event is detected.
`snap_volume`| True | bool | False | When this is active, the volume will snap to the volume increment.  Meaning if you have an increment of 0.5, the volume will only increase to all numerical values that are devisible by 0.05.  I.e. 0.0, 0.05, 0.10, 0.15, etc.
`event_id`| True | str | `multizone` | The `event_id` used in event data for an event service call.
`log_level` | True | `'INFO'` &#124; `'DEBUG'` | `'INFO'` | Switches log level.

## Recommended Setup

#### App configuration.
```
zone1_volume:
  module: convert_media_volume
  class: ConvertMediaVolume
  media_players:
  - media_player.yamaha_receiver
  - media_player.yamaha_receiver_zone_2
```

#### Scripts.yaml
```
multizone_volume_up:
  sequence:
  - event: mz_volume_up
    event_data:
      event_id: multizone
      
multizone_volume_down:
  sequence:
  - event: mz_volume_down
    event_data:
      event_id: multizone
      
multizone_volume_mute:
  sequence:
  - event: mz_volume_mute
    event_data:
      event_id: multizone
      
multizone_cycle_zone:
  sequence:
  - event: mz_cycle_zone
    event_data:
      event_id: multizone
      
multizone_volume_set:
  sequence:
  - event: mz_volume_set
    event_data_template:
      event_id: multizone
      volume_level: "{{ volume_level }}"
```

#### Service calls for the scripts.
```
  # VOLUME UP
  - service: script.multizone_volume_up

  # VOLUME DOWN
  - service: script.multizone_volume_down

  # VOLUME MUTE
  - service: script.multizone_volume_mute

  # CYCLE ZONES
  - service: script.multizone_cycle_zone

  # VOLUME SET
  - service: script.multizone_volume_set
    data:
      volume_level: 0.5
```

## Suggestions

I am open with suggestions.  I don't know if AppDaemon can create a media player and work properly.  But I can add an option's list to the sensor and pair it with an set_option event.  This would allow you to make an input select instead of using a script.  As I said, I'm open to any suggestion.  Ask and you _may_ recieve. 

import appdaemon.plugins.hass.hassapi as hass
import voluptuous as vol

MODULE = 'multizone_media_control'
CLASS = 'MultiZoneController'

CONF_MODULE = 'module'
CONF_CLASS = 'class'
CONF_MEDIA_PLAYERS = 'media_players'
CONF_NAME = 'name'
CONF_LOG_LEVEL = 'log_level'
CONF_SENSOR = 'sensor'
CONF_FRIENDLY_NAME ='friendly_name'
CONF_ENTITIES = 'entities'
CONF_ZONE = 'zone'
CONF_VOLUME_INCREMENT = 'volume_increment'
CONF_VOLUME_MAX = 'volume_max'
CONF_VOLUME_MIN = 'volume_min'
CONF_EVENT_ID = 'event_id'
CONF_SNAP_VOLUME = 'snap_volume'

LOG_ERROR = 'ERROR'
LOG_WARNING = 'WARNING'
LOG_DEBUG = 'DEBUG'
LOG_INFO = 'INFO'

STATE_ON = 'on'
STATE_OFF = 'off'
STATE_ALL = 'all'
STATE_MANY = 'many'

STATE_ORDER = {
    STATE_OFF:0,
    STATE_ALL:1,
    STATE_MANY:1,
    }

EVENT_ID_DEFAULT = 'multizone'

EVENT_VOLUME_UP = 'mz_volume_up'
EVENT_VOLUME_DOWN = 'mz_volume_down'
EVENT_VOLUME_MUTE = 'mz_volume_mute'
EVENT_VOLUME_SET = 'mz_volume_set'
EVENT_CYCLE_ZONE = 'mz_cycle_zone'



ATTRIBUTE_ACTIVE = 'active'
ATTRIBUTE_AVAILABLE = 'available'
ATTRIBUTE_ENTITY_ID = 'entity_id'
ATTRIBUTE_VOLUME_LEVEL = 'volume_level'
ATTRIBUTE_IS_VOLUME_MUTED = 'is_volume_muted'

DEFAULT_NAME = 'Active Media Player'

APP_SCHEMA = vol.Schema({
    vol.Required(CONF_MODULE): MODULE,
    vol.Required(CONF_CLASS): CLASS,
    vol.Required(CONF_MEDIA_PLAYERS, default=[]): [str],
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    vol.Optional(CONF_LOG_LEVEL, default=LOG_DEBUG): vol.Any(LOG_INFO, LOG_DEBUG),
    vol.Optional(CONF_VOLUME_MAX, default = 1.0): vol.All(vol.Coerce(float), vol.Range(min=0.51, max=1.25)),
    vol.Optional(CONF_VOLUME_MIN, default = 0.0): vol.All(vol.Coerce(float), vol.Range(min=0.00, max=0.50)),
    vol.Optional(CONF_VOLUME_INCREMENT, default = 0.01): vol.All(vol.Coerce(float), vol.Range(min=0.01, max=0.25)),
    vol.Optional(CONF_SNAP_VOLUME, default=False): bool,
    vol.Optional(CONF_EVENT_ID, default = EVENT_ID_DEFAULT): str,
})

LEVEL_SCHEMA = vol.Schema({
    vol.Optional(CONF_EVENT_ID): str, 
    vol.Required(ATTRIBUTE_VOLUME_LEVEL): vol.All(vol.Coerce(float), vol.Range(min=0.00, max=1.25))
})

class MultiZoneController(hass.Hass):
    def initialize(self):
        args = APP_SCHEMA(self.args)

        # Set Lazy Logging (to not have to restart appdaemon)
        self._level = args.get(CONF_LOG_LEVEL)
        self.log(args, level=self._level)

        self._players = { e:AppMediaPlayer(e, f'{i+1}') for i, e in enumerate(args.get(CONF_MEDIA_PLAYERS)) }

        self._sensor_name = args.get(CONF_NAME)

        object_id = self._sensor_name.replace(' ','_').lower()

        self._sensor_id = f"{CONF_SENSOR}.{object_id}"
        self._snap_volume = args.get(CONF_SNAP_VOLUME)
        self._threshold = max([ p.option for p in self._players.values() ])
        self._volume_increment = int(args.get(CONF_VOLUME_INCREMENT) * 100)
        self._min_volume = int(args.get(CONF_VOLUME_MIN) * 100)
        self._max_volume = int(args.get(CONF_VOLUME_MAX) * 100)

        # get the current state at startup.
        for p in self._players.values():
            state = self.get_state(p.entity_id)
            self.log(f'detected {p.entity_id} {state}', level = self._level)
            p.set_callback(state)
        self.update_sensor()

        self.listen_handles = {}
        for entity_id in self._players.keys():
            self.log(f'Creating {entity_id} listener.', level = self._level)
            self.listen_handles[entity_id] = self.listen_state(self.media_player_callback, entity_id)

        self.event_handles = {}
        data = {CONF_EVENT_ID: args.get(CONF_EVENT_ID)}

        for evt, callback in zip(
            [
                EVENT_VOLUME_UP,
                EVENT_VOLUME_DOWN,
                EVENT_VOLUME_MUTE,
                EVENT_VOLUME_SET,
                EVENT_CYCLE_ZONE,
            ],[
                self.volume_up_event,
                self.volume_down_event,
                self.volume_mute_event,
                self.volume_set_event,
                self.cycle_event,
            ]):

            self.log(f'Creating {evt} listener.', level = self._level)
            self.event_handles[evt] = self.listen_event(callback, evt, **data)

    def get_volume_level(self):
        """ base 100 volume level """
        levels = [ self.get_state(e, attribute=ATTRIBUTE_VOLUME_LEVEL) for e in self.active ]
        level = int(round(sum(levels) / len(levels), 2) * 100)
        if self._snap_volume:
            return (level - level % self._volume_increment)
        return level

    def set_volume_level(self, level):
        service_data = {
            ATTRIBUTE_ENTITY_ID: ', '.join(self.active),
            ATTRIBUTE_VOLUME_LEVEL: level / 100,
        }
        self.call_service('media_player/volume_set', **service_data)

    def volume_up_event(self, event_name, data, kwargs):
        self.log("volume up event", level = self._level)
        current = self.get_volume_level()
        next = current + self._volume_increment
        next = next if next <= self._max_volume else self._max_volume
        self.set_volume_level(next)

    def volume_down_event(self, event_name, data, kwargs):
        self.log("volume down event", level = self._level)
        current = self.get_volume_level()
        next = current - self._volume_increment
        next = next if next >= self._min_volume else self._min_volume
        self.set_volume_level(next)

    def volume_mute_event(self, event_name, data, kwargs):
        self.log("volume mute event", level = self._level)
        muted = any([ self.get_state(e, attribute=ATTRIBUTE_IS_VOLUME_MUTED) for e in self.active ])
        service_data = {
            ATTRIBUTE_ENTITY_ID: ', '.join(self.active),
            ATTRIBUTE_IS_VOLUME_MUTED: not muted,
        }
        self.call_service('media_player/volume_mute', **service_data)

    def volume_set_event(self, event_name, data, kwargs):
        self.log(f"volume set event: {data}", level = self._level)
        data = LEVEL_SCHEMA(data)

        level = int(data.get(ATTRIBUTE_VOLUME_LEVEL) * 100)
        if self._snap_volume:
            level = (level - level % self._volume_increment)

        if self._min_volume <= level <= self._max_volume:
            self.set_volume_level(level)
        else:
            self.log(f'volume out of range: {level}', level = LOG_WARNING)

    def cycle_event(self, event_name, data, kwargs):
        self.log("cycle active media player event", level = self._level)
        # Never turn off.  Next will be 1 or current + 1.
        next = 1 if self.option == self._threshold else self.option + 1
        if next in self.options:
            self.option = next
            self.update_sensor()

    @property
    def option(self):
        """ returns an integer, order of a 'list' that doesn't exist """
        if len(self.active) == len(self._players):
            return STATE_ORDER[STATE_ALL]
        elif len(self.active) == 0:
            return STATE_ORDER[STATE_OFF]
        else:
            if len(self.active) > 1:
                return STATE_ORDER[STATE_MANY]
            else:
                return self._players[self.active[0]].option

    @option.setter
    def option(self, option):
        if option == 1:
            # many or all option
            for entity_id in self.available:
                self._players[entity_id].activate()
        else:
            # single zone option

            # deactivate all options
            for p in self._players.values():
                p.deactivate()

            # find the option
            selected = [ p.entity_id for p in self._players.values() if p.option == option ]
            if len(selected) == 1:
                self._players[selected[0]].activate()

    @property
    def options(self):
        ret = []
        if len(self.available) == len(self._players):
            ret += [ STATE_ORDER[STATE_ALL] ]
        ret += [ p.option for p in self._players.values() if p.available ]
        return ret

    def update_sensor(self):
        attributes = {
            CONF_FRIENDLY_NAME: self._sensor_name,
            CONF_ENTITIES: list(self._players.keys()),
            ATTRIBUTE_AVAILABLE: self.available,
            ATTRIBUTE_ACTIVE: self.active,
            }

        if len(self.active) == len(self._players):
            state = f'{STATE_ALL} {CONF_ZONE}s'
        elif len(self.active) == 0:
            state = STATE_OFF
        else:
            names = [ p.zone for p in self._players.values() if p.active ]
            names.sort()
            state = f"{CONF_ZONE} {','.join(names)}"

        self.log(f"{self._sensor_id} -> {state}: {attributes}", level = self._level)
        self.set_state(self._sensor_id, state=state, attributes=attributes)

    @property
    def available(self):
        return [ p.entity_id for p in self._players.values() if p.available ]

    @property
    def active(self):
        return [ p.entity_id for p in self._players.values() if p.active ]

    def media_player_callback(self, entity, attribute, old, new, kwargs):
        self.log(f"{entity}.{attribute}: {old} -> {new}", level = self._level)
        if old != new:
            self._players[entity].set_callback(new)
            self.update_sensor()

    def terminate(self):
        for name, handle in self.listen_handles.items():
            self.log(f"Canceling '{name}' listen state handle.", level = self._level)
            self.cancel_listen_state(handle)

        for name, handle in self.event_handles.items():
            self.log(f"Canceling '{name}' listen event handle.", level = self._level)
            self.cancel_listen_event(handle)


class AppMediaPlayer(object):
    def __init__(self, entity_id, zone):
        self.entity_id = entity_id
        self.zone = zone
        self._active = STATE_OFF
        self._available = STATE_OFF
        self._option = int(zone)+1

    @property
    def active(self):
        return self._active == STATE_ON

    @property
    def available(self):
        return self._available == STATE_ON

    @property
    def option(self):
        return self._option

    def set_callback(self, state):
        self._active = state
        self._available = state

    def activate(self):
        self._active = STATE_ON
    
    def deactivate(self):
        self._active = STATE_OFF

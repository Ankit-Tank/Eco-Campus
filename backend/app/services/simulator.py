"""
GhostWatt — services/simulator.py
Manages the in-memory appliance state for interactive demo.
NO FastAPI imports.
"""
from typing import Dict

# appliance_state: {room_code: {equipment_name: bool (True = ON)}}
_appliance_state: Dict[str, Dict[str, bool]] = {}


def get_room_state(room_code: str) -> Dict[str, bool]:
    return _appliance_state.get(room_code, {})


def set_appliance(room_code: str, equipment: str, on: bool) -> Dict[str, bool]:
    if room_code not in _appliance_state:
        _appliance_state[room_code] = {}
    _appliance_state[room_code][equipment] = on
    return _appliance_state[room_code]


def toggle_appliance(room_code: str, equipment: str) -> bool:
    current = _appliance_state.get(room_code, {}).get(equipment, True)
    new_state = not current
    set_appliance(room_code, equipment, new_state)
    return new_state


def get_all_states() -> Dict[str, Dict[str, bool]]:
    return dict(_appliance_state)

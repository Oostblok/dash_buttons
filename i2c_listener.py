import smbus2
import time
import json
import websocket

STATE_SERVER = None
ACTION_SERVER = None

INITIALIZED = False
BRIGHT = False

bus = smbus2.SMBus(1)
SLAVE_ADDR = 0x45

button_map = {
    1: "toggle_mode",
    2: "previous_track",
    3: "toggle_play",
    4: "next_track",
    5: "toggle_brightness"
}

# --- WebSocket helpers ---
def get_state_server():
    global STATE_SERVER
    if STATE_SERVER is None:
        try:
            STATE_SERVER = websocket.create_connection("ws://localhost:54545/state")
        except Exception:
            return None
    return STATE_SERVER

def get_action_server():
    global ACTION_SERVER
    if ACTION_SERVER is None:
        try:
            ACTION_SERVER = websocket.create_connection("ws://localhost:54545/action")
        except Exception:
            return None
    return ACTION_SERVER

def get_state_value(state):
    ws = get_state_server()

    if ws is None:
        return None

    ws.send(json.dumps([state]))
    data = json.loads(ws.recv())

    return data.get(state, 0)

def set_state_value(state, v):
    ws = get_state_server()

    if ws is None:
        return None

    ws.send(json.dumps({state: v}))
    data = json.loads(ws.recv())

    return data.get(state, None)

def toggle_mode():
    ws = get_action_server()

    if ws is None:
        return None

    ws.send(json.dumps(["cycle_page"]))
    json.loads(ws.recv())

def previous_track():
    print("TODO: previous track")

def toggle_play():
    print("TODO: toggling play/pause")

def next_track():
    print("TODO: next track")

def toggle_brightness():
    global BRIGHT
    BRIGHT = not BRIGHT
    set_state_value('mode', 'Light' if BRIGHT else 'Dark')

def set_volume(value):
    value = max(0, min(100, value))
    set_state_value('volume', value)

def handle_button_press(button):
    function_name = button_map.get(button)
    if function_name:
        func = globals().get(function_name)
        if func:
            func()
        else:
            print(f"\033[31mERROR: Function '{function_name}' not found.\033[0m")
    else:
        print(f"\033[31mERROR: Unknown button {button}\033[0m")

def initialize():
    global INITIALIZED, BRIGHT

    ws = get_state_server()
    if ws is None:
        return None

    try:
        values = {
            'volume': get_state_value('volume'),
            'bright': get_state_value('mode') == 'Light'
        }

        BRIGHT = values['bright']

        try:
            bus.write_byte(SLAVE_ADDR, values['volume'])
        except Exception as e:
            print(f"Error sending data to Arduino: {e}")

        print("Initialization done")
        INITIALIZED = True

    except Exception:
        global STATE_SERVER
        if STATE_SERVER:
            STATE_SERVER.close()
            STATE_SERVER = None
        return None

while True:
    if not INITIALIZED:
        if initialize() is None:
            time.sleep(1)

    try:
        # using 255 as empty/falsy value because 0 is reserved for volume
        command = bus.read_byte(SLAVE_ADDR)

        if 0 <= command <= 100:
            set_volume(command)
        elif command != 255:
            handle_button_press(command - 100)

    except Exception as e:
        print(f"Read error: {e}")

    time.sleep(0.03)

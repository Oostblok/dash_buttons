import smbus2
import time
import subprocess
import socketio
from evdev import UInput, ecodes as e

bus = smbus2.SMBus(1)
SLAVE_ADDR = 0x45

sio = socketio.Client()
sio.connect("http://localhost:4000")

VIEWS = ["projection", "dash", "media", "camera", "settings", "devices"]
view_index = 0

night_mode = True

volume_seeded = False

button_map = {
    1: lambda: toggle_mode(),
    2: lambda: press_key(e.KEY_B),
    3: lambda: press_key(e.KEY_P),
    4: lambda: press_key(e.KEY_N),
    5: lambda: toggle_brightness(),
}

KEY_CODES = [e.KEY_B, e.KEY_P, e.KEY_N]
ui = UInput({e.EV_KEY: KEY_CODES}, name="button-panel")
time.sleep(1)  # small wait for libinput

def press_key(code):
    ui.write(e.EV_KEY, code, 1)
    ui.syn()
    time.sleep(0.03)
    ui.write(e.EV_KEY, code, 0)
    ui.syn()


def toggle_mode():
    global view_index
    view_index = (view_index + 1) % len(VIEWS)
    try:
        sio.emit("telemetry:push", {"view": VIEWS[view_index]})
    except Exception as ex:
        print(f"telemetry push (view) failed: {ex}")


def toggle_brightness():
    global night_mode
    night_mode = not night_mode
    try:
        sio.emit("telemetry:push", {"nightMode": night_mode})
    except Exception as ex:
        print(f"telemetry push (nightMode) failed: {ex}")


def get_current_volume_pct():
    try:
        result = subprocess.run(
            ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
            capture_output=True, text=True, check=True
        )
        return round(float(result.stdout.strip().split()[-1]) * 100)
    except Exception as ex:
        print(f"could not read initial volume: {ex}")
        return 0  # Arduino script default


def set_volume(value):
    global volume_seeded

    if not volume_seeded:
        volume_seeded = True
        real_pct = get_current_volume_pct()
        try:
            bus.write_byte(SLAVE_ADDR, real_pct)
        except Exception as ex:
            print(f"could not seed initial volume to Arduino: {ex}")
        return

    try:
        sio.emit("telemetry:push", {"volume": value / 100.0})
    except Exception as ex:
        print(f"telemetry push (volume) failed: {ex}")

def handle_button_press(button):
    action = button_map.get(button)
    if action:
        action()
    else:
        print(f"\033[31mERROR: Unknown button {button}\033[0m")


while True:
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

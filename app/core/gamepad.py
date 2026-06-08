import ctypes
import logging
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger("DASH.Gamepad")

# --- Windows XInput structures ---
class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]

class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", ctypes.c_ulong),
        ("Gamepad", XINPUT_GAMEPAD),
    ]

class GamepadListener(QThread):
    state_changed = pyqtSignal(dict) # Dict of analog values & button states

    # Button Bitmasks
    BUTTON_A = 0x1000
    BUTTON_B = 0x2000
    BUTTON_X = 0x4000
    BUTTON_Y = 0x8000
    BUTTON_LB = 0x0100
    BUTTON_RB = 0x0200
    BUTTON_START = 0x0010
    BUTTON_BACK = 0x0020
    BUTTON_LEFT_THUMB = 0x0040
    BUTTON_RIGHT_THUMB = 0x0080
    
    # DPAD
    DPAD_UP = 0x0001
    DPAD_DOWN = 0x0002
    DPAD_LEFT = 0x0004
    DPAD_RIGHT = 0x0008

    def __init__(self):
        super().__init__()
        self.running = False
        self._xinput = None
        self._load_xinput()

    def _load_xinput(self):
        # Dynamically load the Windows XInput DLL
        for dll_name in ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"):
            try:
                self._xinput = ctypes.windll.LoadLibrary(dll_name)
                logger.info(f"Loaded XInput driver: {dll_name}")
                break
            except OSError:
                continue
        if not self._xinput:
            logger.warning("No XInput DLL found. Gamepad control will be disabled (requires Windows XInput).")

    def run(self):
        if not self._xinput:
            return
            
        self.running = True
        state = XINPUT_STATE()
        last_packet = -1

        logger.info("Gamepad listener loop started.")
        while self.running:
            # Query controller 0 (first connected gamepad)
            res = self._xinput.XInputGetState(0, ctypes.byref(state))
            
            if res == 0: # ERROR_SUCCESS
                if state.dwPacketNumber != last_packet:
                    last_packet = state.dwPacketNumber
                    gp = state.Gamepad
                    
                    # Normalize analog axes (-1.0 to 1.0)
                    # Deadzones: sThumbLX/Y are 16-bit signed shorts (-32768 to 32767)
                    def normalize_stick(val, deadzone=8000):
                        if abs(val) < deadzone:
                            return 0.0
                        # Rescale after deadzone
                        if val > 0:
                            return (val - deadzone) / (32767.0 - deadzone)
                        else:
                            return (val + deadzone) / (32768.0 - deadzone)

                    lx = normalize_stick(gp.sThumbLX)
                    ly = normalize_stick(gp.sThumbLY)
                    rx = normalize_stick(gp.sThumbRX)
                    ry = normalize_stick(gp.sThumbRY)
                    
                    # Normalize triggers (0 to 1.0)
                    lt = gp.bLeftTrigger / 255.0 if gp.bLeftTrigger > 30 else 0.0 # 30 is trigger threshold
                    rt = gp.bRightTrigger / 255.0 if gp.bRightTrigger > 30 else 0.0
                    
                    # Parse buttons
                    btn_bits = gp.wButtons
                    
                    payload = {
                        "connected": True,
                        "lx": lx,
                        "ly": ly,
                        "rx": rx,
                        "ry": ry,
                        "lt": lt,
                        "rt": rt,
                        "btn_a": bool(btn_bits & self.BUTTON_A),
                        "btn_b": bool(btn_bits & self.BUTTON_B),
                        "btn_x": bool(btn_bits & self.BUTTON_X),
                        "btn_y": bool(btn_bits & self.BUTTON_Y),
                        "btn_lb": bool(btn_bits & self.BUTTON_LB),
                        "btn_rb": bool(btn_bits & self.BUTTON_RB),
                        "btn_start": bool(btn_bits & self.BUTTON_START),
                        "btn_back": bool(btn_bits & self.BUTTON_BACK),
                        "dpad_up": bool(btn_bits & self.DPAD_UP),
                        "dpad_down": bool(btn_bits & self.DPAD_DOWN),
                        "dpad_left": bool(btn_bits & self.DPAD_LEFT),
                        "dpad_right": bool(btn_bits & self.DPAD_RIGHT),
                    }
                    self.state_changed.emit(payload)
            else:
                # Controller disconnected
                # Emit disconnected payload occasionally or wait
                self.msleep(100)
                
            self.msleep(30) # Poll at ~33Hz for latency free gamepad response

    def stop(self):
        self.running = False
        self.wait()

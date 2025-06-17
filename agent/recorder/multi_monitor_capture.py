import threading
import time
import json
import os
from PIL import ImageGrab
from pynput import keyboard, mouse

class MultiMonitorCapture:
    """
    Capture periodic full-screen screenshots and keyboard/mouse events.
    """

    def __init__(self, output_dir: str, fps: int = 2):
        self.output_dir = output_dir
        self.fps = fps
        self._running = False
        self.events = []
        os.makedirs(self.output_dir, exist_ok=True)

    def _capture_screens(self):
        while self._running:
            ts = time.time()
            img = ImageGrab.grab(all_screens=True)
            path = os.path.join(self.output_dir, f"screen_{ts:.3f}.png")
            img.save(path)
            self.events.append({
                "type": "screenshot",
                "timestamp": ts,
                "path": path
            })
            time.sleep(1 / self.fps)

    def _on_key(self, key):
        ts = time.time()
        try:
            k = key.char
        except AttributeError:
            k = str(key)
        self.events.append({
            "type": "key",
            "timestamp": ts,
            "key": k
        })

    def _on_click(self, x, y, button, pressed):
        ts = time.time()
        self.events.append({
            "type": "mouse",
            "timestamp": ts,
            "x": x, "y": y,
            "button": str(button),
            "pressed": pressed
        })

    def start(self):
        """Begin recording screenshots & events."""
        self._running = True
        # Screenshot thread
        self._screen_thread = threading.Thread(target=self._capture_screens, daemon=True)
        self._screen_thread.start()
        # Keyboard listener
        self._key_listener = keyboard.Listener(on_press=self._on_key)
        self._key_listener.start()
        # Mouse listener
        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._mouse_listener.start()
        print(f"[Agent] Recording to {self.output_dir} (fps={self.fps})")

    def stop(self):
        """Stop recording and flush events.json."""
        self._running = False
        self._screen_thread.join()
        self._key_listener.stop()
        self._mouse_listener.stop()
        # Dump events log
        with open(os.path.join(self.output_dir, "events.json"), "w") as f:
            json.dump(self.events, f, indent=2)
        print(f"[Agent] Stopped. Events written to {self.output_dir}/events.json")

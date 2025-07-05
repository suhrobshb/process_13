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
        """
        Args:
            output_dir: Where screenshots and events.json will be written.
            fps: Frames-per-second for full-screen capture.
            record_mouse_move: If True, capture mouse‐move events (throttled).
            window_poll_interval: Seconds between active-window-title checks.
        """
        self.output_dir = output_dir
        self.fps = fps
        # Extra, optional features
        self.record_mouse_move = True
        self.window_poll_interval = 0.5
        self._running = False
        self.events = []
        os.makedirs(self.output_dir, exist_ok=True)
        # Used for throttling mouse move events
        self._last_mouse_move_ts = 0.0

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

    # -------- mouse move listener (optional) -------- #
    def _on_move(self, x, y):
        if not self.record_mouse_move:
            return
        ts = time.time()
        # throttle to ~20 events per second
        if ts - self._last_mouse_move_ts < 0.05:
            return
        self._last_mouse_move_ts = ts
        self.events.append({
            "type": "mouse_move",
            "timestamp": ts,
            "x": x,
            "y": y
        })

    # -------- active window polling -------- #
    def _capture_active_window(self):
        try:
            import pygetwindow as gw
        except Exception:
            # Library not available; skip window capture
            return

        last_title = None
        while self._running:
            win = gw.getActiveWindow()
            title = win.title if win else ""
            if title and title != last_title:
                last_title = title
                self.events.append({
                    "type": "window_change",
                    "timestamp": time.time(),
                    "title": title
                })
            time.sleep(self.window_poll_interval)

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
        self._mouse_listener = mouse.Listener(on_click=self._on_click, on_move=self._on_move)
        self._mouse_listener.start()
        # Active window monitor
        self._window_thread = threading.Thread(target=self._capture_active_window, daemon=True)
        self._window_thread.start()
        print(f"[Agent] Recording to {self.output_dir} (fps={self.fps})")

    def stop(self):
        """Stop recording and flush events.json."""
        self._running = False
        self._screen_thread.join()
        self._key_listener.stop()
        self._mouse_listener.stop()
        if hasattr(self, "_window_thread"):
            self._window_thread.join()
        # Dump events log
        with open(os.path.join(self.output_dir, "events.json"), "w") as f:
            json.dump(self.events, f, indent=2)
        print(f"[Agent] Stopped. Events written to {self.output_dir}/events.json")

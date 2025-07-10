import pytesseract
from PIL import Image
import pygetwindow as gw
from typing import Dict, Any

class ContextAnalyzer:
    """
    Extract surrounding OCR text & active window title as features.
    """

    def extract_features(self, screenshot_path: str, event: Dict[str, Any]) -> Dict[str, Any]:
        img = Image.open(screenshot_path).convert("L")
        text = pytesseract.image_to_string(img)
        x, y = event.get("x", 0), event.get("y", 0)
        # pick the window under the cursor
        win = None
        for w in gw.getAllWindows():
            if w.left < x < w.right and w.top < y < w.bottom:
                win = w
                break
        return {
            "ocr_text": text,
            "window_title": win.title if win else None,
            "event": event
        }

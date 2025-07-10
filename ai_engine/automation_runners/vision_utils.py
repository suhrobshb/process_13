"""
Computer Vision Utilities for Resilient UI Automation
=====================================================

This module provides a comprehensive set of computer vision tools to make UI
automation workflows more robust and resilient to changes in the user interface.
Instead of relying on fixed screen coordinates, these utilities allow the automation
engine to find and interact with UI elements based on their appearance (image
templates) or text content (OCR).

Key Features:
-   **Multi-Scale Template Matching**: Finds UI elements (buttons, icons, fields)
    on the screen even if they are slightly resized, making automation less
    brittle.
-   **OCR for Data Extraction**: Extracts text from any part of the screen or
    from image files, enabling interaction with elements that cannot be
    identified by other means and extracting data from images or scanned documents.
-   **Resilient Waiting Mechanisms**: Includes functions to wait for an element
    to appear on the screen before proceeding, handling delays in UI rendering.
-   **Confidence Scoring**: All matching operations return a confidence score,
    allowing workflows to make decisions based on the certainty of a match.
-   **Visual Verification**: Enables steps in a workflow that can "see" the screen
    and confirm that a specific visual state has been reached (e.g., a success
    popup has appeared).

This module is a foundational component for the enhanced Desktop and Browser
runners, moving them from simple coordinate-based replay to intelligent,
vision-powered interaction.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Tuple, List, Union

import cv2
import numpy as np
import pyautogui
import pytesseract

# Configure logging
logger = logging.getLogger(__name__)

# --- Custom Exception for Vision Operations ---

class ElementNotFoundError(Exception):
    """Custom exception raised when a visual element cannot be found on the screen."""
    pass

# --- Core Vision Functions ---

def take_screenshot() -> np.ndarray:
    """
    Takes a screenshot of the entire screen and returns it as an OpenCV image.

    Returns:
        An OpenCV image (as a NumPy array) in BGR format.
    """
    screenshot = pyautogui.screenshot()
    # Convert PIL Image to NumPy array and then from RGB to BGR for OpenCV
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)


def find_on_screen(
    template_path: Union[str, Path],
    screenshot: Optional[np.ndarray] = None,
    threshold: float = 0.8,
    scales: List[float] = [1.0, 0.9, 1.1]
) -> Tuple[int, int, float]:
    """
    Finds the best match for a template image on the screen using multi-scale
    template matching.

    Args:
        template_path: Path to the image file of the element to find.
        screenshot: An optional pre-captured screenshot to search within. If None,
                    a new screenshot will be taken.
        threshold: The minimum confidence score (0.0 to 1.0) required for a match.
        scales: A list of scales to try for matching, to handle size variations.

    Returns:
        A tuple containing the (x, y) coordinates of the center of the best match
        and the confidence score.

    Raises:
        ElementNotFoundError: If no match with a score above the threshold is found.
        FileNotFoundError: If the template image file does not exist.
    """
    template_path = Path(template_path)
    if not template_path.is_file():
        raise FileNotFoundError(f"Template image not found at: {template_path}")

    template = cv2.imread(str(template_path))
    if template is None:
        raise IOError(f"Could not read template image: {template_path}")
    
    # Use grayscale for more robust matching
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    
    if screenshot is None:
        screenshot = take_screenshot()
    screen_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    best_match = {"max_val": -1, "max_loc": None, "scale": 1.0}

    for scale in scales:
        # Resize template and store dimensions
        w, h = template_gray.shape[::-1]
        resized_w, resized_h = int(w * scale), int(h * scale)
        
        # Avoid resizing to zero or making it larger than the screen
        if resized_w == 0 or resized_h == 0 or resized_w > screen_gray.shape[1] or resized_h > screen_gray.shape[0]:
            continue

        resized_template = cv2.resize(template_gray, (resized_w, resized_h), interpolation=cv2.INTER_AREA)

        # Perform template matching
        result = cv2.matchTemplate(screen_gray, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_match["max_val"]:
            best_match.update({
                "max_val": max_val,
                "max_loc": max_loc,
                "scale": scale,
                "dimensions": (resized_w, resized_h)
            })

    logger.debug(f"Best match found for '{template_path.name}' with score {best_match['max_val']:.2f} at scale {best_match['scale']:.1f}")

    if best_match["max_val"] >= threshold:
        top_left = best_match["max_loc"]
        w, h = best_match["dimensions"]
        center_x = top_left[0] + w // 2
        center_y = top_left[1] + h // 2
        return (center_x, center_y, best_match["max_val"])
    else:
        raise ElementNotFoundError(
            f"Element from template '{template_path.name}' not found on screen with a confidence of >= {threshold}."
        )

# --------------------------------------------------------------------------- #
# Utility: wait_for_element
# --------------------------------------------------------------------------- #

def wait_for_element(
    template_path: Union[str, Path],
    timeout: int = 10,
    threshold: float = 0.8
) -> Tuple[int, int, float]:
    """
    Waits for a specified visual element to appear on the screen.

    This function repeatedly searches for the element until it is found or the
    timeout is reached, making scripts resilient to UI loading delays.

    Args:
        template_path: Path to the image file of the element to wait for.
        timeout: Maximum time to wait in seconds.
        threshold: The confidence threshold to accept a match.

    Returns:
        The (x, y, confidence) of the found element.

    Raises:
        ElementNotFoundError: If the element does not appear within the timeout.
    """
    logger.info(f"Waiting for element '{Path(template_path).name}' to appear (timeout: {timeout}s)...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Take a fresh screenshot on each attempt
            coords = find_on_screen(template_path, screenshot=None, threshold=threshold)
            logger.info(f"Element '{Path(template_path).name}' found.")
            return coords
        except ElementNotFoundError:
            time.sleep(0.5)  # Wait half a second before retrying
    
    raise ElementNotFoundError(
        f"Timed out after {timeout} seconds waiting for element '{Path(template_path).name}'."
    )


def ocr_from_region(
    left: int,
    top: int,
    width: int,
    height: int,
    screenshot: Optional[np.ndarray] = None
) -> str:
    """
    Performs OCR on a specific rectangular region of the screen.

    Args:
        left: The x-coordinate of the top-left corner of the region.
        top: The y-coordinate of the top-left corner of the region.
        width: The width of the region.
        height: The height of the region.
        screenshot: An optional pre-captured screenshot. If None, a new one is taken.

    Returns:
        The extracted text as a string.
    """
    if screenshot is None:
        screenshot = take_screenshot()

    # Crop the image to the specified region
    region = screenshot[top:top+height, left:left+width]
    
    if region.size == 0:
        logger.warning("OCR region is empty. Check coordinates.")
        return ""

    try:
        # Use pytesseract to extract text from the cropped image
        text = pytesseract.image_to_string(region)
        logger.info(f"OCR extracted text from region ({left},{top},{width},{height}): '{text.strip()}'")
        return text.strip()
    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract is not installed or not in your PATH. Please install it to use OCR features.")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during OCR: {e}", exc_info=True)
        return ""


# --- Example Usage Block ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Create a dummy directory for test assets
    test_assets_dir = Path("./test_vision_assets")
    test_assets_dir.mkdir(exist_ok=True)

    # 1. Create a dummy "screenshot" and a "template" to find within it
    dummy_screen = np.zeros((600, 800, 3), dtype=np.uint8)
    dummy_screen.fill(200) # Light gray background
    
    # Draw a "button" on the dummy screen
    button_top_left = (300, 250)
    button_bottom_right = (400, 280)
    cv2.rectangle(dummy_screen, button_top_left, button_bottom_right, (0, 150, 0), -1) # Green button
    cv2.putText(dummy_screen, "Submit", (320, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Save the dummy screenshot
    screenshot_path = test_assets_dir / "dummy_screenshot.png"
    cv2.imwrite(str(screenshot_path), dummy_screen)

    # Crop the button to create a template image
    template_image = dummy_screen[
        button_top_left[1]:button_bottom_right[1],
        button_top_left[0]:button_bottom_right[0]
    ]
    template_path = test_assets_dir / "submit_button_template.png"
    cv2.imwrite(str(template_path), template_image)
    
    print("--- Vision Utilities Demo ---")
    print(f"Created dummy assets in '{test_assets_dir.resolve()}'")

    # --- Demo 1: Find an element on the screen ---
    print("\n1. Testing 'find_on_screen'...")
    try:
        loaded_screenshot = cv2.imread(str(screenshot_path))
        x, y, conf = find_on_screen(template_path, screenshot=loaded_screenshot, threshold=0.9)
        print(f"   ✅ SUCCESS: Found element at ({x}, {y}) with confidence {conf:.2f}")
    except (ElementNotFoundError, FileNotFoundError) as e:
        print(f"   ❌ FAILURE: {e}")

    # --- Demo 2: Wait for an element ---
    print("\n2. Testing 'wait_for_element' (will succeed immediately)...")
    # In a real scenario, the element might not be present at first.
    # Here, we mock it by using the pre-existing screenshot.
    # We need to mock pyautogui.screenshot to return our dummy image for the test
    original_screenshot = pyautogui.screenshot
    pyautogui.screenshot = lambda: cv2.cvtColor(dummy_screen, cv2.COLOR_BGR2RGB)
    
    try:
        x, y, conf = wait_for_element(template_path, timeout=2)
        print(f"   ✅ SUCCESS: Waited and found element at ({x}, {y})")
    except ElementNotFoundError as e:
        print(f"   ❌ FAILURE: {e}")
    finally:
        pyautogui.screenshot = original_screenshot # Restore original function
        
    # --- Demo 3: OCR from a specific region ---
    print("\n3. Testing 'ocr_from_region'...")
    try:
        # The region where we drew the text "Submit"
        text = ocr_from_region(300, 250, 100, 30, screenshot=dummy_screen)
        if "Submit" in text:
            print(f"   ✅ SUCCESS: OCR correctly extracted text: '{text}'")
        else:
            print(f"   ⚠️  WARNING: OCR extracted '{text}', which did not contain 'Submit'. This can happen if Tesseract is not configured correctly.")
    except Exception as e:
        print(f"   ❌ FAILURE: OCR failed. Is Tesseract installed and in your PATH? Error: {e}")
        
    # Clean up dummy files
    import shutil
    shutil.rmtree(test_assets_dir)
    print(f"\nCleaned up dummy assets directory.")

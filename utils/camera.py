"""
Camera utility functions.
"""

import cv2


def find_camera(max_tries=5):
    """
    Auto-detect available camera.
    
    Args:
        max_tries: Maximum number of camera indices to try
        
    Returns:
        cv2.VideoCapture object or None if no camera found
    """
    for i in range(max_tries):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            return cap
        cap.release()
    return None
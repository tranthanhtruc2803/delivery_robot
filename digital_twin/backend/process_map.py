import numpy as np
import cv2
import base64
from ros_web_bridge import get_map

def get_processed_map_image():
    """
    Pulls the latest ROS OccupancyGrid, smoothens the raw pixels,
    and converts it to a Base64 PNG styled to match the UI.
    """
    map_data = get_map()
    
    if not map_data or 'data' not in map_data or len(map_data['data']) == 0:
        return None
        
    width = map_data['width']
    height = map_data['height']
    data = map_data['data']
    
    grid = np.array(data, dtype=np.int8)
    
    if grid.size != (width * height):
        return None
        
    grid_2d = grid.reshape((height, width))
    
    # Create an empty BGRA image (Blue, Green, Red, Alpha)
    img = np.zeros((height, width, 4), dtype=np.uint8)
    
    # --- 1. FREE SPACE ---
    # Keep the free space transparent/light purple (Freeze Purple: #e5eaf5)
    # OpenCV uses BGRA format, so #e5eaf5 (229, 234, 245) becomes [245, 234, 229, 200]
    img[grid_2d == 0] = [245, 234, 229, 200]
    
    # --- 2. SMOOTH THE WALLS ---
    # Extract JUST the walls into a binary mask (0 or 255)
    wall_mask = np.zeros((height, width), dtype=np.uint8)
    wall_mask[grid_2d == 100] = 255
    
    # Step A: "Closing" - Reduced from (5,5) to (3,3) so it only connects very close dots
    close_kernel = np.ones((3, 3), np.uint8)
    connected_walls = cv2.morphologyEx(wall_mask, cv2.MORPH_CLOSE, close_kernel)
    
    # Step B: REMOVED DILATION. We don't want to artificially thicken the walls anymore.
    
    # Step C: "Gaussian Blur" - Keep a slight blur to anti-alias the edges
    smooth_walls = cv2.GaussianBlur(connected_walls, (3, 3), 0)
    
    # Apply the vibrant purple color (Purple Pain: #8458B3)
    # BGRA for (132, 88, 179) is [179, 88, 132, 255]
    img[smooth_walls > 100] = [179, 88, 132, 255]
    
    # --- 3. FINALIZE ---
    # ROS map origin is bottom-left, flip to match image top-left coordinates
    img = cv2.flip(img, 0)
    
    # Compress and encode
    success, buffer = cv2.imencode('.png', img)
    if not success:
        return None
        
    base64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/png;base64,{base64_str}"

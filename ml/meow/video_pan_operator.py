import os
import sys

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOLOV7_PATH = os.path.join(ROOT_PATH, "yolov7")
sys.path.insert(0, YOLOV7_PATH)

import cv2
import numpy as np
import torch
from torchvision import transforms
from utils.datasets import letterbox
from utils.general import non_max_suppression_kpt
from utils.plots import output_to_keypoint
from tqdm import tqdm

MODELS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')


def get_player_positions(frame, model, device):
    """Detect players using multiple scales for better far-field detection"""
    scales = [1.0, 2.0, 4.0]  # Process image at different scales
    all_positions = []
    
    for scale in scales:
        # Calculate new dimensions
        width = int(frame.shape[1] * scale)
        height = int(frame.shape[0] * scale)
        
        # Resize image for this scale
        if scale != 1.0:
            scaled_frame = cv2.resize(frame, (width, height))
        else:
            scaled_frame = frame
            
        # Process with YOLOv7
        image = cv2.cvtColor(scaled_frame, cv2.COLOR_BGR2RGB)
        image = letterbox(image, 640, stride=32, auto=True)[0]
        image = transforms.ToTensor()(image)
        image = torch.tensor(np.array([image.numpy()]))
        image = image.to(device).half()
        
        with torch.no_grad():
            output, _ = model(image)
        
        output = non_max_suppression_kpt(output, 0.25, 0.65, nc=model.yaml['nc'])
        output = output_to_keypoint(output)
        
        # Convert detections back to original scale
        for idx in range(output.shape[0]):
            if output[idx][1] == 0 and output[idx][6] >= 0.5:  # Lowered confidence threshold
                x_center = output[idx, 2] * frame.shape[1] / 640
                if scale != 1.0:
                    x_center = x_center / scale
                all_positions.append(x_center)
    
    return all_positions

def track_players_with_flow(prev_frame, curr_frame, prev_positions):
    """Track player positions using optical flow"""
    if len(prev_positions) == 0:
        return []
        
    # Convert positions to points format for optical flow
    prev_points = np.array([[x, prev_frame.shape[0]//2] for x in prev_positions], dtype=np.float32)
    prev_points = prev_points.reshape(-1, 1, 2)  # Reshape for optical flow
    
    # Calculate optical flow
    curr_points, status, _ = cv2.calcOpticalFlowPyrLK(
        prev_frame, curr_frame,
        prev_points, None,
        winSize=(15,15),
        maxLevel=2,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
    )
    
    # Filter out points where flow failed
    status = status.reshape(-1)  # Flatten status array
    good_points = curr_points[status == 1]
    
    # Return x-coordinates of tracked points
    if len(good_points) > 0:
        return [point[0][0] for point in good_points]  # Extract x coordinates
    return []


def pan_video(video_path, output_path, debug_output_path=None):
    """
    Pan video based on player positions on the field. Calculate average position of players 
    and pan the video smoothly based on the average positions over time.
    """
    # Load YOLOv7 model
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    weights = torch.load(os.path.join(MODELS_PATH, 'yolov7.pt'), map_location=device)
    model = weights['model']
    model = model.half().to(device)
    _ = model.eval()
    
    # Fix for newer PyTorch versions
    import torch.nn as nn
    for m in model.modules():
        if isinstance(m, nn.Upsample):
            m.recompute_scale_factor = None  # type: ignore

    # Video processing parameters
    WINDOW_WIDTH = 1920
    WINDOW_HEIGHT = 1080
    LOOK_AHEAD_FRAMES = [20, 40, 90]  # Look ahead at multiple future points
    TRANSITION_FRAMES = 30  # Increased for smoother transitions
    SMOOTHING_WINDOW = 5  # Additional smoothing window
    
    # Open video and get properties
    cap = cv2.VideoCapture(video_path)
    panorama_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    panorama_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"\nProcessing video with {total_frames} frames at {fps} FPS")
    print(f"Input size: {panorama_width}x{panorama_height}")
    print(f"Output size: {min(WINDOW_WIDTH, panorama_width)}x{min(WINDOW_HEIGHT, panorama_height)}")
    print(f"Using device: {device}\n")
    
    # Setup output videos
    output_width = min(WINDOW_WIDTH, panorama_width)
    output_height = min(WINDOW_HEIGHT, panorama_height)
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, 
                         (output_width, output_height))
    
    if debug_output_path:
        debug_out = cv2.VideoWriter(debug_output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps,
                                  (panorama_width, panorama_height))
    
    current_x = (panorama_width - output_width) // 2  # Start from center
    frame_idx = 0
    frames_buffer = []
    recent_positions = []  # Store recent positions for smoothing
    movement_per_frame = 0
    frames_since_last_plan = 0
    
        # Create progress bar
    pbar = tqdm(total=total_frames, desc="Processing frames", unit="frame")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Store frame in buffer
        frames_buffer.append(frame)
        
        # Keep buffer size limited
        if len(frames_buffer) > max(LOOK_AHEAD_FRAMES):
            frames_buffer.pop(0)
            
        # Plan new movement every TRANSITION_FRAMES frames or at start
        if frame_idx % TRANSITION_FRAMES == 0:
            target_positions = []
            
            # Look ahead at multiple future points
            for look_ahead in LOOK_AHEAD_FRAMES:
                if len(frames_buffer) >= look_ahead:
                    future_frame = frames_buffer[look_ahead - 1]
                    player_positions = get_player_positions(future_frame, model, device)
                    
                    if player_positions:
                        # Calculate target x position (center of players)
                        target_x = int(np.mean(player_positions)) - (output_width // 2)
                        target_x = max(0, min(target_x, panorama_width - output_width))
                        target_positions.append(target_x)
            
            if target_positions:
                # Use gentler weighting for future positions
                weights = np.array([1.5, 1.2, 1.0])[:len(target_positions)]
                weights = weights / weights.sum()
                weighted_target = int(np.sum(np.array(target_positions) * weights))
                
                # Apply additional smoothing using recent positions
                recent_positions.append(weighted_target)
                if len(recent_positions) > SMOOTHING_WINDOW:
                    recent_positions.pop(0)
                smoothed_target = int(np.mean(recent_positions))
                
                # Calculate required movement per frame for smooth transition
                total_movement = smoothed_target - current_x
                movement_per_frame = total_movement / TRANSITION_FRAMES
            
            frames_since_last_plan = 0
        
        # Apply movement for this frame with easing
        if frames_since_last_plan < TRANSITION_FRAMES:
            # Apply easing function (ease-in-out)
            progress = frames_since_last_plan / TRANSITION_FRAMES
            ease = 0.5 * (1 - np.cos(progress * np.pi))
            current_x += movement_per_frame * ease
            current_x = max(0, min(current_x, panorama_width - output_width))
            frames_since_last_plan += 1
        
        # Create debug frame with detections if requested
        if debug_output_path:
            debug_frame = frame.copy()
            player_positions = get_player_positions(frame, model, device)
            
            # Draw detections
            for pos in player_positions:
                x = int(pos)
                y = panorama_height // 2  # Approximate vertical position
                cv2.circle(debug_frame, (x, y), 20, (0, 255, 0), 2)
                cv2.circle(debug_frame, (x, y), 2, (0, 0, 255), -1)
            
            # Draw current window
            cv2.rectangle(debug_frame, 
                        (int(current_x), 0),
                        (int(current_x + output_width), panorama_height),
                        (255, 0, 0), 2)
            
            debug_out.write(debug_frame)
        
        # Crop and write frame
        current_x = int(current_x)  # Ensure integer pixel values
        cropped_frame = frame[:, current_x:current_x + output_width]
        if cropped_frame.shape[0] != output_height:
            cropped_frame = cv2.resize(cropped_frame, (output_width, output_height))
            
        out.write(cropped_frame)
        frame_idx += 1
        pbar.update(1)
        
    pbar.close()
    cap.release()
    out.release()
    if debug_output_path:
        debug_out.release()
    
    print(f"\nProcessing complete!")
    print(f"Output saved to: {output_path}")
    if debug_output_path:
        print(f"Debug output saved to: {debug_output_path}")

if __name__ == "__main__":
    DATA_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    print(DATA_FOLDER)
    pan_video(os.path.join(DATA_FOLDER, 'stitching_result_example.mp4'), os.path.join(DATA_FOLDER, 'pan_video.mp4'), os.path.join(DATA_FOLDER, 'debug_pan_video.mp4'))

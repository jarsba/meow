import os
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip
import ffmpeg
from typing import Optional, List, Literal
from .logger import setup_logger
import cv2
import numpy as np
from enum import Enum

logger = setup_logger(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
FRONTEND_ASSETS = os.path.join(ROOT_DIR, 'frontend/assets')
ASSETS_FOLDER = os.path.join(ROOT_DIR, 'assets')
FONT_PATH = os.path.join(FRONTEND_ASSETS, 'fonts/Inconsolata-Medium.ttf')

# Define valid position options
PositionPreset = Literal["top-left", "top-center", "top-right", "bottom-left", "bottom-center", "bottom-right"]

def get_position_coordinates(position: PositionPreset, margin: int, width: int, height: int, element_width: int, element_height: int) -> tuple[str, str]:
    """Get x,y coordinates for an element based on position preset.
    
    Args:
        position: Position preset
        margin: Margin from edges
        width: Video width
        height: Video height
        element_width: Width of element to position
        element_height: Height of element to position
        
    Returns:
        tuple[str, str]: x and y coordinates as FFMPEG expressions
    """
    positions = {
        "top-left": (f"{margin}", f"{margin}"),
        "top-center": (f"(W-{element_width})/2", f"{margin}"),
        "top-right": (f"W-{element_width}-{margin}", f"{margin}"),
        "bottom-left": (f"{margin}", f"H-{element_height}-{margin}"),
        "bottom-center": (f"(W-{element_width})/2", f"H-{element_height}-{margin}"),
        "bottom-right": (f"W-{element_width}-{margin}", f"H-{element_height}-{margin}")
    }
    return positions[position]

def get_package_position(position: PositionPreset, margin: int, width: int, height: int, 
                        logo_size: int, text_width: int) -> tuple[str, str]:
    """Get base x,y coordinates for the team vs team package.
    
    Args:
        position: Position preset
        margin: Margin from edges
        width: Video width
        height: Video height
        logo_size: Size of team logos
        text_width: Width of "vs" text
        
    Returns:
        tuple[str, str]: Base x and y coordinates as FFMPEG expressions
    """
    # Calculate total package width: logo + margin + text + margin + logo
    package_width = logo_size + 20 + text_width + 20 + logo_size
    package_height = logo_size

    positions = {
        "top-left": (f"{margin}", f"{margin}"),
        "top-center": (f"(W-{package_width})/2", f"{margin}"),
        "top-right": (f"W-{package_width}-{margin}", f"{margin}"),
        "bottom-left": (f"{margin}", f"H-{package_height}-{margin}"),
        "bottom-center": (f"(W-{package_width})/2", f"H-{package_height}-{margin}"),
        "bottom-right": (f"W-{package_width}-{margin}", f"H-{package_height}-{margin}")
    }
    return positions[position]

def burn_logo_ffmpeg(video_path: str, gif_path: str, output_path: str, text: Optional[str] = None):
    """Overlay GIF and optional text on top of a video using FFMPEG (faster version)."""
    logger.info("Burning logo onto video using FFMPEG...")
    
    # Input video stream with thread queue size
    main = ffmpeg.input(video_path, **{'thread_queue_size': '1024'})
    
    # Get video dimensions and duration
    probe = ffmpeg.probe(video_path)
    video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    width = int(video_info['width'])
    height = int(video_info['height'])
    duration = float(probe['format']['duration'])
    
    logger.debug(f"Video dimensions: {width}x{height}, duration: {duration}s")
    
    # Input logo stream with loop and thread queue size
    logo = (ffmpeg
            .input(gif_path, stream_loop=-1, **{'thread_queue_size': '1024'})  # -1 means infinite loop
            .filter('scale', -1, 250)  # Scale logo to 250px height
            )
    
    # Position logo at bottom right with margin
    margin = 16
    overlay_x = f'W-w-{margin}'
    overlay_y = f'H-h-{margin}'
    
    # Create overlay with shortest=1 to prevent infinite processing
    video = ffmpeg.overlay(main, logo, x=overlay_x, y=overlay_y, shortest=1)
    
    if text:
        video = video.filter('drawtext',
            text=text,
            fontfile=FONT_PATH,
            fontsize=36,
            fontcolor='white',
            x=f'(W-tw)/2',
            y=f'H-th-{margin}',
            shadowcolor='black',
            shadowx=2,
            shadowy=2
        )

    # Try NVIDIA GPU encoding
    try:
        logger.info("Using NVIDIA GPU encoding...")
        stream = (ffmpeg
                 .output(video,
                        main.audio,
                        output_path,
                        acodec='copy',          # Copy audio codec
                        vcodec='h264_nvenc',    # NVIDIA GPU encoding
                        **{
                            'b:v': '5M',        # Video bitrate (fixed ambiguity)
                            'preset': 'p1',     # Fastest NVIDIA preset
                            't': duration,      # Force output duration
                        })
                 .global_args('-nostdin', '-y'))
        
        cmd = ' '.join(stream.get_args())
        logger.debug(f"FFMPEG command: {cmd}")
        
        stream.run()

    except ffmpeg.Error as e:
        logger.info("NVIDIA encoding failed, falling back to CPU encoding...")
        error_message = e.stderr.decode() if hasattr(e, 'stderr') else str(e)
        logger.debug(f"NVIDIA error: {error_message}")
        
        stream = (ffmpeg
                 .output(video,
                        main.audio,
                        output_path,
                        acodec='copy',           # Copy audio codec
                        vcodec='libx264',        # x264 CPU encoding
                        preset='ultrafast',      # Fastest encoding preset
                        tune='fastdecode',       # Optimize for decoding speed
                        crf=27,                  # Quality (23-28 is good range)
                        threads='auto',          # Use all CPU threads
                        t=duration               # Force output duration
                        )
                 .global_args('-nostdin', '-y'))
        
        stream.run()

    logger.info("Logo burning complete")


def burn_logo(video_path, gif_path, output_path, text: Optional[str] = None):
    """Overlay GIF and optional text on top of a video.

    Args:
        video_path (str): Path to the video file.
        gif_path (str): Path to the GIF file.
        output_path (str): Path to the output file.
        text (str): Optional text to display under logo.
    """
    with VideoFileClip(video_path) as clip:
        clips = [clip]
        
        # Create and position logo first to get its dimensions
        watermark = VideoFileClip(gif_path, has_mask=True) \
            .loop() \
            .set_duration(clip.duration) \
            .resize(height=250)
        
        # Calculate logo position (right-aligned with margin)
        logo_right_margin = 16
        logo_x = clip.w - watermark.w - logo_right_margin
        
        # Create text clip if text is provided
        if text:
            text_clip = TextClip(text, 
                              font=FONT_PATH,
                              fontsize=36,
                              color='white',
                              stroke_color='white',
                              stroke_width=2) \
                .set_duration(clip.duration)
            
            # Center text with logo
            text_x = logo_x + (watermark.w - text_clip.w) / 2
            text_bottom_margin = 16
            text_y = clip.h - text_clip.h - text_bottom_margin
            
            text_clip = text_clip.set_position((text_x, text_y))
            clips.append(text_clip)
            
            # Position logo above text
            margin_bottom = text_clip.h + 8  # Text height + 8px spacing
        else:
            margin_bottom = 8
            
        # Set final logo position
        watermark = watermark \
            .margin(bottom=margin_bottom, opacity=0) \
            .set_position((logo_x, "bottom"))
        clips.append(watermark)

        # Combine all clips
        watermark_video = CompositeVideoClip(clips)
        watermark_video.write_videofile(output_path)


def create_circular_image(image_path: str, output_path: str, size: int = 100, make_circular: bool = True):
    """Create a resized version of the input image, optionally with circular mask.
    
    Args:
        image_path: Path to input image
        output_path: Path to save the processed image
        size: Size of the output image (both width and height)
        make_circular: Whether to apply circular mask
    """
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
        
    # Convert BGR to BGRA
    img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    img = cv2.resize(img, (size, size))
    
    if make_circular:
        # Create and apply circular mask
        mask = np.zeros((size, size), dtype=np.uint8)
        center = (size // 2, size // 2)
        radius = size // 2
        cv2.circle(mask, center, radius, 255, -1)
        img[:, :, 3] = mask
    
    # Save with transparency (must use PNG format)
    output_path = output_path.replace('.jpg', '.png')  # Force PNG extension
    cv2.imwrite(output_path, img)


def burn_team_images(video_path: str, output_path: str, team_image_paths: List[str], 
                    circular_logos: bool = False,
                    position: PositionPreset = "top-left"):
    """Burn team images onto a video.
    
    Args:
        video_path: Path to the video file
        output_path: Path to the output file
        team_image_paths: List of paths to the team image files (expects exactly 2 images)
        circular_logos: Whether to make the logos circular (default: False)
        position: Position preset for the entire team vs team package (default: "top-left")
    """
    if len(team_image_paths) != 2:
        raise ValueError("Exactly 2 team image paths are required")

    logger.info("Burning team images onto video using FFMPEG...")
    
    # Create processed versions of team logos
    temp_dir = os.path.dirname(output_path)
    processed_team1_path = os.path.join(temp_dir, 'team1_processed.png')
    processed_team2_path = os.path.join(temp_dir, 'team2_processed.png')
    
    LOGO_SIZE = 100
    TEXT_WIDTH = 40  # Estimated width of "vs" text
    TEXT_HEIGHT = 36
    INNER_MARGIN = 20  # Space between logos and text
    
    create_circular_image(team_image_paths[0], processed_team1_path, size=LOGO_SIZE, make_circular=circular_logos)
    create_circular_image(team_image_paths[1], processed_team2_path, size=LOGO_SIZE, make_circular=circular_logos)
    
    # Input video stream
    main = ffmpeg.input(video_path, **{'thread_queue_size': '1024'})
    
    # Get video info
    probe = ffmpeg.probe(video_path)
    video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    width = int(video_info['width'])
    height = int(video_info['height'])
    duration = float(probe['format']['duration'])
    
    # Add team logos
    margin = 16
    team1 = ffmpeg.input(processed_team1_path)
    team2 = ffmpeg.input(processed_team2_path)
    
    # Get base position for the package
    base_x, base_y = get_package_position(position, margin, width, height, LOGO_SIZE, TEXT_WIDTH)
    
    # Calculate relative positions
    logo1_x = f"{base_x}"  # First logo starts at base_x
    logo2_x = f"{base_x}+{LOGO_SIZE}+{INNER_MARGIN}+{TEXT_WIDTH}+{INNER_MARGIN}"  # Second logo after text
    text_x = f"{base_x}+{LOGO_SIZE}+{INNER_MARGIN}"  # Text between logos
    
    # Vertical alignment (all elements use same y position)
    logo_y = base_y
    text_y = f"{base_y}+({LOGO_SIZE})/2"  # Center text vertically relative to logos
    
    # Add first team logo
    video = ffmpeg.overlay(main, team1, x=logo1_x, y=logo_y)
    
    # Add second team logo
    video = ffmpeg.overlay(video, team2, x=logo2_x, y=logo_y)
    
    # Add "vs" text
    video = video.filter('drawtext',
        text='vs',
        fontfile=FONT_PATH,
        fontsize=TEXT_HEIGHT,
        fontcolor='white',
        x=text_x,
        y=text_y,
        shadowcolor='black',
        shadowx=2,
        shadowy=2
    )

    try:
        # Try NVIDIA GPU encoding
        logger.info("Using NVIDIA GPU encoding...")
        stream = (ffmpeg
                 .output(video,
                        main.audio,
                        output_path,
                        acodec='copy',
                        vcodec='h264_nvenc',
                        **{
                            'b:v': '5M',
                            'preset': 'p1',
                            't': duration,
                        })
                 .global_args('-nostdin', '-y'))
        
        stream.run()

    except ffmpeg.Error as e:
        # Fall back to CPU encoding
        logger.info("NVIDIA encoding failed, falling back to CPU encoding...")
        error_message = e.stderr.decode() if hasattr(e, 'stderr') else str(e)
        logger.debug(f"NVIDIA error: {error_message}")
        
        stream = (ffmpeg
                 .output(video,
                        main.audio,
                        output_path,
                        acodec='copy',
                        vcodec='libx264',
                        preset='ultrafast',
                        tune='fastdecode',
                        crf=27,
                        threads='auto',
                        t=duration
                        )
                 .global_args('-nostdin', '-y'))
        
        stream.run()



if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_FOLDER = os.path.join(os.path.dirname(CURRENT_DIR), 'data')
    LOGO_FOLDER = os.path.join(os.path.dirname(os.path.dirname(CURRENT_DIR)), 'frontend/assets')
    MEOW_TEMP_FOLDER = "/media/jakki/Qumran/Videos/meow_tmp"
    
    # Test the new FFMPEG version
    #burn_logo_ffmpeg(
    #    os.path.join(MEOW_TEMP_FOLDER, 'ktw5vlwj.mp4'), 
    #    os.path.join(LOGO_FOLDER, 'blinking_logo.gif'), 
    #    os.path.join(MEOW_TEMP_FOLDER, 'ktw5vlwj_with_logo_ffmpeg.mp4'),
    #    "meow"
    #)

    burn_team_images(
        os.path.join(ROOT_DIR, 'meow_sample_sample.mp4'),
        os.path.join(ROOT_DIR, 'meow_sample_sample_logos.mp4'),
        [os.path.join(ASSETS_FOLDER, 'keparoi_logo.jpg'), os.path.join(ASSETS_FOLDER, 'team_logo.jpg')],
        circular_logos=False,
        position="top-left"
    )
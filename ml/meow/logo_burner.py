import os
from moviepy.editor import VideoFileClip, CompositeVideoClip

def burn_logo(video_path, gif_path, output_path):
    """Overlay GIF on top of a video.

    Args:
        video_path (str): Path to the video file.
        gif_path (str): Path to the GIF file.
        output_path (str): Path to the output file.
    """
    with VideoFileClip(video_path) as clip:
        watermark = VideoFileClip(gif_path, has_mask=True) \
            .loop() \
            .set_duration(clip.duration) \
            .resize(height=150) \
            .margin(right=8, bottom=8, opacity=0) \
            .set_pos(("right", "bottom"))

        watermark_video = CompositeVideoClip([clip, watermark])
        watermark_video.write_videofile(output_path)

    

if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_FOLDER = os.path.join(os.path.dirname(CURRENT_DIR), 'data')
    LOGO_FOLDER = os.path.join(os.path.dirname(os.path.dirname(CURRENT_DIR)), 'frontend/assets')
    burn_logo(os.path.join(DATA_FOLDER, 'example_videos_left', 'keparoicam_left_part1.mp4'), os.path.join(LOGO_FOLDER, 'blinking_logo.gif'), os.path.join(DATA_FOLDER, 'blinking_logo_on_video.mp4'))
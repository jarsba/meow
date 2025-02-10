from typing import Dict, Union, List, Tuple, Optional

from .eval_utils import eval_expr
from .file_utils import create_temporary_file_name_with_extension


from tempfile import NamedTemporaryFile
import ffmpeg
from moviepy.video.VideoClip import VideoClip
from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.tools import subprocess_call
from moviepy.config import get_setting
from moviepy.video.io.VideoFileClip import VideoFileClip
import cv2
from ..logger import setup_logger

import os

logger = setup_logger(__name__)


def get_video_info(video_path) -> Dict[str, Union[int, float, str]]:
    """
    Return JSON representing video info:
        file path
        frame width in pixels
        frame high in pixels
        frame rate as FPS
        duration in seconds
    """
    probe = ffmpeg.probe(video_path)
    file_path = str(probe['format']['filename'])
    file_type = os.path.splitext(file_path)[1].lower().replace(".", "")
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    width = int(video_stream['width'])
    height = int(video_stream['height'])
    frame_rate = round(eval_expr(video_stream['avg_frame_rate']))
    duration = float(probe['format']['duration'])

    return {
        "file_path": file_path,
        "file_type": file_type,
        "frame_height": height,
        "frame_width": width,
        "frame_rate": frame_rate,
        "duration": duration
    }


def concatenate_video_clips(video_file_paths) -> VideoClip:
    clips = [VideoFileClip(file) for file in video_file_paths]
    final_clip = concatenate_videoclips(clips)
    return final_clip


def ffmpeg_concatenate_video_clips(video_file_paths: List[str], output_path: Optional[str] = None, temp_dir: Optional[str] = None, file_type: Optional[str] = None):
    """Concatenate video clips and optionally transform FPS.
    
    Args:
        video_file_paths: List of video file paths to concatenate
        output_path: Path for the output video
        output_fps: Target FPS for output video. If None, keeps original FPS.
    """

    if output_path is None:
        output_video_path = create_temporary_file_name_with_extension(temp_dir, file_type)
    else:
        output_video_path = output_path

    merged_video_list_file = NamedTemporaryFile(suffix=".txt")

    with open(merged_video_list_file.name, 'w') as f:
        for video in video_file_paths:
            escaped_path = f"'{video.replace(chr(92), chr(92)*2).replace(chr(39), chr(92)+chr(39))}'"
            print(escaped_path)
            f.write(f"file {escaped_path}\n")

    merged_video_list_file.seek(0)
    
    ffmpeg.input(merged_video_list_file.name, format='concat', safe=0).output(
        output_video_path, 
        codec='copy'
    ).global_args('-nostdin').run()

    return output_video_path


def get_last_frame(capture, duration):
    # Dirty hack to get to last 2 seconds to avoid reading to whole video file
    capture.set(cv2.CAP_PROP_POS_MSEC, (duration - 2) * 1000)
    last_frame = None
    while True:
        ret, tmp_frame = capture.read()
        if not ret:
            break
        last_frame = tmp_frame

    success = last_frame is not None
    return success, last_frame


def transform_video_fps(video_path: str, output_fps: int, output_path: Optional[str] = None, temp_dir: Optional[str] = None, file_type: Optional[str] = None):
    """Transform video FPS by re-encoding while preserving audio.
    
    Args:
        video_path: Input video path
        output_path: Output video path
        output_fps: Target FPS
    """
    
    if output_path is None:
        output_path = create_temporary_file_name_with_extension(temp_dir, file_type)

    logger.info(f"Transforming video FPS from {output_fps} to {output_path}")

    stream = ffmpeg.input(video_path)
    
    # Split into video and audio streams
    video = stream.video
    audio = stream.audio
    
    # Apply FPS filter only to video stream
    video = ffmpeg.filter(video, 'fps', fps=output_fps)
    
    # Output with both streams
    stream = ffmpeg.output(video, audio, output_path,
                         vcodec='libx264',  # Use H.264 codec
                         acodec='copy',     # Copy audio without re-encoding
                         preset='ultrafast'  # Use fastest encoding preset
                         ).global_args('-nostdin')
    ffmpeg.run(stream, overwrite_output=True)

    return output_path


def cut_subclip_with_ffmpeg(input_path: str, output_path: str, start_time: float, end_time: float, output_args: dict):
    """Helper function to cut a single video with ffmpeg."""
    try:
        stream = (
            ffmpeg
            .input(input_path, ss=start_time)
            .output(output_path,
                   t=end_time-start_time,
                   **output_args)
            .overwrite_output()
        )
        stream.run()
    except ffmpeg.Error as e:
        logger.error(f"Error cutting video {input_path}: {str(e)}")
        raise

def cut_clips_with_ffmpeg(temp_dir: str, file_type: str, start_time: float, end_time: float, left_video_path: str, right_video_path: str) -> Tuple[str, str]:
    """
    Cut video clips with ffmpeg based on start and end time.
    Returns paths to both cut video files.
    """
    preprocessed_video_left_path = create_temporary_file_name_with_extension(temp_dir, file_type)
    preprocessed_video_right_path = create_temporary_file_name_with_extension(temp_dir, file_type)
    ffmpeg_extract_subclip(left_video_path, start_time, end_time, preprocessed_video_left_path)
    ffmpeg_extract_subclip(right_video_path, start_time, end_time,
                            preprocessed_video_right_path)
    
    return preprocessed_video_left_path, preprocessed_video_right_path


def ffmpeg_extract_subclip(filename: str, t1: float, t2: float, target_name: str = None):
    """ Makes a new video file playing video file ``filename`` between
    the times ``t1`` and ``t2``. t1 and t2 are in seconds."""
    name, ext = os.path.splitext(filename)
    if not target_name:
        T1, T2 = [int(1000 * t) for t in [t1, t2]]
        target_name = "%sSUB%d_%d.%s" % (name, T1, T2, ext)

    cmd = [get_setting("FFMPEG_BINARY"), "-y",
           "-ss", "%0.2f" % t1,
           "-i", filename,
           "-t", "%0.2f" % (t2 - t1),
           "-vcodec", "copy", "-acodec", "copy", target_name]

    subprocess_call(cmd)


def extract_subclip(input_video_path, start_time, end_time) -> VideoFileClip:
    video = VideoFileClip(input_video_path)
    subclip: VideoFileClip = video.subclip(start_time, end_time)
    return subclip


def merge_video_and_audio(video_path: str, audio_path: str, output_path: str, output_fps: int = None, overwrite: bool = False):
    """Merge video and audio using FFMPEG stream copy or AAC as fallback.
    
    Args:
        video_path: Path to input video
        audio_path: Path to input audio
        output_path: Path to output file
        output_fps: Output framerate (optional)
    """
    input_video = ffmpeg.input(video_path)
    input_audio = ffmpeg.input(audio_path)

    # Get actual duration from the processed video
    video_info = get_video_info(video_path)
    duration = video_info['duration']

    ffmpeg.output(
        input_video.video,
        input_audio.audio,
        output_path,
        vcodec='copy',
        acodec='aac',
        r=output_fps,
        t=duration,  # Set the correct duration
        shortest=None  # End when shortest input ends
    ).global_args('-nostdin').run(overwrite_output=overwrite)
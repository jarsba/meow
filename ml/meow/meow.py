import argparse
from enum import Enum
import sys
from typing import List, Optional, Callable
import tempfile
import re
import os
from dotenv import load_dotenv
import contextlib
from moviepy.audio.io.AudioFileClip import AudioFileClip

from .fast_stitching import call_image_stitching
from .clip_sorter import calculate_video_file_linking
from .video_synchronizer import synchronize_videos
from .utils.video_utils import ffmpeg_concatenate_video_clips, get_video_info, transform_video_fps, cut_clips_with_ffmpeg, merge_video_and_audio
from .utils.file_utils import create_temporary_file_name_with_extension
from .audio_synchronizer import sync_and_mix_audio
from .utils.audio_utils import cut_audio_clip
from .abs_diff_optical_flow_mixer import AbsoluteDifferenceOpticalFlowMixer
from .logo_burner import burn_logo
from .utils.prompt_utils import prompt_continue
from .youtube_uploader import upload_video
from .utils.meow_utils import determine_start_and_end_time, determine_start_and_end_time_sample
import ffmpeg
import cv2
import logging
from .logger import setup_logger

load_dotenv()

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_FOLDER = os.path.join(os.path.dirname(os.path.dirname(CURRENT_DIR)), 'frontend/assets')

logger = setup_logger(__name__)

class TaskStatus(str, Enum):
    STARTED = 'started'
    FINISHED = 'finished'
    FAILED = 'failed'


def run_with_args(left_videos: List[str], right_videos: List[str], output_name: str = 'meow_output', 
                  use_mixer: bool = True, use_panorama_stitching: bool = False, upload_to_Youtube: bool = False,
                  output_file_type: Optional[str] = None, output_fps: int = 30, save_intermediate: bool = False,
                  mixer_type: str = "farneback", output_directory: Optional[str] = None, start_time: Optional[float] = None, end_time: Optional[float] = None,
                  progress_callback: Optional[Callable[[str, TaskStatus, int], None]] = None, determine_output_file_type: bool = True,
                  youtube_title: str = "Meow Match Video", use_logo: bool = False, make_sample: bool = False, auto_yes: bool = False, *args, **kwargs):
    """Run meow process:
        1. Sort videos
        2. Concatenate videos
        3. Separate audio tracks and preprocess them
        4. Find delay between audio tracks
        5. Synchronize videos based on delay
        6. Merge audiotracks to keep audio coherent
        7. Cut videos and audio to game start and end
        8. Either mix videos using VideoMixer or create panorama video using Stitcher
        9. Burn logo on video if needed
        10. Either return link to download video or upload to Youtube (not supported yet)
    """

    try:
        if progress_callback:
            progress_callback("Video processing", TaskStatus.STARTED, 5)

        logger.info("Starting meow")
        logger.debug(f"Arguments: {locals()}")
        video_info = get_video_info(left_videos[0])
        input_fps = round(video_info['frame_rate'])
        input_file_type = video_info['file_type']
        needs_fps_transform = input_fps != output_fps

        if os.path.exists(output_name):
            if not auto_yes:
                if not prompt_continue("Output file already exists. Overwrite?"):
                    sys.exit(0)
            overwrite = True
        else:
            overwrite = False

        if output_file_type is not None:
            output_file_type = output_file_type.lower().replace(".", "")

        if "." in output_name:
            output_name_without_file_type, output_file_type_from_name = output_name.split(".")
            if determine_output_file_type is True and output_file_type is None:
                logger.warning(f"File type was not specified, using file type from output name: {output_file_type_from_name}.")
                output_file_type = output_file_type_from_name.lower()
            output_name = output_name_without_file_type
        else:
            if determine_output_file_type is True and output_file_type is None:
                logger.warning(f"Output file name does not contain file type. Using input video file type {input_file_type}.")
                output_file_type = input_file_type

        if video_info['file_type'] != output_file_type.lower():
            raise ValueError(f"Input file type {input_file_type} does not match output file type {output_file_type}. Please use -t option to specify the output file type that matches the input file type or use output name that contains file type.")

        full_output_name = f"{output_name}.{output_file_type}"

        if make_sample:
            # Skip FPS transform for sample video as we want make it fast
            needs_fps_transform = False
            output_fps = input_fps

        if needs_fps_transform:
            logger.info(f"Transforming video FPS from {input_fps} to {output_fps}")

        if progress_callback:
            progress_callback("Sorting videos", TaskStatus.STARTED, 5)

        logger.info("Calculating video linking")
        left_videos_sorted = calculate_video_file_linking(left_videos)
        right_videos_sorted = calculate_video_file_linking(right_videos)
        logger.debug(f"Sorted left videos: {left_videos_sorted}")
        logger.debug(f"Sorted right videos: {right_videos_sorted}")

        if progress_callback:
            progress_callback("Sorting videos", TaskStatus.FINISHED, 10)

        base_temp_dir = tempfile.gettempdir()
            
        with (contextlib.nullcontext(output_directory)
            if save_intermediate is True
            else tempfile.TemporaryDirectory(dir=base_temp_dir)
        ) as temp_dir:

            # Make sure temp_dir exists
            os.makedirs(temp_dir, exist_ok=True)
            logger.info(
                f"Writing files to {'temporary' if save_intermediate is True else 'output'} directory {temp_dir}")

            if progress_callback:
                progress_callback("Concatenating files", TaskStatus.STARTED, 10)

            # Concatenate videos with ffmpeg concat-demuxer, because it is the fastest way to concat long video files.
            logger.info("Concatenating files")

            if len(left_videos_sorted) == 1 or make_sample is True:
                left_video_path = left_videos_sorted[0]
            else:
                left_video_path = ffmpeg_concatenate_video_clips(left_videos_sorted, temp_dir=temp_dir, file_type=output_file_type)

            if needs_fps_transform:
                temp_path = transform_video_fps(left_video_path, output_fps, temp_dir=temp_dir, file_type=output_file_type)
                left_video_path = temp_path

            if len(right_videos_sorted) == 1 or make_sample is True:
                right_video_path = right_videos_sorted[0]
            else:
                right_video_path = ffmpeg_concatenate_video_clips(right_videos_sorted, temp_dir=temp_dir, file_type=output_file_type)

            if needs_fps_transform:
                temp_path = transform_video_fps(right_video_path, output_fps, temp_dir=temp_dir, file_type=output_file_type)
                right_video_path = temp_path


            if make_sample:
                logger.debug("Making video shorter for sample to speed up further processing")
                adjusted_start_time, adjusted_end_time = determine_start_and_end_time_sample(start_time, end_time)
                # Cut both videos and audio using adjusted times
                left_video_path, right_video_path = cut_clips_with_ffmpeg(
                        temp_dir, 
                        output_file_type, 
                        adjusted_start_time, 
                        adjusted_end_time, 
                        left_video_path, 
                        right_video_path
                )

            left_audio_path = create_temporary_file_name_with_extension(temp_dir, 'wav')
            right_audio_path = create_temporary_file_name_with_extension(temp_dir, 'wav')

            # Write audio as mono for synchronization
            logger.info("Writing audio files")
            AudioFileClip(left_video_path).write_audiofile(left_audio_path, ffmpeg_params=["-ac", "1"])
            AudioFileClip(right_video_path).write_audiofile(right_audio_path, ffmpeg_params=["-ac", "1"])
            logger.debug(f"Writing audio, files found from {left_audio_path} for left "
                         f"and {right_audio_path} for right")

            if progress_callback:
                progress_callback("Concatenating files", TaskStatus.FINISHED, 15)
                progress_callback("Synchronizing audio", TaskStatus.STARTED, 15)

            logger.info("Mixing audio tracks")
            if progress_callback:
                progress_callback("Mixing audio", TaskStatus.STARTED, 20)

            merged_audio_path = create_temporary_file_name_with_extension(temp_dir, 'wav')
            audio_result = sync_and_mix_audio(
                left_audio_path, 
                right_audio_path, 
                merged_audio_path
            )
            delay = audio_result["delay_ms"] / 1000  # Convert to seconds

            if progress_callback:
                progress_callback("Mixing audio", TaskStatus.FINISHED, 20)

            if progress_callback:
                progress_callback("Synchronizing videos", TaskStatus.STARTED, 20)

            logger.info("Synchronizing videos")
            synchronized_left_video_path, synchronized_right_video_path = synchronize_videos(video1_path=left_video_path, video2_path=right_video_path, delay=delay, temp_dir=temp_dir, output_file_type=output_file_type)

            if progress_callback:
                progress_callback("Synchronizing videos", TaskStatus.FINISHED, 25)
                progress_callback("Cutting videos", TaskStatus.STARTED, 25)

            logger.debug(f"Synchronized videos found from {synchronized_left_video_path} for left "
                         f"and {synchronized_right_video_path} for right")


            left_video_info = get_video_info(synchronized_left_video_path)
            right_video_info = get_video_info(synchronized_right_video_path)
            duration = min(left_video_info["duration"], right_video_info["duration"]) 

            if start_time is not None or end_time is not None:
                logger.debug("Processing time range request")
                
                # Skip time range processing for sample video as it is already cut for speed
                if not make_sample:

                    # We need to adjust the times because they were relative to the original unsynchronized video
                    adjusted_start_time, adjusted_end_time = determine_start_and_end_time(delay, start_time, end_time, duration)
                    logger.debug(f"Cutting video based on time range: {adjusted_start_time}s - {adjusted_end_time}s")

                    # Cut both videos and audio using adjusted times
                    preprocessed_video_left_path, preprocessed_video_right_path = cut_clips_with_ffmpeg(
                            temp_dir, 
                            output_file_type, 
                            adjusted_start_time, 
                            adjusted_end_time, 
                            synchronized_left_video_path, 
                            synchronized_right_video_path
                    )
                else:
                    preprocessed_video_left_path = synchronized_left_video_path
                    preprocessed_video_right_path = synchronized_right_video_path

                # Cut audio using the same adjusted times
                logger.info(f"Cutting audio based on time range: {adjusted_start_time}s - {adjusted_end_time}s")
                preprocessed_audio_path = cut_audio_clip(merged_audio_path, adjusted_start_time, adjusted_end_time, temp_dir=temp_dir)
            
            else:
                preprocessed_video_left_path = synchronized_left_video_path
                preprocessed_video_right_path = synchronized_right_video_path
                preprocessed_audio_path = merged_audio_path


            if progress_callback:
                progress_callback("Cutting videos", TaskStatus.FINISHED, 30)
                progress_callback("Editing videos", TaskStatus.STARTED, 30)

            if use_mixer:
                if progress_callback:
                    progress_callback("Mixing videos using optical flow", TaskStatus.STARTED, 30)
                left_stream = cv2.VideoCapture(preprocessed_video_left_path)
                right_stream = cv2.VideoCapture(preprocessed_video_right_path)

                optical_flow_mixer = AbsoluteDifferenceOpticalFlowMixer()
                processed_video_path = create_temporary_file_name_with_extension(temp_dir, output_file_type)

                logger.info("Starting mixing")
                optical_flow_mixer.mix_video_with_field_mask(
                    video_capture_left=left_stream,
                    video_capture_right=right_stream,
                    video_output_path=processed_video_path,
                    input_fps=input_fps,
                    output_fps=output_fps,
                    progress_callback=lambda p: progress_callback("Mixing videos", TaskStatus.STARTED,
                                                                  int(30 + 50 * (p / 100))) if progress_callback else None
                )
            elif use_panorama_stitching:
                if progress_callback:
                    progress_callback("Stitching panorama video", TaskStatus.STARTED, 30)
                processed_video_path = call_image_stitching(
                    output_dir=temp_dir,
                    output_filename=f"stitching_result.{output_file_type}",
                    fps=output_fps,
                    left_file_path=preprocessed_video_left_path,
                    right_file_path=preprocessed_video_right_path,
                    progress_callback=lambda p: progress_callback("Stitching video", TaskStatus.STARTED,
                                                                  int(30 + 50 * (p / 100))) if progress_callback else None
                )

            if progress_callback:
                progress_callback("Editing videos", TaskStatus.FINISHED, 80)
                progress_callback("Finalizing video", TaskStatus.STARTED, 80)

            # Create temporary path for video with logo if needed
            if use_logo:
                video_with_logo_path = create_temporary_file_name_with_extension(temp_dir, output_file_type)
                burn_logo(processed_video_path, 
                         os.path.join(LOGO_FOLDER, 'blinking_logo.gif'),
                         video_with_logo_path)
                video_to_merge = video_with_logo_path
            else:
                video_to_merge = processed_video_path

            if make_sample:
                # Modify output filename to indicate it's a sample
                full_output_name = f"{output_name}_sample.{output_file_type}"
                logger.info(f"Sample video will be saved as: {full_output_name}")

            # Final video assembly
            final_video_path = full_output_name
            
            # Then merge with audio using fast FFMPEG stream copy
            logger.info("Merging final video and audio")
            merge_video_and_audio(
                video_to_merge,
                preprocessed_audio_path,
                final_video_path,
                output_fps=output_fps,
                overwrite=overwrite
            )

            if progress_callback:
                progress_callback("Finalizing video", TaskStatus.FINISHED, 85)

            if upload_to_Youtube:
                if not auto_yes:
                    if not prompt_continue("Continue with YouTube upload?"):
                        return {
                            'type': 'file',
                            'file_path': final_video_path
                        }
                if progress_callback:
                    progress_callback("Uploading to YouTube", TaskStatus.STARTED, 85)
                try:
                    response = upload_video(
                        video_file=final_video_path,
                        title=youtube_title,
                        description="Video created with meow https://github.com/jarsba/meow",
                        tags=[],
                        privacy_status="unlisted"
                    )
                    video_id = response['id']
                    if progress_callback:
                        progress_callback("Uploading to YouTube", TaskStatus.FINISHED, 100)
                    return {
                        'type': 'youtube',
                        'url': f"https://youtu.be/{video_id}",
                        'file_path': final_video_path
                    }
                except Exception as e:
                    logger.error(f"YouTube upload failed: {str(e)}")
                    # Fall back to file download if YouTube upload fails
                    return {
                        'type': 'file',
                        'file_path': final_video_path
                    }

            if progress_callback:
                progress_callback("Video processing", TaskStatus.FINISHED, 100)

            return {
                'type': 'file',
                'file_path': final_video_path
            }

    except Exception as e:
        logger.error(f"Error in run_with_args: {str(e)}")
        if progress_callback:
            progress_callback(f"Error", TaskStatus.FAILED, 0, error=str(e))
        raise


def parse_arguments():
    parser = argparse.ArgumentParser(prog='meow', description='Stitch videos to panorama')
    # Basic arguments - modify to handle both files and directories
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("-l", "--left-videos", dest='left_videos',
                            help="path to the left video file or directory containing left camera videos")
    input_group.add_argument("-ld", "--left-directory", dest='left_directory',
                            help="path to the directory containing left camera videos")
    
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("-r", "--right-videos", dest='right_videos',
                            help="path to the right video file or directory containing right camera videos")
    input_group.add_argument("-rd", "--right-directory", dest='right_directory',
                            help="path to the directory containing right camera videos")
    
    parser.add_argument("-o", "--output", default="meow_output", dest='output_name',
                        help="path of the output file (default meow_output). If contains filetype, it will be used as output filetype unless -t option is used.")
    # Option arguments
    parser.add_argument("-t", "--file-type", dest='output_file_type', help="file type for output video (without dot)")
    parser.add_argument("-m", "--mixer", default=False, action='store_true', dest='use_mixer', help="use video mixer")
    parser.add_argument("-p", "--panorama", default=False, action='store_true', dest='use_panorama_stitching',
                        help="use panorama stitching")
    parser.add_argument("-YT", "--upload-YT", default=False, action='store_true', dest='upload_to_Youtube',
                        help="automatically upload to Youtube")
    parser.add_argument("-s", "--save", default=False, action='store_true', dest='save_intermediate',
                        help="save intermediate files")
    parser.add_argument("-od", "--output-directory", default=None, dest='output_directory',
                        help="path of the output directory")
    parser.add_argument("-st", "--start-time", default=None, dest="start_time",
                        help="start time of the game as HH:MM:SS string")
    parser.add_argument("-et", "--end-time", default=None, dest="end_time",
                        help="end time of the game as HH:MM:SS string")
    parser.add_argument("-mt", "--mixer-type", default="farneback", dest="mixer_type",
                        help="type of mixer to use, either farneback or abs_diff")
    parser.add_argument("--use-logo", default=False, action='store_true', dest="use_logo",
                        help="burn logo on video")
    parser.add_argument("--sample", default=False, action='store_true', dest="make_sample",
                        help="make sample video (1 min. long) for testing. make sure you pass videos that are longer than 1 min.")
    parser.add_argument("-y", "--yes", action='store_true', dest='auto_yes',
                        help="Automatically answer yes to all prompts")

    # Meta arguments
    parser.add_argument("-v", "--verbose", action='store_true', dest='verbose', help="verbose output")
    args = parser.parse_args()
    return args


def run():
    args = parse_arguments()
    args_dict = vars(args)

    if (args_dict['use_mixer'] is False and args_dict['use_panorama_stitching'] is False) \
            or (args_dict['use_mixer'] is True and args_dict['use_panorama_stitching'] is True):
        raise ValueError("Either mixer or panorama stitching must be selected.")

    if args_dict['make_sample'] is True:
        logger.info("Creating sample video")
        if args_dict['end_time'] is not None:
            raise ValueError("Cannot make sample video with end time. Sample video is 1 min. long and starts from 00:00:00 or start time. Make sure to use only start time and the first/only video is longer than 1 min.")

    if args_dict['verbose'] is True:
        # Set all loggers to DEBUG level
        for name in logging.root.manager.loggerDict:
            if name.startswith('ml.meow'):
                logging.getLogger(name).setLevel(logging.DEBUG)

    if args_dict['start_time'] is not None:
        start_time_components = args_dict['start_time'].split(":")
        start_time = int(start_time_components[0]) * (60 * 60) + int(start_time_components[1]) * 60 + int(
            start_time_components[2])
        args_dict["start_time"] = start_time

    if args_dict['end_time'] is not None:
        end_time_components = args_dict['end_time'].split(":")
        end_time = int(end_time_components[0]) * (60 * 60) + int(end_time_components[1]) * 60 + int(
            end_time_components[2])
        args_dict["end_time"] = end_time

    file_type = args_dict['output_file_type']
    determine_output_file_type = file_type is None
    args_dict['determine_output_file_type'] = determine_output_file_type

    # Handle left videos
    if args_dict.get('left_directory'):
        left_videos_path = args_dict['left_directory']
        left_videos = [os.path.join(left_videos_path, filename) for filename in os.listdir(left_videos_path) if
                      re.search(rf'\.{file_type}$', filename, re.IGNORECASE)]
    else:
        left_video_path = args_dict['left_videos']
        if not os.path.isfile(left_video_path):
            raise ValueError(f"Left video file not found: {left_video_path}")
        left_videos = [left_video_path]

    # Handle right videos
    if args_dict.get('right_directory'):
        right_videos_path = args_dict['right_directory']
        right_videos = [os.path.join(right_videos_path, filename) for filename in os.listdir(right_videos_path) if
                       re.search(rf'\.{file_type}$', filename, re.IGNORECASE)]
    else:
        right_video_path = args_dict['right_videos']
        if not os.path.isfile(right_video_path):
            raise ValueError(f"Right video file not found: {right_video_path}")
        right_videos = [right_video_path]

    args_dict.pop('left_videos')
    args_dict.pop('right_videos')

    video_path = run_with_args(left_videos=left_videos, right_videos=right_videos, **args_dict)
    logger.info(f"Video ready, path: {video_path}")


if __name__ == "__main__":
    run()

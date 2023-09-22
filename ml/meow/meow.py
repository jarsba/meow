import argparse
import sys
from typing import List
import tempfile
import re
import os

from moviepy.audio.io.AudioFileClip import AudioFileClip

from clip_sorter import calculate_video_file_linking
from video_synchronizer import synchronize_videos
from utils.video_utils import ffmpeg_concatenate_video_clips, get_video_info
from utils.audio_utils import merge_audio_tracks, preprocess_audio
from utils.file_utils import create_temporary_file_name_with_extension
from audio_synchronizer import calculate_synchronization_delay, synchronize_audios
from stitcher import Stitcher
from utils.string_utils import generate_random_string
from abs_diff_optical_flow_mixer import AbsoluteDifferenceOpticalFlowMixer
import ffmpeg
from scipy.io import wavfile
import cv2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(prog='meow', description='Stitch videos to panorama')
    # Basic arguments
    parser.add_argument("-l", "--left-videos", required=True, dest='left_videos', help="path to the left video files")
    parser.add_argument("-r", "--right-videos", required=True, dest='right_videos',
                        help="path to the right video files")
    parser.add_argument("-o", "--output", default="meow_output.mp4", dest='output',
                        help="path of the output file (default meow_output.mp4)")
    # Option arguments
    parser.add_argument("-t", "--file-type", default='mp4', dest='file_type', help="file type for videos (without dot)")
    parser.add_argument("-m", "--mixer", default=False, action='store_true', dest='use_mixer', help="use video mixer")
    parser.add_argument("-p", "--panorama", default=False, action='store_true', dest='use_panorama_stitching',
                        help="use panorama stitching")
    parser.add_argument("-YT", "--upload-YT", default=False, action='store_true', dest='upload_to_Youtube',
                        help="automatically upload to Youtube")
    # Meta arguments
    parser.add_argument("-v", "--verbose", action='store_true', dest='verbose', help="verbose output")
    args = parser.parse_args()
    return args


def run_with_args(left_videos: List[str], right_videos: List[str], output: str = 'meow_output.mp4',
                  use_mixer: bool = True, use_panorama_stitching: bool = False, upload_to_Youtube: bool = False,
                  verbose: bool = False, file_type: str = "mp4", output_fps: int = 60, *args, **kwargs):
    """Run meow process:
        1. Sort videos
        2. Concatenate videos
        3. Separate audio tracks and preprocess them
        4. Find delay between audio tracks
        5. Synchronize videos based on delay
        6. Merge audiotracks to keep audio coherent
        7. Either mix videos using VideoMixer or create panorama video using Stitcher
        8. Either return link to download video or upload to Youtube
    """

    logger.info("Starting meow")
    video_info = get_video_info(left_videos[0])
    input_fps = round(video_info['frame_rate'])

    logger.info("Calculating video linking")
    left_videos_sorted = calculate_video_file_linking(left_videos)
    right_videos_sorted = calculate_video_file_linking(right_videos)

    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"Writing files to temporary directory {temp_dir}")
        left_video_path = create_temporary_file_name_with_extension(temp_dir, file_type)
        right_video_path = create_temporary_file_name_with_extension(temp_dir, file_type)

        # Concatenate videos with ffmpeg concat-demuxer, because it is the fastest way to concat long video files.
        # Moviepy is very slow.
        logger.info("Concatenating files")
        ffmpeg_concatenate_video_clips(left_videos_sorted, left_video_path)
        ffmpeg_concatenate_video_clips(right_videos_sorted, right_video_path)

        left_audio_path = create_temporary_file_name_with_extension(temp_dir, 'wav')
        right_audio_path = create_temporary_file_name_with_extension(temp_dir, 'wav')

        # Write audio as mono for synchronization
        AudioFileClip(left_video_path).write_audiofile(left_audio_path, ffmpeg_params=["-ac", "1"])
        AudioFileClip(right_video_path).write_audiofile(right_audio_path, ffmpeg_params=["-ac", "1"])

        samplerate1, preprocessed_audio1 = preprocess_audio(left_audio_path, to_mono=True, high_pass=True)
        samplerate2, preprocessed_audio2 = preprocess_audio(right_audio_path, to_mono=True, high_pass=True)

        assert samplerate1 == samplerate2

        logger.info("Calculating synchronization delay")
        delay = calculate_synchronization_delay(preprocessed_audio1, preprocessed_audio2, samplerate=samplerate1)

        logger.info("Synchronizing audio")
        audio1, audio2 = synchronize_audios(audio1_path=left_audio_path, audio2_path=right_audio_path, delay=delay)

        logger.info("Synchronizing video")
        synchronized_left_video_path = create_temporary_file_name_with_extension(temp_dir, file_type)
        synchronized_right_video_path = create_temporary_file_name_with_extension(temp_dir, file_type)
        synchronize_videos(video1_path=left_video_path, video2_path=right_video_path, delay=delay,
                           video1_output_path=synchronized_left_video_path,
                           video2_output_path=synchronized_right_video_path)

        logger.info("Merging audiotracks")
        merged_audio = merge_audio_tracks(audio1, audio2)
        merged_audio_path = create_temporary_file_name_with_extension(temp_dir, 'wav')
        merged_audio.export(merged_audio_path, format="wav")

        if use_mixer:
            logger.info("Starting video mixer")
            left_stream = cv2.VideoCapture(synchronized_left_video_path)
            right_stream = cv2.VideoCapture(synchronized_right_video_path)

            optical_flow_mixer = AbsoluteDifferenceOpticalFlowMixer()
            mixed_video_path = create_temporary_file_name_with_extension(temp_dir, file_type)

            logger.info("Starting mixing")
            mixed_video_output = optical_flow_mixer.mix_video_with_field_mask(left_stream, right_stream,
                                                                              mixed_video_path, input_fps=input_fps, output_fps=output_fps)
        elif use_panorama_stitching:
            left_stream = cv2.VideoCapture(synchronized_left_video_path)
            right_stream = cv2.VideoCapture(synchronized_right_video_path)

            logger.warning("Stitcher is not ready yet, please use video mixer")
            sys.exit(1)
            # stitcher = Stitcher()

        if upload_to_Youtube:
            logger.warning("Youtube upload is not ready yet, please use regular file download")
            sys.exit(1)
        else:
            final_video_path = output
            input_video = ffmpeg.input(mixed_video_path)
            input_audio = ffmpeg.input(merged_audio_path)

            logger.info(f"Saving final output to file {final_video_path}")
            ffmpeg.output(
                input_video.video,
                input_audio.audio,
                final_video_path,
                vcodec='copy',
                acodec='aac',
            ).run()

            return final_video_path


def run():
    args = parse_arguments()
    args_dict = vars(args)

    if args_dict['use_mixer'] is False and args_dict['use_panorama_stitching'] is False:
        logger.error("Either mixer or panorama stitching must be selected.")
        sys.exit(1)

    file_type = args_dict['file_type']
    left_videos_path = args_dict['left_videos']
    right_videos_path = args_dict['right_videos']

    left_videos = [os.path.join(left_videos_path, filename) for filename in os.listdir(left_videos_path) if
                   re.search(rf'\.{file_type}$', filename, re.IGNORECASE)]
    right_videos = [os.path.join(right_videos_path, filename) for filename in os.listdir(right_videos_path) if
                    re.search(rf'\.{file_type}$', filename, re.IGNORECASE)]

    args_dict.pop('left_videos')
    args_dict.pop('right_videos')

    run_with_args(left_videos=left_videos, right_videos=right_videos, **args_dict)


if __name__ == "__main__":
    run()

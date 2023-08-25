import argparse
from typing import List
import tempfile
import os
import re
import sys
from clip_sorter import calculate_video_file_linking
from utils.video_utils import concatenate_video_clips, ffmpeg_concatenate_video_clips
from audio_synchronizer import calculate_synchronization_delay
from utils.string_utils import generate_random_string


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
    parser.add_argument("-m", "--mixer", default=True, action='store_true', dest='use_mixer', help="use video mixer")
    parser.add_argument("-p", "--panorama", default=False, action='store_true', dest='use_panorama_stitching',
                        help="use panorama stitching")
    parser.add_argument("-YT", "--upload-YT", default=False, action='store_true', dest='upload_to_Youtube',
                        help="automatically upload to Youtube")
    # Meta arguments
    parser.add_argument("-v", "--verbose", action='store_true', dest='verbose', help="verbose output")
    args = parser.parse_args()
    return args


def run_with_args(left_videos: List[str], right_videos: List[str], use_mixer: bool = True,
                  use_panorama_stitching: bool = False, upload_to_Youtube: bool = False, verbose: bool = False,
                  file_type: str = "mp4", *args, **kwargs):
    """Run meow process:
        1. Sort videos
        2. Concatenate videos
        3. Separate audio track and find delay between audio tracks
        4. Synchronize videos based on delay
        5. Merge audiotracks to keep audio coherent
        6. Either mix videos using VideoMixer or create panorama video using Stitcher
        7. Either return link to download video or upload to Youtube
    """

    left_videos_sorted = calculate_video_file_linking(left_videos)
    right_videos_sorted = calculate_video_file_linking(right_videos)

    left_video_path = os.path.join(tempfile.gettempdir(), f'{generate_random_string()}.{file_type}')
    right_video_path = os.path.join(tempfile.gettempdir(), f'{generate_random_string()}.{file_type}')

    # Concatenate videos with ffmpeg concat-demuxer, because it is the fastest way to concat long video files.
    # Moviepy is very slow.
    ffmpeg_concatenate_video_clips(left_videos_sorted, left_video_path)
    ffmpeg_concatenate_video_clips(right_videos_sorted, right_video_path)




    delay = calculate_synchronization_delay(left_clip.audio, right_clip.audio)


def run():
    args = parse_arguments()
    args_dict = vars(args)

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

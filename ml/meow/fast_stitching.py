import subprocess
import os
from enum import Enum
from typing import Optional, Callable
import logging
import argparse
from .logger import setup_logger

logger = setup_logger(__name__)

STICHING_DIR = os.path.join(os.path.dirname(os.path.abspath(__name__)), "stitching")
BUILD_DIR = os.path.join(STICHING_DIR, "build")


class TaskStatus(str, Enum):
    STARTED = 'started'
    FINISHED = 'finished'
    FAILED = 'failed'


def call_image_stitching(
        output_dir: str,
        output_filename: str,
        fps: int,
        left_file_path: str,
        right_file_path: str,
        dry_run: bool = False,
        use_lir: bool = True,
        progress_callback: Optional[Callable[[str, TaskStatus, int], None]] = None
) -> Optional[str]:
    logger.info("Starting fast image stitching")

    stitching_command = [
        './image-stitching',
        output_dir,
        output_filename,
        str(fps),
        str(dry_run).lower(),
        str(use_lir).lower(),
        left_file_path,
        right_file_path
    ]

    try:
        # Use Popen instead of run to get real-time output
        process = subprocess.Popen(
            stitching_command,
            cwd=BUILD_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )

        # Read output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                if "PROGRESS" in output:
                    progress = int(output.split(":")[1].strip())
                    logger.info(f"Progress: {progress}%")
                    if progress_callback:
                        progress_callback(progress)
                else:
                    logger.debug(output.strip())

        # Get the return code
        return_code = process.poll()
        if return_code != 0:
            error = process.stderr.read()
            raise Exception(f"Stitching failed with code {return_code}: {error}")

        output_file = os.path.join(output_dir, output_filename)
        return output_file

    except Exception as exc:
        logger.exception("Exception happened during video stitching", exc_info=exc)
        raise exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='fast stitching', description='Fast stitch videos to panorama')
    parser.add_argument("-o", "--output-directory", required=True, default=None, dest='output_directory',
                        help="path of the output directory")
    parser.add_argument("-f", "--file-name", default="stitching_result.mp4", dest='file_name',
                        help="file name for output video")
    parser.add_argument("-s", "--fps", required=True, default=30, type=int, dest='fps', help="fps")
    parser.add_argument("-l", "--left-video", required=True, dest='left_video', help="path to the left video file")
    parser.add_argument("-r", "--right-video", required=True, dest='right_video',
                        help="path to the right video file")
    parser.add_argument("-d", "--dry-run", action='store_true', dest='dry_run', help="dry run")
    parser.add_argument("--no-lir", action='store_false', dest='use_lir',
                        help="disable Largest Interior Rectangle cropping")
    parser.add_argument("-v", "--verbose", action='store_true', dest='verbose', help="verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    args_dict = vars(args)

    video_path = call_image_stitching(
        output_dir=args_dict["output_directory"], 
        output_filename=args_dict["file_name"],
        fps=args_dict["fps"], 
        left_file_path=args_dict["left_video"],
        right_file_path=args_dict["right_video"], 
        dry_run=args_dict["dry_run"],
        use_lir=args_dict["use_lir"]
    )
    logger.info(f"Video ready, path: {video_path}")

import subprocess
import os
from typing import Optional
import logging
import argparse

logger = logging.getLogger(__name__)

STICHING_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__name__)))), "stitching")
BUILD_DIR = os.path.join(STICHING_DIR, "build")


def call_image_stitching(
        output_dir: str,
        output_filename: str,
        fps: int,
        left_file_path: str,
        right_file_path: str
) -> Optional[str]:
    logger.info(f"Starting fast image stitching")

    stitching_command = [
        './image-stitching',
        output_dir,
        output_filename,
        str(fps),
        left_file_path,
        right_file_path
    ]

    try:
        result = subprocess.run(
            stitching_command,
            cwd=BUILD_DIR,
            check=True,  # Raises an error if the command exits with a non-zero status
            capture_output=True,  # Capture the output for logging
            text=True  # Return output as string rather than bytes
        )

        logger.debug(f"Stitching output: {result.stdout}")
        logger.debug(f"Stitching errors: {result.stderr}")

        output_file = os.path.join(output_dir, output_filename)
        return output_file

    except subprocess.CalledProcessError as exc:
        logger.exception("Exception happened during video stitching", exc_info=exc)
        return None


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

    args = parser.parse_args()
    args_dict = vars(args)

    video_path = call_image_stitching(output_dir=args_dict["output_directory"], output_filename=args_dict["file_name"],
                                      fps=args_dict["fps"], left_file_path=args_dict["left_video"],
                                      right_file_path=args_dict["right_video"])
    logger.info(f"Video ready, path: {video_path}")

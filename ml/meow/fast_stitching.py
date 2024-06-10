import subprocess
import os
from typing import Optional
import logging

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

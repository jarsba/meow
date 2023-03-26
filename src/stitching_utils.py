from typing import Literal, List
import cv2

DEFAULT_MEDIUM_MEGAPIX = 0.6
DEFAULT_LOW_MEGAPIX = 0.1
DEFAULT_FINAL_MEGAPIX = -1


def resize_images(images: List, scale: float) -> List:
    scaled_images = []

    for image in images:
        original_width, original_height = image.shape[0], image.shape[1]
        target_width = int(round(original_width[0] * scale))
        target_height = int(round(original_height[1] * scale))

        scaled_image = cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_LINEAR_EXACT)
        scaled_images.append(scaled_image)
    return scaled_images



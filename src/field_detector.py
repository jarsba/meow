import cv2
import numpy as np


def mask_field_from_image(frame):
    median_blurred_image = cv2.medianBlur(frame, 51)
    gray_image = cv2.cvtColor(median_blurred_image, cv2.COLOR_RGB2GRAY)
    
    _, mask = cv2.threshold(gray_image, 100, 255, cv2.THRESH_BINARY)
    mask = ~mask

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (151, 151))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    max_contour = max(contours, key=cv2.contourArea)

    approx = cv2.approxPolyDP(max_contour, 0.1 * cv2.arcLength(max_contour, True), True)

    final_mask = np.zeros(gray_image.shape, np.uint8)
    cv2.drawContours(final_mask, [approx], 0, (255), -1)
    final_mask = ~final_mask

    return final_mask

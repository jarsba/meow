import cv2
from PIL import Image, ImageDraw
import numpy as np
import os

# From https://stackoverflow.com/a/64474046
# This code adapted from https://github.com/python-pillow/Pillow/issues/4644 to resolve an issue
# described in https://github.com/python-pillow/Pillow/issues/4640
#
# There is a long-standing issue with the Pillow library that messes up GIF transparency by replacing the
# transparent pixels with black pixels (among other issues) when the GIF is saved using PIL.Image.save().
# This code works around the issue and allows us to properly generate transparent GIFs.

from typing import Tuple, List, Union
from collections import defaultdict
from random import randrange
from itertools import chain

class TransparentAnimatedGifConverter(object):
    _PALETTE_SLOTSET = set(range(256))

    def __init__(self, img_rgba: Image, alpha_threshold: int = 0):
        self._img_rgba = img_rgba
        self._alpha_threshold = alpha_threshold

    def _process_pixels(self):
        """Set the transparent pixels to the color 0."""
        self._transparent_pixels = set(
            idx for idx, alpha in enumerate(
                self._img_rgba.getchannel(channel='A').getdata())
            if alpha <= self._alpha_threshold)

    def _set_parsed_palette(self):
        """Parse the RGB palette color `tuple`s from the palette."""
        palette = self._img_p.getpalette()
        self._img_p_used_palette_idxs = set(
            idx for pal_idx, idx in enumerate(self._img_p_data)
            if pal_idx not in self._transparent_pixels)
        self._img_p_parsedpalette = dict(
            (idx, tuple(palette[idx * 3:idx * 3 + 3]))
            for idx in self._img_p_used_palette_idxs)

    def _get_similar_color_idx(self):
        """Return a palette index with the closest similar color."""
        old_color = self._img_p_parsedpalette[0]
        dict_distance = defaultdict(list)
        for idx in range(1, 256):
            color_item = self._img_p_parsedpalette[idx]
            if color_item == old_color:
                return idx
            distance = sum((
                abs(old_color[0] - color_item[0]),  # Red
                abs(old_color[1] - color_item[1]),  # Green
                abs(old_color[2] - color_item[2])))  # Blue
            dict_distance[distance].append(idx)
        return dict_distance[sorted(dict_distance)[0]][0]

    def _remap_palette_idx_zero(self):
        """Since the first color is used in the palette, remap it."""
        free_slots = self._PALETTE_SLOTSET - self._img_p_used_palette_idxs
        new_idx = free_slots.pop() if free_slots else \
            self._get_similar_color_idx()
        self._img_p_used_palette_idxs.add(new_idx)
        self._palette_replaces['idx_from'].append(0)
        self._palette_replaces['idx_to'].append(new_idx)
        self._img_p_parsedpalette[new_idx] = self._img_p_parsedpalette[0]
        del(self._img_p_parsedpalette[0])

    def _get_unused_color(self) -> tuple:
        """ Return a color for the palette that does not collide with any other already in the palette."""
        used_colors = set(self._img_p_parsedpalette.values())
        while True:
            new_color = (randrange(256), randrange(256), randrange(256))
            if new_color not in used_colors:
                return new_color

    def _process_palette(self):
        """Adjust palette to have the zeroth color set as transparent. Basically, get another palette
        index for the zeroth color."""
        self._set_parsed_palette()
        if 0 in self._img_p_used_palette_idxs:
            self._remap_palette_idx_zero()
        self._img_p_parsedpalette[0] = self._get_unused_color()

    def _adjust_pixels(self):
        """Convert the pixels into their new values."""
        if self._palette_replaces['idx_from']:
            trans_table = bytearray.maketrans(
                bytes(self._palette_replaces['idx_from']),
                bytes(self._palette_replaces['idx_to']))
            self._img_p_data = self._img_p_data.translate(trans_table)
        for idx_pixel in self._transparent_pixels:
            self._img_p_data[idx_pixel] = 0
        self._img_p.frombytes(data=bytes(self._img_p_data))

    def _adjust_palette(self):
        """Modify the palette in the new `Image`."""
        unused_color = self._get_unused_color()
        final_palette = chain.from_iterable(
            self._img_p_parsedpalette.get(x, unused_color) for x in range(256))
        self._img_p.putpalette(data=final_palette)

    def process(self):
        """Return the processed mode `P` `Image`."""
        self._img_p = self._img_rgba.convert(mode='P')
        self._img_p_data = bytearray(self._img_p.tobytes())
        self._palette_replaces = dict(idx_from=list(), idx_to=list())
        self._process_pixels()
        self._process_palette()
        self._adjust_pixels()
        self._adjust_palette()
        self._img_p.info['transparency'] = 0
        self._img_p.info['background'] = 0
        return self._img_p


def _create_animated_gif(images: List, durations: Union[int, List[int]]) -> Tuple:
    """If the image is a GIF, create an its thumbnail here."""
    save_kwargs = dict()
    new_images: List[Image] = []

    for frame in images:
        thumbnail = frame.copy()  # type: Image
        thumbnail_rgba = thumbnail.convert(mode='RGBA')
        thumbnail_rgba.thumbnail(size=frame.size, reducing_gap=3.0)
        converter = TransparentAnimatedGifConverter(img_rgba=thumbnail_rgba)
        thumbnail_p = converter.process()  # type: Image
        new_images.append(thumbnail_p)

    output_image = new_images[0]
    save_kwargs.update(
        format='GIF',
        save_all=True,
        optimize=False,
        append_images=new_images[1:],
        duration=durations,
        disposal=2,  # Other disposals don't work
        loop=0)
    return output_image, save_kwargs


def save_transparent_gif(images: List, durations: Union[int, List[int]], save_file):
    """Creates a transparent GIF, adjusting to avoid transparency issues that are present in the PIL library

    Note that this does NOT work for partial alpha. The partial alpha gets discarded and replaced by solid colors.

    Parameters:
        images: a list of PIL Image objects that compose the GIF frames
        durations: an int or List[int] that describes the animation durations for the frames of this GIF
        save_file: A filename (string), pathlib.Path object or file object. (This parameter corresponds
                   and is passed to the PIL.Image.save() method.)
    Returns:
        Image - The PIL Image object (after first saving the image to the specified target)
    """
    root_frame, save_args = _create_animated_gif(images, durations)
    root_frame.save(save_file, **save_args)

def create_blinking_logo(logo_path, blink_duration=0.5):
    """Creates a GIF of the logo with a blinking red eye effect.
    
    Args:
        logo_path (str): Path to the original logo image
        blink_duration (float): Duration of each blink frame in seconds
    """
    # Load the original logo
    logo = Image.open(logo_path).convert('RGBA')
    
    # Create frames for the animation
    frames = []
    
    # Define the eye position (you'll need to adjust these coordinates)
    eye_x, eye_y = 137, 97  # Example coordinates - adjust based on your logo
    eye_radius = 3  # Core light radius
    glow_radius = 6  # Outer glow radius
    
    # Create frames with varying opacity
    num_transition_frames = 15
    max_opacity = int(255 * 0.95)  # 75% maximum opacity
    
    # Generate fade-in frames
    for i in range(num_transition_frames):
        # Create a new transparent layer for the glow effect
        glow_layer = Image.new('RGBA', logo.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow_layer)
        opacity = int((i / num_transition_frames) * max_opacity)
        
        # Draw outer glow
        glow_opacity = int(opacity * 0.3)
        draw.ellipse([eye_x - glow_radius, eye_y - glow_radius,
                     eye_x + glow_radius, eye_y + glow_radius],
                    fill=(255, 0, 0, glow_opacity))
        
        # Draw core light
        draw.ellipse([eye_x - eye_radius, eye_y - eye_radius,
                     eye_x + eye_radius, eye_y + eye_radius],
                    fill=(255, 50, 50, opacity))
        
        # Composite the glow layer onto the logo
        frame = Image.alpha_composite(logo, glow_layer)
        frames.append(frame)
    
    # Hold the full brightness for a few frames
    for _ in range(5):
        glow_layer = Image.new('RGBA', logo.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow_layer)
        
        # Draw outer glow
        draw.ellipse([eye_x - glow_radius, eye_y - glow_radius,
                     eye_x + glow_radius, eye_y + glow_radius],
                    fill=(255, 0, 0, int(max_opacity * 0.3)))
        
        # Draw core light
        draw.ellipse([eye_x - eye_radius, eye_y - eye_radius,
                     eye_x + eye_radius, eye_y + eye_radius],
                    fill=(255, 50, 50, max_opacity))
        
        frame = Image.alpha_composite(logo, glow_layer)
        frames.append(frame)
    
    # Generate fade-out frames
    for i in range(num_transition_frames):
        glow_layer = Image.new('RGBA', logo.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow_layer)
        opacity = int(((num_transition_frames - i) / num_transition_frames) * max_opacity)
        
        # Draw outer glow
        glow_opacity = int(opacity * 0.3)
        draw.ellipse([eye_x - glow_radius, eye_y - glow_radius,
                     eye_x + glow_radius, eye_y + glow_radius],
                    fill=(255, 0, 0, glow_opacity))
        
        # Draw core light
        draw.ellipse([eye_x - eye_radius, eye_y - eye_radius,
                     eye_x + eye_radius, eye_y + eye_radius],
                    fill=(255, 50, 50, opacity))
        
        frame = Image.alpha_composite(logo, glow_layer)
        frames.append(frame)
    
    # Add some frames of the original logo at the end for pause between blinks
    for _ in range(20):
        frames.append(logo.copy())
    
    # Save individual frames
    for i, frame in enumerate(frames):
        frame.save(f'temp_frame_{i}.png', 'PNG')
    
    return frames

if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    print(CURRENT_DIR)
    LOGO_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))), 'frontend/assets')
    print(LOGO_FOLDER)
    frames = create_blinking_logo(os.path.join(LOGO_FOLDER, 'logo.png'), blink_duration=0.5)
    save_transparent_gif(frames, 5, os.path.join(LOGO_FOLDER, 'blinking_logo.gif'))

    
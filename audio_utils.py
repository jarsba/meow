import moviepy.editor as mp
import os
from scipy.io.wavfile import read
import numpy as np
from typing import Tuple


def extract_audio(video_path) -> mp.AudioClip:
    video = mp.VideoFileClip(video_path)
    audio = video.audio
    return audio


def write_to_file(audio: mp.AudioClip, path, filename, extension="mp3"):
    audio.write_audiofile(os.path.join(path, f"{filename}.{extension}"))


def wav_to_numpy(wav_file_path) -> Tuple[int, np.array]:
    a = read(wav_file_path)
    sample_rate = a[0]
    audio_array = np.array(a[1], dtype=float)
    return sample_rate, audio_array

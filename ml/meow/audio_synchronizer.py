from typing import Tuple

import numpy as np
from scipy import fft
import logging
from pydub import AudioSegment

logger = logging.getLogger(__name__)


def audio_fft_correlation(audio1, audio2):
    audio1_length = len(audio1)
    audio2_length = len(audio2)

    padsize = audio1_length + audio2_length + 1
    padsize = 2 ** (int(np.log(padsize) / np.log(2)) + 1)

    audio1_pad = np.zeros(padsize)
    audio1_pad[:audio1_length] = audio1

    audio2_pad = np.zeros(padsize)
    audio2_pad[:audio2_length] = audio2

    corr = fft.ifft(fft.fft(audio1_pad) * np.conj(fft.fft(audio2_pad)))
    ca = np.absolute(corr)
    xmax = np.argmax(ca)

    return padsize, corr, ca, xmax


def calculate_synchronization_delay(audio1: np.array, audio2: np.array, samplerate=44100):
    """Compare first audio clip to second audio clip and calculate offset in seconds to synchronize audio inputs.

    :param audio1: First audio as numpy array
    :param audio2: Second audio as numpy array
    :param samplerate: Samplerate of the audio. Must be the same for both clips
    :return: Positive offset if audio 1 needs delay and negative offset if audio 2 needs delay
    """
    padsize, corr, ca, xmax = audio_fft_correlation(audio1, audio2)

    if xmax > padsize // 2:
        offset = (padsize - xmax) / samplerate
        logger.info(f"Audio 1 needs {offset} second delay")
        return offset
    else:
        offset = xmax / samplerate
        logger.info(f"Audio 2 needs {offset} second delay")
        return -offset


def synchronize_audios(audio1_path: np.array, audio2_path: np.array, delay: float) -> Tuple[AudioSegment, AudioSegment]:
    audio1 = AudioSegment.from_wav(audio1_path)
    audio2 = AudioSegment.from_wav(audio2_path)

    final_duration = min(audio1.duration_seconds, audio2.duration_seconds) - abs(delay)

    if delay >= 0:
        logger.debug(f"Delay {audio1_path} by {delay} seconds")

        audio1_start_time = delay
        audio1_end_time = final_duration + delay
        audio2_start_time = 0
        audio2_end_time = final_duration

        # Multiply by 1000 to get milliseconds for pydub
        audio1_cut = audio1[audio1_start_time*1000:audio1_end_time*1000]
        audio2_cut = audio2[audio2_start_time*1000:audio2_end_time*1000]

    else:
        logger.debug(f"Delay {audio2_path} by {delay} seconds")
        delay = abs(delay)

        audio1_start_time = 0
        audio1_end_time = final_duration
        audio2_start_time = delay
        audio2_end_time = final_duration + delay

        # Multiply by 1000 to get milliseconds for pydub
        audio1_cut = audio1[audio1_start_time * 1000:audio1_end_time * 1000]
        audio2_cut = audio2[audio2_start_time * 1000:audio2_end_time * 1000]

    return audio1_cut, audio2_cut

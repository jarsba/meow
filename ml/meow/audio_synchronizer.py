import numpy as np
from scipy import fft
import logging

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

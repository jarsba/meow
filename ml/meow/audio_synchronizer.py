from typing import Tuple

import numpy as np
from scipy import fft
from scipy.signal import correlate
import soundfile as sf
import librosa
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


def calculate_synchronization_delay(audio1: np.array, audio2: np.array, samplerate: int = 44100, comparison_length_sec: int = 180) -> float:
    """Compare first audio clip to second audio clip and calculate offset in seconds to synchronize audio inputs.
    If audios are very long, compare only the first 3 minutes of the audio.

    :param audio1: First audio as numpy array
    :param audio2: Second audio as numpy array
    :param samplerate: Samplerate of the audio. Must be the same for both clips
    :return: Positive offset if audio 1 needs delay and negative offset if audio 2 needs delay
    """

    if min(len(audio1), len(audio2)) > comparison_length_sec * samplerate:
        audio1 = audio1[:comparison_length_sec * samplerate]
        audio2 = audio2[:comparison_length_sec * samplerate]

    padsize, corr, ca, xmax = audio_fft_correlation(audio1, audio2)

    if xmax > padsize // 2:
        offset = (padsize - xmax) / samplerate
        logger.info(f"Audio 1 needs {offset} second delay")
        return offset
    else:
        offset = xmax / samplerate
        logger.info(f"Audio 2 needs {offset} second delay")
        return -offset


def calculate_robust_audio_delay(file1_path, file2_path):
    """
    Calculate the delay between two audio files using cross-correlation.
    Returns delay in milliseconds.

    Parameters:
    file1_path (str): Path to first audio file
    file2_path (str): Path to second audio file

    Returns:
    float: Delay in milliseconds (positive if file2 is delayed relative to file1)
    """
    # Load audio files using librosa (resamples automatically)
    y1, sr1 = librosa.load(file1_path)
    y2, sr2 = librosa.load(file2_path)

    # Ensure both arrays are the same length
    min_length = min(len(y1), len(y2))
    y1 = y1[:min_length]
    y2 = y2[:min_length]

    # Apply preprocessing to reduce noise impact
    # High-pass filter to reduce wind noise
    y1_filtered = librosa.effects.preemphasis(y1)
    y2_filtered = librosa.effects.preemphasis(y2)

    # Normalize the signals
    y1_normalized = y1_filtered / np.sqrt(np.sum(y1_filtered ** 2))
    y2_normalized = y2_filtered / np.sqrt(np.sum(y2_filtered ** 2))

    # Compute cross-correlation
    correlation = correlate(y1_normalized, y2_normalized, mode='full')

    # Find the peak in the correlation
    max_correlation_idx = np.argmax(correlation)

    # Calculate delay in samples
    delay_samples = max_correlation_idx - (len(y1_normalized) - 1)

    # Convert to milliseconds
    delay_ms = (delay_samples / sr1) * 1000

    # Calculate confidence score based on correlation peak height
    max_correlation = np.max(correlation)
    confidence = max_correlation

    logger.info(f"Delay: {delay_ms:.2f} ms")
    logger.info(f"Confidence: {confidence:.2f}")

    return {
        'delay_ms': delay_ms,
        'confidence': confidence,
        'delay_samples': delay_samples
    }

def mix_audio_tracks(audio1: np.array, audio2: np.array, mix_ratio=(0.5, 0.5)) -> np.array:
    # Create stereo mix
    # Left channel: mix of both signals according to left_ratio
    left = audio1 * mix_ratio[0] + audio2 * (1 - mix_ratio[0])
    # Right channel: mix of both signals according to right_ratio
    right = audio1 * (1 - mix_ratio[1]) + audio2 * mix_ratio[1]

    # Combine into stereo array
    stereo_mix = np.vstack((left, right)).T

    return stereo_mix

def sync_and_mix_audio(file1_path, file2_path, output_path, mix_ratio=(0.5, 0.5)):
    """
    Synchronize two audio files and mix them into a stereo file with specified balance.

    Parameters:
    file1_path (str): Path to first audio file
    file2_path (str): Path to second audio file
    output_path (str): Path to save mixed stereo file
    mix_ratio (tuple): (left_ratio, right_ratio) for mixing the files (default: 0.5, 0.5)
    """
    # Calculate delay
    result = calculate_robust_audio_delay(file1_path, file2_path)
    delay_samples = result['delay_samples']

    # Load both files
    y1, sr = librosa.load(file1_path, mono=True)
    y2, sr = librosa.load(file2_path, mono=True)

    # Ensure both arrays are the same length
    max_length = max(len(y1), len(y2))
    y1 = np.pad(y1, (0, max(0, max_length - len(y1))), mode='constant')
    y2 = np.pad(y2, (0, max(0, max_length - len(y2))), mode='constant')

    # Apply the delay to y2
    if delay_samples > 0:
        y2 = np.pad(y2, (delay_samples, 0), mode='constant')[:-delay_samples]
    else:
        y2 = np.pad(y2, (0, -delay_samples), mode='constant')[-delay_samples:]

    # Normalize both signals
    y1 = y1 / np.max(np.abs(y1))
    y2 = y2 / np.max(np.abs(y2))

    stereo_mix = mix_audio_tracks(y1, y2)

    # Save the result
    sf.write(output_path, stereo_mix, sr, 'PCM_24')

    return {
        'delay_ms': result['delay_ms'],
        'confidence': result['confidence'],
        'sample_rate': sr,
        'duration': len(stereo_mix) / sr
    }


def synchronize_audios(audio1_path: np.array, audio2_path: np.array, delay: float) -> Tuple[AudioSegment, AudioSegment]:
    """Delay is calculated based on audio1 relative position to audio2 in seconds. If delay is positive, audio1 is playing delay
    amount of time before audio2 and audio1 needs to delayed, meaning that we need to cut delay amount of time from the
    start of audio2. If delay is negative, we need to do opposite."""

    audio1 = AudioSegment.from_wav(audio1_path)
    audio2 = AudioSegment.from_wav(audio2_path)

    final_duration = min(audio1.duration_seconds, audio2.duration_seconds) - abs(delay)

    if delay < 0:
        # Left video is ahead of right video by delay seconds
        logger.debug(f"Delay {audio1_path} by {delay} seconds")

        audio1_start_time = delay
        audio1_end_time = final_duration + delay
        audio2_start_time = 0
        audio2_end_time = final_duration

        # Multiply by 1000 to get milliseconds for pydub
        audio1_cut = audio1[audio1_start_time * 1000:audio1_end_time * 1000]
        audio2_cut = audio2[audio2_start_time * 1000:audio2_end_time * 1000]
    else:
        # Right video is ahead of left video by delay seconds
        delay = abs(delay)
        logger.debug(f"Delay {audio2_path} by {delay} seconds")

        audio1_start_time = 0
        audio1_end_time = final_duration
        audio2_start_time = delay
        audio2_end_time = final_duration + delay

        # Multiply by 1000 to get milliseconds for pydub
        audio1_cut = audio1[audio1_start_time * 1000:audio1_end_time * 1000]
        audio2_cut = audio2[audio2_start_time * 1000:audio2_end_time * 1000]

    return audio1_cut, audio2_cut

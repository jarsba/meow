import moviepy.editor as mp
import os
from scipy.io.wavfile import read
import numpy as np
from typing import Tuple, Optional
import math
import subprocess
from .math_utils import safe_division
from .file_utils import create_temporary_file_name_with_extension
from tqdm import tqdm
from pydub import AudioSegment
from scipy import signal
import pyloudnorm as pyln
from ..logger import setup_logger
import ffmpeg
import librosa

logger = setup_logger(__name__)


def extract_audio(video_path) -> mp.AudioClip:
    video = mp.VideoFileClip(video_path)
    audio = video.audio
    return audio


def extract_audio_from_video_ffmpeg(video_path, output_path, temp_dir):

    if output_path is None:
        output_path = create_temporary_file_name_with_extension(temp_dir, 'wav')

    audio_path = create_temporary_file_name_with_extension(temp_dir, 'wav')
    subprocess.run([
        'ffmpeg', '-i', video_path, '-q:a', '0', '-map', '0:a', audio_path
    ])
    return audio_path

def write_to_file(audio: mp.AudioClip, path, filename, extension="mp3"):
    audio.write_audiofile(os.path.join(path, f"{filename}.{extension}"))


def wav_to_numpy(wav_file_path) -> Tuple[int, np.array]:
    a = read(wav_file_path)
    sample_rate = a[0]
    audio_array = np.array(a[1], dtype=float)
    return sample_rate, audio_array


def wav_to_blocks(wav_array: np.ndarray, block_size=882, overlap=441, aggregation_func=np.mean) -> np.ndarray:
    blocks = np.array([])
    array_length = len(wav_array)
    block_amount = math.ceil(array_length / (block_size - overlap))
    for i in range(block_amount):
        block_start = (block_size - overlap) * i
        block_end = min(block_start + block_size, array_length)
        current_block = wav_array[block_start: block_end]
        block_aggregate = aggregation_func(current_block)
        blocks = np.append(blocks, block_aggregate)

    return blocks


def stereo_to_mono(wav_array: np.ndarray):
    # If wav_array is already mono and has one channel, return it
    if wav_array.ndim == 1:
        mono_wav = wav_array
    else:
        mono_wav = wav_array.mean(axis=1)
    return mono_wav


def z_normalization(wav_array: np.ndarray):
    normalized_wav_array = 2. * (wav_array - np.min(wav_array)) / np.ptp(wav_array) - 1
    return normalized_wav_array


def contrast_audio(audio_array: np.ndarray, exponent=2):
    return audio_array ** exponent


def preprocess_audio(audio_file_path: str, to_mono=True, z_normalize=False, normalize=False,
                     high_pass=False, low_pass=False) -> Tuple[int, np.ndarray]:
    samplerate, audio = read(audio_file_path)
    audio_data = np.array(audio, dtype=float)
    if to_mono:
        audio_data = stereo_to_mono(audio_data)
    if z_normalize:
        audio_data = z_normalization(audio_data)
    if normalize:
        audio_data = normalize_audio(audio_data, samplerate)
    if low_pass:
        audio_data = butter_lowpass_filter(audio_data, 5000, samplerate)
    if high_pass:
        audio_data = butter_highpass_filter(audio_data, 1000, samplerate)

    return samplerate, audio_data


# Calculate MSE score between audio samples
def audio_mse_score(audio1, audio2, blocks=False):
    assert len(audio1) == len(audio2)

    if blocks:
        audio1_blocks = wav_to_blocks(audio1, block_size=441, overlap=0)
        audio2_blocks = wav_to_blocks(audio2, block_size=441, overlap=0)
        mse_score = (np.square(audio1_blocks - audio2_blocks)).mean()
    else:
        mse_score = (np.square(audio1 - audio2)).mean()

    return mse_score


# Calculate absolute distance between audio samples
def audio_absolute_distance_score(audio1, audio2, blocks=False):
    assert len(audio1) == len(audio2)

    if blocks:
        audio1_blocks = wav_to_blocks(audio1, block_size=441, overlap=0)
        audio2_blocks = wav_to_blocks(audio2, block_size=441, overlap=0)
        distance_score = (np.abs(audio1_blocks - audio2_blocks)).sum()
    else:
        distance_score = (np.abs(audio1 - audio2)).sum()

    return distance_score


# Compare windows from audio1 to audio2 and find windows that minimize the distance between audio files
def calculate_audio_delay(audio1: np.ndarray, audio2: np.ndarray, sample_rate=44100, verbose=False) -> float:
    audio1_distance_scores = []
    audio2_distance_scores = []

    # Accuracy of 1000th of a second
    window_increment = math.floor(sample_rate / 1000)
    # Sliding window size is len(audio) / window_size_factor
    window_size_factor = 2

    audio1_length = len(audio1)
    window_size_1 = math.floor(audio1_length / window_size_factor)
    windows_amount_1 = math.ceil((audio1_length - window_size_1) / window_increment)

    # We don't know which audio file is delayed compared to the other, so we need to run the analysis both ways,
    # first comparing audio1 window to audio2 start and then comparing audio2 windows to audio1 start
    for i in tqdm(range(windows_amount_1)):
        window_start = window_increment * i
        window_end = min(window_start + window_size_1, audio1_length)
        audio1_window = audio1[window_start: window_end]
        audio2_window = audio2[0: window_size_1]
        mse_score = audio_absolute_distance_score(audio1_window, audio2_window)
        audio1_distance_scores.append(mse_score)

        if verbose and i % math.floor(windows_amount_1 / 100) == 0:
            print(f"{round(safe_division(i, windows_amount_1) * 100, 2)}%")

    audio2_length = len(audio2)
    window_size_2 = math.floor(audio2_length / window_size_factor)
    windows_amount_2 = math.ceil((audio2_length - window_size_2) / window_increment)

    for i in tqdm(range(windows_amount_2)):
        window_start = window_increment * i
        window_end = min(window_start + window_size_2, audio2_length)
        audio1_window = audio1[0: window_size_2]
        audio2_window = audio2[window_start: window_end]
        mse_score = audio_absolute_distance_score(audio1_window, audio2_window)
        audio2_distance_scores.append(mse_score)

        if verbose and i % math.floor(windows_amount_2 / 100) == 0:
            print(f"{round(safe_division(i, windows_amount_2) * 100, 2)}%")

    audio1_distance_scores_np = np.array(audio1_distance_scores)
    audio2_distance_scores_np = np.array(audio2_distance_scores)

    # Minimum score index equals the best audio position and we use the index to calculate the delay
    audio1_lowest_score_arg = np.argmin(audio1_distance_scores_np)
    audio2_lowest_score_arg = np.argmin(audio2_distance_scores_np)

    audio1_lowest_score = np.min(audio1_distance_scores)
    audio2_lowest_score = np.min(audio2_distance_scores)

    # Calculate delay in seconds and return positive delay if audio1 needs to be delayed and negative delay
    # if audio2 needs to be delayed
    if audio1_lowest_score < audio2_lowest_score:
        delay_seconds = (audio1_lowest_score_arg * window_increment) / sample_rate
        if verbose:
            print(f"Audio 1 needs {delay_seconds} second delay")
    else:
        delay_seconds = (audio2_lowest_score_arg * window_increment) / sample_rate * -1
        if verbose:
            print(f"Audio 2 needs {delay_seconds} second delay")

    return delay_seconds


def merge_audio_tracks(audio1: AudioSegment, audio2: AudioSegment):
    merged_audios = audio1.overlay(audio2, position=0)
    return merged_audios


def normalize_audio(data: np.ndarray, samplerate: int, loudness_reduction=-12.0) -> np.ndarray:
    meter = pyln.Meter(samplerate)
    loudness = meter.integrated_loudness(data)
    loudness_normalized_audio = pyln.normalize.loudness(data, loudness, loudness_reduction)
    return loudness_normalized_audio


def butter_lowpass_filter(data: np.ndarray, cutoff: float, samplerate: float, order: int = 5) -> np.ndarray:
    nyq = 0.5 * samplerate
    normal_cutoff = cutoff / nyq
    b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
    y = signal.filtfilt(b, a, data)
    return y


def butter_highpass_filter(data: np.ndarray, cutoff: float, samplerate: float, order: int = 5) -> np.ndarray:
    nyq = 0.5 * samplerate
    normal_cutoff = cutoff / nyq
    b, a = signal.butter(order, normal_cutoff, btype='high', analog=False)
    y = signal.filtfilt(b, a, data)
    return y


def butter_bandpass_filter(data: np.ndarray, lowcut: float, highcut: float, samplerate: float, order: int = 5) -> np.ndarray:
    nyq = 0.5 * samplerate
    low = lowcut / nyq
    high = highcut / nyq
    b, a = signal.butter(order, [low, high], btype='band')
    y = signal.filtfilt(b, a, data)
    return y


def cut_audio_clip(audio_path: str, start_time: float, end_time: float, output_path: Optional[str] = None, temp_dir: Optional[str] = None):
    """
        Cut audio clip with ffmpeg based on start and end time.

        Args:
            audio_path: Path to the audio file to cut
            start_time: Start time of the clip in seconds
            end_time: End time of the clip in seconds
            output_path: Path to save the cut audio file
            temp_dir: Directory to save the cut audio file
    """

    if output_path is None:
        output_path = create_temporary_file_name_with_extension(temp_dir, 'wav')

    audio = AudioSegment.from_file(audio_path)
    audio = audio[start_time * 1000:end_time * 1000]
    audio.export(output_path, format="wav")
    logger.debug(f"Cut audio clip saved to {output_path}")

    return output_path


def spectral_noise_reduction(audio: np.ndarray, sr: int) -> np.ndarray:
    """Remove noise using spectral gating."""
    D = librosa.stft(audio)
    
    noise_profile = np.mean(np.abs(D[:, :sr//2]), axis=1)
    
    D_denoised = D * (np.abs(D) > 2 * noise_profile[:, np.newaxis])
    
    return librosa.istft(D_denoised)


def compress_dynamic_range(audio: np.ndarray, threshold: float, ratio: float) -> np.ndarray:
    """Apply compression to reduce dynamic range."""
    threshold_linear = 10.0 ** (threshold/20.0)
    
    gain_mask = audio > threshold_linear
    gain_reduction = np.zeros_like(audio)
    gain_reduction[gain_mask] = (1.0/ratio - 1.0) * (audio[gain_mask] - threshold_linear)
    
    audio_compressed = audio + gain_reduction
    
    return audio_compressed / np.max(np.abs(audio_compressed))

import moviepy.editor as mp
import os
from scipy.io.wavfile import read
import numpy as np
from typing import Tuple, Optional
import subprocess
from .file_utils import create_temporary_file_name_with_extension
from pydub import AudioSegment
from scipy import signal
import pyloudnorm as pyln
from ..logger import setup_logger
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


def remove_wind_noise(audio: np.ndarray, frame_size: int = 2048, overlap: float = 0.75) -> np.ndarray:
    """Remove wind noise using spectral subtraction.
    
    Args:
        audio: Input audio
        frame_size: Size of FFT frames (default 2048)
        overlap: Overlap between frames (default 0.75)
    
    Returns:
        Processed audio with reduced wind noise
    """
    hop_length = int(frame_size * (1 - overlap))
    frames = librosa.util.frame(audio, frame_length=frame_size, hop_length=hop_length)
    window = np.hanning(frame_size)
    
    processed_frames = []
    for frame in frames.T:
        windowed = frame * window
        fft = np.fft.rfft(windowed)
        magnitude = np.abs(fft)
        phase = np.angle(fft)
        
        # Focus on low frequency range where wind noise typically occurs (0-200 Hz)
        wind_region = magnitude[:int(len(magnitude) * 0.05)]  # First 5% of frequencies
        noise_floor = np.mean(wind_region)
        
        # More conservative gain calculation
        gain = np.ones_like(magnitude)
        
        # Only apply reduction to low frequencies
        low_freq_idx = int(len(magnitude) * 0.1)  # First 10% of frequencies
        gain[:low_freq_idx] = np.maximum(0.3, 1 - (noise_floor / (magnitude[:low_freq_idx] + 1e-10)))
        
        # Smooth transitions
        gain = signal.medfilt(gain, 3)
        
        # Apply gain and reconstruct
        magnitude_clean = magnitude * gain
        fft_clean = magnitude_clean * np.exp(1j * phase)
        frame_clean = np.fft.irfft(fft_clean)
        
        processed_frames.append(frame_clean[:frame_size])
    
    # Overlap-add reconstruction
    output = np.zeros(len(audio))
    for i, frame in enumerate(processed_frames):
        start = i * hop_length
        end = start + frame_size
        if end > len(output):
            break
        output[start:end] += frame
    
    # Normalize but preserve some headroom
    output = 0.95 * (output / np.max(np.abs(output)))
    
    return output


def filter_claps(audio: np.ndarray, sr: int) -> np.ndarray:
    """Filter claps from audio."""
    
    filtered_audio = butter_bandpass_filter(audio, 6500, 8500, sr)

    return filtered_audio
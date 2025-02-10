from typing import Tuple, Optional
from ..logger import setup_logger

logger = setup_logger(__name__)

def determine_start_and_end_time(delay: str, start_time: Optional[float], end_time: Optional[float], duration: float) -> Tuple[float, float]:
    """
    Determine the start and end time for the video based on the delay.
    Start time and end time are based on the left camera video.

    If delay is positive, clips are like this:
    
    |-<delay>|
    |0 -------<left clip>---------- left end_time|
             |0 --------<right clip>-------- right end_time|
             |--<synchronized clip duration>-----|
    -------------------------time------------------------->
            

    If delay is negative, clips are like this:
    |<delay>|
            |0------------<left clip>----------left end_time|
    |0-------------<right clip>-----------right end_time|
            |--------<synchronized clip duration>-------|  
    -------------------------time------------------------->
    
    Args:
        delay: Delay in seconds
        start_time: Start time in seconds (left camera video)
        end_time: End time in seconds (left camera video)
        duration: Duration of the video in seconds
    """
    # We need to cut video and audio according to the game start and end time
    # We need to take to account delay as this will shift our start and end time
    # Assumed that start time and end time is coming from left camera
    if start_time is None and end_time is not None:
        start_time = 0
        if delay > 0:
            # If delay is positive, left camera video is delay sec. ahead of right
            # So we need to subtract delay from end_time
            end_time = end_time - delay
        else:
            end_time = min(duration, end_time)
    elif start_time is not None and end_time is None:
        if delay > 0:
            # If delay is positive, left camera video is delay sec. ahead of right
            # So we need to subtract delay from start_time
            start_time = max(0, start_time - delay)
        else:
            start_time = start_time
        end_time = duration
    else:
        if delay > 0:
            # If delay is positive, left camera video is delay sec. ahead of right
            # So we need to subtract delay from start_time and end_time
            start_time = max(0, start_time - delay)
            end_time = end_time - delay
        else:
            start_time = start_time
            end_time = min(duration, end_time)

    return start_time, end_time

def determine_start_and_end_time_sample(start_time: Optional[float], end_time: Optional[float]) -> Tuple[float, float]:
    """
    Determine the start and end times if making a sample video.
    """
    if start_time is None:
        start_time = 0
        logger.info("No start time provided, using start of video")
    else:
        start_time = start_time

    # Set end_time to start_time + 60 seconds
    end_time = start_time + 60.0

    return start_time, end_time
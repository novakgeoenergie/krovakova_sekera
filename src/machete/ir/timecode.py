import math
import uuid
from fractions import Fraction

PPRO_TICKS_PER_SEC: int = 254_016_000_000

EDIT_RATES: dict[str, Fraction] = {
    "23.976": Fraction(24000, 1001),
    "24": Fraction(24, 1),
    "25": Fraction(25, 1),
    "29.97": Fraction(30000, 1001),
    "30": Fraction(30, 1),
    "50": Fraction(50, 1),
    "59.94": Fraction(60000, 1001),
    "60": Fraction(60, 1),
}


def ticks_to_frames(ticks: int, edit_rate: Fraction) -> int:
    """Exact rational conversion from Premiere ticks to integer frame number."""
    val = Fraction(ticks, PPRO_TICKS_PER_SEC) * edit_rate + Fraction(1, 2)
    return math.floor(val)


def frames_to_ticks(frames: int, edit_rate: Fraction) -> int:
    """Exact rational conversion from integer frame number to Premiere ticks."""
    val = (Fraction(frames, 1) / edit_rate) * PPRO_TICKS_PER_SEC + Fraction(1, 2)
    return math.floor(val)


def samples_to_frames(samples: int, sample_rate: int, edit_rate: Fraction) -> int:
    """Exact rational conversion from audio samples to integer frame number."""
    val = (Fraction(samples, sample_rate) * edit_rate) + Fraction(1, 2)
    return math.floor(val)


def frames_to_samples(frames: int, sample_rate: int, edit_rate: Fraction) -> int:
    """Exact rational conversion from integer frame number to audio samples."""
    val = (Fraction(frames, 1) / edit_rate) * sample_rate + Fraction(1, 2)
    return math.floor(val)


def frames_to_smpte_tc(frames: int, edit_rate: Fraction, drop_frame: bool = False) -> str:
    """Convert frame number to SMPTE timecode (HH:MM:SS:FF or HH:MM:SS;FF for drop-frame)."""
    nominal_fps = math.floor(edit_rate + Fraction(1, 2))

    if drop_frame:
        drop_frames = 4 if nominal_fps >= 50 else 2
        frames_per_minute = nominal_fps * 60 - drop_frames
        frames_per_10min = nominal_fps * 60 * 10 - drop_frames * 9

        d10 = frames // frames_per_10min
        m10 = frames % frames_per_10min

        if m10 < nominal_fps * 60:
            minute_in_block = 0
            frame_in_minute = m10
            frame_number = frame_in_minute
        else:
            rem = m10 - nominal_fps * 60
            minute_in_block = 1 + rem // frames_per_minute
            frame_in_minute = rem % frames_per_minute
            frame_number = frame_in_minute + drop_frames

        total_minutes = d10 * 10 + minute_in_block
        hours = total_minutes // 60
        minutes = total_minutes % 60
        seconds = frame_number // nominal_fps
        ff = frame_number % nominal_fps
        delimiter = ";"
    else:
        total_seconds = frames // nominal_fps
        ff = frames % nominal_fps
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        delimiter = ":"

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{delimiter}{ff:02d}"


def deterministic_mob_uid(seed_str: str) -> uuid.UUID:
    """Generate deterministic UUIDv5 for AAF MobID relinking."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"krovak.machete:{seed_str}")

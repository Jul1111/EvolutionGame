TICKS_PER_SECOND = 60   # Simulation ticks per simulated second: the time unit of the displays


def format_time(ticks):
    """Convert a number of ticks to a mm:ss string (simulated time)."""
    seconds = ticks / TICKS_PER_SECOND
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{seconds:02d}"

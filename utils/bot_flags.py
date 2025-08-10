IS_READY = False
PAUSED = False


def set_ready(value: bool) -> None:
    global IS_READY
    IS_READY = value


def set_paused(value: bool) -> None:
    global PAUSED
    PAUSED = value

from utils.state_manager import load_state
from notifications.notifier import kirim_notifikasi_telegram


def handle_resume(resume_flag: bool, notif_resume: bool) -> list:
    """Load saved positions and optionally send Telegram notification.

    Returns the list of active positions loaded from state.
    """
    if not resume_flag:
        return []

    active = load_state()
    if active and notif_resume:
        kirim_notifikasi_telegram(f"🔄 Bot resumed with {len(active)} active positions")
    return active

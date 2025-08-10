import pandas as pd
from datetime import datetime, timezone
from risk_management.circuit_breaker import CircuitBreaker
from utils import bot_flags


def test_circuit_breaker_trigger(monkeypatch):
    df = pd.DataFrame({
        'entry_time': [datetime.now(timezone.utc).isoformat()],
        'pnl': [-60.0],
    })
    monkeypatch.setattr('risk_management.circuit_breaker.get_all_trades', lambda: df)
    monkeypatch.setattr('risk_management.circuit_breaker.kirim_notifikasi_telegram', lambda msg: None)
    bot_flags.set_paused(False)
    cb = CircuitBreaker(max_drawdown=50, max_losses=2)
    triggered = cb.check()
    assert triggered is True
    assert bot_flags.PAUSED is True

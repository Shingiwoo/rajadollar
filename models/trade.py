from dataclasses import dataclass

@dataclass
class Trade:
    symbol: str
    side: str
    entry_time: str
    entry_price: float
    size: float
    sl: float
    tp: float
    trailing_sl: float | None = None
    pnl: float | None = None
    exit_time: str | None = None
    exit_price: float | None = None

    def to_dict(self):
        return self.__dict__

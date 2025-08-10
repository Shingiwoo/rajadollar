"""Aplikasi FastAPI dasar untuk mengendalikan bot trading."""
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()

API_TOKEN = "ubah_token_ini"


def _validate_token(token: str) -> None:
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Token tidak valid")


@app.post("/start_bot")
def start_bot(token: str = Header(...)):
    _validate_token(token)
    # TODO: hubungkan ke utils/trading_controller.start_bot
    return {"status": "started"}


@app.post("/stop_bot")
def stop_bot(token: str = Header(...)):
    _validate_token(token)
    # TODO: hubungkan ke utils/trading_controller.stop_bot
    return {"status": "stopped"}


@app.get("/status")
def status():
    # TODO: kembalikan status bot sebenarnya
    return {"status": "ok"}


@app.post("/backtest")
def backtest(token: str = Header(...)):
    _validate_token(token)
    # TODO: panggil modul backtesting
    return {"result": "pending"}


@app.get("/trades")
def trades():
    # TODO: ambil daftar transaksi dari DB
    return []


@app.get("/signals")
def signals():
    # TODO: ambil sinyal terbaru dari controller
    return []

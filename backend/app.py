"""Aplikasi FastAPI untuk mengendalikan bot trading dan streaming event."""
import asyncio
import json
import os
from typing import Dict, Any, Set

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect

from utils import trading_controller
from database import signal_logger, sqlite_logger
from execution.ws_signal_listener import get_top_reasons

app = FastAPI()

API_TOKEN = "ubah_token_ini"
CONFIG_PATH = "config/strategy_params.json"

bot_state: Dict[str, Any] = {"running": False, "strategy": None, "handles": None}
strategy_params: Dict[str, Any] = {}
clients: Set[WebSocket] = set()
broadcast_queue: asyncio.Queue = asyncio.Queue()


def _validate_token(token: str) -> None:
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Token tidak valid")


def publish_event(event: Dict[str, Any]) -> None:
    try:
        broadcast_queue.put_nowait(event)
    except Exception:
        pass


@app.on_event("startup")
async def _startup() -> None:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                data = json.load(f)
                strategy_params.update(data)
        except Exception:
            pass
    asyncio.create_task(_broadcaster())


async def _broadcaster() -> None:
    while True:
        event = await broadcast_queue.get()
        dead = []
        for ws in clients:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            clients.discard(ws)


@app.post("/start_bot")
def start_bot(token: str = Header(...)):
    _validate_token(token)
    if bot_state["running"]:
        return {"status": "already_running"}
    cfg = {
        "client": None,
        "symbols": list(strategy_params.keys()),
        "strategy_params": strategy_params,
        "capital": 1000.0,
        "leverage": 1,
        "risk_pct": 1.0,
        "max_pos": 1,
        "max_sym": 1,
        "max_slip": 0.5,
    }
    handles = trading_controller.start_bot(cfg, publisher=publish_event)
    bot_state["handles"] = handles
    bot_state["running"] = bool(handles)
    bot_state["strategy"] = "ScalpingStrategy" if handles else None
    return {"status": "started" if handles else "failed"}


@app.post("/stop_bot")
def stop_bot(token: str = Header(...)):
    _validate_token(token)
    trading_controller.stop_bot(bot_state.get("handles") or {})
    bot_state["handles"] = None
    bot_state["running"] = False
    bot_state["strategy"] = None
    return {"status": "stopped"}


@app.post("/risk/cut")
def risk_cut(token: str = Header(...)):
    _validate_token(token)
    trading_controller.cut_all(bot_state.get("handles") or {})
    return {"status": "cut"}


@app.get("/status")
def status():
    return {
        "running": bot_state["running"],
        "strategy": bot_state["strategy"],
        "top_reasons": get_top_reasons(),
    }


@app.post("/backtest")
def backtest(data: Dict[str, Any], token: str = Header(...)):
    _validate_token(token)
    return {"result": "pending"}


@app.get("/config/strategy_params")
def get_strategy_params():
    return strategy_params


@app.put("/config/strategy_params")
def put_strategy_params(params: Dict[str, Any], token: str = Header(...)):
    _validate_token(token)
    strategy_params.clear()
    strategy_params.update(params)
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(strategy_params, f)
    return {"status": "saved"}


@app.get("/signals/recent")
def signals_recent():
    df = signal_logger.get_signals_recent(20)
    return df.to_dict(orient="records")


@app.get("/trades/recent")
def trades_recent():
    df = sqlite_logger.get_all_trades()
    return df.head(100).to_dict(orient="records")


@app.websocket("/ws/stream")
async def ws_stream(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        clients.discard(ws)

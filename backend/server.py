import asyncio, json, sys, os, time, httpx, websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from engine.matrix_engine import TIMEFRAMES, aggregate_bars, evaluate_120_factors

app = FastAPI(title="ORBIT AI v28.0 Supreme Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

BINANCE_FAPI = "https://fapi.binance.com"
BINANCE_WS = "wss://fstream.binance.com/market/stream"
STATE = {"symbols": {}, "cooldowns": {}, "signals": [], "clients": set()}

async def broadcast(payload: dict):
    dead = set()
    msg = json.dumps(payload)
    for ws in STATE["clients"]:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    STATE["clients"] -= dead

async def warmup_symbols(top_n: int = 70):
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{BINANCE_FAPI}/fapi/v1/ticker/24hr")
        tickers = resp.json()
        usdt_pairs = [x for x in tickers if x["symbol"].endswith("USDT") and "_" not in x["symbol"]]
        usdt_pairs.sort(key=lambda x: float(x["quoteVolume"]), reverse=True)
        for item in usdt_pairs[:top_n]:
            STATE["symbols"][item["symbol"]] = {"bars1m": [], "last": float(item["lastPrice"])}

        async def fetch_kline(sym: str):
            try:
                r = await client.get(f"{BINANCE_FAPI}/fapi/v1/klines", params={"symbol": sym, "interval": "1m", "limit": 80})
                STATE["symbols"][sym]["bars1m"] = [
                    {"t": x[0], "o": float(x[1]), "h": float(x[2]), "l": float(x[3]), "c": float(x[4]), "v": float(x[5]), "V": float(x[9])}
                    for x in r.json()
                ]
            except Exception:
                pass
        await asyncio.gather(*(fetch_kline(s) for s in STATE["symbols"]))

async def process_kline(sym: str, k: dict):
    rec = STATE["symbols"].get(sym)
    if not rec:
        return
    bars = rec["bars1m"]
    bar = {"t": k["t"], "o": float(k["o"]), "h": float(k["h"]), "l": float(k["l"]), "c": float(k["c"]), "v": float(k["v"]), "V": float(k["V"])}
    if bars and bars[-1]["t"] == bar["t"]:
        bars[-1] = bar
    else:
        bars.append(bar)
        if len(bars) > 700:
            bars.pop(0)
    rec["last"] = bar["c"]
    now_ms = int(time.time() * 1000)

    for tf, mult in TIMEFRAMES:
        res = evaluate_120_factors(aggregate_bars(bars, mult), tf)
        if not res:
            continue
        key = f"{sym}|{tf}|{res['dir']}"
        cool_ms = 8000 if mult <= 5 else (30000 if mult <= 60 else 120000)
        if now_ms - STATE["cooldowns"].get(key, 0) < cool_ms:
            continue
        STATE["cooldowns"][key] = now_ms
        sig = {
            "id": f"{sym}-{tf}-{now_ms}", "sym": sym, "tf": tf, "dir": res["dir"],
            "px": res["entry"], "sl": res["sl"], "tp1": res["tp1"], "tp2": res["tp2"], "tp3": res["tp3"],
            "score": res["score"], "probWin": res["probWin"], "factors": res["factors"],
            "state": "OPEN", "R": 0.0, "ts": now_ms,
        }
        STATE["signals"].insert(0, sig)
        STATE["signals"] = STATE["signals"][:300]
        await broadcast({"type": "NEW_SIGNAL", "signal": sig})

async def binance_stream_loop():
    await warmup_symbols(70)
    streams = "/".join(f"{s.lower()}@kline_1m" for s in STATE["symbols"])
    url = f"{BINANCE_WS}?streams={streams}"
    while True:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                async for raw in ws:
                    data = json.loads(raw).get("data", {})
                    if data.get("e") == "kline" and "k" in data:
                        await process_kline(data["s"], data["k"])
        except Exception:
            await asyncio.sleep(3)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(binance_stream_loop())

@app.get("/api/health")
def health():
    return {"status": "ONLINE", "symbols_tracked": len(STATE["symbols"]), "cached_signals": len(STATE["signals"])}

@app.get("/api/signals")
def get_signals():
    return {"signals": STATE["signals"]}

@app.websocket("/ws/signals")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    STATE["clients"].add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        STATE["clients"].discard(ws)

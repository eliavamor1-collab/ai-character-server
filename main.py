"""
AI Character — lightweight Perchance proxy.

Strategy (fits Render free 512MB most of the time):
  - camoufox (heavy Firefox) runs ONLY to solve Cloudflare and grab a
    cf_clearance cookie + userKey, then is closed immediately.
  - hrequests (light) handles all generate calls using that cookie.
  - When the cookie/userKey expires, we refresh via camoufox again.

Endpoints:
  GET  /health          -> keep-alive
  POST /generate        -> { "prompt": "...", "stopSequences": [...] } -> { "text": "..." }
"""

import os
import random
import threading
import time
import urllib.request

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = "https://text-generation.perchance.org"

# Shared session state (protected by a lock).
_lock = threading.Lock()
_state = {"cf_clearance": None, "user_agent": None, "user_key": None}


class GenerateRequest(BaseModel):
    prompt: str
    stopSequences: list[str] | None = None


def _refresh_clearance():
    """Run camoufox briefly to solve Cloudflare and capture cookie + userKey."""
    from camoufox.sync_api import Camoufox

    print("[proxy] refreshing clearance via camoufox...", flush=True)
    cf = None
    ua = None
    key = None
    # Run headed (headless=False) behind Xvfb — pure headless crashes in Docker.
    # Disable Firefox's content sandbox: gVisor (Cloud Run) blocks the syscalls
    # it relies on, which otherwise triggers mozalloc_abort.
    prefs = {
        "security.sandbox.content.level": 0,
        "security.sandbox.gpu.level": 0,
        "media.gmp.decoder.enabled": False,
        "layers.acceleration.disabled": True,
        "gfx.webrender.software": True,
    }
    with Camoufox(headless=False, firefox_user_prefs=prefs) as browser:
        page = browser.new_page()
        page.goto(f"{BASE}/embed", timeout=60000)
        time.sleep(18)
        ua = page.evaluate("() => navigator.userAgent")
        for c in page.context.cookies():
            if c["name"] == "cf_clearance":
                cf = c["value"]
        body = page.evaluate(
            "async () => { var r = await fetch('%s/api/verifyUser?thread=0&__cacheBust=' + Math.random(), {credentials:'include'}); return await r.text(); }"
            % BASE
        )
        idx = body.find('"userKey":"')
        if idx != -1:
            s = idx + len('"userKey":"')
            e = body.find('"', s)
            key = body[s:e]
    _state["cf_clearance"] = cf
    _state["user_agent"] = ua
    _state["user_key"] = key
    print(f"[proxy] refreshed: key={str(key)[:12]} cf={'yes' if cf else 'no'}", flush=True)
    return key is not None


def _make_session():
    import hrequests

    s = hrequests.Session(browser="firefox")
    if _state["cf_clearance"]:
        s.cookies.set("cf_clearance", _state["cf_clearance"], domain=".perchance.org")
    return s


def _do_generate(prompt: str, stop):
    """Try a generate call with current state. Returns text or raises."""
    session = _make_session()
    req_id = "aiTextCompletion" + str(random.randint(0, 2**30))
    cb = random.random()
    url = (
        f"{BASE}/api/generate?userKey={_state['user_key']}"
        f"&requestId={req_id}&__cacheBust={cb}"
    )
    payload = {
        "generatorName": "ai-text-generator",
        "instruction": prompt,
        "instructionTokenCount": 1,
        "startWith": "",
        "startWithTokenCount": 1,
        "stopSequences": stop or [],
    }
    headers = {
        "User-Agent": _state["user_agent"] or "",
        "Content-Type": "application/json",
    }
    r = session.post(url, json=payload, headers=headers, timeout=45)
    if r.status_code != 200:
        raise RuntimeError(f"generate HTTP {r.status_code}: {r.text[:120]}")
    # Parse the t:"..." stream lines into text.
    import json as _json

    out = []
    for line in r.text.splitlines():
        line = line.strip()
        if line.startswith("t:"):
            try:
                out.append(_json.loads(line[2:]))
            except Exception:
                pass
        elif line.startswith("data:"):
            break
    return "".join(out)


@app.get("/")
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate")
def generate(req: GenerateRequest):
    with _lock:
        try:
            # Ensure we have a userKey.
            if not _state["user_key"]:
                _refresh_clearance()
            try:
                text = _do_generate(req.prompt, req.stopSequences)
                if text.strip():
                    return {"text": text}
                # empty — refresh once and retry
                raise RuntimeError("empty response")
            except Exception as first:
                print(f"[proxy] first attempt failed: {first}; refreshing...", flush=True)
                _refresh_clearance()
                text = _do_generate(req.prompt, req.stopSequences)
                return {"text": text}
        except Exception as e:
            print(f"[proxy] ERROR: {e}", flush=True)
            return {"error": str(e)}


def _keep_alive():
    host = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("SELF_URL")
    if not host:
        return
    while True:
        time.sleep(600)
        try:
            urllib.request.urlopen(f"{host}/health", timeout=15)
        except Exception:
            pass


@app.on_event("startup")
def _startup():
    threading.Thread(target=_keep_alive, daemon=True).start()

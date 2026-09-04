#!/usr/bin/env python3
"""BODY OS coach server — static files + LLM coach API + conversation memory.

Endpoints:
  GET  /*            -> static app files (same as before)
  POST /api/ask      -> {q, stats?} -> {a, model, ts}   (LLM coach, falls back to glm->qwen)
  GET  /api/memory   -> {conversations, topics, summary} (the map of all coach chats)
  GET  /api/health   -> {ok, models}

Memory: every Q&A appended to coach-memory/conversations.jsonl; a rolling
summary + topic map rebuilt each call and injected into the next prompt,
so the coach remembers everything you've ever asked it.
"""
import json, os, re, threading, time, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

API_BASE = os.environ.get("BAI_BASE", "https://api.b.ai/v1")
API_KEY  = os.environ.get("BAI_API_KEY", "")
MODELS   = ["glm-5.3-flash", "qwen3.8-flash"]        # both at reasoning effort=max (per user request)
REASON   = os.environ.get("COACH_REASONING", "max")
TOKEN    = os.environ.get("COACH_TOKEN", "bodyos-local")  # cheap abuse gate
MEM_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coach-memory")
CONVO    = os.path.join(MEM_DIR, "conversations.jsonl")
SUMMARY  = os.path.join(MEM_DIR, "summary.md")
TOPICS   = os.path.join(MEM_DIR, "topics.json")
PLAN_MD  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "body", "PLAN-HOME-MAX.md")
LOCK     = threading.Lock()

TOPIC_KEYS = {
  "belly fat": ["belly","stomach","gut","waist"],
  "abs": ["abs","six pack","six-pack","crack"],
  "protein": ["protein","whey","dal","paneer","soy","eggs"],
  "soreness/pain": ["sore","ache","pain","hurt","injur"],
  "plateau": ["plateau","stall","not losing","no change","stuck"],
  "sleep": ["sleep","tired","insomnia"],
  "diet/food": ["eat","food","diet","hungry","calorie","snack","biryani","pizza","cheat","alcohol"],
  "training": ["lift","workout","squat","bench","deadlift","pull-up","pullup","reps","sets","cardio","steps","walk","run"],
  "gym vs home": ["gym","barbell","dumbbell","equipment","membership"],
  "motivation": ["quit","motivat","lazy","bored","give up","missed","skip"],
  "timeline": ["when","how long","result","progress","timeline","nov","december"],
}

def load_plan():
    try:
        with open(PLAN_MD) as f: return f.read()[:9000]
    except Exception: return "Plan: 13wk recomp, 1850kcal wk/2000 refeed, 170g protein, 5d DB/band split, deload wk7+12."

def recent(n=12):
    if not os.path.exists(CONVO): return []
    with open(CONVO) as f:
        lines = f.readlines()
    out = []
    for ln in lines[-n:]:
        try: out.append(json.loads(ln))
        except Exception: pass
    return out

def topic_of(q):
    ql = q.lower()
    hits = [t for t, keys in TOPIC_KEYS.items() if any(k in ql for k in keys)]
    return hits or ["general"]

def update_topics(q):
    with LOCK:
        t = {}
        if os.path.exists(TOPICS):
            try: t = json.load(open(TOPICS))
            except Exception: t = {}
        for k in topic_of(q): t[k] = t.get(k, 0) + 1
        json.dump(t, open(TOPICS, "w"), indent=1)

def append_memory(entry):
    os.makedirs(MEM_DIR, exist_ok=True)
    with LOCK:
        with open(CONVO, "a") as f: f.write(json.dumps(entry) + "\n")
    update_topics(entry["q"])

def rebuild_summary():
    """Rolling memory doc the LLM sees: topic counts + last 30 Q/A one-liners."""
    if not os.path.exists(CONVO): return ""
    rows = []
    with open(CONVO) as f:
        for ln in f:
            try: rows.append(json.loads(ln))
            except Exception: pass
    topics = json.load(open(TOPICS)) if os.path.exists(TOPICS) else {}
    lines = ["# Coach memory (auto)", "", "## Topics asked about (count)",
             "\n".join(f"- {k}: {v}" for k, v in sorted(topics.items(), key=lambda x: -x[1])) or "- none yet",
             "", "## Recent conversations"]
    for r in rows[-30:]:
        lines.append(f"- [{r['ts'][:10]}] Q: {r['q'][:120]} → A: {r['a'][:160]}")
    txt = "\n".join(lines)
    with LOCK:
        open(SUMMARY, "w").write(txt)
    return txt

def call_llm(model, messages, timeout=45):
    body = {"model": model, "messages": messages, "temperature": 0.6, "max_tokens": 600}
    if REASON: body["reasoning_effort"] = REASON
    req = urllib.request.Request(API_BASE + "/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    try:
        content = (d["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        content = ""
    if not content:
        raise RuntimeError(f"{model} returned empty content")
    return content

def coach_answer(q, stats):
    sys_prompt = (
      "You are the BODY OS coach for a 25y Indian male (178cm, 78kg start, skinny-fat, vegetarian+eggs, "
      "dumbbells+bands at home, goal: belly fat gone + muscle + abs by Nov 30 2026). "
      "Rules: answer ONLY from the plan below and standard exercise/nutrition science. Be direct, warm, specific, "
      "max 120 words, no lists unless asked, reference his actual logged numbers when given. "
      "If asked something outside fitness/nutrition/recovery, say it's outside the chart and suggest the relevant Life OS chart.\n\n"
      "=== THE PLAN ===\n" + load_plan() + "\n\n=== YOUR MEMORY OF PAST CHATS ===\n" + rebuild_summary()
    )
    msgs = [{"role": "system", "content": sys_prompt}]
    for r in recent(6):
        msgs.append({"role": "user", "content": r["q"]})
        msgs.append({"role": "assistant", "content": r["a"]})
    user = q if not stats else f"{q}\n(his today: {stats})"
    msgs.append({"role": "user", "content": user})
    used, errs = None, []
    for attempt in range(2):
        for m in MODELS:
            try:
                ans = call_llm(m, msgs); used = m; return ans, used, None
            except Exception as e:
                errs.append(f"{m}: {e}")
        if attempt == 0: time.sleep(6)   # bai rate-limit is per-minute; one backoff retry
    return None, None, " | ".join(errs)

class H(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/api/health"):
            return self._json(200, {"ok": True, "models": MODELS, "memory": os.path.exists(CONVO)})
        if self.path.startswith("/api/memory"):
            rows = recent(10**6)
            return self._json(200, {"conversations": rows, "topics": json.load(open(TOPICS)) if os.path.exists(TOPICS) else {}, "summary": rebuild_summary()})
        return super().do_GET()

    def do_POST(self):
        if not self.path.startswith("/api/ask"): return self._json(404, {"error": "not found"})
        if self.headers.get("X-Coach-Token") != TOKEN: return self._json(401, {"error": "bad token"})
        try:
            n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}")
        except Exception: return self._json(400, {"error": "bad json"})
        q = str(body.get("q", ""))[:600].strip()
        if not q: return self._json(400, {"error": "empty"})
        stats = str(body.get("stats", ""))[:1400]
        t0 = time.time()
        ans, model, err = coach_answer(q, stats)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        if ans is None:
            return self._json(502, {"error": err or "all models failed", "ts": ts})
        append_memory({"ts": ts, "q": q, "a": ans, "model": model, "topics": topic_of(q), "ms": int((time.time()-t0)*1000)})
        return self._json(200, {"a": ans, "model": model, "ts": ts})

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    port = int(os.environ.get("BODYOS_PORT", "8790"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"BODY OS coach server on :{port} (static + /api/ask + /api/memory)", flush=True)
    srv.serve_forever()

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
import json, os, re, threading, time, urllib.request, urllib.error, urllib.parse
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

def call_llm(model, messages, timeout=45, temp=0.6, maxtok=600):
    body = {"model": model, "messages": messages, "temperature": temp, "max_tokens": maxtok}
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

# ---------- FOOD SCAN (vision) ----------
SCAN_PROMPT = (
  "You are a precision nutrition vision engine. Analyze the food image and return STRICT JSON only — "
  "no markdown, no prose outside the JSON object.\n\n"
  "MODE DETECTION: if the image shows a packaged product (especially a nutrition label/ingredients panel), "
  "kind='packet': READ THE LABEL DIGITS EXACTLY — do not guess from the brand. Compute kcal/protein for the "
  "portion actually visible or stated (per 100g × grams eaten). If no label is legible, say so in warnings and "
  "estimate from product identity with confidence<=0.5.\n"
  "If it shows prepared food on a plate/bowl, kind='plate': identify each component, estimate its cooked weight "
  "in grams from visual cues (plate size, spoon, hand if present), then kcal from standard food-composition "
  "values (USDA/IFCT/NIN). Indian vegetarian dishes: use realistic ghee/oil amounts — cooked dishes carry hidden fat.\n"
  "If both, kind='mixed'.\n\n"
  "ACCURACY RULES: kcal = grams × per-100g value, computed, not vibes. Protein to 1 decimal. "
  "confidence per item: 0.9+ label read directly, 0.7-0.9 clear familiar food, <0.7 ambiguous — never hide uncertainty. "
  "If the image is not food, return {\"kind\":\"not_food\",\"items\":[],\"total_kcal\":0,\"total_protein\":0,\"warnings\":[\"not food\"]}.\n\n"
  "SCHEMA: {\"kind\":\"packet|plate|mixed|not_food\",\"items\":[{\"name\":\"\",\"qty_g\":int,\"kcal\":num,\"protein_g\":num,\"carbs_g\":num,\"fat_g\":num,\"confidence\":0-1,\"basis\":\"label|standard-table|visual-estimate\"}],\"total_kcal\":num,\"total_protein\":num,\"total_carbs\":num,\"total_fat\":num,\"warnings\":[\"\"],\"label_text\":\"exact label numbers if read, else empty\"}"
)

def scan_image(img_data_url, hint=""):
    msgs = [{"role": "system", "content": SCAN_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": ("Context from user: " + hint[:200]) if hint else "Analyze this food image."},
                {"type": "image_url", "image_url": {"url": img_data_url[:3_500_000]}}]}]
    last_err = None
    for attempt in range(2):
        for m in ["glm-5.3-flash", "qwen3.8-flash"]:
            try:
                raw = call_llm(m, msgs, timeout=90, temp=0.1, maxtok=900)
                s = raw.find("{"); e = raw.rfind("}")
                if s < 0 or e < 0: raise RuntimeError("no JSON in response")
                d = json.loads(raw[s:e+1])
                if not isinstance(d.get("items"), list): raise RuntimeError("missing items")
                d["model"] = m
                return d, None
            except Exception as ex:
                last_err = f"{m}: {ex}"
        if attempt == 0: time.sleep(6)
    return None, last_err

# ---------- BARCODE LOOKUP (Open Food Facts, free, no key) ----------
def off_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "BODY-OS-PWA/1.0 (personal use)"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read())

def barcode_lookup(code):
    """Exact barcode -> OFF product nutriments per 100g. status 0 = not in DB."""
    if not re.fullmatch(r"\d{8,14}", code or ""): return None, "invalid barcode"
    try:
        d = off_get(f"https://world.openfoodfacts.org/api/v2/product/{code}.json?fields=product_name,nutriments,serving_quantity,quantity,brands")
    except Exception as e:
        return None, f"OFF lookup failed: {e}"
    if not d.get("status"): return None, "not in Open Food Facts"
    p = d.get("product") or {}
    n = p.get("nutriments") or {}
    kcal = n.get("energy-kcal_100g")
    if kcal is None: return None, "in DB but no kcal data"
    return {"name": p.get("product_name") or code, "brands": p.get("brands") or "",
            "per100": {"kcal": kcal, "p": n.get("proteins_100g") or 0,
                       "c": n.get("carbohydrates_100g") or 0, "f": n.get("fat_100g") or 0},
            "serving_g": p.get("serving_quantity") or p.get("quantity") or None}, None

def off_search(term):
    try:
        d = off_get("https://world.openfoodfacts.org/cgi/search.pl?search_terms=" + urllib.parse.quote(term) +
                    "&search_simple=1&action=process&json=1&page_size=8&fields=code,product_name,brands,nutriments,serving_quantity")
    except Exception as e:
        return None, f"OFF search failed: {e}"
    out = []
    for p in d.get("products") or []:
        n = p.get("nutriments") or {}
        if n.get("energy-kcal_100g") is None: continue
        out.append({"code": p.get("code"), "name": p.get("product_name") or "", "brands": p.get("brands") or "",
                    "per100": {"kcal": n["energy-kcal_100g"], "p": n.get("proteins_100g") or 0,
                               "c": n.get("carbohydrates_100g") or 0, "f": n.get("fat_100g") or 0}})
    return out, None


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

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Security-Policy", "frame-ancestors *")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/health"):
            return self._json(200, {"ok": True, "models": MODELS, "memory": os.path.exists(CONVO)})
        if self.path.startswith("/api/barcode"):
            from urllib.parse import urlparse, parse_qs
            code = (parse_qs(urlparse(self.path).query).get("code") or [""])[0]
            res, err = barcode_lookup(code)
            return self._json(200 if res else 404, res or {"error": err})
        if self.path.startswith("/api/foodsearch"):
            from urllib.parse import urlparse, parse_qs
            q = (parse_qs(urlparse(self.path).query).get("q") or [""])[0]
            if len(q) < 3: return self._json(400, {"error": "query too short"})
            res, err = off_search(q)
            return self._json(200 if res is not None else 502, {"results": res} if res is not None else {"error": err})
        if self.path.startswith("/api/memory"):
            rows = recent(10**6)
            return self._json(200, {"conversations": rows, "topics": json.load(open(TOPICS)) if os.path.exists(TOPICS) else {}, "summary": rebuild_summary()})
        return super().do_GET()

    def do_POST(self):
        if self.headers.get("X-Coach-Token") != TOKEN: return self._json(401, {"error": "bad token"})
        if self.path.startswith("/api/scan"):
            try:
                n = int(self.headers.get("Content-Length", 0))
                if n > 6_000_000: return self._json(413, {"error": "image too large (max ~4MB)"})
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception: return self._json(400, {"error": "bad json"})
            img = str(body.get("image", ""))
            if not img.startswith("data:image/"): return self._json(400, {"error": "image must be a data:image/* URL"})
            t0 = time.time()
            res, err = scan_image(img, str(body.get("hint", "")))
            if res is None: return self._json(502, {"error": err or "scan failed"})
            res["ms"] = int((time.time() - t0) * 1000)
            return self._json(200, res)
        if not self.path.startswith("/api/ask"): return self._json(404, {"error": "not found"})
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

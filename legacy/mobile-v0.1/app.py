
import asyncio
import json
import time
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "lfm-thinking"
OPENCLAW = "/home/ubuntu/.npm-global/bin/openclaw"
OPENCLAW_AGENT = "main"

app = FastAPI(title="Mobile AI", docs_url=None, redoc_url=None)


class Message(BaseModel):
    role: str
    content: str


class FastRequest(BaseModel):
    messages: list[Message]


class AgentRequest(BaseModel):
    message: str
    session_key: str = Field(default_factory=lambda: "mobile-" + uuid.uuid4().hex[:24])


def visible_text(raw: str) -> str:
    # Retire les blocs <think>...</think> lorsqu'ils sont complets.
    out = raw
    while True:
        start = out.find("<think>")
        if start == -1:
            break
        end = out.find("</think>", start + 7)
        if end == -1:
            return out[:start]
        out = out[:start] + out[end + 8:]
    return out.strip()


@app.get("/api/status")
async def status():
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get("http://127.0.0.1:8080/health")
            llama_ok = r.is_success
    except Exception:
        llama_ok = False
    return {"ok": True, "llama": llama_ok}


@app.post("/api/chat/fast")
async def chat_fast(req: FastRequest):
    messages = [
        {
            "role": "system",
            "content": "Tu es un assistant utile. Réponds en français sauf demande contraire. Sois clair et concis."
        }
    ] + [m.model_dump() for m in req.messages]

    async def generate():
        accumulated = ""
        shown_len = 0
        body = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.05,
            "max_tokens": 1024,
            "stream": True,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(600, connect=5)) as client:
                async with client.stream("POST", LLAMA_URL, json=body) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            data = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        choices = data.get("choices") or []
                        if not choices:
                            continue
                        delta = choices[0].get("delta") or {}
                        piece = delta.get("content") or ""
                        if not piece:
                            continue
                        accumulated += piece
                        visible = visible_text(accumulated)
                        if len(visible) > shown_len:
                            chunk = visible[shown_len:]
                            shown_len = len(visible)
                            yield chunk
        except Exception as exc:
            yield f"\n\n[Erreur: {exc}]"

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


@app.post("/api/chat/agent")
async def chat_agent(req: AgentRequest):
    if not Path(OPENCLAW).exists():
        raise HTTPException(500, "OpenClaw introuvable sur le serveur.")

    safe_session = "".join(
        c for c in req.session_key if c.isalnum() or c in "-_"
    )[:80] or ("mobile-" + uuid.uuid4().hex[:24])

    started = time.perf_counter()
    proc = await asyncio.create_subprocess_exec(
        OPENCLAW,
        "agent",
        "--agent", OPENCLAW_AGENT,
        "--session-key", safe_session,
        "--message", req.message,
        "--timeout", "900",
        "--json",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=930)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise HTTPException(504, "OpenClaw a dépassé le délai maximum.")

    stdout = stdout.decode("utf-8", errors="replace").strip()
    stderr = stderr.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        raise HTTPException(500, stderr or stdout or "Erreur OpenClaw")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        start = stdout.find("{")
        end = stdout.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(stdout[start:end+1])
        else:
            raise HTTPException(500, "Sortie OpenClaw invalide.")

    def extract(obj):
        if isinstance(obj, dict):
            payloads = obj.get("payloads")
            if isinstance(payloads, list):
                texts = [str(x.get("text")) for x in payloads if isinstance(x, dict) and x.get("text")]
                if texts:
                    return "\n".join(texts)
            for key in ("final", "text", "content", "reply", "message"):
                val = obj.get(key)
                if isinstance(val, str) and val.strip():
                    return val
            for val in obj.values():
                found = extract(val)
                if found:
                    return found
        if isinstance(obj, list):
            for val in obj:
                found = extract(val)
                if found:
                    return found
        return None

    text = extract(data) or "(OpenClaw a terminé sans réponse textuelle.)"
    return {"text": text, "seconds": round(time.perf_counter() - started, 1)}


INDEX = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#111318">
<title>Mon IA</title>
<style>
:root{color-scheme:dark;--bg:#0d0f13;--panel:#15181e;--bubble:#1a1e27;--user:#263249;--line:#303747;--text:#eef1f6;--muted:#98a2b3}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;height:100dvh}
.app{display:flex;flex-direction:column;height:100dvh;max-width:900px;margin:auto}
header{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid var(--line);background:var(--panel);position:sticky;top:0}
header b{flex:1}.mode{display:flex;background:#0f1116;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.mode button{border:0;background:transparent;color:var(--muted);padding:9px 12px}.mode button.active{background:#293247;color:white}
#chat{flex:1;overflow:auto;padding:14px}
.msg{padding:12px 14px;border-radius:14px;margin:9px 0;white-space:pre-wrap;line-height:1.45;word-wrap:break-word}
.user{background:var(--user);margin-left:12%}.assistant{background:var(--bubble);margin-right:8%}
.meta{font-size:12px;color:var(--muted);margin-top:6px}
footer{padding:10px 12px calc(10px + env(safe-area-inset-bottom));border-top:1px solid var(--line);background:var(--panel)}
textarea{width:100%;resize:none;min-height:54px;max-height:150px;background:#11141a;color:var(--text);border:1px solid var(--line);border-radius:13px;padding:12px;font:inherit}
.actions{display:flex;align-items:center;margin-top:8px;gap:8px}.status{flex:1;font-size:12px;color:var(--muted)}
button.send{border:1px solid var(--line);border-radius:10px;background:#293247;color:white;padding:10px 16px;font-weight:600}
button:disabled{opacity:.5}.new{border:0;background:transparent;color:var(--muted);font-size:18px;padding:6px}
</style>
</head>
<body>
<div class="app">
<header>
<button class="new" id="newBtn" title="Nouvelle conversation">＋</button>
<b>Mon IA</b>
<div class="mode">
<button id="fastBtn" class="active">⚡ Rapide</button>
<button id="agentBtn">🛠 Agent</button>
</div>
</header>
<main id="chat"></main>
<footer>
<textarea id="input" placeholder="Écris ton message…"></textarea>
<div class="actions">
<div class="status" id="status">Connexion…</div>
<button class="send" id="sendBtn">Envoyer</button>
</div>
</footer>
</div>
<script>
let mode="fast";
let messages=JSON.parse(localStorage.getItem("mobile-ai-messages")||"[]");
let sessionKey=localStorage.getItem("mobile-ai-session")||("mobile-"+crypto.randomUUID().replaceAll("-","").slice(0,24));
localStorage.setItem("mobile-ai-session",sessionKey);

const chat=document.getElementById("chat"), input=document.getElementById("input"), send=document.getElementById("sendBtn");
const statusEl=document.getElementById("status"), fastBtn=document.getElementById("fastBtn"), agentBtn=document.getElementById("agentBtn");

function save(){localStorage.setItem("mobile-ai-messages",JSON.stringify(messages))}
function render(pending=null){
  chat.innerHTML="";
  for(const m of messages){
    const d=document.createElement("div"); d.className="msg "+(m.role==="user"?"user":"assistant"); d.textContent=m.content; chat.appendChild(d);
  }
  if(pending!==null){const d=document.createElement("div");d.className="msg assistant";d.textContent=pending||"…";chat.appendChild(d)}
  chat.scrollTop=chat.scrollHeight;
}
function setMode(m){mode=m;fastBtn.classList.toggle("active",m==="fast");agentBtn.classList.toggle("active",m==="agent");statusEl.textContent=m==="fast"?"Mode rapide":"Mode agent"}
fastBtn.onclick=()=>setMode("fast"); agentBtn.onclick=()=>setMode("agent");
document.getElementById("newBtn").onclick=()=>{messages=[];sessionKey="mobile-"+crypto.randomUUID().replaceAll("-","").slice(0,24);localStorage.setItem("mobile-ai-session",sessionKey);save();render();statusEl.textContent="Nouvelle conversation"};
input.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMessage()}});

async function sendMessage(){
  const text=input.value.trim(); if(!text||send.disabled)return;
  input.value=""; messages.push({role:"user",content:text}); save(); render("");
  send.disabled=true; const start=performance.now();
  try{
    if(mode==="fast"){
      const r=await fetch("/api/chat/fast",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({messages})});
      if(!r.ok)throw new Error(await r.text());
      const reader=r.body.getReader(), dec=new TextDecoder(); let answer="";
      while(true){const {done,value}=await reader.read(); if(done)break; answer+=dec.decode(value,{stream:true}); render(answer); statusEl.textContent="Rapide • "+((performance.now()-start)/1000).toFixed(1)+" s"}
      messages.push({role:"assistant",content:answer.trim()});save();render();
    }else{
      statusEl.textContent="Agent en cours…";
      const r=await fetch("/api/chat/agent",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text,session_key:sessionKey})});
      if(!r.ok)throw new Error(await r.text());
      const data=await r.json(); messages.push({role:"assistant",content:data.text});save();render();statusEl.textContent="Agent • "+data.seconds+" s";
    }
  }catch(e){render("Erreur : "+e.message);statusEl.textContent="Erreur"}
  finally{send.disabled=false;input.focus()}
}
fetch("/api/status").then(r=>r.json()).then(s=>statusEl.textContent=s.llama?"Serveur prêt":"IA indisponible").catch(()=>statusEl.textContent="Serveur indisponible");
render();
</script>
</body></html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return INDEX

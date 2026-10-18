import asyncio
import json
import time
import uuid
from pathlib import Path

import httpx
import psutil
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "lfm-thinking"
OPENCLAW = "/home/ubuntu/.npm-global/bin/openclaw"
OPENCLAW_AGENT = "main"

app = FastAPI(title="Mon IA", docs_url=None, redoc_url=None)


class Message(BaseModel):
    role: str
    content: str


class FastRequest(BaseModel):
    messages: list[Message]


class AgentRequest(BaseModel):
    message: str
    session_key: str = Field(
        default_factory=lambda: "mobile-" + uuid.uuid4().hex[:24]
    )


def visible_text(raw: str) -> str:
    out = raw
    while True:
        start = out.find("<think>")
        if start == -1:
            break
        end = out.find("</think>", start + 7)
        if end == -1:
            return out[:start]
        out = out[:start] + out[end + 8 :]
    return out.strip()


async def tcp_ok(port: int) -> bool:
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", port), timeout=0.5
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


@app.get("/api/status")
async def status():
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    return {
        "ok": True,
        "llama": await tcp_ok(8080),
        "openclaw": await tcp_ok(18789),
        "mobile": True,
        "cpu": psutil.cpu_percent(interval=0.05),
        "ram_used": vm.used,
        "ram_total": vm.total,
        "swap_used": sw.used,
        "swap_total": sw.total,
        "uptime": max(0, time.time() - psutil.boot_time()),
    }


@app.post("/api/chat/fast")
async def chat_fast(req: FastRequest):
    messages = [
        {
            "role": "system",
            "content": "Tu es un assistant utile. Réponds en français sauf demande contraire. Sois clair et concis.",
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
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(600, connect=5)
            ) as client:
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
                        piece = (
                            (choices[0].get("delta") or {}).get("content") or ""
                        )
                        if not piece:
                            continue
                        accumulated += piece
                        visible = visible_text(accumulated)
                        if len(visible) > shown_len:
                            chunk = visible[shown_len:]
                            shown_len = len(visible)
                            yield chunk
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            yield f"\n\n[Erreur: {exc}]"

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


@app.post("/api/chat/agent")
async def chat_agent(req: AgentRequest, request: Request):
    if not Path(OPENCLAW).exists():
        raise HTTPException(500, "OpenClaw introuvable sur le serveur.")

    safe_session = "".join(
        c for c in req.session_key if c.isalnum() or c in "-_"
    )[:80] or ("mobile-" + uuid.uuid4().hex[:24])

    started = time.perf_counter()
    proc = await asyncio.create_subprocess_exec(
        OPENCLAW,
        "agent",
        "--agent",
        OPENCLAW_AGENT,
        "--session-key",
        safe_session,
        "--message",
        req.message,
        "--timeout",
        "900",
        "--json",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    deadline = time.monotonic() + 930
    try:
        while proc.returncode is None:
            if await request.is_disconnected():
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=3)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                raise asyncio.CancelledError()

            if time.monotonic() > deadline:
                proc.kill()
                await proc.wait()
                raise HTTPException(504, "OpenClaw a dépassé le délai maximum.")

            try:
                await asyncio.wait_for(proc.wait(), timeout=0.5)
            except asyncio.TimeoutError:
                pass

        stdout, stderr = await proc.communicate()
    except asyncio.CancelledError:
        if proc.returncode is None:
            proc.terminate()
        raise

    stdout = stdout.decode("utf-8", errors="replace").strip()
    stderr = stderr.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        raise HTTPException(500, stderr or stdout or "Erreur OpenClaw")

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        a, b = stdout.find("{"), stdout.rfind("}")
        if a >= 0 and b > a:
            data = json.loads(stdout[a : b + 1])
        else:
            raise HTTPException(500, "Sortie OpenClaw invalide.")

    def extract(obj):
        if isinstance(obj, dict):
            payloads = obj.get("payloads")
            if isinstance(payloads, list):
                texts = [
                    str(x.get("text"))
                    for x in payloads
                    if isinstance(x, dict) and x.get("text")
                ]
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
        elif isinstance(obj, list):
            for val in obj:
                found = extract(val)
                if found:
                    return found
        return None

    return {
        "text": extract(data) or "(OpenClaw a terminé sans réponse textuelle.)",
        "seconds": round(time.perf_counter() - started, 1),
    }


MANIFEST = {
    "name": "Mon IA",
    "short_name": "Mon IA",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#0d0f13",
    "theme_color": "#111318",
    "description": "Client privé pour mon IA locale sur VPS.",
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
    ],
}

SERVICE_WORKER = r'''
const CACHE="mon-ia-v1";
const CORE=["/","/manifest.webmanifest","/icon-192.png","/icon-512.png"];
self.addEventListener("install",e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE))));
self.addEventListener("activate",e=>e.waitUntil(self.clients.claim()));
self.addEventListener("fetch",e=>{
  if(e.request.method!=="GET"||e.request.url.includes("/api/"))return;
  e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));
});
'''

INDEX = r'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#111318">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/icon-192.png">
<title>Mon IA</title>
<style>
:root{color-scheme:dark;--bg:#0c0e12;--panel:#15181e;--bubble:#1a1e27;--user:#253149;--line:#303747;--text:#eef1f6;--muted:#98a2b3;--accent:#303b55}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;height:100dvh;overflow:hidden}
.app{display:flex;flex-direction:column;height:100dvh;max-width:950px;margin:auto}header{display:flex;align-items:center;gap:9px;padding:10px 12px;border-bottom:1px solid var(--line);background:var(--panel)}
header b{flex:1}.iconbtn{border:0;background:transparent;color:var(--text);font-size:20px;padding:7px}.mode{display:flex;background:#0f1116;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.mode button{border:0;background:transparent;color:var(--muted);padding:9px 11px}.mode button.active{background:var(--accent);color:white}
#chat{flex:1;overflow:auto;padding:14px}.msg{padding:12px 14px;border-radius:14px;margin:9px 0;line-height:1.45;word-wrap:break-word}.user{background:var(--user);margin-left:12%}.assistant{background:var(--bubble);margin-right:8%}
.msg pre{background:#090b0f;padding:10px;border-radius:9px;overflow:auto;white-space:pre-wrap}.msg code{font-family:monospace}
footer{padding:10px 12px calc(10px + env(safe-area-inset-bottom));border-top:1px solid var(--line);background:var(--panel)}
textarea{width:100%;resize:none;min-height:54px;max-height:150px;background:#11141a;color:var(--text);border:1px solid var(--line);border-radius:13px;padding:12px;font:inherit}
.actions{display:flex;align-items:center;margin-top:8px;gap:8px}.status{flex:1;font-size:12px;color:var(--muted)}button.action{border:1px solid var(--line);border-radius:10px;background:#293247;color:white;padding:10px 15px;font-weight:600}
button.stop{background:#322128}.hidden{display:none!important}.drawer{position:fixed;inset:0;z-index:20;pointer-events:none}.drawer.open{pointer-events:auto}.shade{position:absolute;inset:0;background:#0008;opacity:0;transition:.2s}.drawer.open .shade{opacity:1}
.panel{position:absolute;left:0;top:0;bottom:0;width:min(86vw,360px);background:#15181e;border-right:1px solid var(--line);transform:translateX(-102%);transition:.2s;display:flex;flex-direction:column;padding:12px}.drawer.open .panel{transform:none}
.panelhead{display:flex;align-items:center;gap:8px}.panelhead b{flex:1}#convs{overflow:auto;flex:1;margin-top:10px}.conv{padding:11px;border-radius:9px;margin:3px 0;background:#11141a;display:flex;gap:7px;align-items:center}.conv.active{background:#293247}
.conv span{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.tiny{border:0;background:transparent;color:var(--muted);padding:4px}.serverbox{border-top:1px solid var(--line);padding-top:10px;font-size:13px;color:var(--muted);line-height:1.6}
</style>
</head>
<body>
<div class="app">
<header><button class="iconbtn" id="menuBtn">☰</button><b>Mon IA</b><div class="mode"><button id="fastBtn" class="active">⚡ Rapide</button><button id="agentBtn">🛠 Agent</button></div></header>
<main id="chat"></main>
<footer><textarea id="input" placeholder="Écris ton message…"></textarea><div class="actions"><div class="status" id="status">Connexion…</div><button class="action stop hidden" id="stopBtn">Arrêter</button><button class="action" id="sendBtn">Envoyer</button></div></footer>
</div>
<div class="drawer" id="drawer"><div class="shade" id="shade"></div><div class="panel"><div class="panelhead"><b>Conversations</b><button class="iconbtn" id="newBtn">＋</button><button class="iconbtn" id="closeBtn">×</button></div><div id="convs"></div><div class="serverbox" id="serverBox">État serveur…</div></div></div>
<script>
const $=id=>document.getElementById(id);
const chat=$("chat"),input=$("input"),send=$("sendBtn"),stopBtn=$("stopBtn"),statusEl=$("status"),fastBtn=$("fastBtn"),agentBtn=$("agentBtn"),drawer=$("drawer"),convs=$("convs"),serverBox=$("serverBox");
let mode="fast",controller=null,started=0,tick=null;
function uid(){return crypto.randomUUID()}
let conversations=JSON.parse(localStorage.getItem("mon-ia-conversations")||"null");
if(!Array.isArray(conversations)){const old=JSON.parse(localStorage.getItem("mobile-ai-messages")||"[]");conversations=[{id:uid(),title:"Nouvelle conversation",mode:"fast",session:"mobile-"+uid().replaceAll("-","").slice(0,24),messages:Array.isArray(old)?old:[]}]}
let currentId=localStorage.getItem("mon-ia-current")||conversations[0]?.id;
if(!conversations.some(c=>c.id===currentId))currentId=conversations[0]?.id;
function current(){return conversations.find(c=>c.id===currentId)}
function saveAll(){localStorage.setItem("mon-ia-conversations",JSON.stringify(conversations));localStorage.setItem("mon-ia-current",currentId||"")}
function esc(s){return(s||"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function md(s){s=esc(s||"");const blocks=[];s=s.replace(/```([\s\S]*?)```/g,(_,c)=>{blocks.push("<pre><code>"+c.trim()+"</code></pre>");return"@@CODE"+(blocks.length-1)+"@@"});s=s.replace(/`([^`\n]+)`/g,"<code>$1</code>").replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>").replace(/\n/g,"<br>");return s.replace(/@@CODE(\d+)@@/g,(_,i)=>blocks[Number(i)])}
function setMode(m){mode=m;fastBtn.classList.toggle("active",m==="fast");agentBtn.classList.toggle("active",m==="agent");const c=current();if(c){c.mode=m;saveAll()}}
function render(pending=null){const c=current();chat.innerHTML="";if(c){for(const m of c.messages){const d=document.createElement("div");d.className="msg "+(m.role==="user"?"user":"assistant");d.innerHTML=md(m.content);chat.appendChild(d)}}if(pending!==null){const d=document.createElement("div");d.className="msg assistant";d.innerHTML=md(pending||"…");chat.appendChild(d)}chat.scrollTop=chat.scrollHeight;renderConvs()}
function renderConvs(){convs.innerHTML="";for(const c of conversations){const d=document.createElement("div");d.className="conv"+(c.id===currentId?" active":"");const icon=document.createElement("b");icon.textContent=c.mode==="agent"?"🛠":"⚡";const name=document.createElement("span");name.textContent=c.title||"Conversation";name.onclick=()=>{currentId=c.id;mode=c.mode||"fast";setMode(mode);saveAll();render();drawer.classList.remove("open")};const ren=document.createElement("button");ren.className="tiny";ren.textContent="✎";ren.onclick=()=>renameConv(c.id);const del=document.createElement("button");del.className="tiny";del.textContent="×";del.onclick=()=>deleteConv(c.id);d.append(icon,name,ren,del);convs.appendChild(d)}}
function newConv(){const c={id:uid(),title:"Nouvelle conversation",mode,session:"mobile-"+uid().replaceAll("-","").slice(0,24),messages:[]};conversations.unshift(c);currentId=c.id;saveAll();render();drawer.classList.remove("open");input.focus()}
function renameConv(id){const c=conversations.find(x=>x.id===id);if(!c)return;const v=prompt("Nom de la conversation :",c.title||"");if(v&&v.trim()){c.title=v.trim().slice(0,80);saveAll();renderConvs()}}
function deleteConv(id){if(!confirm("Supprimer cette conversation ?"))return;conversations=conversations.filter(x=>x.id!==id);if(!conversations.length){newConv();return}if(currentId===id)currentId=conversations[0].id;const c=current();mode=c.mode||"fast";setMode(mode);saveAll();render()}
function busy(v){send.disabled=v;input.disabled=v;stopBtn.classList.toggle("hidden",!v);if(!v){controller=null;if(tick)clearInterval(tick);tick=null}}
function startClock(label){started=performance.now();tick=setInterval(()=>statusEl.textContent=label+" • "+((performance.now()-started)/1000).toFixed(1)+" s",500)}
async function sendMessage(){const text=input.value.trim(),c=current();if(!text||!c||send.disabled)return;input.value="";c.messages.push({role:"user",content:text});if(c.title==="Nouvelle conversation")c.title=text.replace(/\s+/g," ").slice(0,42);saveAll();render("");busy(true);controller=new AbortController();try{if(mode==="fast"){startClock("Rapide");const r=await fetch("/api/chat/fast",{method:"POST",signal:controller.signal,headers:{"Content-Type":"application/json"},body:JSON.stringify({messages:c.messages})});if(!r.ok)throw new Error(await r.text());const reader=r.body.getReader(),dec=new TextDecoder();let answer="";while(true){const{done,value}=await reader.read();if(done)break;answer+=dec.decode(value,{stream:true});render(answer)}c.messages.push({role:"assistant",content:answer.trim()});statusEl.textContent="Rapide • "+((performance.now()-started)/1000).toFixed(1)+" s"}else{startClock("Agent");const r=await fetch("/api/chat/agent",{method:"POST",signal:controller.signal,headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text,session_key:c.session})});if(!r.ok)throw new Error(await r.text());const data=await r.json();c.messages.push({role:"assistant",content:data.text});statusEl.textContent="Agent • "+data.seconds+" s"}saveAll();render()}catch(e){if(e.name==="AbortError"){statusEl.textContent="Génération arrêtée";render()}else{statusEl.textContent="Erreur";render("Erreur : "+e.message)}}finally{busy(false);input.disabled=false;input.focus()}}
function fmtBytes(v){if(!v)return"0";const u=["o","Ko","Mo","Go"];let i=0;while(v>=1024&&i<u.length-1){v/=1024;i++}return v.toFixed(i>1?1:0)+" "+u[i]}
function fmtUp(s){s=Math.floor(s||0);const d=Math.floor(s/86400),h=Math.floor((s%86400)/3600),m=Math.floor((s%3600)/60);return d?d+" j "+h+" h":h?h+" h "+m+" min":m+" min"}
async function refreshStatus(){try{const s=await fetch("/api/status",{cache:"no-store"}).then(r=>r.json());serverBox.innerHTML=`IA ${s.llama?"●":"○"} &nbsp; Agent ${s.openclaw?"●":"○"}<br>RAM ${fmtBytes(s.ram_used)} / ${fmtBytes(s.ram_total)}<br>Swap ${fmtBytes(s.swap_used)} / ${fmtBytes(s.swap_total)}<br>CPU ${s.cpu.toFixed(0)} % • Uptime ${fmtUp(s.uptime)}`;if(!send.disabled)statusEl.textContent=s.llama?"Serveur prêt":"IA indisponible"}catch{serverBox.textContent="Serveur indisponible"}}
fastBtn.onclick=()=>setMode("fast");agentBtn.onclick=()=>setMode("agent");send.onclick=sendMessage;stopBtn.onclick=()=>controller?.abort();$("menuBtn").onclick=()=>drawer.classList.add("open");$("shade").onclick=$("closeBtn").onclick=()=>drawer.classList.remove("open");$("newBtn").onclick=newConv;
input.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMessage()}});
const c=current();if(c){mode=c.mode||"fast";setMode(mode)}render();refreshStatus();setInterval(refreshStatus,30000);if("serviceWorker"in navigator)navigator.serviceWorker.register("/service-worker.js").catch(()=>{});
</script>
</body>
</html>'''


@app.get("/", response_class=HTMLResponse)
async def index():
    return INDEX


@app.get("/manifest.webmanifest")
async def manifest():
    return JSONResponse(MANIFEST, media_type="application/manifest+json")


@app.get("/service-worker.js")
async def service_worker():
    return Response(SERVICE_WORKER, media_type="application/javascript")


@app.get("/icon-192.png")
async def icon192():
    return Response(
        Path(__file__).with_name("icon-192.png").read_bytes(), media_type="image/png"
    )


@app.get("/icon-512.png")
async def icon512():
    return Response(
        Path(__file__).with_name("icon-512.png").read_bytes(), media_type="image/png"
    )

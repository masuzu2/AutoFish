"""
AutoFish by Herlove v2.0 - Web UI Edition (Remastered)
pywebview + Tailwind CSS + OCR + SendInput + Glassmorphism UI
"""
import time,sys,os,json,threading,ctypes,random,base64,io
SCRIPT_DIR=os.path.dirname(os.path.abspath(__file__))

def is_admin():
    if sys.platform!='win32': return True
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False
if not is_admin() and sys.platform=='win32':
    try: ctypes.windll.shell32.ShellExecuteW(None,"runas",sys.executable,f'"{os.path.abspath(__file__)}"',None,1)
    except: pass
    sys.exit()

try:
    import webview
    import mss,cv2,numpy as np
    from PIL import Image,ImageGrab
    import pytesseract
except ImportError as e:
    print(f"pip install pywebview mss opencv-python numpy Pillow pytesseract");sys.exit(1)
for p in [r"C:\Program Files\Tesseract-OCR\tesseract.exe",r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]:
    if os.path.exists(p): pytesseract.pytesseract.tesseract_cmd=p; break

SCAN={'q':0x10,'w':0x11,'e':0x12,'r':0x13,'a':0x1E,'s':0x1F,'d':0x20,'f':0x21,'space':0x39}
if sys.platform=='win32':
    PUL=ctypes.POINTER(ctypes.c_ulong)
    class KI(ctypes.Structure):
        _fields_=[("wVk",ctypes.c_ushort),("wScan",ctypes.c_ushort),("dwFlags",ctypes.c_ulong),("time",ctypes.c_ulong),("dwExtraInfo",PUL)]
    class HI(ctypes.Structure):
        _fields_=[("uMsg",ctypes.c_ulong),("wParamL",ctypes.c_short),("wParamH",ctypes.c_ushort)]
    class MI(ctypes.Structure):
        _fields_=[("dx",ctypes.c_long),("dy",ctypes.c_long),("mouseData",ctypes.c_ulong),("dwFlags",ctypes.c_ulong),("time",ctypes.c_ulong),("dwExtraInfo",PUL)]
    class IU(ctypes.Union):
        _fields_=[("ki",KI),("mi",MI),("hi",HI)]
    class INP(ctypes.Structure):
        _fields_=[("type",ctypes.c_ulong),("ii",IU)]

def press_key(key):
    sc=SCAN.get(key.lower())
    if not sc or sys.platform!='win32': return False
    try:
        ex=ctypes.c_ulong(0)
        ii=IU();ii.ki=KI(0,sc,0x0008,0,ctypes.pointer(ex))
        x=INP(1,ii);ctypes.windll.user32.SendInput(1,ctypes.pointer(x),ctypes.sizeof(x))
        time.sleep(random.uniform(0.03,0.08))
        ii2=IU();ii2.ki=KI(0,sc,0x0008|0x0002,0,ctypes.pointer(ex))
        x2=INP(1,ii2);ctypes.windll.user32.SendInput(1,ctypes.pointer(x2),ctypes.sizeof(x2))
        return True
    except: return False

_sct=None
def grab(r):
    global _sct
    L,T,W,H=int(r["left"]),int(r["top"]),int(r["width"]),int(r["height"])
    if _sct is None:
        try: _sct=mss.mss()
        except: pass
    if _sct:
        try:
            a=np.array(_sct.grab({"left":L,"top":T,"width":W,"height":H}))
            if a.size>0: return cv2.cvtColor(a,cv2.COLOR_BGRA2BGR)
        except: pass
    try:
        i=ImageGrab.grab(bbox=(L,T,L+W,T+H))
        if i: return cv2.cvtColor(np.array(i),cv2.COLOR_RGB2BGR)
    except: pass
    return None

VALID=set("qweasd")
def _ocr_slot(slot):
    if slot is None or slot.size<20: return None
    big=cv2.resize(slot,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
    for inv in [False,True]:
        try:
            _,t=cv2.threshold(big,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            if inv: t=cv2.bitwise_not(t)
            if np.count_nonzero(t)>t.size//2: t=cv2.bitwise_not(t)
            txt=pytesseract.image_to_string(t,config='--psm 10 -c tessedit_char_whitelist=QWEASDqweasd').strip().lower()
            for c in txt:
                if c in VALID: return c
        except: continue
    return None

def read_fast(gray,num):
    if gray is None or gray.size<100: return None
    h,w=gray.shape[:2]
    trim=int(w*0.05);uw=w-trim if trim>3 else w
    kernel=np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    proc=cv2.filter2D(gray[:,:uw],-1,kernel)
    proc=cv2.GaussianBlur(proc,(3,3),0)
    big=cv2.resize(proc,None,fx=2,fy=2,interpolation=cv2.INTER_LINEAR)
    for inv in [False,True]:
        try:
            _,t=cv2.threshold(big,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            if inv: t=cv2.bitwise_not(t)
            if np.count_nonzero(t)>t.size//2: t=cv2.bitwise_not(t)
            txt=pytesseract.image_to_string(t,config='--psm 7 -c tessedit_char_whitelist=QWEASDqweasd').strip().lower()
            chars=[c for c in txt if c in VALID]
            if len(chars)==num:
                sw=uw//num
                last=_ocr_slot(gray[:,(num-1)*sw:uw])
                if last and last!=chars[-1]: chars[-1]=last
                return chars
        except: continue
    sw=uw//num;chars=[]
    for i in range(num):
        pad=max(sw//10,2)
        chars.append(_ocr_slot(gray[:,max(0,i*sw-pad):min(uw,(i+1)*sw+pad)]))
    return chars if all(c is not None for c in chars) else None

CFG=os.path.join(SCRIPT_DIR,"config.json")
S={"running":False,"paused":False,"region":None,"keys":0,"fish":0,"scans":0,
   "last":"","log":[],"start":0,"nk":5,"kd":60,"preview":""}
try:
    with open(CFG) as f: c=json.load(f); S["region"]=c.get("region"); S["nk"]=c.get("nk",5)
except: pass

def add_log(m):
    S["log"].append(f"[{time.strftime('%H:%M:%S')}] {m}")
    if len(S["log"])>40: S["log"]=S["log"][-40:]

def save():
    try:
        with open(CFG,"w") as f: json.dump({"region":S["region"],"nk":S["nk"],"kd":S["kd"]},f)
    except: pass

def run_loop():
    num=S["nk"];kd=S["kd"]/1000
    S["keys"]=0;S["fish"]=0;S["scans"]=0;S["start"]=time.time()
    add_log("System Scanning initialized...")
    lseq=""
    while S["running"]:
        if S["paused"]: time.sleep(0.1);continue
        try:
            r=S["region"]
            if not r: time.sleep(0.1);continue
            f=grab(r)
            if f is None: time.sleep(0.04);continue
            g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
            S["scans"]+=1
            h2,w2=f.shape[:2];nw=280;nh=max(int(h2*nw/w2),10)
            sm=cv2.resize(f,(nw,nh))
            _,buf=cv2.imencode('.jpg',sm,[cv2.IMWRITE_JPEG_QUALITY,50])
            S["preview"]=base64.b64encode(buf).decode()
            k=read_fast(g,num)
            if k and len(k)==num:
                seq="".join(k)
                if seq!=lseq:
                    S["fish"]+=1;S["last"]=" ".join(x.upper() for x in k)
                    add_log(f"Catch #{S['fish']} \u00bb {S['last']}")
                    if random.random()<0.05: time.sleep(random.uniform(0.3,1.0))
                    for key in k:
                        if not S["running"]: break
                        press_key(key);S["keys"]+=1
                        time.sleep(kd+random.uniform(0.03,0.12))
                    if sys.platform=='win32':
                        try: import winsound;winsound.Beep(800,60)
                        except: pass
                    lseq=seq;time.sleep(0.6+random.uniform(0.1,0.3))
                else: time.sleep(0.03)
            else: time.sleep(0.04)
        except Exception as e:
            add_log(f"Error: {e}");time.sleep(0.5)
    add_log("System Stopped.")

class Api:
    def get_status(self):
        e=int(time.time()-S["start"]) if S["running"] else 0
        m,s=divmod(e,60)
        rate=f"{int(S['fish']/max(S['scans'],1)*100)}%" if S["scans"]>0 else "\u2014"
        return json.dumps({
            "running":S["running"],"paused":S["paused"],
            "keys":S["keys"],"fish":S["fish"],"rate":rate,
            "time":f"{m:02d}:{s:02d}","last":S["last"],
            "log":S["log"][-20:],"preview":S["preview"],
            "region":S["region"],"admin":is_admin()
        })

    def start(self,nk,kd):
        if S["running"]: return
        if not S["region"]: add_log("Warning: Set region first!");return
        S["nk"]=int(nk);S["kd"]=int(kd);save()
        S["running"]=True;S["paused"]=False
        add_log("Bot Engine Started!")
        threading.Thread(target=run_loop,daemon=True).start()

    def stop(self):
        S["running"]=False;S["paused"]=False

    def pause(self):
        if not S["running"]: return
        S["paused"]=not S["paused"]
        add_log("Engine Paused" if S["paused"] else "Engine Resumed")

    def set_region(self,x,y,w,h):
        S["region"]={"left":int(x),"top":int(y),"width":int(w),"height":int(h)}
        save();add_log(f"Region Set: {w}x{h}")

    def test_read(self):
        if not S["region"]: return "[]"
        f=grab(S["region"])
        if f is None: return "[]"
        g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
        k=read_fast(g,S["nk"])
        return json.dumps(k or [])

    def test_key(self):
        press_key('d');time.sleep(0.1);press_key('s')
        add_log("Tested Virtual Keys (D+S)")

HTML="""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  :root{--bg-main:#020617;--glass-bg:rgba(30,41,59,0.45);--glass-border:rgba(255,255,255,0.08)}
  body{font-family:'Inter',sans-serif;background-color:var(--bg-main);background-image:radial-gradient(circle at 15% 50%,rgba(56,189,248,0.08),transparent 25%),radial-gradient(circle at 85% 30%,rgba(16,185,129,0.08),transparent 25%);color:#e2e8f0;margin:0;user-select:none;overflow:hidden;height:100vh}
  .bg-grid{position:fixed;top:0;left:0;right:0;bottom:0;z-index:-1;background-size:40px 40px;background-image:linear-gradient(to right,rgba(255,255,255,0.02) 1px,transparent 1px),linear-gradient(to bottom,rgba(255,255,255,0.02) 1px,transparent 1px);-webkit-mask-image:linear-gradient(to bottom,transparent 10%,black 50%,transparent 90%)}
  .glass{background:var(--glass-bg);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border:1px solid var(--glass-border);border-radius:16px;box-shadow:0 4px 30px rgba(0,0,0,0.2)}
  .glass-inner{background:rgba(15,23,42,0.6);border:1px solid rgba(255,255,255,0.03);box-shadow:inset 0 2px 10px rgba(0,0,0,0.5)}
  .btn{border-radius:12px;font-weight:700;cursor:pointer;transition:all 0.25s cubic-bezier(0.4,0,0.2,1);border:1px solid transparent;display:flex;align-items:center;justify-content:center;gap:6px}
  .btn:hover{transform:translateY(-2px);filter:brightness(1.15)}
  .btn:active{transform:scale(0.96);filter:brightness(0.9)}
  .btn-start-active{background:linear-gradient(135deg,#e11d48,#be123c);box-shadow:0 0 25px rgba(225,29,72,0.4);border-color:rgba(255,255,255,0.2)}
  .btn-start-idle{background:linear-gradient(135deg,#10b981,#059669);box-shadow:0 0 25px rgba(16,185,129,0.3);border-color:rgba(255,255,255,0.2)}
  .btn-sub{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.05)}
  .btn-sub:hover{background:rgba(255,255,255,0.08);border-color:rgba(255,255,255,0.15)}
  .keycap{width:38px;height:38px;background:linear-gradient(180deg,#334155 0%,#1e293b 100%);border:1px solid #475569;border-bottom-width:3px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:16px;color:#38bdf8;text-shadow:0 0 8px rgba(56,189,248,0.5);box-shadow:0 4px 6px rgba(0,0,0,0.3)}
  .text-gradient{background-clip:text;-webkit-background-clip:text;-webkit-text-fill-color:transparent}
  .glow-text{text-shadow:0 0 12px currentColor}
  ::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.2);border-radius:4px}
  input[type=range]{-webkit-appearance:none;height:6px;border-radius:3px;background:rgba(255,255,255,0.08);outline:none}
  input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;border-radius:50%;background:#38bdf8;box-shadow:0 0 10px #38bdf8;cursor:pointer;transition:0.2s}
  input[type=range]::-webkit-slider-thumb:hover{transform:scale(1.2)}
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="max-w-[480px] mx-auto px-5 py-5 space-y-4 relative z-10 h-full flex flex-col">
  <div class="flex items-center justify-between glass px-4 py-3">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center text-xl shadow-[0_0_15px_rgba(56,189,248,0.4)]">&#x1F41F;</div>
      <div>
        <div class="text-lg font-bold tracking-tight text-white flex items-center gap-2">AutoFish <span class="px-1.5 py-0.5 rounded bg-white/10 text-[9px] text-cyan-300 font-mono">PRO</span></div>
        <div class="text-[10px] text-slate-400 font-medium tracking-wide uppercase">by Herlove</div>
      </div>
    </div>
    <div id="badge" class="px-3 py-1.5 rounded-lg text-[10px] font-bold tracking-widest transition-all duration-300 border border-slate-700 bg-slate-800 text-slate-400 shadow-inner">STANDBY</div>
  </div>
  <div class="glass p-1">
    <div class="glass-inner rounded-xl overflow-hidden relative">
      <div class="absolute top-0 left-0 w-full px-3 py-1.5 bg-gradient-to-b from-black/60 to-transparent text-[9px] font-bold text-slate-400 uppercase tracking-wider z-10 flex justify-between">
        <span>Vision Preview</span><span id="regI" class="font-mono text-cyan-500 glow-text">NO REGION</span>
      </div>
      <div class="h-24 flex items-center justify-center relative">
        <img id="prev" class="hidden w-full h-full object-contain mix-blend-screen opacity-90 transition-all duration-300">
        <div id="prevT" class="flex flex-col items-center gap-1 opacity-50">
          <svg class="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
          <span class="text-[10px] font-medium text-slate-300 uppercase tracking-widest">Awaiting Region Data</span>
        </div>
      </div>
    </div>
  </div>
  <div class="flex flex-col items-center justify-center min-h-[50px]">
    <div class="text-[9px] text-slate-500 font-bold tracking-widest mb-2 uppercase">Current Sequence</div>
    <div id="keysRow" class="flex justify-center gap-2"><span class="text-xs text-slate-600 font-mono italic">Waiting for scan...</span></div>
  </div>
  <button id="btnS" onclick="doToggle()" class="btn btn-start-idle w-full py-3.5 text-base text-white tracking-widest uppercase shadow-lg">
    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Initialize Engine
  </button>
  <div class="grid grid-cols-4 gap-2.5">
    <div class="glass p-3 text-center flex flex-col items-center justify-center relative overflow-hidden group"><div class="absolute inset-0 bg-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity"></div><div id="sK" class="text-xl font-bold font-mono text-gradient bg-gradient-to-br from-blue-300 to-blue-500 glow-text mb-0.5">0</div><div class="text-[8px] text-slate-400 font-bold tracking-wider">KEYS</div></div>
    <div class="glass p-3 text-center flex flex-col items-center justify-center relative overflow-hidden group"><div class="absolute inset-0 bg-cyan-500/10 opacity-0 group-hover:opacity-100 transition-opacity"></div><div id="sF" class="text-xl font-bold font-mono text-gradient bg-gradient-to-br from-cyan-300 to-emerald-400 glow-text mb-0.5">0</div><div class="text-[8px] text-slate-400 font-bold tracking-wider">FISH</div></div>
    <div class="glass p-3 text-center flex flex-col items-center justify-center relative overflow-hidden group"><div class="absolute inset-0 bg-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity"></div><div id="sR" class="text-xl font-bold font-mono text-gradient bg-gradient-to-br from-purple-400 to-pink-400 glow-text mb-0.5">\u2014</div><div class="text-[8px] text-slate-400 font-bold tracking-wider">RATE</div></div>
    <div class="glass p-3 text-center flex flex-col items-center justify-center relative overflow-hidden group"><div class="absolute inset-0 bg-amber-500/10 opacity-0 group-hover:opacity-100 transition-opacity"></div><div id="sT" class="text-xl font-bold font-mono text-gradient bg-gradient-to-br from-amber-300 to-orange-400 glow-text mb-0.5">0:00</div><div class="text-[8px] text-slate-400 font-bold tracking-wider">TIME</div></div>
  </div>
  <div class="flex gap-3">
    <div class="glass p-3 flex-1 flex flex-col gap-2">
      <div class="text-[9px] font-bold text-slate-400 tracking-wider mb-1">MODULES</div>
      <div class="grid grid-cols-2 gap-2 h-full">
        <button onclick="doRegion()" class="btn btn-sub py-2 text-[10px] text-blue-300 hover:text-blue-200"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/></svg> Area</button>
        <button onclick="doTest()" class="btn btn-sub py-2 text-[10px] text-cyan-300 hover:text-cyan-200"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/></svg> Scan</button>
        <button onclick="doKey()" class="btn btn-sub py-2 text-[10px] text-purple-300 hover:text-purple-200"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"/></svg> Test</button>
        <button onclick="doPause()" class="btn btn-sub py-2 text-[10px] text-amber-300 hover:text-amber-200"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> Hold</button>
      </div>
    </div>
    <div class="glass p-3 flex-1 flex flex-col gap-2">
      <div class="text-[9px] font-bold text-slate-400 tracking-wider mb-1">PARAMETERS</div>
      <div class="flex-1 flex flex-col justify-center gap-3">
        <div><div class="flex justify-between items-end mb-1"><span class="text-[10px] text-slate-300">Slots</span><span id="vK" class="text-xs font-mono font-bold text-cyan-400">5</span></div><input type="range" id="rK" min="2" max="10" value="5" class="w-full" oninput="$('vK').textContent=this.value"></div>
        <div><div class="flex justify-between items-end mb-1"><span class="text-[10px] text-slate-300">Delay (ms)</span><span id="vD" class="text-xs font-mono font-bold text-emerald-400">60</span></div><input type="range" id="rD" min="30" max="200" value="60" class="w-full" oninput="$('vD').textContent=this.value"></div>
      </div>
    </div>
  </div>
  <div class="glass flex-1 flex flex-col overflow-hidden min-h-[90px]">
    <div class="px-3 py-2 border-b border-white/5 bg-white/5 text-[9px] font-bold text-slate-400 tracking-widest flex items-center gap-2"><div class="w-1.5 h-1.5 rounded-full bg-slate-500 animate-pulse" id="logDot"></div> TERMINAL</div>
    <div class="glass-inner flex-1 p-2 overflow-hidden"><div id="log" class="h-full overflow-y-auto font-mono text-[10px] text-slate-400 leading-relaxed pr-1 flex flex-col justify-end"></div></div>
  </div>
  <div class="text-center text-[9px] font-medium text-slate-600 tracking-widest">[F5] POWER &middot; [F7] HOLD &middot; CORE: PYWEBVIEW</div>
</div>
<script>
const $=id=>document.getElementById(id);let on=false;
async function py(fn,...args){return await window.pywebview.api[fn](...args)}
async function doToggle(){if(on){await py('stop');on=false;upUI(false)}else{await py('start',$('rK').value,$('rD').value);on=true;upUI(true)}}
async function doRegion(){const x=prompt("Target X:"),y=prompt("Target Y:"),w=prompt("Width:"),h=prompt("Height:");if(x&&y&&w&&h) await py('set_region',x,y,w,h)}
async function doTest(){const r=JSON.parse(await py('test_read'));if(r.length) showK(r)}
async function doKey(){await py('test_key')}
async function doPause(){await py('pause')}
function upUI(r){const btn=$('btnS'),badge=$('badge'),dot=$('logDot');if(r){btn.innerHTML='<svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Abort Sequence';btn.className='btn btn-start-active w-full py-3.5 text-base text-white tracking-widest uppercase';badge.textContent='ACTIVE';badge.className='px-3 py-1.5 rounded-lg text-[10px] font-bold tracking-widest transition-all duration-300 border border-emerald-500/50 bg-emerald-500/20 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.3)] animate-pulse';dot.className='w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_5px_#10b981]'}else{btn.innerHTML='<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Initialize Engine';btn.className='btn btn-start-idle w-full py-3.5 text-base text-white tracking-widest uppercase shadow-lg';badge.textContent='STANDBY';badge.className='px-3 py-1.5 rounded-lg text-[10px] font-bold tracking-widest transition-all duration-300 border border-slate-700 bg-slate-800 text-slate-400 shadow-inner';dot.className='w-1.5 h-1.5 rounded-full bg-slate-500'}}
function showK(c){$('keysRow').innerHTML=c.map(k=>'<div class="keycap">'+k.toUpperCase()+'</div>').join('')}
function formatLog(logs){return logs.map(l=>{let f=l.replace(/Catch #\\d+/g,m=>'<span class="text-emerald-400 font-bold">'+m+'</span>').replace(/Error:/g,'<span class="text-rose-400 font-bold">ERR:</span>').replace(/\\[\\d{2}:\\d{2}:\\d{2}\\]/g,m=>'<span class="text-slate-500">'+m+'</span>');return '<div class="mb-1"><span class="text-cyan-500/50 mr-1">\u00bb</span>'+f+'</div>'}).join('')}
async function poll(){try{const s=JSON.parse(await py('get_status'));$('sK').textContent=s.keys;$('sF').textContent=s.fish;$('sR').textContent=s.rate;$('sT').textContent=s.time;if(s.last)showK(s.last.split(' ').map(k=>k.toLowerCase()));if(s.region)$('regI').textContent=s.region.width+'\u00d7'+s.region.height;if(s.preview){$('prev').src='data:image/jpeg;base64,'+s.preview;$('prev').classList.remove('hidden');$('prevT').classList.add('hidden')}const le=$('log'),wb=le.scrollTop+le.clientHeight>=le.scrollHeight-10;le.innerHTML=formatLog(s.log);if(wb)le.scrollTop=le.scrollHeight;if(s.running!==on){on=s.running;upUI(on)}if(s.paused){$('badge').textContent='HOLDING';$('badge').className='px-3 py-1.5 rounded-lg text-[10px] font-bold tracking-widest transition-all duration-300 border border-amber-500/50 bg-amber-500/20 text-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.3)] animate-pulse'}else if(on&&$('badge').textContent==='HOLDING'){upUI(true)}}catch{}}
setInterval(poll,200);
document.addEventListener('keydown',e=>{if(e.key==='F5'){e.preventDefault();doToggle()}if(e.key==='F7'){e.preventDefault();doPause()}});
</script>
</body></html>"""

if __name__=="__main__":
    add_log("System Boot: AutoFish UI Remastered")
    add_log(f"Privilege Level: {'ROOT/ADMIN' if is_admin() else 'USER'}")
    try: add_log(f"OCR Engine: Tesseract {pytesseract.get_tesseract_version()}")
    except: add_log("OCR Engine: OFFLINE (NOT FOUND)")
    api=Api()
    window=webview.create_window(
        "AutoFish Pro - Remastered",html=HTML,
        width=520,height=780,resizable=False,on_top=True,
        js_api=api,background_color='#020617')
    webview.start(debug=False)

"""
AutoFish by Herlove v2.0 - Web UI Edition
pywebview + Tailwind CSS + OCR + SendInput
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

# ═══ SendInput Scancode ═══
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

# ═══ Capture ═══
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

# ═══ OCR (เร็ว) ═══
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

# ═══ State ═══
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

# ═══ Main Loop ═══
def run_loop():
    num=S["nk"];kd=S["kd"]/1000
    S["keys"]=0;S["fish"]=0;S["scans"]=0;S["start"]=time.time()
    add_log("> Scanning...")
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
            # Preview
            h2,w2=f.shape[:2];nw=280;nh=max(int(h2*nw/w2),10)
            sm=cv2.resize(f,(nw,nh))
            _,buf=cv2.imencode('.jpg',sm,[cv2.IMWRITE_JPEG_QUALITY,50])
            S["preview"]=base64.b64encode(buf).decode()
            k=read_fast(g,num)
            if k and len(k)==num:
                seq="".join(k)
                if seq!=lseq:
                    S["fish"]+=1;S["last"]=" ".join(x.upper() for x in k)
                    add_log(f"> #{S['fish']} {S['last']}")
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
            add_log(f"> {e}");time.sleep(0.5)
    add_log("> Stopped")

# ═══ API for pywebview ═══
class Api:
    def get_status(self):
        e=int(time.time()-S["start"]) if S["running"] else 0
        m,s=divmod(e,60)
        rate=f"{int(S['fish']/max(S['scans'],1)*100)}%" if S["scans"]>0 else "—"
        return json.dumps({
            "running":S["running"],"paused":S["paused"],
            "keys":S["keys"],"fish":S["fish"],"rate":rate,
            "time":f"{m:02d}:{s:02d}","last":S["last"],
            "log":S["log"][-20:],"preview":S["preview"],
            "region":S["region"],"admin":is_admin()
        })

    def start(self,nk,kd):
        if S["running"]: return
        if not S["region"]: add_log("> Set region first!");return
        S["nk"]=int(nk);S["kd"]=int(kd);save()
        S["running"]=True;S["paused"]=False
        add_log("> Started!")
        threading.Thread(target=run_loop,daemon=True).start()

    def stop(self):
        S["running"]=False;S["paused"]=False

    def pause(self):
        if not S["running"]: return
        S["paused"]=not S["paused"]
        add_log("> Paused" if S["paused"] else "> Resumed")

    def set_region(self,x,y,w,h):
        S["region"]={"left":int(x),"top":int(y),"width":int(w),"height":int(h)}
        save();add_log(f"> Region: {w}x{h}")

    def test_read(self):
        if not S["region"]: return "[]"
        f=grab(S["region"])
        if f is None: return "[]"
        g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
        k=read_fast(g,S["nk"])
        return json.dumps(k or [])

    def test_key(self):
        press_key('d');time.sleep(0.1);press_key('s')
        add_log("> Pressed D+S")

# ═══ HTML ═══
HTML="""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  body{font-family:'Inter',sans-serif;background:#0f172a;color:#e5e7eb;margin:0;user-select:none}
  .card{background:#1e293b;border-radius:14px;border:1px solid #334155}
  .btn{border-radius:10px;font-weight:700;cursor:pointer;transition:all 0.15s;border:none}
  .btn:hover{transform:translateY(-1px);filter:brightness(1.1)}
  .btn:active{transform:scale(0.97)}
  ::-webkit-scrollbar{width:3px}
  ::-webkit-scrollbar-thumb{background:#334155;border-radius:3px}
  input[type=range]{-webkit-appearance:none;height:4px;border-radius:2px;background:#334155}
  input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:14px;height:14px;border-radius:50%;background:#3b82f6}
</style>
</head><body>
<div class="max-w-[460px] mx-auto px-4 py-4 space-y-3">
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-2.5">
      <div class="text-2xl">🐟</div>
      <div><div class="text-base font-bold text-white">AutoFish</div>
      <div class="text-[10px] text-slate-500">by Herlove · v2.0</div></div>
    </div>
    <div id="badge" class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-700 text-slate-400">OFF</div>
  </div>

  <div class="card overflow-hidden">
    <div class="px-3 py-1.5 border-b border-slate-700/50 text-[9px] font-bold text-slate-500 uppercase tracking-wider">Preview</div>
    <div class="bg-slate-900 h-20 flex items-center justify-center">
      <img id="prev" class="hidden w-full h-full object-contain">
      <span id="prevT" class="text-xs text-slate-600">Set region to see preview</span>
    </div>
  </div>

  <div id="keysRow" class="flex justify-center gap-1.5 min-h-[32px]"></div>

  <button id="btnS" onclick="doToggle()" class="btn w-full py-2.5 text-sm bg-emerald-500 text-white">Start</button>

  <div class="grid grid-cols-4 gap-2">
    <div class="card p-2.5 text-center"><div id="sK" class="text-lg font-bold text-blue-400 font-mono">0</div><div class="text-[8px] text-slate-500 font-bold">KEYS</div></div>
    <div class="card p-2.5 text-center"><div id="sF" class="text-lg font-bold text-cyan-400 font-mono">0</div><div class="text-[8px] text-slate-500 font-bold">FISH</div></div>
    <div class="card p-2.5 text-center"><div id="sR" class="text-lg font-bold text-violet-400 font-mono">—</div><div class="text-[8px] text-slate-500 font-bold">RATE</div></div>
    <div class="card p-2.5 text-center"><div id="sT" class="text-lg font-bold text-amber-400 font-mono">0:00</div><div class="text-[8px] text-slate-500 font-bold">TIME</div></div>
  </div>

  <div class="card p-3">
    <div class="text-[9px] font-bold text-slate-500 mb-2">CONTROLS</div>
    <div class="flex gap-1.5">
      <button onclick="doRegion()" class="btn flex-1 py-2 text-xs bg-blue-500/20 text-blue-400">Region</button>
      <button onclick="doTest()" class="btn flex-1 py-2 text-xs bg-emerald-500/20 text-emerald-400">Test Read</button>
      <button onclick="doKey()" class="btn flex-1 py-2 text-xs bg-violet-500/20 text-violet-400">Test Key</button>
      <button onclick="doPause()" class="btn flex-1 py-2 text-xs bg-amber-500/20 text-amber-400">Pause</button>
    </div>
    <div class="text-right mt-1"><span id="regI" class="text-[10px] font-mono text-slate-600">not set</span></div>
  </div>

  <div class="card p-3 space-y-2">
    <div class="text-[9px] font-bold text-slate-500">SETTINGS</div>
    <div class="flex items-center justify-between">
      <span class="text-xs text-slate-300">Keys/Lane</span>
      <div class="flex items-center gap-2">
        <input type="range" id="rK" min="2" max="10" value="5" class="w-20" oninput="$('vK').textContent=this.value">
        <span id="vK" class="text-xs font-mono font-bold text-blue-400 w-4">5</span>
      </div>
    </div>
    <div class="flex items-center justify-between">
      <span class="text-xs text-slate-300">Key Delay (ms)</span>
      <div class="flex items-center gap-2">
        <input type="range" id="rD" min="30" max="200" value="60" class="w-20" oninput="$('vD').textContent=this.value">
        <span id="vD" class="text-xs font-mono font-bold text-emerald-400 w-6">60</span>
      </div>
    </div>
  </div>

  <div class="card overflow-hidden">
    <div class="px-3 py-1.5 border-b border-slate-700/50 text-[9px] font-bold text-slate-500">LOG</div>
    <div id="log" class="px-3 py-2 h-20 overflow-y-auto font-mono text-[10px] text-slate-500 space-y-px"></div>
  </div>

  <div class="text-center text-[8px] text-slate-700">F5 Start · F7 Pause · pywebview</div>
</div>

<script>
const $=id=>document.getElementById(id);
let on=false;

async function py(fn,...args){return await window.pywebview.api[fn](...args)}

async function doToggle(){
  if(on){await py('stop');on=false;upUI(false)}
  else{await py('start',$('rK').value,$('rD').value);on=true;upUI(true)}
}
async function doRegion(){
  const x=prompt("X:"),y=prompt("Y:"),w=prompt("Width:"),h=prompt("Height:");
  if(x&&y&&w&&h) await py('set_region',x,y,w,h);
}
async function doTest(){
  const r=JSON.parse(await py('test_read'));
  if(r.length) showK(r);
}
async function doKey(){await py('test_key')}
async function doPause(){await py('pause')}

function upUI(r){
  $('btnS').textContent=r?'Stop':'Start';
  $('btnS').className='btn w-full py-2.5 text-sm '+(r?'bg-red-500 text-white':'bg-emerald-500 text-white');
  $('badge').textContent=r?'ACTIVE':'OFF';
  $('badge').className='px-2.5 py-1 rounded-full text-[10px] font-bold '+(r?'bg-emerald-500/20 text-emerald-400':'bg-slate-700 text-slate-400');
}

function showK(c){
  $('keysRow').innerHTML=c.map(k=>
    `<div class="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 font-bold text-sm font-mono">${k.toUpperCase()}</div>`
  ).join('');
}

async function poll(){
  try{
    const s=JSON.parse(await py('get_status'));
    $('sK').textContent=s.keys;$('sF').textContent=s.fish;
    $('sR').textContent=s.rate;$('sT').textContent=s.time;
    if(s.last) showK(s.last.split(' ').map(k=>k.toLowerCase()));
    if(s.region) $('regI').textContent=s.region.width+'x'+s.region.height;
    if(s.preview){$('prev').src='data:image/jpeg;base64,'+s.preview;$('prev').classList.remove('hidden');$('prevT').classList.add('hidden')}
    $('log').innerHTML=s.log.map(l=>'<div>'+l+'</div>').join('');
    $('log').scrollTop=$('log').scrollHeight;
    if(s.running!==on){on=s.running;upUI(on)}
    if(s.paused) $('badge').textContent='PAUSE';
  }catch{}
}

setInterval(poll,200);
document.addEventListener('keydown',e=>{
  if(e.key==='F5'){e.preventDefault();doToggle()}
  if(e.key==='F7'){e.preventDefault();doPause()}
});
</script>
</body></html>"""

# ═══ Start ═══
if __name__=="__main__":
    add_log("> AutoFish v2.0 Web UI")
    add_log(f"> Admin: {'YES' if is_admin() else 'NO!'}")
    try: add_log(f"> Tesseract {pytesseract.get_tesseract_version()}")
    except: add_log("> Tesseract NOT FOUND!")

    api=Api()
    window=webview.create_window(
        "AutoFish by Herlove",
        html=HTML,
        width=500, height=720,
        resizable=False,
        on_top=True,
        js_api=api
    )
    webview.start(debug=False)

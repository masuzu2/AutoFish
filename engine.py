"""
AutoFish Engine - HTTP API for Tauri UI
รัน: python engine.py
Tauri UI เชื่อมผ่าน http://localhost:8765
"""
import time,sys,os,json,threading,ctypes,random
from http.server import HTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
import base64,io

SCRIPT_DIR=os.path.dirname(os.path.abspath(__file__))

# ═══ Auto Admin ═══
def is_admin():
    if sys.platform!='win32': return True
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False
if not is_admin() and sys.platform=='win32':
    try: ctypes.windll.shell32.ShellExecuteW(None,"runas",sys.executable,f'"{os.path.abspath(__file__)}"',None,1)
    except: pass
    sys.exit()

try:
    import mss,cv2,numpy as np
    from PIL import Image,ImageGrab
    import pytesseract
except ImportError as e:
    print(f"pip install mss opencv-python numpy Pillow pytesseract"); sys.exit(1)
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

# ═══ OCR ═══
VALID=set("qweasd")
from collections import Counter

def _ocr_slot(gray_slot):
    if gray_slot is None or gray_slot.size<20: return None
    kernel=np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    sharp=cv2.filter2D(gray_slot,-1,kernel)
    big=cv2.resize(sharp,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
    votes=[]
    for m in range(3):
        try:
            if m==0: _,t=cv2.threshold(big,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            elif m==1:
                _,t=cv2.threshold(big,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
                t=cv2.bitwise_not(t)
            else: _,t=cv2.threshold(big,180,255,cv2.THRESH_BINARY)
            if np.count_nonzero(t)>t.size//2: t=cv2.bitwise_not(t)
            txt=pytesseract.image_to_string(t,config='--psm 10 -c tessedit_char_whitelist=QWEASDqweasd').strip().lower()
            for c in txt:
                if c in VALID: votes.append(c); break
        except: continue
    if not votes: return None
    return Counter(votes).most_common(1)[0][0]

def read_fast(gray,num):
    if gray is None or gray.size<100: return None
    h,w=gray.shape[:2]
    trim=int(w*0.05); uw=w-trim if trim>3 else w
    kernel=np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    proc=cv2.filter2D(gray[:,:uw],-1,kernel)
    proc=cv2.GaussianBlur(proc,(3,3),0)
    big=cv2.resize(proc,None,fx=2,fy=2,interpolation=cv2.INTER_LINEAR)
    line=None
    for m in range(3):
        try:
            if m==0: _,t=cv2.threshold(big,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            elif m==1:
                _,t=cv2.threshold(big,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
                t=cv2.bitwise_not(t)
            else: _,t=cv2.threshold(big,180,255,cv2.THRESH_BINARY)
            if np.count_nonzero(t)>t.size//2: t=cv2.bitwise_not(t)
            txt=pytesseract.image_to_string(t,config='--psm 7 -c tessedit_char_whitelist=QWEASDqweasd').strip().lower()
            chars=[c for c in txt if c in VALID]
            if len(chars)==num and all(c in VALID for c in chars): line=chars; break
        except: continue
    if line:
        sw=uw//num
        last=_ocr_slot(gray[:,(num-1)*sw:uw])
        if last and last!=line[-1]: line[-1]=last
        return line
    sw=uw//num
    chars=[]
    for i in range(num):
        pad=max(sw//10,2)
        chars.append(_ocr_slot(gray[:,max(0,i*sw-pad):min(uw,(i+1)*sw+pad)]))
    return chars if all(c is not None for c in chars) else None

# ═══ Global State ═══
state={
    "running":False,"region":None,"keys":0,"fish":0,"fps":0,
    "last_keys":"","log":[],"preview_b64":"","start_time":0,
    "num_keys":5,"key_delay":60,"auto_cast":False,"cast_key":"e","cast_delay":5
}
CFG=os.path.join(SCRIPT_DIR,"config.json")
try:
    with open(CFG,"r") as f:
        c=json.load(f)
        state["region"]=c.get("region")
        state["num_keys"]=c.get("nk",5)
        state["key_delay"]=c.get("kd",60)
except: pass

def save_state():
    try:
        with open(CFG,"w") as f:
            json.dump({"region":state["region"],"nk":state["num_keys"],"kd":state["key_delay"]},f)
    except: pass

def add_log(msg):
    state["log"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    if len(state["log"])>50: state["log"]=state["log"][-50:]
    print(msg)

# ═══ Main Loop ═══
def run_loop():
    num=state["num_keys"]; kd=state["key_delay"]/1000
    state["keys"]=0; state["fish"]=0; state["start_time"]=time.time()
    lt=time.time()
    add_log("> Scanning...")
    lseq=""
    while state["running"]:
        try:
            r=state["region"]
            if not r: time.sleep(0.1); continue
            f=grab(r)
            if f is None: time.sleep(0.04); continue
            g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
            now=time.time(); state["fps"]=int(1.0/max(now-lt,0.001)); lt=now
            # Preview
            h2,w2=f.shape[:2]; nw=300; nh=max(int(h2*nw/w2),10)
            small=cv2.resize(f,(nw,nh))
            _,buf=cv2.imencode('.jpg',small,[cv2.IMWRITE_JPEG_QUALITY,50])
            state["preview_b64"]=base64.b64encode(buf).decode()
            k=read_fast(g,num)
            if k and len(k)==num:
                seq="".join(k)
                if seq!=lseq:
                    state["fish"]+=1
                    state["last_keys"]=" ".join(x.upper() for x in k)
                    add_log(f"> #{state['fish']} {state['last_keys']}")
                    if random.random()<0.05: time.sleep(random.uniform(0.3,1.0))
                    for key in k:
                        if not state["running"]: break
                        ok=press_key(key); state["keys"]+=1
                        if not ok: time.sleep(0.02); press_key(key)
                        time.sleep(kd+random.uniform(0.03,0.12))
                    lseq=seq
                    if state["auto_cast"] and state["running"]:
                        def _cast():
                            time.sleep(state["cast_delay"]+random.uniform(0.2,0.8))
                            if state["running"]:
                                press_key(state["cast_key"])
                                add_log("> Cast!")
                        threading.Thread(target=_cast,daemon=True).start()
                        lseq=""
                    else: time.sleep(0.6+random.uniform(0.1,0.3))
                else: time.sleep(0.03)
            else: time.sleep(0.04)
        except Exception as e:
            add_log(f"> Error: {e}"); time.sleep(0.5)
    add_log("> Stopped")

# ═══ HTTP API ═══
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path=urlparse(self.path).path
        params=parse_qs(urlparse(self.path).query)

        if path=="/status":
            elapsed=int(time.time()-state["start_time"]) if state["running"] else 0
            m,s=divmod(elapsed,60)
            data={
                "running":state["running"],"keys":state["keys"],"fish":state["fish"],
                "fps":state["fps"],"time":f"{m:02d}:{s:02d}",
                "last_keys":state["last_keys"],"region":state["region"],
                "log":state["log"][-20:],"admin":is_admin()
            }
            self._json(data)

        elif path=="/preview":
            self._json({"b64":state["preview_b64"]})

        elif path=="/start":
            if not state["region"]:
                self._json({"ok":False,"msg":"No region"}); return
            state["num_keys"]=int(params.get("keys",[5])[0])
            state["key_delay"]=int(params.get("delay",[60])[0])
            state["auto_cast"]=params.get("cast",["0"])[0]=="1"
            state["cast_key"]=params.get("castkey",["e"])[0]
            state["cast_delay"]=int(params.get("castdelay",[5])[0])
            if not state["running"]:
                state["running"]=True
                threading.Thread(target=run_loop,daemon=True).start()
                add_log("> Started!")
            self._json({"ok":True})

        elif path=="/stop":
            state["running"]=False
            self._json({"ok":True})

        elif path=="/region":
            x=int(params.get("x",[0])[0]); y=int(params.get("y",[0])[0])
            w=int(params.get("w",[0])[0]); h=int(params.get("h",[0])[0])
            if w>10 and h>10:
                state["region"]={"left":x,"top":y,"width":w,"height":h}
                save_state()
                add_log(f"> Region: {w}x{h} @ ({x},{y})")
                self._json({"ok":True})
            else:
                self._json({"ok":False})

        elif path=="/testkey":
            press_key('d'); time.sleep(0.1); press_key('s')
            add_log("> Pressed D+S")
            self._json({"ok":True})

        elif path=="/testread":
            r=state["region"]
            if not r: self._json({"ok":False,"keys":[]}); return
            f=grab(r)
            if f is None: self._json({"ok":False,"keys":[]}); return
            g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
            k=read_fast(g,state["num_keys"])
            self._json({"ok":True,"keys":k or []})

        else:
            self._json({"error":"unknown"})

    def _json(self,data):
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self,*args): pass  # silence logs

if __name__=="__main__":
    add_log(f"> AutoFish Engine v5.1")
    add_log(f"> Admin: {'YES' if is_admin() else 'NO'}")
    try: add_log(f"> Tesseract {pytesseract.get_tesseract_version()}")
    except: add_log("> Tesseract NOT FOUND!")
    if state["region"]: add_log(f"> Region loaded")

    port=8765
    server=HTTPServer(("127.0.0.1",port),Handler)
    add_log(f"> API running on http://localhost:{port}")
    print(f"\n  AutoFish Engine running on http://localhost:{port}\n")
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nShutdown")

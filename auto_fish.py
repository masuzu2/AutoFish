"""
AutoFish by Herlove v5.0 ULTIMATE
DXcam + Template 5ms + SendInput Scancode
"""

import time, sys, os, json, threading, ctypes, random
import tkinter as tk
from tkinter import messagebox
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION = "5.0"

# ═══ Auto Admin ═══
def is_admin():
    if sys.platform != 'win32': return True
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if not is_admin() and sys.platform == 'win32':
    try: ctypes.windll.shell32.ShellExecuteW(None,"runas",sys.executable,f'"{os.path.abspath(__file__)}"',None,1)
    except: pass
    sys.exit()

try:
    import keyboard as kb, mss, cv2, numpy as np
    from PIL import Image, ImageTk, ImageGrab
    import pytesseract
except ImportError as e:
    root=tk.Tk(); root.withdraw()
    messagebox.showerror("AutoFish",f"pip install keyboard mss opencv-python numpy Pillow pytesseract"); sys.exit(1)

for p in [r"C:\Program Files\Tesseract-OCR\tesseract.exe",r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]:
    if os.path.exists(p): pytesseract.pytesseract.tesseract_cmd=p; break

# ═══ SendInput Scancode (Hardware) ═══
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
        ii=IU(); ii.ki=KI(0,sc,0x0008,0,ctypes.pointer(ex))
        x=INP(1,ii); ctypes.windll.user32.SendInput(1,ctypes.pointer(x),ctypes.sizeof(x))
        time.sleep(random.uniform(0.03,0.08))
        ii2=IU(); ii2.ki=KI(0,sc,0x0008|0x0002,0,ctypes.pointer(ex))
        x2=INP(1,ii2); ctypes.windll.user32.SendInput(1,ctypes.pointer(x2),ctypes.sizeof(x2))
        return True
    except Exception: return False

# ═══ Capture (DXcam → mss → PIL) ═══
_cam=None; _sct=None; CAP="mss"
try:
    import dxcam; _cam=dxcam.create(); CAP="dxcam"
except Exception: pass

def grab(r):
    global _sct
    L,T,W,H=int(r["left"]),int(r["top"]),int(r["width"]),int(r["height"])
    if _cam:
        try:
            f=_cam.grab(region=(L,T,L+W,T+H))
            if f is not None: return cv2.cvtColor(np.array(f),cv2.COLOR_RGB2BGR)
        except Exception: pass
    if _sct is None:
        try: _sct=mss.mss()
        except Exception: pass
    if _sct:
        try:
            a=np.array(_sct.grab({"left":L,"top":T,"width":W,"height":H}))
            if a.size>0: return cv2.cvtColor(a,cv2.COLOR_BGRA2BGR)
        except Exception: pass
    try:
        i=ImageGrab.grab(bbox=(L,T,L+W,T+H))
        if i: return cv2.cvtColor(np.array(i),cv2.COLOR_RGB2BGR)
    except Exception: pass
    return None

# ═══ Template Engine (FAST: ~1ms per slot) ═══
VALID=set("qweasd")
TD=os.path.join(SCRIPT_DIR,"templates"); os.makedirs(TD,exist_ok=True)
TH=48; tmpls={}

def load_t():
    global tmpls; tmpls.clear()
    for f in os.listdir(TD):
        if not f.endswith(".png"): continue
        k=f.split("_")[0].split(".")[0].lower()
        if len(k)==1 and k in VALID:
            img=cv2.imread(os.path.join(TD,f),cv2.IMREAD_GRAYSCALE)
            if img is not None:
                h,w=img.shape[:2]
                tmpls.setdefault(k,[]).append(cv2.resize(img,(max(int(w*TH/h),3),TH)))

def save_t(key,gray):
    key=key.lower()
    n=len([f for f in os.listdir(TD) if f.startswith(key) and f.endswith(".png")])
    if n>=3: return
    cv2.imwrite(os.path.join(TD,f"{key}.png" if n==0 else f"{key}_{n+1}.png"),gray)
    h,w=gray.shape[:2]
    tmpls.setdefault(key,[]).append(cv2.resize(gray,(max(int(w*TH/h),3),TH)))

def match_t(gray):
    """Template match 1 slot (~1ms)"""
    if not tmpls or gray is None or gray.size<20: return None,0
    h,w=gray.shape[:2]
    if h<3 or w<3: return None,0
    roi=cv2.resize(gray,(max(int(w*TH/h),3),TH))
    bc,bv=None,0
    for ch,ts in tmpls.items():
        for t in ts:
            tw=t.shape[1]
            if tw>roi.shape[1]*1.5 or tw<roi.shape[1]*0.3: continue
            tgt=roi
            if tw>roi.shape[1] or t.shape[0]>roi.shape[0]:
                px,py=max(0,(tw-roi.shape[1])//2+3),max(0,(t.shape[0]-roi.shape[0])//2+3)
                tgt=cv2.copyMakeBorder(roi,py,py,px,px,cv2.BORDER_CONSTANT,value=0)
            try:
                res=cv2.matchTemplate(tgt,t,cv2.TM_CCOEFF_NORMED)
                _,mx,_,_=cv2.minMaxLoc(res)
                if mx>bv: bc,bv=ch,mx
                if mx>0.85: return bc,bv
            except Exception: continue
    return (bc,bv) if bv>0.55 else (None,0)

def ocr_one(gray):
    """Tesseract 1 slot (~50ms) - ใช้แค่ตอนเรียนรู้"""
    if gray is None or gray.size<20: return None
    big=cv2.resize(gray,None,fx=4,fy=4,interpolation=cv2.INTER_CUBIC)
    for tv in [180,160]:
        try:
            _,t=cv2.threshold(big,tv,255,cv2.THRESH_BINARY)
            if np.count_nonzero(t)>t.size//2: t=cv2.bitwise_not(t)
            txt=pytesseract.image_to_string(t,config='--psm 10 -c tessedit_char_whitelist=QWEASDqweasd').strip().lower()
            for c in txt:
                if c in VALID: return c
        except Exception: continue
    return None

def prep(gray):
    """Threshold + crop สำหรับ template"""
    if gray is None or gray.size<20: return None
    _,t=cv2.threshold(gray,180,255,cv2.THRESH_BINARY)
    if np.count_nonzero(t)>t.size//2: t=cv2.bitwise_not(t)
    cs=np.argwhere(t>127)
    if len(cs)<5: return None
    y0,x0=cs.min(0); y1,x1=cs.max(0)
    c=t[max(0,y0-1):y1+2,max(0,x0-1):x1+2]
    return c if c.shape[0]>3 and c.shape[1]>3 else None

def read_fast(gray,num):
    """อ่านทั้งแถว: Template ~5ms total / OCR ~250ms (แค่ครั้งแรก)"""
    if gray is None or gray.size<100: return None
    h,w=gray.shape[:2]
    trim=int(w*0.08); uw=w-trim if trim>3 else w
    has_t=len(tmpls)>=4
    chars=[]
    for i in range(num):
        x1=int(i*uw/num); x2=int((i+1)*uw/num)
        pad=max((x2-x1)//12,2)
        slot=gray[:,max(0,x1-pad):min(uw,x2+pad)]
        p=prep(slot); ch=None
        if has_t and p is not None:
            ch,_=match_t(p)
        if ch is None:
            ch=ocr_one(slot)
            if ch and p is not None: save_t(ch,p)
        chars.append(ch)
    return chars if all(c is not None and c in VALID for c in chars) else None

load_t()

# ═══ Debug Preview ═══
_fc=0
def debug_img(frame,keys,num):
    global _fc; _fc+=1
    h,w=frame.shape[:2]; sw=w//num
    pt,pb=30,24; ch=h+pt+pb
    cv=np.zeros((ch,w,3),dtype=np.uint8); cv[:]=10
    cv[pt:pt+h,0:w]=frame
    cv2.rectangle(cv,(0,0),(w-1,pt-1),(15,23,42),-1)
    sx=int((_fc*8)%w)
    cv2.line(cv,(sx,0),(sx,pt),(34,211,238),1)
    m="TMPL" if len(tmpls)>=4 else "OCR"
    cv2.putText(cv,f"AUTOFISH [{m}]",(6,12),cv2.FONT_HERSHEY_SIMPLEX,0.35,(34,211,238),1)
    if keys:
        cv2.putText(cv,"  ".join(k.upper() for k in keys),(6,26),cv2.FONT_HERSHEY_SIMPLEX,0.45,(74,222,128),1)
    for i in range(num):
        x1,x2=i*sw,min((i+1)*sw,w)
        if keys and i<len(keys) and keys[i]:
            ov=cv[pt:pt+h,x1:x2].copy()
            cv2.addWeighted(ov,0.85,np.full_like(ov,(15,40,10)),0.15,0,cv[pt:pt+h,x1:x2])
            cv2.rectangle(cv,(x1+1,pt+1),(x2-1,pt+h-1),(74,222,128),2)
            l=keys[i].upper(); fs=1.0 if sw>35 else 0.7
            (tw2,th2),_=cv2.getTextSize(l,cv2.FONT_HERSHEY_SIMPLEX,fs,2)
            cv2.putText(cv,l,(x1+(sw-tw2)//2,pt+(h+th2)//2),cv2.FONT_HERSHEY_SIMPLEX,fs,(74,222,128),2)
        else:
            cv2.rectangle(cv,(x1+1,pt+1),(x2-1,pt+h-1),(40,50,70),1)
    gi=int(abs((_fc%60)-30)*3)
    cv2.rectangle(cv,(0,pt),(w-1,pt+h-1),(56+gi//4,189,248),2)
    by=pt+h
    cv2.rectangle(cv,(0,by),(w-1,ch-1),(15,23,42),-1)
    for i in range(num):
        cx2=int(w/num*i+w/num/2); cy2=by+pb//2
        if keys and i<len(keys) and keys[i]: cv2.circle(cv,(cx2,cy2),4,(74,222,128),-1)
        else: cv2.circle(cv,(cx2,cy2),4,(40,50,70),-1)
    return cv

# ═══ Config ═══
CFG=os.path.join(SCRIPT_DIR,"config.json"); region=None
def load_cfg():
    global region
    try:
        with open(CFG,"r") as f: c=json.load(f); region=c.get("region"); return c
    except Exception: return {}
def save_cfg(**kw):
    c=load_cfg(); c.update(kw); c["region"]=region
    try:
        with open(CFG,"w") as f: json.dump(c,f,indent=2)
    except Exception: pass
load_cfg()

# ═══ Theme ═══
BG="#020617";BG2="#0a1128";CARD="#0f172a";CARD2="#1e293b"
ACCENT="#22d3ee";GLOW="#0ea5e9";GREEN="#4ade80";GREEN2="#22c55e"
RED="#f87171";ORANGE="#fb923c";PURPLE="#a78bfa";DIM="#334155";DIM2="#1e293b";WHITE="#e2e8f0"

# ═══ App ═══
class App:
    def __init__(self):
        self.root=tk.Tk()
        self.root.title(f"AutoFish v{VERSION}")
        self.root.geometry("500x720")
        self.root.configure(bg=BG)
        self.root.resizable(False,False)
        self.root.attributes("-topmost",True)
        self.running=False; self.session_keys=0; self.session_start=0
        self.dbg=None; self.fish=0; self.scans=0; self.lt=time.time()
        self.nk=tk.IntVar(value=load_cfg().get("nk",5))
        self.kd=tk.IntVar(value=load_cfg().get("kd",60))
        self.ac=tk.BooleanVar(value=load_cfg().get("ac",False))
        self.ck=tk.StringVar(value=load_cfg().get("ck","e"))
        self.cd=tk.IntVar(value=load_cfg().get("cd",5))
        try:
            ico=os.path.join(SCRIPT_DIR,"logo.png")
            if os.path.exists(ico):
                img=ImageTk.PhotoImage(Image.open(ico).resize((32,32),Image.LANCZOS))
                self.root.iconphoto(True,img); self._ico=img
        except Exception: pass
        self._build(); self._prev_loop(); self._tick()
        self.root.protocol("WM_DELETE_WINDOW",self._quit)

    def _build(self):
        hdr=tk.Frame(self.root,bg=BG); hdr.pack(fill=tk.X,padx=18,pady=(12,0))
        try:
            lp=os.path.join(SCRIPT_DIR,"mascot.png")
            if not os.path.exists(lp): lp=os.path.join(SCRIPT_DIR,"logo.png")
            if os.path.exists(lp):
                li=Image.open(lp).resize((56,56),Image.LANCZOS)
                self._logo=ImageTk.PhotoImage(li)
                lf=tk.Frame(hdr,bg=CARD,highlightbackground=GLOW,highlightthickness=1)
                lf.pack(side=tk.LEFT,padx=(0,12))
                tk.Label(lf,image=self._logo,bg=CARD,padx=2,pady=2).pack()
        except Exception: pass
        tf=tk.Frame(hdr,bg=BG); tf.pack(side=tk.LEFT,fill=tk.X,expand=True)
        tk.Label(tf,text="AutoFish",bg=BG,fg=WHITE,font=("Segoe UI",22,"bold")).pack(anchor="w")
        s=tk.Frame(tf,bg=BG); s.pack(anchor="w")
        tk.Label(s,text="ULTIMATE",bg=BG,fg=ACCENT,font=("Consolas",9,"bold")).pack(side=tk.LEFT)
        tk.Label(s,text=f" v{VERSION}",bg=BG,fg=DIM,font=("Consolas",9)).pack(side=tk.LEFT)
        tk.Label(tf,text="by Herlove",bg=BG,fg=DIM,font=("Segoe UI",8)).pack(anchor="w")
        self.sf=tk.Frame(hdr,bg=CARD,highlightbackground=DIM,highlightthickness=1)
        self.sf.pack(side=tk.RIGHT)
        self.dot=tk.Label(self.sf,text=" ",bg=DIM,font=("Segoe UI",3))
        self.dot.pack(side=tk.LEFT,padx=(6,4),pady=6)
        self.st=tk.Label(self.sf,text="OFF",bg=CARD,fg=DIM,font=("Consolas",9,"bold"))
        self.st.pack(side=tk.LEFT,padx=(0,8),pady=6)

        line=tk.Canvas(self.root,bg=BG,height=2,highlightthickness=0)
        line.pack(fill=tk.X,padx=18,pady=(8,0))
        for i in range(464):
            t=i/464; line.create_line(i+18,0,i+18,2,fill=f"#{int(14+(74-14)*t):02x}{int(165+(222-165)*t):02x}{int(233+(128-233)*t):02x}")

        nt=sum(len(v) for v in tmpls.values())
        tk.Label(self.root,text=f"Capture: {CAP} | Templates: {nt} | {'FAST' if nt>=4 else 'Learning'}",
                 bg=BG,fg=DIM2,font=("Consolas",7)).pack(pady=(4,0))

        po=tk.Frame(self.root,bg=GLOW); po.pack(fill=tk.X,padx=18,pady=(4,0))
        pi=tk.Frame(po,bg=BG2); pi.pack(fill=tk.X,padx=1,pady=1)
        self.prev=tk.Label(pi,bg="#030810",text="F6 Select Region",fg=DIM,font=("Consolas",9))
        self.prev.pack(fill=tk.X,ipady=38)

        self.seq=tk.Label(self.root,text="",bg=BG,fg=ACCENT,font=("Consolas",14,"bold"))
        self.seq.pack(pady=(3,0))

        bo=tk.Frame(self.root,bg=GREEN2); bo.pack(fill=tk.X,padx=18,pady=(3,0))
        self.btn=tk.Button(bo,text="START",bg=GREEN,fg=BG,font=("Segoe UI",15,"bold"),
            relief="flat",pady=7,cursor="hand2",activebackground=GREEN2,bd=0,command=self.toggle)
        self.btn.pack(fill=tk.X,padx=1,pady=1)
        self.btn.bind("<Enter>",lambda e:self.btn.config(bg=GREEN2 if not self.running else "#ef4444"))
        self.btn.bind("<Leave>",lambda e:self.btn.config(bg=GREEN if not self.running else RED))
        self.bo=bo

        da=tk.Frame(self.root,bg=CARD,highlightbackground=DIM2,highlightthickness=1)
        da.pack(fill=tk.X,padx=18,pady=(4,0))
        di=tk.Frame(da,bg=CARD); di.pack(fill=tk.X,padx=6,pady=6)
        for a,i,l,c in [("cnt","0","KEYS",ACCENT),("fsh","0","FISH",GLOW),
            ("rt","0%","RATE",GREEN),("fps","0.0","FPS",PURPLE),("tmr","00:00","TIME",ORANGE)]:
            if a!="cnt": tk.Frame(di,bg=DIM2,width=1).pack(side=tk.LEFT,fill=tk.Y,padx=3)
            f=tk.Frame(di,bg=CARD); f.pack(side=tk.LEFT,expand=True)
            lb=tk.Label(f,text=i,bg=CARD,fg=c,font=("Consolas",15,"bold")); lb.pack()
            tk.Label(f,text=l,bg=CARD,fg=DIM,font=("Consolas",6,"bold")).pack()
            setattr(self,"l_"+a,lb)

        ct=tk.Frame(self.root,bg=CARD,highlightbackground=DIM2,highlightthickness=1)
        ct.pack(fill=tk.X,padx=18,pady=(4,0))
        ci=tk.Frame(ct,bg=CARD); ci.pack(fill=tk.X,padx=6,pady=5)
        for t,c,cmd in [("Select F6",ACCENT,self.pick),("Test Read",GREEN,self.tread),
                         ("Test Key",PURPLE,self.tkey),("Clear",RED,self.clr)]:
            b=tk.Button(ci,text=t,bg=BG2,fg=c,font=("Segoe UI",8,"bold"),
                relief="flat",padx=6,pady=2,cursor="hand2",command=cmd)
            b.pack(side=tk.LEFT,padx=2)
        self.lreg=tk.Label(ci,text="not set",bg=CARD,fg=ORANGE,font=("Consolas",8,"bold"))
        self.lreg.pack(side=tk.RIGHT,padx=4)

        sf=tk.Frame(self.root,bg=CARD,highlightbackground=DIM2,highlightthickness=1)
        sf.pack(fill=tk.X,padx=18,pady=(4,0))
        self._sl(sf,"Keys",self.nk,2,10,ACCENT)
        self._sl(sf,"Delay ms",self.kd,30,200,GREEN)
        af=tk.Frame(sf,bg=CARD); af.pack(fill=tk.X,padx=10,pady=(1,4))
        tk.Checkbutton(af,text="Auto Cast",variable=self.ac,bg=CARD,fg=WHITE,
            selectcolor=BG,activebackground=CARD,font=("Segoe UI",9)).pack(side=tk.LEFT)
        tk.Label(af,text="Key:",bg=CARD,fg=DIM,font=("Segoe UI",8)).pack(side=tk.LEFT,padx=(8,2))
        tk.Entry(af,textvariable=self.ck,bg=BG,fg=ACCENT,font=("Consolas",10,"bold"),
            width=3,relief="flat",justify="center").pack(side=tk.LEFT)
        tk.Label(af,text="Wait:",bg=CARD,fg=DIM,font=("Segoe UI",8)).pack(side=tk.LEFT,padx=(6,2))
        vl=tk.Label(af,text=str(self.cd.get()),bg=CARD,fg=ORANGE,font=("Consolas",9,"bold"),width=2)
        vl.pack(side=tk.LEFT)
        tk.Scale(af,from_=1,to=20,orient=tk.HORIZONTAL,variable=self.cd,bg=CARD,fg=CARD,
            troughcolor=BG,highlightthickness=0,showvalue=False,length=50,sliderlength=10,
            activebackground=ORANGE,command=lambda v,l=vl:l.config(text=str(int(float(v))))).pack(side=tk.LEFT)

        lo=tk.Frame(self.root,bg=DIM2); lo.pack(fill=tk.BOTH,expand=True,padx=18,pady=(4,0))
        self.log_b=tk.Text(lo,bg="#030810",fg=GREEN,font=("Consolas",9),
            relief="flat",wrap=tk.WORD,state=tk.DISABLED,padx=8,pady=4)
        self.log_b.pack(fill=tk.BOTH,expand=True,padx=1,pady=1)

        ft=tk.Frame(self.root,bg=BG); ft.pack(fill=tk.X,padx=18,pady=(3,6))
        tk.Label(ft,text="F5 Start | F6 Region",bg=BG,fg=DIM2,font=("Consolas",7)).pack(side=tk.LEFT)
        tk.Label(ft,text="Admin" if is_admin() else "NO ADMIN!",bg=BG,
            fg=DIM2 if is_admin() else RED,font=("Consolas",7,"bold")).pack(side=tk.RIGHT)

        self.root.bind("<F5>",lambda e:self.toggle())
        self.root.bind("<F6>",lambda e:self.pick())
        self.log(f"> AutoFish v{VERSION} ULTIMATE")
        self.log(f"> {CAP} | {sum(len(v) for v in tmpls.values())} templates")
        if region: self.log(f"> Region: {region['width']}x{region['height']}")

    def _sl(self,p,l,v,lo,hi,c):
        f=tk.Frame(p,bg=CARD); f.pack(fill=tk.X,padx=10,pady=1)
        tk.Label(f,text=l,bg=CARD,fg=WHITE,font=("Segoe UI",9)).pack(side=tk.LEFT)
        vl=tk.Label(f,text=str(v.get()),bg=CARD,fg=c,font=("Consolas",10,"bold"),width=4)
        vl.pack(side=tk.RIGHT)
        tk.Scale(f,from_=lo,to=hi,orient=tk.HORIZONTAL,variable=v,bg=CARD,fg=CARD,
            troughcolor=BG,highlightthickness=0,showvalue=False,length=110,sliderlength=14,
            activebackground=c,command=lambda v2,l2=vl:l2.config(text=str(int(float(v2))))).pack(side=tk.RIGHT,padx=3)

    def _tick(self):
        if self.running:
            e=int(time.time()-self.session_start); m,s=divmod(e,60)
            self.l_tmr.config(text=f"{m:02d}:{s:02d}")
            self.dot.config(bg=GREEN if self.dot.cget("bg")==CARD else CARD)
            if self.scans>0: self.l_rt.config(text=f"{min(int(self.fish/max(self.scans,1)*100),100)}%")
        self.root.after(500,self._tick)

    def pick(self):
        global region
        if self.running: return
        self.root.iconify(); time.sleep(0.3)
        sel=tk.Toplevel(self.root); sel.overrideredirect(True)
        sel.attributes("-topmost",True); sel.attributes("-alpha",0.25)
        sw,sh=sel.winfo_screenwidth(),sel.winfo_screenheight()
        sel.geometry(f"{sw}x{sh}+0+0"); sel.configure(bg="black")
        c=tk.Canvas(sel,bg="black",highlightthickness=0,cursor="cross"); c.pack(fill=tk.BOTH,expand=True)
        c.create_rectangle(sw//2-220,12,sw//2+220,82,fill="black",outline=ACCENT,width=2)
        c.create_text(sw//2,28,text="Drag over QTE keys only",fill=ACCENT,font=("Segoe UI",14,"bold"))
        c.create_text(sw//2,50,text="Exclude counter circle",fill=WHITE,font=("Segoe UI",10))
        c.create_text(sw//2,68,text="ESC = Cancel",fill=DIM,font=("Segoe UI",9))
        p=c.create_text(sw//2,100,text="",fill=ACCENT,font=("Consolas",12,"bold"))
        st={"sx":0,"sy":0,"r":None}
        c.bind("<Motion>",lambda e:c.itemconfig(p,text=f"X:{e.x} Y:{e.y}"))
        def _p(e):
            st["sx"],st["sy"]=e.x,e.y
            if st["r"]: c.delete(st["r"])
            st["r"]=c.create_rectangle(e.x,e.y,e.x,e.y,outline=ACCENT,width=3)
        def _d(e):
            c.coords(st["r"],st["sx"],st["sy"],e.x,e.y); c.delete("sz")
            c.create_text((st["sx"]+e.x)//2,min(st["sy"],e.y)-14,
                text=f"{abs(e.x-st['sx'])}x{abs(e.y-st['sy'])}",fill=ACCENT,font=("Consolas",13,"bold"),tags="sz")
        def _r(e):
            global region
            x1,y1=min(st["sx"],e.x),min(st["sy"],e.y); x2,y2=max(st["sx"],e.x),max(st["sy"],e.y)
            if (x2-x1)>10 and (y2-y1)>10:
                region={"left":x1,"top":y1,"width":x2-x1,"height":y2-y1}; save_cfg()
                self.lreg.config(text=f"{x2-x1}x{y2-y1}",fg=GREEN)
                self.log(f"> Region set")
            sel.destroy(); self.root.deiconify()
        c.bind("<ButtonPress-1>",_p); c.bind("<B1-Motion>",_d); c.bind("<ButtonRelease-1>",_r)
        sel.bind("<Escape>",lambda e:(sel.destroy(),self.root.deiconify()))
        sel.after(50,sel.focus_force)

    def tread(self):
        if not region: return
        t0=time.time(); f=grab(region)
        if f is None: self.log("> Capture fail"); return
        g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
        k=read_fast(g,self.nk.get()); ms=int((time.time()-t0)*1000)
        m="TMPL" if len(tmpls)>=4 else "OCR"
        self.dbg=debug_img(f,k,self.nk.get()); self._show()
        self.log(f"> [{m}] {ms}ms: {' '.join(x.upper() for x in k)}" if k else f"> Fail {ms}ms")

    def tkey(self):
        self.log("> D+S in 3s")
        def _do():
            time.sleep(3); press_key('d'); time.sleep(0.2); press_key('s')
            self.root.after(0,self.log,"> Pressed!")
        threading.Thread(target=_do,daemon=True).start()

    def clr(self):
        import shutil
        if os.path.isdir(TD): shutil.rmtree(TD)
        os.makedirs(TD,exist_ok=True); tmpls.clear()
        self.log("> Templates cleared")

    def toggle(self):
        if self.running: self.running=False
        else:
            if not region: messagebox.showwarning("AutoFish","F6 Select Region!"); return
            self.running=True
            save_cfg(nk=self.nk.get(),kd=self.kd.get(),ac=self.ac.get(),ck=self.ck.get(),cd=self.cd.get())
            self.btn.config(text="STOP",bg=RED); self.bo.config(bg="#b91c1c")
            self.st.config(text="ON",fg=GREEN); self.dot.config(bg=GREEN)
            self.sf.config(highlightbackground=GREEN)
            self.log("> Go! 3s...")
            threading.Thread(target=self._run,daemon=True).start()

    def _run(self):
        num=self.nk.get(); kd=self.kd.get()/1000
        ac=self.ac.get(); ck=self.ck.get().lower(); cd=self.cd.get()
        self.session_keys=0; self.session_start=time.time()
        self.fish=0; self.scans=0; self.lt=time.time()
        t=grab(region)
        if t is None:
            self.root.after(0,self.log,"> Capture fail"); self.running=False
            self.root.after(0,self._rst); return
        time.sleep(3); self.root.after(0,self.log,"> Scanning..."); lseq=""
        while self.running:
            try:
                f=grab(region)
                if f is None: time.sleep(0.04); continue
                g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
                now=time.time(); fps=1.0/max(now-self.lt,0.001); self.lt=now
                self.scans+=1
                k=read_fast(g,num); self.dbg=debug_img(f,k,num)
                if k and len(k)==num:
                    seq="".join(k)
                    if seq!=lseq:
                        self.fish+=1
                        self.root.after(0,self.log,f"> #{self.fish} {' '.join(x.upper() for x in k)}")
                        self.root.after(0,self.seq.config,{"text":" ".join(x.upper() for x in k)})
                        if random.random()<0.05: time.sleep(random.uniform(0.3,1.0))
                        for key in k:
                            if not self.running: break
                            ok=press_key(key)
                            if not ok: time.sleep(0.02); press_key(key)
                            self.session_keys+=1
                            time.sleep(kd+random.uniform(0.03,0.12))
                        if sys.platform=='win32':
                            try: import winsound; winsound.Beep(800,60)
                            except Exception: pass
                        self.root.after(0,self._upd,fps); lseq=seq
                        if ac and self.running:
                            time.sleep(cd+random.uniform(0.2,0.8))
                            if self.running: press_key(ck); time.sleep(2+random.uniform(0.3,0.7)); lseq=""
                        else: time.sleep(0.6+random.uniform(0.1,0.3))
                    else: time.sleep(0.03)
                else: time.sleep(0.04)
            except Exception as e:
                self.root.after(0,self.log,f"> {e}"); time.sleep(0.5)
        self.root.after(0,self._rst)

    def _upd(self,fps=0):
        self.l_cnt.config(text=str(self.session_keys))
        self.l_fsh.config(text=str(self.fish))
        self.l_fps.config(text=f"{fps:.0f}")

    def _rst(self):
        self.btn.config(text="START",bg=GREEN); self.bo.config(bg=GREEN2)
        self.st.config(text="OFF",fg=DIM); self.dot.config(bg=DIM)
        self.sf.config(highlightbackground=DIM); self.seq.config(text="")
        self.log("> Stopped")

    def _show(self):
        if self.dbg is None: return
        try:
            rgb=cv2.cvtColor(self.dbg,cv2.COLOR_BGR2RGB)
            img=Image.fromarray(rgb); w,h=img.size
            nw=462; nh=max(int(h*nw/w),20)
            img=img.resize((nw,nh),Image.LANCZOS)
            ph=ImageTk.PhotoImage(img)
            self.prev.config(image=ph,text=""); self.prev.image=ph
        except Exception: pass

    def _prev_loop(self):
        if self.running and self.dbg is not None: self._show()
        elif region:
            try:
                f=grab(region)
                if f is not None:
                    d=debug_img(f,None,self.nk.get())
                    rgb=cv2.cvtColor(d,cv2.COLOR_BGR2RGB)
                    img=Image.fromarray(rgb); w,h=img.size
                    nw=462; nh=max(int(h*nw/w),20)
                    img=img.resize((nw,nh),Image.LANCZOS)
                    ph=ImageTk.PhotoImage(img)
                    self.prev.config(image=ph,text=""); self.prev.image=ph
            except Exception: pass
        self.root.after(100,self._prev_loop)

    def log(self,msg):
        self.log_b.config(state=tk.NORMAL)
        self.log_b.insert(tk.END,f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_b.see(tk.END)
        n=int(self.log_b.index("end-1c").split(".")[0])
        if n>60: self.log_b.delete("1.0",f"{n-60}.0")
        self.log_b.config(state=tk.DISABLED)

    def _quit(self): self.running=False; time.sleep(0.1); self.root.destroy()
    def run(self): self.root.mainloop()

if __name__=="__main__": App().run()

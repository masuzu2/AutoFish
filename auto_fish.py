"""
AutoFish by Herlove v2.0 (FAST)
OCR เร็ว + SendInput Scancode
"""
import time,sys,os,json,threading,ctypes,random
import tkinter as tk
from tkinter import messagebox
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
    import keyboard as kb,mss,cv2,numpy as np
    from PIL import Image,ImageTk,ImageGrab
    import pytesseract
except ImportError as e:
    root=tk.Tk();root.withdraw()
    messagebox.showerror("AutoFish",f"pip install keyboard mss opencv-python numpy Pillow pytesseract");sys.exit(1)
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

def make_debug(frame,keys,num):
    d=frame.copy();h,w=d.shape[:2];sw=w//num
    # กรอบบาง สีฟ้าอ่อน
    cv2.rectangle(d,(0,0),(w-1,h-1),(180,140,60),1)
    for i in range(num):
        x1,x2=i*sw,min((i+1)*sw,w)
        if keys and i<len(keys) and keys[i]:
            # เจอ: กรอบเขียว + ตัวอักษรกลาง
            cv2.rectangle(d,(x1+2,2),(x2-2,h-2),(0,200,0),2)
            l=keys[i].upper()
            fs=0.8 if sw>40 else 0.6
            (tw,th),_=cv2.getTextSize(l,cv2.FONT_HERSHEY_SIMPLEX,fs,2)
            tx=x1+(sw-tw)//2;ty=(h+th)//2
            cv2.putText(d,l,(tx,ty),cv2.FONT_HERSHEY_SIMPLEX,fs,(0,255,0),2)
        else:
            cv2.rectangle(d,(x1+2,2),(x2-2,h-2),(50,50,50),1)
    return d

CFG=os.path.join(SCRIPT_DIR,"config.json");region=None
def load_cfg():
    global region
    try:
        with open(CFG,"r") as f: c=json.load(f);region=c.get("region");return c
    except: return {}
def save_cfg(**kw):
    c=load_cfg();c.update(kw);c["region"]=region
    try:
        with open(CFG,"w") as f: json.dump(c,f,indent=2)
    except: pass
load_cfg()

BG="#020617";CARD="#0f172a";ACCENT="#22d3ee";GLOW="#0ea5e9"
GREEN="#4ade80";GREEN2="#22c55e";RED="#f87171";DIM="#334155";DIM2="#1e293b";WHITE="#e2e8f0"

class App:
    def __init__(self):
        self.root=tk.Tk();self.root.title("AutoFish v2.0")
        self.root.geometry("480x650");self.root.configure(bg=BG)
        self.root.resizable(False,False);self.root.attributes("-topmost",True)
        self.running=False;self.paused=False;self.keys=0;self.fish=0;self.scans=0
        self.lt=time.time();self.dbg=None;self.start_t=0
        self.nk=tk.IntVar(value=load_cfg().get("nk",5))
        self.kd=tk.IntVar(value=load_cfg().get("kd",60))
        try:
            ico=os.path.join(SCRIPT_DIR,"logo.png")
            if os.path.exists(ico):
                img=ImageTk.PhotoImage(Image.open(ico).resize((32,32),Image.LANCZOS))
                self.root.iconphoto(True,img);self._ico=img
        except: pass
        self._build();self._prev();self._tick()
        self.root.protocol("WM_DELETE_WINDOW",self._quit)

    def _build(self):
        hdr=tk.Frame(self.root,bg=BG);hdr.pack(fill=tk.X,padx=16,pady=(12,0))
        try:
            lp=os.path.join(SCRIPT_DIR,"mascot.png")
            if not os.path.exists(lp): lp=os.path.join(SCRIPT_DIR,"logo.png")
            if os.path.exists(lp):
                self._logo=ImageTk.PhotoImage(Image.open(lp).resize((48,48),Image.LANCZOS))
                tk.Label(hdr,image=self._logo,bg=BG).pack(side=tk.LEFT,padx=(0,10))
        except: pass
        tf=tk.Frame(hdr,bg=BG);tf.pack(side=tk.LEFT)
        tk.Label(tf,text="AutoFish",bg=BG,fg=WHITE,font=("Segoe UI",20,"bold")).pack(anchor="w")
        tk.Label(tf,text="v2.0 FAST | by Herlove",bg=BG,fg=DIM,font=("Segoe UI",8)).pack(anchor="w")
        self.st=tk.Label(hdr,text="OFF",bg=BG,fg=DIM,font=("Consolas",10,"bold"))
        self.st.pack(side=tk.RIGHT)

        pf=tk.Frame(self.root,bg=GLOW);pf.pack(fill=tk.X,padx=16,pady=(10,0))
        pi=tk.Frame(pf,bg="#0a1128");pi.pack(fill=tk.X,padx=1,pady=1)
        self.pv=tk.Label(pi,bg="#030810",text="F6 Select Region",fg=DIM,font=("Consolas",9))
        self.pv.pack(fill=tk.X,ipady=35)

        self.seq=tk.Label(self.root,text="",bg=BG,fg=ACCENT,font=("Consolas",14,"bold"))
        self.seq.pack(pady=(4,0))

        self.btn=tk.Button(self.root,text="START (F5)",bg=GREEN,fg=BG,
            font=("Segoe UI",14,"bold"),relief="flat",pady=6,command=self.toggle)
        self.btn.pack(fill=tk.X,padx=16,pady=(4,0))

        sf=tk.Frame(self.root,bg=CARD);sf.pack(fill=tk.X,padx=16,pady=(6,0))
        for a,v,l,c in [("lk","0","KEYS",ACCENT),("lf","0","FISH",GLOW),("lr","—","RATE","#a78bfa"),("lt2","00:00","TIME","#fb923c")]:
            f=tk.Frame(sf,bg=CARD);f.pack(side=tk.LEFT,expand=True,pady=6)
            lb=tk.Label(f,text=v,bg=CARD,fg=c,font=("Consolas",18,"bold"));lb.pack()
            tk.Label(f,text=l,bg=CARD,fg=DIM,font=("Consolas",7,"bold")).pack()
            setattr(self,a,lb)

        cf=tk.Frame(self.root,bg=CARD);cf.pack(fill=tk.X,padx=16,pady=(4,0))
        ci=tk.Frame(cf,bg=CARD);ci.pack(padx=6,pady=6)
        for t,c,cmd in [("Select F6",ACCENT,self.pick),("Test Read",GREEN,self.tread),("Test Key","#a78bfa",self.tkey)]:
            tk.Button(ci,text=t,bg="#0a1128",fg=c,font=("Segoe UI",8,"bold"),relief="flat",padx=6,pady=2,command=cmd).pack(side=tk.LEFT,padx=2)
        self.lr=tk.Label(ci,text="not set",bg=CARD,fg="#fb923c",font=("Consolas",8));self.lr.pack(side=tk.RIGHT,padx=4)

        stf=tk.Frame(self.root,bg=CARD);stf.pack(fill=tk.X,padx=16,pady=(4,0))
        for l,v,lo,hi,c in [("Keys",self.nk,2,10,ACCENT),("Delay",self.kd,30,200,GREEN)]:
            f=tk.Frame(stf,bg=CARD);f.pack(fill=tk.X,padx=10,pady=1)
            tk.Label(f,text=l,bg=CARD,fg=WHITE,font=("Segoe UI",9)).pack(side=tk.LEFT)
            vl=tk.Label(f,text=str(v.get()),bg=CARD,fg=c,font=("Consolas",10,"bold"),width=4);vl.pack(side=tk.RIGHT)
            tk.Scale(f,from_=lo,to=hi,orient=tk.HORIZONTAL,variable=v,bg=CARD,fg=CARD,troughcolor=BG,highlightthickness=0,showvalue=False,length=110,sliderlength=14,activebackground=c,command=lambda v2,l2=vl:l2.config(text=str(int(float(v2))))).pack(side=tk.RIGHT,padx=3)

        self.log_b=tk.Text(self.root,bg="#030810",fg=GREEN,font=("Consolas",9),height=6,relief="flat",wrap=tk.WORD,state=tk.DISABLED,padx=8,pady=4)
        self.log_b.pack(fill=tk.BOTH,expand=True,padx=16,pady=(6,8))

        self.root.bind("<F5>",lambda e:self.toggle())
        self.root.bind("<F6>",lambda e:self.pick())
        self.root.bind("<F7>",lambda e:self.pause())
        self.log(f"> AutoFish v2.0 FAST | F5 Start | F6 Region | F7 Pause")
        self.log(f"> Admin: {'YES' if is_admin() else 'NO!'}")
        try: self.log(f"> Tesseract {pytesseract.get_tesseract_version()}")
        except: self.log("> Tesseract NOT FOUND!")
        if region: self.log(f"> Region loaded")

    def _tick(self):
        if self.running:
            e=int(time.time()-self.start_t);m,s=divmod(e,60)
            self.lt2.config(text=f"{m:02d}:{s:02d}")
        self.root.after(500,self._tick)

    def pick(self):
        global region
        if self.running: return
        self.root.iconify();time.sleep(0.3)
        sel=tk.Toplevel(self.root);sel.overrideredirect(True);sel.attributes("-topmost",True);sel.attributes("-alpha",0.25)
        sw,sh=sel.winfo_screenwidth(),sel.winfo_screenheight()
        sel.geometry(f"{sw}x{sh}+0+0");sel.configure(bg="black")
        c=tk.Canvas(sel,bg="black",highlightthickness=0,cursor="cross");c.pack(fill=tk.BOTH,expand=True)
        c.create_text(sw//2,35,text="Drag over QTE keys (exclude counter)",fill=ACCENT,font=("Segoe UI",13,"bold"))
        c.create_text(sw//2,58,text="ESC = Cancel",fill=DIM,font=("Segoe UI",10))
        pos=c.create_text(sw//2,90,text="",fill=ACCENT,font=("Consolas",12,"bold"))
        st={"sx":0,"sy":0,"r":None}
        c.bind("<Motion>",lambda e:c.itemconfig(pos,text=f"X:{e.x} Y:{e.y}"))
        def _p(e):
            st["sx"],st["sy"]=e.x,e.y
            if st["r"]: c.delete(st["r"])
            st["r"]=c.create_rectangle(e.x,e.y,e.x,e.y,outline=ACCENT,width=3)
        def _d(e):
            c.coords(st["r"],st["sx"],st["sy"],e.x,e.y)
        def _r(e):
            global region
            x1,y1=min(st["sx"],e.x),min(st["sy"],e.y);x2,y2=max(st["sx"],e.x),max(st["sy"],e.y)
            if (x2-x1)>10 and (y2-y1)>10:
                region={"left":x1,"top":y1,"width":x2-x1,"height":y2-y1};save_cfg()
                self.lr.config(text=f"{x2-x1}x{y2-y1}",fg=GREEN)
                self.log("> Region set")
            sel.destroy();self.root.deiconify()
        c.bind("<ButtonPress-1>",_p);c.bind("<B1-Motion>",_d);c.bind("<ButtonRelease-1>",_r)
        sel.bind("<Escape>",lambda e:(sel.destroy(),self.root.deiconify()))
        sel.after(50,sel.focus_force)

    def tread(self):
        if not region: return
        t0=time.time();f=grab(region)
        if f is None: self.log("> Capture fail");return
        g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
        k=read_fast(g,self.nk.get());ms=int((time.time()-t0)*1000)
        self.dbg=make_debug(f,k,self.nk.get());self._show()
        self.log(f"> Read ({ms}ms): {' '.join(x.upper() for x in k)}" if k else f"> Fail {ms}ms")

    def tkey(self):
        self.log("> D+S in 3s")
        def _do():
            time.sleep(3);press_key('d');time.sleep(0.2);press_key('s')
            self.root.after(0,self.log,"> Pressed!")
        threading.Thread(target=_do,daemon=True).start()

    def pause(self):
        if not self.running: return
        self.paused=not self.paused
        if self.paused:
            self.st.config(text="PAUSE",fg="#fb923c")
            self.log("> Paused (F7 resume)")
        else:
            self.st.config(text="ON",fg=GREEN)
            self.log("> Resumed!")

    def toggle(self):
        if self.running: self.running=False;self.paused=False
        else:
            if not region: messagebox.showwarning("AutoFish","F6 Select Region!");return
            num=self.nk.get();kd=self.kd.get()/1000
            self.running=True;self.paused=False;save_cfg(nk=num,kd=self.kd.get())
            self.btn.config(text="STOP",bg=RED);self.st.config(text="ON",fg=GREEN)
            self.log("> Go! 3s...")
            threading.Thread(target=self._run,args=(num,kd),daemon=True).start()

    def _run(self,num,kd):
        self.keys=0;self.fish=0;self.scans=0;self.start_t=time.time();self.lt=time.time()
        t=grab(region)
        if t is None:
            self.root.after(0,self.log,"> Capture fail");self.running=False;self.root.after(0,self._rst);return
        time.sleep(3);self.root.after(0,self.log,"> Scanning...");lseq=""
        while self.running:
            try:
                # F7 Pause
                if self.paused: time.sleep(0.1);continue
                f=grab(region)
                if f is None: time.sleep(0.04);continue
                g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
                self.scans+=1
                k=read_fast(g,num);self.dbg=make_debug(f,k,num)
                if k and len(k)==num:
                    seq="".join(k)
                    if seq!=lseq:
                        self.fish+=1
                        self.root.after(0,self.log,f"> #{self.fish} {' '.join(x.upper() for x in k)}")
                        self.root.after(0,self.seq.config,{"text":" ".join(x.upper() for x in k)})
                        if random.random()<0.05: time.sleep(random.uniform(0.3,1.0))
                        for key in k:
                            if not self.running: break
                            press_key(key);self.keys+=1
                            time.sleep(kd+random.uniform(0.03,0.12))
                        # Update stats
                        rate=f"{int(self.fish/max(self.scans,1)*100)}%"
                        self.root.after(0,self.lk.config,{"text":str(self.keys)})
                        self.root.after(0,self.lf.config,{"text":str(self.fish)})
                        self.root.after(0,self.lr.config,{"text":rate})
                        # Beep!
                        if sys.platform=='win32':
                            try:
                                import winsound;winsound.Beep(800,60)
                            except: pass
                        lseq=seq;time.sleep(0.6+random.uniform(0.1,0.3))
                    else: time.sleep(0.03)
                else: time.sleep(0.04)
            except Exception as e:
                self.root.after(0,self.log,f"> {e}");time.sleep(0.5)
        self.root.after(0,self._rst)

    def _rst(self):
        self.btn.config(text="START (F5)",bg=GREEN);self.st.config(text="OFF",fg=DIM)
        self.seq.config(text="");self.log("> Stopped")

    def _show(self):
        if self.dbg is None: return
        try:
            h,w=self.dbg.shape[:2];nw=448;nh=max(int(h*nw/w),20)
            r=cv2.resize(self.dbg,(nw,nh),interpolation=cv2.INTER_NEAREST)
            ph=ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(r,cv2.COLOR_BGR2RGB)))
            self.pv.config(image=ph,text="");self.pv.image=ph
        except: pass

    def _prev(self):
        if self.running and self.dbg is not None: self._show()
        elif region and not self.running:
            try:
                f=grab(region)
                if f is not None:
                    self.dbg=make_debug(f,None,self.nk.get());self._show()
            except: pass
        self.root.after(100,self._prev)

    def log(self,msg):
        self.log_b.config(state=tk.NORMAL)
        self.log_b.insert(tk.END,f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_b.see(tk.END);n=int(self.log_b.index("end-1c").split(".")[0])
        if n>60: self.log_b.delete("1.0",f"{n-60}.0")
        self.log_b.config(state=tk.DISABLED)

    def _quit(self): self.running=False;time.sleep(0.1);self.root.destroy()
    def run(self): self.root.mainloop()

if __name__=="__main__": App().run()

"""
AutoFish by Herlove v2.0
Cyberpunk Neon Fishing Macro
"""

import time, sys, os, json, threading, ctypes, random
import tkinter as tk
from tkinter import messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══ Auto Admin ═══
def is_admin():
    if sys.platform != 'win32': return True
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if not is_admin() and sys.platform == 'win32':
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable,
            f'"{os.path.abspath(__file__)}"', None, 1)
    except: pass
    sys.exit()

try:
    import keyboard as kb
    import mss, cv2, numpy as np
    from PIL import Image, ImageTk, ImageGrab
    import pytesseract
except ImportError as e:
    root = tk.Tk(); root.withdraw()
    messagebox.showerror("AutoFish", f"Missing: {e}\npip install keyboard mss opencv-python numpy Pillow pytesseract")
    sys.exit(1)

for p in [r"C:\Program Files\Tesseract-OCR\tesseract.exe",
          r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]:
    if os.path.exists(p): pytesseract.pytesseract.tesseract_cmd = p; break

# ═══ SendInput Scancode ═══
SCAN = {'q':0x10,'w':0x11,'e':0x12,'r':0x13,'a':0x1E,'s':0x1F,'d':0x20,'f':0x21,'space':0x39}
if sys.platform == 'win32':
    PUL = ctypes.POINTER(ctypes.c_ulong)
    class KEYBDINPUT(ctypes.Structure):
        _fields_=[("wVk",ctypes.c_ushort),("wScan",ctypes.c_ushort),("dwFlags",ctypes.c_ulong),("time",ctypes.c_ulong),("dwExtraInfo",PUL)]
    class HARDWAREINPUT(ctypes.Structure):
        _fields_=[("uMsg",ctypes.c_ulong),("wParamL",ctypes.c_short),("wParamH",ctypes.c_ushort)]
    class MOUSEINPUT(ctypes.Structure):
        _fields_=[("dx",ctypes.c_long),("dy",ctypes.c_long),("mouseData",ctypes.c_ulong),("dwFlags",ctypes.c_ulong),("time",ctypes.c_ulong),("dwExtraInfo",PUL)]
    class INPUT_UNION(ctypes.Union):
        _fields_=[("ki",KEYBDINPUT),("mi",MOUSEINPUT),("hi",HARDWAREINPUT)]
    class INPUT(ctypes.Structure):
        _fields_=[("type",ctypes.c_ulong),("ii",INPUT_UNION)]

def press_key(key):
    sc = SCAN.get(key.lower())
    if not sc or sys.platform != 'win32': return False
    try:
        extra = ctypes.c_ulong(0)
        ii = INPUT_UNION(); ii.ki = KEYBDINPUT(0, sc, 0x0008, 0, ctypes.pointer(extra))
        x = INPUT(1, ii)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
        time.sleep(0.05)
        ii2 = INPUT_UNION(); ii2.ki = KEYBDINPUT(0, sc, 0x0008|0x0002, 0, ctypes.pointer(extra))
        x2 = INPUT(1, ii2)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(x2), ctypes.sizeof(x2))
        return True
    except: return False

# ═══ Capture ═══
_sct = None
def get_sct():
    global _sct
    if _sct is None:
        try: _sct = mss.mss()
        except: pass
    return _sct

def grab(r):
    left,top,w,h = int(r["left"]),int(r["top"]),int(r["width"]),int(r["height"])
    s = get_sct()
    if s:
        try:
            arr = np.array(s.grab({"left":left,"top":top,"width":w,"height":h}))
            if arr.size > 0: return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        except: pass
    try:
        img = ImageGrab.grab(bbox=(left,top,left+w,top+h))
        if img: return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    except: pass
    return None

# ═══ OCR ═══
VALID = set("qweasd")
def read_slot_single(gray_slot):
    """อ่าน 1 ตัวอักษรจาก slot เดี่ยว (PSM 10)"""
    if gray_slot is None or gray_slot.size < 20: return None
    big = cv2.resize(gray_slot, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    for method in range(2):
        try:
            if method == 0:
                _, t = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            else:
                _, t = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
                t = cv2.bitwise_not(t)
            if np.count_nonzero(t) > t.size // 2: t = cv2.bitwise_not(t)
            text = pytesseract.image_to_string(t, config='--psm 10 -c tessedit_char_whitelist=QWEASDqweasd').strip().lower()
            for c in text:
                if c in VALID: return c
        except: continue
    return None

def read_all(gray, num_keys):
    """อ่านทั้งแถว + ตรวจซ้ำตัวสุดท้ายแยก"""
    if gray is None or gray.size < 100: return None
    h, w = gray.shape[:2]

    # ตัดขอบขวา 5% ออก (กัน counter เล้ยเข้ามา)
    trim = int(w * 0.05)
    trimmed = gray[:, :w-trim] if trim > 3 else gray

    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    processed = cv2.filter2D(trimmed, -1, kernel)
    processed = cv2.GaussianBlur(processed, (3,3), 0)
    big = cv2.resize(processed, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)

    # อ่านทั้งแถว (PSM 7)
    for method in range(3):
        try:
            if method == 0:
                _, t = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            elif method == 1:
                _, t = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
                t = cv2.bitwise_not(t)
            else:
                _, t = cv2.threshold(big, 180, 255, cv2.THRESH_BINARY)
            if np.count_nonzero(t) > t.size // 2: t = cv2.bitwise_not(t)
            text = pytesseract.image_to_string(t, config='--psm 7 -c tessedit_char_whitelist=QWEASDqweasd').strip().lower()
            chars = [c for c in text if c in VALID]

            if len(chars) == num_keys and all(c in VALID for c in chars):
                # ตรวจซ้ำตัวสุดท้ายด้วย PSM 10 (แยก slot)
                sw = w // num_keys
                last_slot = gray[:, (num_keys-1)*sw:]
                last_char = read_slot_single(last_slot)
                if last_char and last_char != chars[-1]:
                    chars[-1] = last_char  # แก้ตัวสุดท้าย
                return chars
        except: continue

    # Fallback: อ่านทีละ slot (ถ้าอ่านทั้งแถวไม่ได้)
    sw = w // num_keys
    chars = []
    for i in range(num_keys):
        pad = max(sw // 10, 2)
        slot = gray[:, max(0, i*sw-pad):min(w, (i+1)*sw+pad)]
        c = read_slot_single(slot)
        chars.append(c)
    if all(c is not None for c in chars):
        return chars
    return None

def make_debug(frame, keys, num):
    d = frame.copy(); h,w = d.shape[:2]; sw = w // num
    cv2.rectangle(d, (0,0), (w-1,h-1), (56,189,248), 2)
    for i in range(num):
        x1, x2 = i*sw, min((i+1)*sw, w)
        if keys and i < len(keys) and keys[i]:
            cv2.rectangle(d, (x1+2,2), (x2-2,h-2), (0,255,0), 2)
            cv2.putText(d, keys[i].upper(), (x1+8,24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        else:
            cv2.rectangle(d, (x1+2,2), (x2-2,h-2), (40,40,60), 1)
    cv2.putText(d, "AUTOFISH", (8, h-8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0,255,255), 1)
    return d

# ═══ Config ═══
CFG = os.path.join(SCRIPT_DIR, "config.json")
region = None
def load_cfg():
    global region
    try:
        with open(CFG,"r") as f: c=json.load(f); region=c.get("region"); return c
    except: return {}
def save_cfg(**kw):
    c=load_cfg(); c.update(kw); c["region"]=region
    try:
        with open(CFG,"w") as f: json.dump(c,f,indent=2)
    except: pass
load_cfg()

# ═══ Theme ═══
BG      = "#020617"
BG2     = "#0a1128"
CARD    = "#0f172a"
CARD2   = "#1e293b"
ACCENT  = "#22d3ee"
GLOW    = "#0ea5e9"
GREEN   = "#4ade80"
GREEN2  = "#22c55e"
RED     = "#f87171"
ORANGE  = "#fb923c"
PURPLE  = "#a78bfa"
DIM     = "#334155"
DIM2    = "#1e293b"
WHITE   = "#e2e8f0"

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AutoFish by Herlove")
        self.root.geometry("500x750")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.running = False
        self.session_keys = 0
        self.session_start = 0
        self.debug_img = None
        self.fish_count = 0
        self.last_time = time.time()
        self.num_keys = tk.IntVar(value=load_cfg().get("num_keys", 5))
        self.key_delay = tk.IntVar(value=60)

        try:
            ico = os.path.join(SCRIPT_DIR, "logo.png")
            if os.path.exists(ico):
                img = ImageTk.PhotoImage(Image.open(ico).resize((32,32),Image.LANCZOS))
                self.root.iconphoto(True, img); self._ico = img
        except: pass

        self._build()
        self._preview_loop()
        self._status_blink()
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

    def _build(self):
        # ════════════════ HEADER ════════════════
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill=tk.X, padx=20, pady=(14,0))

        # Mascot
        try:
            lp = os.path.join(SCRIPT_DIR, "mascot.png")
            if not os.path.exists(lp): lp = os.path.join(SCRIPT_DIR, "logo.png")
            if os.path.exists(lp):
                li = Image.open(lp).resize((60, 60), Image.LANCZOS)
                self._logo = ImageTk.PhotoImage(li)
                logo_frame = tk.Frame(hdr, bg=CARD, highlightbackground=GLOW, highlightthickness=1)
                logo_frame.pack(side=tk.LEFT, padx=(0,14))
                tk.Label(logo_frame, image=self._logo, bg=CARD, padx=3, pady=3).pack()
        except: pass

        # Title
        tf = tk.Frame(hdr, bg=BG)
        tf.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(tf, text="AutoFish", bg=BG, fg=WHITE,
                 font=("Segoe UI", 24, "bold")).pack(anchor="w")

        sub = tk.Frame(tf, bg=BG)
        sub.pack(anchor="w")
        tk.Label(sub, text="FISHING SYSTEM", bg=BG, fg=ACCENT,
                 font=("Consolas", 9, "bold")).pack(side=tk.LEFT)
        tk.Label(sub, text=" v2.0", bg=BG, fg=DIM,
                 font=("Consolas", 9)).pack(side=tk.LEFT)

        tk.Label(tf, text="by Herlove", bg=BG, fg=DIM,
                 font=("Segoe UI", 8)).pack(anchor="w")

        # Status badge
        self.status_frame = tk.Frame(hdr, bg=CARD, highlightbackground=DIM, highlightthickness=1)
        self.status_frame.pack(side=tk.RIGHT)
        self.lbl_dot = tk.Label(self.status_frame, text="  ", bg=DIM, font=("Segoe UI",4))
        self.lbl_dot.pack(side=tk.LEFT, padx=(6,4), pady=6)
        self.lbl_st = tk.Label(self.status_frame, text="OFFLINE", bg=CARD, fg=DIM,
                                font=("Consolas", 9, "bold"))
        self.lbl_st.pack(side=tk.LEFT, padx=(0,8), pady=6)

        # ════════════════ GRADIENT LINE ════════════════
        line = tk.Canvas(self.root, bg=BG, height=2, highlightthickness=0)
        line.pack(fill=tk.X, padx=20, pady=(10,0))
        for i in range(460):
            t = i / 460
            r = int(14 + (74-14)*t)
            g = int(165 + (222-165)*t)
            b = int(233 + (128-233)*t)
            line.create_line(i+20, 0, i+20, 2, fill=f"#{r:02x}{g:02x}{b:02x}")

        # ════════════════ PREVIEW ════════════════
        prev_outer = tk.Frame(self.root, bg=GLOW)
        prev_outer.pack(fill=tk.X, padx=20, pady=(10,0))
        prev_inner = tk.Frame(prev_outer, bg=BG2)
        prev_inner.pack(fill=tk.X, padx=1, pady=1)
        self.preview = tk.Label(prev_inner, bg="#030810",
            text="  Select Region (F6) to start  ", fg=DIM,
            font=("Consolas", 9))
        self.preview.pack(fill=tk.X, ipady=35)

        # ════════════════ START BUTTON ════════════════
        btn_outer = tk.Frame(self.root, bg=GREEN2)
        btn_outer.pack(fill=tk.X, padx=20, pady=(8,0))
        self.btn = tk.Button(btn_outer, text="START", bg=GREEN, fg=BG,
            font=("Segoe UI", 16, "bold"), relief="flat", pady=8, cursor="hand2",
            activebackground=GREEN2, bd=0, command=self.toggle)
        self.btn.pack(fill=tk.X, padx=1, pady=1)
        self.btn.bind("<Enter>", self._btn_hover)
        self.btn.bind("<Leave>", self._btn_leave)
        self.btn_outer = btn_outer

        # Hotkey hint
        tk.Label(self.root, text="F5", bg=BG, fg=DIM2,
                 font=("Consolas", 8)).pack(pady=(2,0))

        # ════════════════ STATS DASHBOARD ════════════════
        dash = tk.Frame(self.root, bg=CARD, highlightbackground=DIM2, highlightthickness=1)
        dash.pack(fill=tk.X, padx=20, pady=(6,0))
        di = tk.Frame(dash, bg=CARD)
        di.pack(fill=tk.X, padx=6, pady=10)

        # KEYS
        self._stat_block(di, "lbl_cnt", "0", "KEYS PRESSED", ACCENT)

        # Divider
        tk.Frame(di, bg=DIM2, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # FISH
        self._stat_block(di, "lbl_fish", "0", "FISH CAUGHT", GLOW)

        # Divider
        tk.Frame(di, bg=DIM2, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # FPS
        self._stat_block(di, "lbl_fps", "0.0", "SCAN FPS", PURPLE)

        # ════════════════ CONTROLS ════════════════
        ctrl = tk.Frame(self.root, bg=CARD, highlightbackground=DIM2, highlightthickness=1)
        ctrl.pack(fill=tk.X, padx=20, pady=(6,0))
        ci = tk.Frame(ctrl, bg=CARD)
        ci.pack(fill=tk.X, padx=6, pady=8)

        self._ctrl_btn(ci, "Select Region", ACCENT, self.pick_region)
        self._ctrl_btn(ci, "Test Read", GREEN, self.test_read)
        self._ctrl_btn(ci, "Test Press", PURPLE, self.test_press)

        self.lbl_reg = tk.Label(ci, text="not set", bg=CARD, fg=ORANGE,
                                 font=("Consolas", 8, "bold"))
        self.lbl_reg.pack(side=tk.RIGHT, padx=4)
        tk.Label(ci, text="F6", bg=CARD, fg=DIM2, font=("Consolas",7)).pack(side=tk.RIGHT)

        # ════════════════ SETTINGS ════════════════
        stf = tk.Frame(self.root, bg=CARD, highlightbackground=DIM2, highlightthickness=1)
        stf.pack(fill=tk.X, padx=20, pady=(6,0))

        tk.Label(stf, text="  SETTINGS", bg=CARD, fg=DIM,
                 font=("Consolas", 7, "bold"), anchor="w").pack(fill=tk.X, padx=6, pady=(6,0))

        self._slider(stf, "Keys / Lane", self.num_keys, 2, 10, ACCENT)
        self._slider(stf, "Key Delay (ms)", self.key_delay, 30, 200, GREEN)

        # ════════════════ LOG ════════════════
        log_hdr = tk.Frame(self.root, bg=BG)
        log_hdr.pack(fill=tk.X, padx=22, pady=(8,2))
        tk.Label(log_hdr, text="> SYSTEM LOG", bg=BG, fg=DIM,
                 font=("Consolas", 7, "bold")).pack(side=tk.LEFT)
        tk.Button(log_hdr, text="clear", bg=BG, fg=DIM2, font=("Consolas",7),
                  relief="flat", cursor="hand2", command=self._clear_log).pack(side=tk.RIGHT)

        log_outer = tk.Frame(self.root, bg=DIM2)
        log_outer.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0,0))
        self.log_box = tk.Text(log_outer, bg="#030810", fg=GREEN,
            font=("Consolas", 9), relief="flat", wrap=tk.WORD, state=tk.DISABLED,
            padx=10, pady=8, insertbackground=ACCENT, selectbackground=DIM2)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.log_box.tag_configure("accent", foreground=ACCENT)
        self.log_box.tag_configure("warn", foreground=ORANGE)
        self.log_box.tag_configure("dim", foreground=DIM)

        # ════════════════ FOOTER ════════════════
        ft = tk.Frame(self.root, bg=BG)
        ft.pack(fill=tk.X, padx=20, pady=(6,8))
        tk.Label(ft, text="F5 Start/Stop", bg=BG, fg=DIM2,
                 font=("Consolas", 7)).pack(side=tk.LEFT)
        tk.Label(ft, text="F6 Region", bg=BG, fg=DIM2,
                 font=("Consolas", 7)).pack(side=tk.LEFT, padx=8)
        admin_text = "Admin" if is_admin() else "NOT Admin!"
        admin_color = DIM2 if is_admin() else RED
        tk.Label(ft, text=admin_text, bg=BG, fg=admin_color,
                 font=("Consolas", 7, "bold")).pack(side=tk.RIGHT)

        # Keybinds
        self.root.bind("<F5>", lambda e: self.toggle())
        self.root.bind("<F6>", lambda e: self.pick_region())

        # Init log
        self.log("> AutoFish by Herlove v2.0")
        self.log(f"> Admin: {'YES' if is_admin() else 'NO - Run as Admin!'}")
        try:
            v = pytesseract.get_tesseract_version()
            self.log(f"> Tesseract {v}")
        except:
            self.log("> Tesseract: NOT FOUND!")
        self.log("> Select region (F6) then Start (F5)")

    # ═══ UI Helpers ═══
    def _stat_block(self, parent, attr, init_text, label, color):
        f = tk.Frame(parent, bg=CARD)
        f.pack(side=tk.LEFT, expand=True)
        lbl = tk.Label(f, text=init_text, bg=CARD, fg=color,
                        font=("Consolas", 26, "bold"))
        lbl.pack()
        tk.Label(f, text=label, bg=CARD, fg=DIM,
                 font=("Consolas", 6, "bold")).pack()
        setattr(self, attr, lbl)

    def _ctrl_btn(self, parent, text, color, cmd):
        b = tk.Button(parent, text=text, bg=BG2, fg=color,
            font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=3,
            cursor="hand2", activebackground=CARD2, command=cmd)
        b.pack(side=tk.LEFT, padx=2)
        b.bind("<Enter>", lambda e, b=b, c=color: b.config(bg=CARD2))
        b.bind("<Leave>", lambda e, b=b: b.config(bg=BG2))

    def _slider(self, parent, label, var, lo, hi, color):
        f = tk.Frame(parent, bg=CARD)
        f.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(f, text=label, bg=CARD, fg=WHITE,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        vl = tk.Label(f, text=str(var.get()), bg=CARD, fg=color,
                       font=("Consolas", 10, "bold"), width=4)
        vl.pack(side=tk.RIGHT)
        tk.Scale(f, from_=lo, to=hi, orient=tk.HORIZONTAL, variable=var,
            bg=CARD, fg=CARD, troughcolor=BG, highlightthickness=0,
            showvalue=False, length=120, sliderlength=14, activebackground=color,
            command=lambda v, l=vl: l.config(text=str(int(float(v))))).pack(side=tk.RIGHT, padx=4)

    def _btn_hover(self, e):
        if self.running:
            self.btn.config(bg="#ef4444")
        else:
            self.btn.config(bg=GREEN2)

    def _btn_leave(self, e):
        if self.running:
            self.btn.config(bg=RED)
        else:
            self.btn.config(bg=GREEN)

    def _status_blink(self):
        if self.running:
            cur = self.lbl_dot.cget("bg")
            self.lbl_dot.config(bg=GREEN if cur == CARD else CARD)
        self.root.after(600, self._status_blink)

    def _clear_log(self):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.config(state=tk.DISABLED)

    # ═══ Region ═══
    def pick_region(self):
        global region
        if self.running: self.log("> Stop first!"); return
        self.root.iconify(); time.sleep(0.3)
        sel = tk.Toplevel(self.root)
        sel.overrideredirect(True); sel.attributes("-topmost", True)
        sel.attributes("-alpha", 0.25)
        sw, sh = sel.winfo_screenwidth(), sel.winfo_screenheight()
        sel.geometry(f"{sw}x{sh}+0+0"); sel.configure(bg="black")
        c = tk.Canvas(sel, bg="black", highlightthickness=0, cursor="cross")
        c.pack(fill=tk.BOTH, expand=True)

        # Guide box
        c.create_rectangle(sw//2-230, 12, sw//2+230, 85, fill="black", outline=ACCENT, width=2)
        c.create_text(sw//2, 32, text="Drag over the QTE key boxes",
            fill=ACCENT, font=("Segoe UI", 14, "bold"))
        c.create_text(sw//2, 52, text="Do NOT include the counter circle",
            fill=WHITE, font=("Segoe UI", 10))
        c.create_text(sw//2, 72, text="ESC = Cancel",
            fill=DIM, font=("Segoe UI", 9))

        pos = c.create_text(sw//2, 105, text="", fill=ACCENT, font=("Consolas", 12, "bold"))
        st = {"sx": 0, "sy": 0, "r": None}

        c.bind("<Motion>", lambda e: c.itemconfig(pos, text=f"X: {e.x}   Y: {e.y}"))
        def _p(e):
            st["sx"], st["sy"] = e.x, e.y
            if st["r"]: c.delete(st["r"])
            st["r"] = c.create_rectangle(e.x, e.y, e.x, e.y, outline=ACCENT, width=3)
        def _d(e):
            c.coords(st["r"], st["sx"], st["sy"], e.x, e.y)
            c.delete("sz")
            w, h = abs(e.x - st["sx"]), abs(e.y - st["sy"])
            c.create_text((st["sx"]+e.x)//2, min(st["sy"], e.y)-16,
                text=f"{w} x {h}", fill=ACCENT, font=("Consolas", 14, "bold"), tags="sz")
        def _r(e):
            global region
            x1, y1 = min(st["sx"], e.x), min(st["sy"], e.y)
            x2, y2 = max(st["sx"], e.x), max(st["sy"], e.y)
            if (x2-x1) > 10 and (y2-y1) > 10:
                region = {"left": x1, "top": y1, "width": x2-x1, "height": y2-y1}
                save_cfg()
                self.lbl_reg.config(text=f"{x2-x1}x{y2-y1}", fg=GREEN)
                self.log(f"> Region set: {x2-x1}x{y2-y1} @ ({x1},{y1})")
            sel.destroy(); self.root.deiconify()

        c.bind("<ButtonPress-1>", _p)
        c.bind("<B1-Motion>", _d)
        c.bind("<ButtonRelease-1>", _r)
        sel.bind("<Escape>", lambda e: (sel.destroy(), self.root.deiconify()))
        sel.after(50, sel.focus_force)

    # ═══ Test ═══
    def test_read(self):
        if not region: self.log("> Select region first!"); return
        t0 = time.time()
        frame = grab(region)
        if frame is None: self.log("> Capture failed!"); return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        keys = read_all(gray, self.num_keys.get())
        ms = int((time.time()-t0)*1000)
        self.debug_img = make_debug(frame, keys, self.num_keys.get())
        self._show_debug()
        if keys:
            self.log(f"> Read ({ms}ms): {' '.join(k.upper() for k in keys)}")
        else:
            self.log(f"> Failed ({ms}ms) - adjust region")

    def test_press(self):
        self.log("> Press D+S in 3s (click game!)")
        def _do():
            time.sleep(3)
            press_key('d'); time.sleep(0.2); press_key('s')
            self.root.after(0, self.log, "> Pressed D S!")
        threading.Thread(target=_do, daemon=True).start()

    # ═══ Toggle ═══
    def toggle(self):
        if self.running:
            self.running = False
        else:
            if not region:
                messagebox.showwarning("AutoFish", "Select Region first (F6)!")
                return
            self.running = True
            save_cfg(num_keys=self.num_keys.get())
            self.btn.config(text="STOP", bg=RED, activebackground="#ef4444")
            self.btn_outer.config(bg="#b91c1c")
            self.lbl_st.config(text="ACTIVE", fg=GREEN)
            self.lbl_dot.config(bg=GREEN)
            self.status_frame.config(highlightbackground=GREEN)
            self.log("> Switch to game in 3s!")
            threading.Thread(target=self._run, daemon=True).start()

    # ═══ Main Loop ═══
    def _run(self):
        num = self.num_keys.get()
        kd = self.key_delay.get() / 1000
        self.session_keys = 0
        self.session_start = time.time()
        self.fish_count = 0
        self.last_time = time.time()

        test = grab(region)
        if test is None:
            self.root.after(0, self.log, "> Capture failed!")
            self.running = False
            self.root.after(0, self._reset)
            return

        time.sleep(3)
        self.root.after(0, self.log, "> Scanning...")
        last_seq = ""

        while self.running:
            try:
                frame = grab(region)
                if frame is None: time.sleep(0.06); continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                now = time.time()
                fps = 1.0 / max(now - self.last_time, 0.001)
                self.last_time = now

                keys = read_all(gray, num)
                self.debug_img = make_debug(frame, keys, num)

                if keys and len(keys) == num:
                    seq = "".join(keys)
                    if seq != last_seq:
                        self.fish_count += 1
                        display = " ".join(k.upper() for k in keys)
                        self.root.after(0, self.log, f"> #{self.fish_count} {display}")

                        if random.random() < 0.05:
                            time.sleep(random.uniform(0.5, 1.5))

                        for key in keys:
                            if not self.running: break
                            press_key(key)
                            self.session_keys += 1
                            time.sleep(kd + random.uniform(0.02, 0.08))

                        if sys.platform == 'win32':
                            try:
                                import winsound
                                winsound.Beep(800, 80)
                            except: pass

                        self.root.after(0, self._update_stats, fps)
                        last_seq = seq
                        time.sleep(0.8 + random.uniform(0.1, 0.3))
                    else:
                        time.sleep(0.04)
                else:
                    time.sleep(0.06)

            except Exception as e:
                self.root.after(0, self.log, f"> Error: {e}")
                time.sleep(0.5)

        self.root.after(0, self._reset)

    def _update_stats(self, fps=0):
        self.lbl_cnt.config(text=str(self.session_keys))
        self.lbl_fish.config(text=str(self.fish_count))
        self.lbl_fps.config(text=f"{fps:.1f}")

    def _reset(self):
        self.btn.config(text="START", bg=GREEN, activebackground=GREEN2)
        self.btn_outer.config(bg=GREEN2)
        self.lbl_st.config(text="OFFLINE", fg=DIM)
        self.lbl_dot.config(bg=DIM)
        self.status_frame.config(highlightbackground=DIM)
        self.log("> Stopped")

    # ═══ Preview ═══
    def _show_debug(self):
        if self.debug_img is None: return
        try:
            rgb = cv2.cvtColor(self.debug_img, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            w, h = img.size
            nw = 458; nh = max(int(h * nw / w), 20)
            img = img.resize((nw, nh), Image.NEAREST)
            photo = ImageTk.PhotoImage(img)
            self.preview.config(image=photo, text="")
            self.preview.image = photo
        except: pass

    def _preview_loop(self):
        if self.running and self.debug_img is not None:
            self._show_debug()
        elif region:
            try:
                frame = grab(region)
                if frame is not None:
                    d = make_debug(frame, None, self.num_keys.get())
                    rgb = cv2.cvtColor(d, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(rgb)
                    w, h = img.size
                    nw = 458; nh = max(int(h * nw / w), 20)
                    img = img.resize((nw, nh), Image.NEAREST)
                    photo = ImageTk.PhotoImage(img)
                    self.preview.config(image=photo, text="")
                    self.preview.image = photo
            except: pass
        self.root.after(150, self._preview_loop)

    # ═══ Log ═══
    def log(self, msg):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_box.see(tk.END)
        lines = int(self.log_box.index("end-1c").split(".")[0])
        if lines > 80:
            self.log_box.delete("1.0", f"{lines-80}.0")
        self.log_box.config(state=tk.DISABLED)

    def _quit(self):
        self.running = False
        time.sleep(0.1)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()

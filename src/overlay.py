"""
overlay.py — 游戏内悬浮状态框 (纯 Win32 API, 零外部依赖)

左上角小绿框，实时显示脚本运行状态。
  - 穿透点击 (WS_EX_TRANSPARENT) — 不影响游戏操作
  - 不抢焦点 (WS_EX_NOACTIVATE) — 不干扰 DirectInput
  - 置顶显示 (WS_EX_TOPMOST) — 始终在游戏画面之上
  - 颜色键透明 — 窗口背景透明，只显示绿框+文字

注意: 游戏需设置为「无边框窗口」模式，独占全屏下悬浮框不可见。
"""

import ctypes
import ctypes.wintypes as wintypes
import threading


# ============================================================
# Win32 常量
# ============================================================
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

CS_HREDRAW = 0x0002
CS_VREDRAW = 0x0001

WM_PAINT = 0x000F
WM_TIMER = 0x0113
WM_DESTROY = 0x0002

LWA_COLORKEY = 0x00000001

TRANSPARENT = 1
OPAQUE = 2

DT_LEFT = 0x0000
DT_TOP = 0x0000
DT_NOCLIP = 0x0100

FW_BOLD = 700
DEFAULT_QUALITY = 0
OUT_DEFAULT_PRECIS = 0
CLIP_DEFAULT_PRECIS = 0
DEFAULT_CHARSET = 1
FF_SWISS = 0x20

PS_SOLID = 0

TIMER_ID = 1
TIMER_INTERVAL = 300  # ms

# 颜色 (BGR format for Win32 COLORREF)
COLOR_KEY = 0x00FF00FF      # 紫红色 — 透明色键
COLOR_BG = 0x0018280D       # 深绿背景 #0D2818 (BGR)
COLOR_BORDER = 0x0000CC00   # 亮绿边框 #00CC00 (BGR)
COLOR_TEXT = 0x0066FF00     # 亮绿文字 #00FF66 (BGR)

# 窗口尺寸
WIN_W = 260
WIN_H = 72
WIN_X = 10
WIN_Y = 10


# ============================================================
# Win32 结构体
# ============================================================

class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("fErase", wintypes.BOOL),
        ("rcPaint", wintypes.RECT),
        ("fRestore", wintypes.BOOL),
        ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", ctypes.c_byte * 32),
    ]


# WndProc 回调类型
WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long, wintypes.HWND, wintypes.UINT,
    wintypes.WPARAM, wintypes.LPARAM
)


# ============================================================
# 加载 Win32 库
# ============================================================
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# 设置函数签名
user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wintypes.ATOM

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
    wintypes.DWORD, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU,
    wintypes.HINSTANCE, ctypes.c_void_p
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.SetLayeredWindowAttributes.argtypes = [
    wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD
]
user32.SetLayeredWindowAttributes.restype = wintypes.BOOL

user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.BeginPaint.restype = wintypes.HDC

user32.EndPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.EndPaint.restype = wintypes.BOOL

user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.restype = wintypes.BOOL

user32.InvalidateRect.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.BOOL]
user32.InvalidateRect.restype = wintypes.BOOL

user32.SetTimer.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.UINT, ctypes.c_void_p]
user32.SetTimer.restype = wintypes.UINT

user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT
]
user32.GetMessageW.restype = wintypes.BOOL

user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL

user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = ctypes.c_long

user32.DefWindowProcW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
]
user32.DefWindowProcW.restype = ctypes.c_long

user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None

user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL

user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.UINT
]
user32.SetWindowPos.restype = wintypes.BOOL

gdi32.CreateFontW.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
    wintypes.LPCWSTR
]
gdi32.CreateFontW.restype = wintypes.HFONT

gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ

gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL

gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
gdi32.SetTextColor.restype = wintypes.COLORREF

gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.SetBkMode.restype = ctypes.c_int

gdi32.SetBkColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
gdi32.SetBkColor.restype = wintypes.COLORREF

gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH

# FillRect 和 DrawTextW 实际在 user32.dll
user32.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH]
user32.FillRect.restype = ctypes.c_int

user32.DrawTextW.argtypes = [
    wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int,
    ctypes.POINTER(wintypes.RECT), wintypes.UINT
]
user32.DrawTextW.restype = ctypes.c_int

gdi32.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.COLORREF]
gdi32.CreatePen.restype = wintypes.HPEN

gdi32.Rectangle.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
gdi32.Rectangle.restype = wintypes.BOOL


# ============================================================
# Overlay 单例
# ============================================================

class Overlay:
    """游戏内悬浮状态框"""

    def __init__(self):
        self._phase = "等待启动"
        self._rounds = 0
        self._success = 0
        self._running = False
        self._lock = threading.Lock()
        self._thread = None
        self._started = False
        self._hwnd = None
        self._font = None

    def start(self):
        """启动悬浮框线程 (仅一次)"""
        if self._started:
            return
        self._started = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def update(self, phase=None, rounds=None, success=None, running=None):
        """线程安全更新状态"""
        with self._lock:
            if phase is not None:
                self._phase = phase
            if rounds is not None:
                self._rounds = rounds
            if success is not None:
                self._success = success
            if running is not None:
                self._running = running

    def _get_text(self):
        """获取当前显示文本"""
        with self._lock:
            state = "● 运行中" if self._running else "○ 待命"
            return f"{state}  R:{self._rounds}  OK:{self._success}\n{self._phase}"

    def _run(self):
        """悬浮框主线程 — 创建窗口并运行消息循环"""
        class_name = "D2OverlayClass"
        window_name = "D2Overlay"

        hInstance = kernel32.GetModuleHandleW(None)

        # 创建字体
        self._font = gdi32.CreateFontW(
            15,           # nHeight
            0, 0, 0,      # nWidth, nEscapement, nOrientation
            FW_BOLD,      # fnWeight
            0, 0, 0,      # fdwItalic, fdwUnderline, fdwStrikeOut
            DEFAULT_CHARSET,
            OUT_DEFAULT_PRECIS,
            CLIP_DEFAULT_PRECIS,
            DEFAULT_QUALITY,
            FF_SWISS,
            "Consolas"
        )

        # WndProc 回调
        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_PAINT:
                self._on_paint(hwnd)
                return 0
            elif msg == WM_TIMER:
                user32.InvalidateRect(hwnd, None, False)
                return 0
            elif msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wnd_proc_ref = WNDPROC(wnd_proc)

        # 注册窗口类
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.style = CS_HREDRAW | CS_VREDRAW
        wc.lpfnWndProc = ctypes.cast(self._wnd_proc_ref, ctypes.c_void_p)
        wc.hInstance = hInstance
        # 窗口类背景设为深绿色 — WM_PAINT 时自动填充
        wc.hbrBackground = gdi32.CreateSolidBrush(COLOR_BG)
        wc.lpszClassName = class_name

        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if atom == 0:
            return

        # 创建窗口
        ex_style = (WS_EX_LAYERED | WS_EX_TRANSPARENT |
                    WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
        style = WS_POPUP | WS_VISIBLE

        self._hwnd = user32.CreateWindowExW(
            ex_style, class_name, window_name, style,
            WIN_X, WIN_Y, WIN_W, WIN_H,
            None, None, hInstance, None
        )

        if self._hwnd == 0:
            return

        # 设置颜色键透明 — COLOR_KEY 变透明，其余不透明
        user32.SetLayeredWindowAttributes(
            self._hwnd, COLOR_KEY, 255, LWA_COLORKEY
        )

        # 置顶
        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        user32.SetWindowPos(
            self._hwnd, HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        )

        # 定时刷新
        user32.SetTimer(self._hwnd, TIMER_ID, TIMER_INTERVAL, None)

        # 消息循环
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _on_paint(self, hwnd):
        """WM_PAINT 处理 — 绘制绿框+文字"""
        ps = PAINTSTRUCT()
        hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))

        try:
            # 1. 用深绿画刷 + 亮绿画笔绘制填充矩形 (背景+边框一体)
            bg_brush = gdi32.CreateSolidBrush(COLOR_BG)
            border_pen = gdi32.CreatePen(PS_SOLID, 1, COLOR_BORDER)

            old_brush = gdi32.SelectObject(hdc, bg_brush)
            old_pen = gdi32.SelectObject(hdc, border_pen)

            gdi32.Rectangle(hdc, 0, 0, WIN_W, WIN_H)

            gdi32.SelectObject(hdc, old_brush)
            gdi32.SelectObject(hdc, old_pen)
            gdi32.DeleteObject(bg_brush)
            gdi32.DeleteObject(border_pen)

            # 2. 绘制文字
            old_font = gdi32.SelectObject(hdc, self._font)
            gdi32.SetTextColor(hdc, COLOR_TEXT)
            gdi32.SetBkMode(hdc, TRANSPARENT)

            text = self._get_text()

            text_rect = wintypes.RECT()
            text_rect.left = 8
            text_rect.top = 5
            text_rect.right = WIN_W - 8
            text_rect.bottom = WIN_H - 5

            user32.DrawTextW(
                hdc, text, -1,
                ctypes.byref(text_rect),
                DT_LEFT | DT_TOP | DT_NOCLIP
            )

            gdi32.SelectObject(hdc, old_font)
        finally:
            user32.EndPaint(hwnd, ctypes.byref(ps))


# 全局单例
overlay = Overlay()

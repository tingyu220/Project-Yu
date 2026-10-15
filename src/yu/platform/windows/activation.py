"""复用已运行的应用，不通过再次启动程序来唤回窗口。"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import time

import psutil


def running_app_pids(executable: str) -> tuple[set[int], bool]:
    """按完整路径匹配；同名但无法读取路径时保守阻止重复启动。"""
    wanted = os.path.normcase(os.path.realpath(executable))
    pids: set[int] = set()
    uncertain = False
    for process in psutil.process_iter(["pid", "name", "exe"]):
        try:
            info = process.info
            path = info.get("exe")
            if path and os.path.normcase(os.path.realpath(path)) == wanted:
                pids.add(info["pid"])
            elif not path and (info.get("name") or "").casefold() == Path(executable).name.casefold():
                uncertain = True
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            uncertain = True
    return pids, uncertain


def _user32():
    api = ctypes.WinDLL("user32", use_last_error=True)
    api.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    api.GetWindowThreadProcessId.restype = wintypes.DWORD
    api.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    api.GetWindowTextLengthW.restype = ctypes.c_int
    api.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    api.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    api.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    api.GetWindow.restype = wintypes.HWND
    api.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    api.GetWindowLongW.restype = ctypes.c_long
    api.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    api.GetWindowRect.restype = wintypes.BOOL
    api.IsWindowVisible.argtypes = [wintypes.HWND]
    api.IsWindowVisible.restype = wintypes.BOOL
    api.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
    api.ShowWindowAsync.restype = wintypes.BOOL
    api.SetForegroundWindow.argtypes = [wintypes.HWND]
    api.SetForegroundWindow.restype = wintypes.BOOL
    api.GetForegroundWindow.restype = wintypes.HWND
    return api


def select_main_windows(windows: list[tuple[int, bool, int, int]]) -> list[int]:
    """同一进程内按可见性、面积优先恢复主窗口，独立进程仍保留歧义。"""
    selected: dict[int, tuple[bool, int, int]] = {}
    for pid, visible, area, hwnd in windows:
        candidate = (visible, area, hwnd)
        if pid not in selected or candidate[:2] > selected[pid][:2]:
            selected[pid] = candidate
    return [item[2] for item in selected.values()]


def is_main_window(title: str, class_name: str, style: int, extended: int, owner: int) -> bool:
    """消息辅助窗口即使带标题栏和大面积，也不能当作主窗口恢复。"""
    helper = "messagewindow" in (title + class_name).casefold()
    return bool(title.strip() and not helper and not owner and not extended & 0x80
                and style & 0x00C00000 == 0x00C00000)


def app_windows(pids: set[int]) -> list[int]:
    """只列出目标进程的无所属、带标题顶层窗口，排除后台辅助窗口。"""
    api = _user32()
    candidates: list[tuple[int, bool, int, int]] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def collect(hwnd, _):
        pid = wintypes.DWORD()
        api.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        style = api.GetWindowLongW(hwnd, -16)
        extended = api.GetWindowLongW(hwnd, -20)
        title, class_name = ctypes.create_unicode_buffer(512), ctypes.create_unicode_buffer(256)
        if pid.value not in pids:
            return True
        api.GetWindowTextW(hwnd, title, len(title))
        api.GetClassNameW(hwnd, class_name, len(class_name))
        # 仅恢复有标题栏的普通顶层窗口，不显示托盘消息窗口和工具窗。
        if is_main_window(title.value, class_name.value, style, extended, api.GetWindow(hwnd, 4)):
            rect = wintypes.RECT()
            if api.GetWindowRect(hwnd, ctypes.byref(rect)):
                area = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
                if area:
                    candidates.append((pid.value, bool(api.IsWindowVisible(hwnd)), area, hwnd))
        return True

    api.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    api.EnumWindows.restype = wintypes.BOOL
    if not api.EnumWindows(collect, 0):
        raise OSError("无法枚举应用窗口")
    return select_main_windows(candidates)


def activate_window(hwnd: int) -> bool:
    api = _user32()
    api.ShowWindowAsync(hwnd, 9)  # SW_RESTORE：同时适用最小化和托盘隐藏窗口。
    api.SetForegroundWindow(hwnd)
    deadline = time.monotonic() + 0.5
    while time.monotonic() < deadline:
        if api.GetForegroundWindow() == hwnd and api.IsWindowVisible(hwnd):
            return True
        time.sleep(0.025)
    return False


def reuse_running_app(executable: str) -> bool | None:
    """None 表示未运行，True 表示已恢复，False 表示已运行但无法可靠恢复。"""
    if os.name != "nt":
        return None
    pids, uncertain = running_app_pids(executable)
    if not pids:
        return False if uncertain else None
    windows = app_windows(pids)
    return activate_window(windows[0]) if len(windows) == 1 else False

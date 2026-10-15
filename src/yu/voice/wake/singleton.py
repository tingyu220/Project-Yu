"""Windows 命名互斥，只释放本进程持有的句柄。"""
import ctypes
from ctypes import wintypes


class SingleInstance:
    def __init__(self, name: str):
        self.name, self.handle = name, None

    def __enter__(self):
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        api.CreateMutexW.restype = wintypes.HANDLE
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        api.CloseHandle.restype = wintypes.BOOL
        self.api = api
        self.handle = api.CreateMutexW(None, False, self.name)
        error = ctypes.get_last_error()
        if not self.handle:
            raise OSError("无法创建本地监听互斥锁")
        if error == 183:
            self.__exit__()
            raise RuntimeError("Yu 已在运行，不会重复创建语音监听器")
        return self

    def __exit__(self, *_):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None

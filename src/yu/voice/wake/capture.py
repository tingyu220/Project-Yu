"""单麦克风输入和有界缓冲；回调不执行解码、网络或磁盘操作。"""
from queue import Empty, Full, Queue

from .config import WakeConfig


class CaptureError(RuntimeError):
    """采集已失效，必须关闭输入，不能继续假装待唤醒。"""


class AudioCapture:
    def __init__(self, config: WakeConfig):
        self.config = config
        self._queue: Queue[bytes] = Queue(config.queue_frames)
        self._stream = None
        self._error: str | None = None
        self.muted = False

    def _callback(self, data, frames, timing, status):
        if self._error:
            return
        audio = bytes(data)
        if status:
            self._error = "麦克风音频采集异常"
        elif frames != 1600 or len(audio) != 3200:
            self._error = "麦克风音频帧格式异常"
        elif self.muted:
            return
        else:
            try:
                self._queue.put_nowait(audio)
            except Full:
                self._error = "音频队列溢出，停止本次监听"

    def __enter__(self):
        if self._stream is not None:
            raise RuntimeError("麦克风已开启")
        import sounddevice as sd
        sd.check_input_settings(device=self.config.device, channels=1, dtype="int16", samplerate=16000)
        self._stream = sd.RawInputStream(
            device=self.config.device, channels=1, dtype="int16", samplerate=16000,
            blocksize=1600, callback=self._callback,
        )
        try:
            self._stream.start()
        except BaseException:
            self._stream.close()
            self._stream = None
            raise
        return self

    def read(self, timeout: float) -> bytes:
        if self._error:
            raise CaptureError(self._error)
        if self._stream is not None and not self._stream.active:
            raise CaptureError("麦克风已断开，停止监听")
        try:
            audio = self._queue.get(timeout=timeout)
        except Empty:
            if self._error:
                raise CaptureError(self._error)
            raise TimeoutError("暂未收到音频") from None
        if self._error:
            raise CaptureError(self._error)
        return audio

    def discard(self):
        """切换状态时丢弃积压音频；采集错误不能通过清空队列隐藏。"""
        while True:
            try:
                self._queue.get_nowait()
            except Empty:
                return

    def __exit__(self, *_):
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()

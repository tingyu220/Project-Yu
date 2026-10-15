"""中国大陆默认语音识别，凭据仅保留在后端。"""
from __future__ import annotations

import base64
import io
import json
import os
import urllib.error
import urllib.request
import wave
from typing import Protocol

MAX_AUDIO_BYTES = 4 * 1024 * 1024


class VoiceError(Exception):
    """可以展示给用户的稳定错误。"""


class SpeechRecognizer(Protocol):
    def transcribe(self, audio: bytes) -> str: ...


def validate_wav(audio: bytes) -> None:
    if not audio or len(audio) > MAX_AUDIO_BYTES:
        raise VoiceError("录音为空或过大，请录制 30 秒以内的语音。")
    try:
        with wave.open(io.BytesIO(audio), "rb") as source:
            rate, frames = source.getframerate(), source.getnframes()
            if source.getnchannels() != 1 or source.getsampwidth() != 2 or not 8000 <= rate <= 48000:
                raise VoiceError("录音需要单声道 PCM16 WAV 格式。")
            if not 0.15 <= frames / rate <= 31:
                raise VoiceError("请录制 0.15 至 30 秒的语音。")
            if len(source.readframes(frames)) != frames * 2:
                raise VoiceError("录音不完整，请重试。")
    except (wave.Error, EOFError) as exc:
        raise VoiceError("无法读取录音，请重新录制。") from exc


class QwenRecognizer:
    model = "qwen3-asr-flash"

    def __init__(self):
        self.key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
        self.region = os.environ.get("YU_VOICE_REGION", "cn-beijing")
        hosts = {"cn-beijing": "dashscope.aliyuncs.com", "singapore": "dashscope-intl.aliyuncs.com"}
        self.host = hosts.get(self.region)

    @property
    def available(self) -> bool:
        return bool(self.key and self.host)

    def transcribe(self, audio: bytes) -> str:
        validate_wav(audio)
        if not self.available:
            raise VoiceError("语音服务未配置，请在本机设置北京地域 DASHSCOPE_API_KEY。")
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": [{"type": "input_audio", "input_audio": {
                "data": "data:audio/wav;base64," + base64.b64encode(audio).decode("ascii")
            }}]}],
            "stream": False,
            "asr_options": {"enable_itn": False},
        }
        request = urllib.request.Request(
            f"https://{self.host}/compatible-mode/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.loads(response.read(256 * 1024))
            text = result["choices"][0]["message"]["content"]
            if not isinstance(text, str) or len(text) > 4000:
                raise VoiceError("语音服务返回异常，请重试。")
            if not text.strip():
                raise VoiceError("没有听清，请靠近麦克风再试一次。")
            return text.strip()
        except urllib.error.HTTPError as exc:
            messages = {401: "语音密钥无效，请核对地域和 Key。", 403: "语音模型未开通或没有访问权限。", 429: "语音服务繁忙或额度不足，请稍后重试。"}
            raise VoiceError(messages.get(exc.code, "语音服务暂不可用，请改用文字输入。")) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise VoiceError("语音识别连接超时，请重试或改用文字。") from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise VoiceError("语音服务返回异常，请重试。") from exc

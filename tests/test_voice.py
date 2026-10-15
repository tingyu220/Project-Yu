"""语音转写不执行命令，验证协议、错误和音频边界。"""
import io
import json
import wave
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yu.api.voice import voice_router
from yu.voice.provider import QwenRecognizer, VoiceError, validate_wav


def wav(seconds=1):
    output = io.BytesIO()
    with wave.open(output, "wb") as source:
        source.setparams((1, 2, 16000, 0, "NONE", "NONE"))
        source.writeframes(b"\x00\x00" * int(seconds * 16000))
    return output.getvalue()


@pytest.mark.parametrize("audio", [b"", b"not audio", wav(32), wav(0.01), wav()[:-10]], ids=["empty", "invalid", "too-long", "too-short", "truncated"])
def test_invalid_audio_is_rejected(audio):
    with pytest.raises(VoiceError):
        validate_wav(audio)


def test_provider_uses_china_endpoint_and_audio_payload(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.delenv("YU_VOICE_REGION", raising=False)
    response = io.BytesIO(json.dumps({"choices": [{"message": {"content": "打开QQ音乐"}}]}).encode())
    with patch("urllib.request.urlopen", return_value=response) as call:
        assert QwenRecognizer().transcribe(wav()) == "打开QQ音乐"
    request = call.call_args.args[0]
    assert request.full_url.startswith("https://dashscope.aliyuncs.com/")
    payload = json.loads(request.data)
    assert payload["model"] == "qwen3-asr-flash"
    assert payload["messages"][0]["content"][0]["input_audio"]["data"].startswith("data:audio/wav;base64,")


def test_unsupported_region_fails_closed(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test")
    monkeypatch.setenv("YU_VOICE_REGION", "us")
    assert not QwenRecognizer().available


def test_api_only_returns_transcript(monkeypatch):
    app = FastAPI()
    app.include_router(voice_router())
    monkeypatch.setattr(QwenRecognizer, "transcribe", lambda self, data: "打开QQ音乐")
    with TestClient(app) as client:
        response = client.post("/api/voice/transcribe", content=wav(), headers={"content-type": "audio/wav"})
        assert response.json() == {"text": "打开QQ音乐"}
        assert client.post("/api/voice/transcribe", content=b"junk").status_code == 415


def test_status_does_not_expose_key(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "private-test-value")
    app = FastAPI()
    app.include_router(voice_router())
    with TestClient(app) as client:
        response = client.get("/api/voice/status")
        assert "private-test-value" not in response.text
        assert response.json()["available"]

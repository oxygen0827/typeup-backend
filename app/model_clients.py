import base64
import io
import wave

import requests

from app.config import get_settings

SAMPLE_RATE = 16000


def pcm_to_wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    return buf.getvalue()


def transcribe_glm_asr(pcm: bytes) -> str:
    settings = get_settings()
    if not settings.glm_api_key:
        raise RuntimeError("GLM_API_KEY 未配置")
    wav = pcm_to_wav(pcm)
    resp = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/audio/transcriptions",
        headers={"Authorization": f"Bearer {settings.glm_api_key}"},
        data={"model": settings.glm_asr_model, "stream": "false"},
        files={"file": ("audio.wav", wav, "audio/wav")},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"GLM-ASR HTTP {resp.status_code}: {resp.text}")
    return (resp.json().get("text") or "").strip()


def chat_zhipu(messages: list[dict], temperature: float = 0.1, max_tokens: int = 1000) -> dict:
    settings = get_settings()
    if not settings.glm_api_key:
        raise RuntimeError("GLM_API_KEY 未配置")
    resp = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.glm_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    if not resp.ok:
        raise RuntimeError(f"LLM HTTP {resp.status_code}: {resp.text}")
    data = resp.json()
    text = data["choices"][0]["message"]["content"].strip()
    return {"text": text, "usage": data.get("usage") or {}}


def estimate_pcm_seconds(pcm: bytes) -> int:
    return max(1, round(len(pcm) / SAMPLE_RATE / 2))

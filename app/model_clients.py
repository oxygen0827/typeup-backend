import io
import math
import wave

import requests

from app.config import get_settings

SAMPLE_RATE = 16000
WAV_CHANNELS = 1
WAV_SAMPLE_WIDTH = 2
MAX_ASR_SECONDS = 30
MAX_ASR_FILE_BYTES = 25 * 1024 * 1024


class InvalidWavAudio(ValueError):
    pass


def validate_wav_audio(wav_audio: bytes) -> int:
    if not wav_audio:
        raise InvalidWavAudio("音频文件不能为空")
    if len(wav_audio) > MAX_ASR_FILE_BYTES:
        raise InvalidWavAudio("音频文件不能超过 25 MB")

    try:
        with wave.open(io.BytesIO(wav_audio), "rb") as wav:
            if wav.getcomptype() != "NONE":
                raise InvalidWavAudio("仅支持 PCM 编码的 WAV 音频")
            if wav.getnchannels() != WAV_CHANNELS:
                raise InvalidWavAudio("WAV 音频必须是单声道 mono")
            if wav.getsampwidth() != WAV_SAMPLE_WIDTH:
                raise InvalidWavAudio("WAV 音频必须是 16-bit PCM")
            if wav.getframerate() != SAMPLE_RATE:
                raise InvalidWavAudio("WAV 音频采样率必须是 16000 Hz")

            frame_count = wav.getnframes()
            if frame_count <= 0:
                raise InvalidWavAudio("WAV 音频没有可识别的音频帧")

            audio_seconds = max(1, math.ceil(frame_count / SAMPLE_RATE))
            if audio_seconds > MAX_ASR_SECONDS:
                raise InvalidWavAudio("单次语音识别音频不能超过 30 秒")
            return audio_seconds
    except InvalidWavAudio:
        raise
    except (EOFError, wave.Error) as e:
        raise InvalidWavAudio("请上传合法的 WAV 音频文件") from e


def transcribe_glm_asr(wav_audio: bytes) -> str:
    settings = get_settings()
    if settings.dev_mock_models:
        return "这是一段本地联调用的模拟语音识别结果。"
    if not settings.glm_api_key:
        raise RuntimeError("GLM_API_KEY 未配置")
    resp = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/audio/transcriptions",
        headers={"Authorization": f"Bearer {settings.glm_api_key}"},
        data={"model": settings.glm_asr_model, "stream": "false"},
        files={"file": ("audio.wav", wav_audio, "audio/wav")},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"GLM-ASR HTTP {resp.status_code}: {resp.text}")
    return (resp.json().get("text") or "").strip()


def chat_zhipu(messages: list[dict], temperature: float = 0.1, max_tokens: int = 1000) -> dict:
    settings = get_settings()
    if settings.dev_mock_models:
        last_user_message = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        text = "这是本地联调用的模拟 AI 回复。"
        if last_user_message:
            text += f" 我收到了你的消息：{last_user_message}"
        return {
            "text": text,
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "mock": True,
            },
        }
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

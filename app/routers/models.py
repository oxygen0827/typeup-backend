from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.model_clients import chat_zhipu, estimate_pcm_seconds, transcribe_glm_asr
from app.models import UsageKind, UsageRecord, User
from app.schemas import LLMChatIn, LLMChatOut
from app.security import get_current_user
from app.services import ensure_ai_quota, ensure_stt_quota

router = APIRouter(prefix="/v1", tags=["models"])


@router.post("/stt/transcribe")
async def transcribe(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pcm = await file.read()
    audio_seconds = estimate_pcm_seconds(pcm)
    try:
        ensure_stt_quota(db, current_user.id, audio_seconds)
    except PermissionError as e:
        raise HTTPException(status_code=402, detail=str(e)) from e

    try:
        text = transcribe_glm_asr(pcm)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"语音识别失败: {e}") from e

    settings = get_settings()
    db.add(UsageRecord(
        user_id=current_user.id,
        kind=UsageKind.stt,
        provider="zhipuai",
        model=settings.glm_asr_model,
        audio_seconds=audio_seconds,
    ))
    db.commit()
    return {"text": text, "audio_seconds": audio_seconds}


@router.post("/llm/chat", response_model=LLMChatOut)
def llm_chat(
    payload: LLMChatIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        ensure_ai_quota(db, current_user.id)
    except PermissionError as e:
        raise HTTPException(status_code=402, detail=str(e)) from e

    messages = [m.model_dump() for m in payload.messages]
    try:
        result = chat_zhipu(messages, temperature=payload.temperature, max_tokens=payload.max_tokens)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM 请求失败: {e}") from e

    settings = get_settings()
    usage = result["usage"]
    db.add(UsageRecord(
        user_id=current_user.id,
        kind=UsageKind.llm_chat,
        provider=settings.llm_provider,
        model=settings.llm_model,
        input_tokens=int(usage.get("prompt_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or 0),
    ))
    db.commit()
    return LLMChatOut(text=result["text"], usage=usage)

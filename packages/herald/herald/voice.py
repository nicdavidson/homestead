from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

from aiogram import Bot, types

log = logging.getLogger(__name__)


async def handle_voice(bot: Bot, message: types.Message) -> str | None:
    """Download and transcribe a voice message. Returns text or None."""
    if not message.voice:
        return None

    # Download the voice file
    file = await bot.get_file(message.voice.file_id)
    if not file.file_path:
        return None

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        await bot.download_file(file.file_path, str(tmp_path))
        log.info("Downloaded voice message: %s (%d bytes)", tmp_path, tmp_path.stat().st_size)

        # Try whisper transcription
        text = await _transcribe_whisper(tmp_path)
        if text:
            return text

        # Fallback: try using Claude's built-in audio (future)
        return None

    finally:
        tmp_path.unlink(missing_ok=True)


async def _transcribe_whisper(audio_path: Path) -> str | None:
    """Transcribe using local whisper if available."""
    try:
        # Try whisper CLI
        proc = await asyncio.create_subprocess_exec(
            "whisper", str(audio_path),
            "--model", "base",
            "--output_format", "txt",
            "--output_dir", str(audio_path.parent),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.wait(), timeout=60)

        txt_path = audio_path.with_suffix(".txt")
        if txt_path.exists():
            text = txt_path.read_text().strip()
            txt_path.unlink(missing_ok=True)
            if text:
                log.info("Whisper transcription: %d chars", len(text))
                return text
    except FileNotFoundError:
        log.debug("whisper CLI not found")
    except asyncio.TimeoutError:
        log.warning("whisper transcription timed out")
    except Exception:
        log.debug("whisper transcription failed", exc_info=True)

    return None

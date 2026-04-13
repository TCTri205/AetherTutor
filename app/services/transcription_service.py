"""
Audio Transcription Service - Transcribe audio files to text.

Supports:
- OpenAI Whisper API (cloud)
- Local mode rejection (per BR-008)

Audio formats: .mp3, .wav, .m4a, .ogg, .flac
"""

import logging
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from ..config import settings

logger = logging.getLogger(__name__)

# Supported audio extensions
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.webm'}


@dataclass
class TranscriptionSegment:
    """A single segment of transcribed audio."""
    text: str
    start: float  # seconds
    end: float


@dataclass
class TranscriptionResult:
    """Complete transcription result."""
    full_text: str
    segments: List[TranscriptionSegment]
    language: str
    duration: float  # seconds

    @property
    def formatted_transcript(self) -> str:
        """Format transcript with timestamps."""
        if not self.segments:
            return self.full_text

        lines = []
        for seg in self.segments:
            start_min = int(seg.start // 60)
            start_sec = int(seg.start % 60)
            lines.append(f"[{start_min:02d}:{start_sec:02d}] {seg.text}")

        return "\n".join(lines)


class TranscriptionService:
    """
    Service for transcribing audio files.

    BR-008 Compliance:
    - If local_mode=True and whisper_cpp=False → reject with clear error
    - Requires OpenAI API key for cloud transcription
    """

    def __init__(self):
        self._openai_client = None

    def _get_openai_client(self):
        """Lazy-load OpenAI client."""
        if self._openai_client is None:
            if not settings.OPENAI_API_KEY:
                logger.warning("OPENAI_API_KEY not configured")
                return None

            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
                return None

        return self._openai_client

    def validate_audio_file(self, file_path: Path) -> tuple[bool, str]:
        """
        Validate audio file for transcription.

        Args:
            file_path: Path to audio file

        Returns:
            (is_valid, error_message)
        """
        if not file_path.exists():
            return False, f"File not found: {file_path}"

        if file_path.suffix.lower() not in AUDIO_EXTENSIONS:
            return False, f"Unsupported audio format: {file_path.suffix}. Supported: {', '.join(AUDIO_EXTENSIONS)}"

        # Check file size (max 25MB for Whisper API)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 25:
            return False, f"File too large: {file_size_mb:.1f}MB. Maximum: 25MB"

        return True, ""

    async def transcribe(
        self,
        file_path: Path,
        language: Optional[str] = None,
        response_format: str = "verbose_json",
    ) -> Optional[TranscriptionResult]:
        """
        Transcribe an audio file using OpenAI Whisper.

        BR-008: Rejects if local mode without Whisper support.

        Args:
            file_path: Path to audio file
            language: Target language code (e.g., 'en', 'vi')
            response_format: Whisper response format

        Returns:
            TranscriptionResult or None if failed
        """
        # BR-008 Compliance Check
        if settings.LOCAL_MODE and not getattr(settings, 'WHISPER_CPP', False):
            error_msg = (
                "Transcription không khả dụng ở Local Mode. "
                "Vui lòng: (1) Chuyển sang Cloud Mode với OpenAI API key, "
                "hoặc (2) Cài đặt Whisper.cpp, hoặc (3) Dán transcript thủ công."
            )
            logger.warning(f"BR-008: {error_msg}")
            raise RuntimeError(error_msg)

        # Validate file
        is_valid, error_msg = self.validate_audio_file(file_path)
        if not is_valid:
            logger.error(f"Invalid audio file: {error_msg}")
            return None

        client = self._get_openai_client()
        if not client:
            logger.error("OpenAI client not available")
            return None

        try:
            with open(file_path, "rb") as audio_file:
                kwargs = {
                    "file": audio_file,
                    "model": "whisper-1",
                    "response_format": response_format,
                }
                if language:
                    kwargs["language"] = language

                result = client.audio.transcriptions.create(**kwargs)

            # Parse response
            if response_format == "verbose_json":
                segments = [
                    TranscriptionSegment(
                        text=seg.text.strip(),
                        start=seg.start,
                        end=seg.end,
                    )
                    for seg in result.segments
                ] if hasattr(result, 'segments') else []

                return TranscriptionResult(
                    full_text=result.text.strip(),
                    segments=segments,
                    language=result.language if hasattr(result, 'language') else 'unknown',
                    duration=segments[-1].end if segments else 0.0,
                )
            else:
                # Simple text response
                return TranscriptionResult(
                    full_text=result.text.strip() if hasattr(result, 'text') else str(result),
                    segments=[],
                    language=language or 'unknown',
                    duration=0.0,
                )

        except Exception as e:
            logger.error(f"Transcription failed for {file_path}: {e}")
            return None

    async def transcribe_chunks(
        self,
        file_path: Path,
        chunk_duration: float = 600.0,  # 10 minutes
    ) -> Optional[TranscriptionResult]:
        """
        Transcribe audio in chunks (for long files).

        Args:
            file_path: Path to audio file
            chunk_duration: Max duration per chunk in seconds

        Returns:
            Combined TranscriptionResult or None
        """
        # For now, use simple transcription
        # TODO: Implement actual chunking for files > 25MB
        return await self.transcribe(file_path)


# Singleton instance
transcription_service = TranscriptionService()

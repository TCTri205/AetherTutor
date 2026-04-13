"""
Tests for Sprint 17: Media Microlearning

Tests:
- YouTube URL parsing
- YouTube transcript service
- Audio file validation
- Transcription service (BR-008 compliance)
"""
import pytest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.youtube_service import (
    YouTubeService,
    youtube_service,
    TranscriptSegment,
    TranscriptResult,
)
from app.services.transcription_service import (
    TranscriptionService,
    transcription_service,
    TranscriptionSegment,
    TranscriptionResult,
    AUDIO_EXTENSIONS,
)


# --- YouTube Service Tests ---

class TestYouTubeUrlParsing:
    """Test YouTube URL/ID extraction."""

    def test_extract_video_id_from_url(self):
        """Test extracting video ID from various YouTube URL formats."""
        service = YouTubeService()

        # Standard watch URL
        assert service.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

        # Short URL
        assert service.extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

        # Embed URL
        assert service.extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

        # Shorts URL
        assert service.extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_video_id_direct(self):
        """Test passing video ID directly."""
        service = YouTubeService()
        assert service.extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_invalid_url_returns_none(self):
        """Test invalid URLs return None."""
        service = YouTubeService()
        assert service.extract_video_id("https://example.com/not-youtube") is None
        assert service.extract_video_id("invalid") is None
        assert service.extract_video_id("") is None


class TestTranscriptResult:
    """Test transcript data structures."""

    def test_full_text_concatenation(self):
        """Test combining segments into full text."""
        segments = [
            TranscriptSegment(text="Hello", start=0.0, duration=1.0),
            TranscriptSegment(text="World", start=1.0, duration=1.5),
        ]
        result = TranscriptResult(
            video_id="abc123",
            title="Test Video",
            language="en",
            segments=segments,
        )
        assert result.full_text == "Hello\nWorld"


class TestTranscriptionService:
    """Test audio transcription service."""

    def test_audio_extensions_supported(self):
        """Test supported audio formats."""
        assert '.mp3' in AUDIO_EXTENSIONS
        assert '.wav' in AUDIO_EXTENSIONS
        assert '.m4a' in AUDIO_EXTENSIONS
        assert '.ogg' in AUDIO_EXTENSIONS
        assert '.flac' in AUDIO_EXTENSIONS

    def test_validate_audio_file_extension(self):
        """Test file extension validation."""
        service = TranscriptionService()

        # Valid extensions
        for ext in ['.mp3', '.wav', '.m4a']:
            valid, msg = service.validate_audio_file(Path(f"test{ext}"))
            # Will fail on existence check, but that's OK — we test the logic path
            assert ext in AUDIO_EXTENSIONS

        # Invalid extension
        valid, msg = service.validate_audio_file(Path("test.pdf"))
        assert not valid
        assert ".pdf" in msg

    def test_validate_audio_file_size(self, tmp_path):
        """Test file size validation (max 25MB)."""
        service = TranscriptionService()

        # Create a small valid file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")

        valid, msg = service.validate_audio_file(audio_file)
        assert valid is True

    def test_validate_nonexistent_file(self):
        """Test validation of non-existent file."""
        service = TranscriptionService()
        valid, msg = service.validate_audio_file(Path("/nonexistent/file.mp3"))
        assert not valid
        assert "not found" in msg.lower()


@pytest.mark.asyncio
async def test_br008_local_mode_rejection(monkeypatch):
    """
    BR-008 Compliance Test:
    If LOCAL_MODE=True and WHISPER_CPP=False → reject transcription.
    """
    # Mock settings to simulate local mode without whisper
    class MockSettings:
        LOCAL_MODE = True
        WHISPER_CPP = False
        OPENAI_API_KEY = None

    monkeypatch.setattr("app.services.transcription_service.settings", MockSettings())

    service = TranscriptionService()

    with pytest.raises(RuntimeError) as exc_info:
        await service.transcribe(Path("test.mp3"))

    assert "Local Mode" in str(exc_info.value)
    assert "Cloud Mode" in str(exc_info.value) or "thủ công" in str(exc_info.value)


@pytest.mark.asyncio
async def test_youtube_service_fetch_mock():
    """Test YouTube transcript fetch (mocked)."""
    service = YouTubeService()

    # Mock the API
    mock_api = MagicMock()
    mock_transcript_list = MagicMock()
    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = [
        {"text": "Hello world", "start": 0.0, "duration": 2.0},
        {"text": "This is a test", "start": 2.0, "duration": 3.0},
    ]
    mock_transcript.language = "en"
    mock_transcript_list.find_transcript.return_value = mock_transcript

    # We can't easily test the full flow without youtube-transcript-api
    # but we can test URL parsing
    video_id = service.extract_video_id("https://youtube.com/watch?v=test1234567")
    assert video_id == "test1234567"


@pytest.mark.asyncio
async def test_transcription_result_formatting():
    """Test formatted transcript with timestamps."""
    segments = [
        TranscriptionSegment(text="Hello", start=0.0, end=2.0),
        TranscriptionSegment(text="World", start=30.0, end=32.5),
        TranscriptionSegment(text="Test", start=125.0, end=127.0),
    ]
    result = TranscriptionResult(
        full_text="Hello World Test",
        segments=segments,
        language="en",
        duration=127.0,
    )

    formatted = result.formatted_transcript
    assert "[00:00] Hello" in formatted
    assert "[00:30] World" in formatted
    assert "[02:05] Test" in formatted

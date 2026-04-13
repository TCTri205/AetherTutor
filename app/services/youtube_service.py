"""
YouTube Transcript Service - Fetch transcripts from YouTube videos.

Uses youtube-transcript-api package to extract transcripts.
Supports both video URLs and video IDs.
"""

import re
import logging
from typing import Optional, List
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    """A single segment of a YouTube transcript."""
    text: str
    start: float  # seconds
    duration: float


@dataclass
class TranscriptResult:
    """Complete transcript result."""
    video_id: str
    title: str
    language: str
    segments: List[TranscriptSegment]

    @property
    def full_text(self) -> str:
        """Combine all segments into full text."""
        return "\n".join(s.text for s in self.segments)


# YouTube URL patterns
YOUTUBE_URL_PATTERN = re.compile(
    r'(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})'
)


class YouTubeService:
    """
    Service for fetching YouTube video transcripts.

    Usage:
        service = YouTubeService()
        result = await service.fetch_transcript("https://youtube.com/watch?v=abc123")
    """

    def __init__(self):
        self._api = None

    def _get_api(self):
        """Lazy-load youtube-transcript-api."""
        if self._api is None:
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                self._api = YouTubeTranscriptApi
            except ImportError:
                logger.warning("youtube-transcript-api not installed. Run: pip install youtube-transcript-api")
                self._api = None
        return self._api

    @staticmethod
    def extract_video_id(url_or_id: str) -> Optional[str]:
        """
        Extract YouTube video ID from URL or return as-is if already an ID.

        Args:
            url_or_id: Full YouTube URL or just the video ID

        Returns:
            Video ID string or None if invalid
        """
        # Check if it's already a valid ID (11 chars)
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
            return url_or_id

        # Try to extract from URL
        match = YOUTUBE_URL_PATTERN.search(url_or_id)
        if match:
            return match.group(1)

        # Try parsing query params
        try:
            parsed = urlparse(url_or_id)
            if parsed.hostname and 'youtube.com' in parsed.hostname:
                params = parse_qs(parsed.query)
                if 'v' in params:
                    return params['v'][0]
        except Exception:
            pass

        return None

    async def fetch_transcript(
        self,
        url_or_id: str,
        languages: Optional[List[str]] = None,
    ) -> Optional[TranscriptResult]:
        """
        Fetch transcript from a YouTube video.

        Args:
            url_or_id: YouTube URL or video ID
            languages: Preferred languages (default: ['en', 'vi'])

        Returns:
            TranscriptResult or None if failed
        """
        api = self._get_api()
        if not api:
            logger.error("YouTube transcript API not available")
            return None

        video_id = self.extract_video_id(url_or_id)
        if not video_id:
            logger.error(f"Invalid YouTube URL or ID: {url_or_id}")
            return None

        try:
            # Fetch transcript with language preference
            langs = languages or ['en', 'vi']
            transcript_list = api.list_transcripts(video_id)

            # Try to find transcript in preferred languages
            transcript = None
            for lang in langs:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    break
                except Exception:
                    continue

            # Fallback to any available transcript
            if not transcript:
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                except Exception:
                    try:
                        transcript = transcript_list.find_manually_created_transcript(['en'])
                    except Exception:
                        # Last resort: get first available
                        for t in transcript_list:
                            transcript = t
                            break

            if not transcript:
                logger.warning(f"No transcript found for video {video_id}")
                return None

            # Fetch transcript data
            data = transcript.fetch()
            segments = [
                TranscriptSegment(
                    text=item['text'],
                    start=item.get('start', 0.0),
                    duration=item.get('duration', 0.0),
                )
                for item in data
            ]

            # Translate transcript title if possible
            title = f"YouTube Video: {video_id}"
            try:
                # Try to get translated title
                title = transcript.translation.lang_code
            except Exception:
                pass

            result = TranscriptResult(
                video_id=video_id,
                title=title,
                language=transcript.language if hasattr(transcript, 'language') else 'unknown',
                segments=segments,
            )

            logger.info(f"Fetched transcript for video {video_id}: {len(segments)} segments")
            return result

        except Exception as e:
            logger.error(f"Failed to fetch YouTube transcript for {video_id}: {e}")
            return None

    async def get_video_info(self, url_or_id: str) -> Optional[dict]:
        """
        Get basic video information (title, duration, etc).

        Note: This is a placeholder. For full video info,
        consider using pytube or yt-dlp.

        Args:
            url_or_id: YouTube URL or video ID

        Returns:
            Dict with video info or None
        """
        video_id = self.extract_video_id(url_or_id)
        if not video_id:
            return None

        return {
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "embed_url": f"https://www.youtube.com/embed/{video_id}",
        }


# Singleton instance
youtube_service = YouTubeService()

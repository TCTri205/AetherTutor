/**
 * VideoPlayer Component - Sprint 17: Media Microlearning
 * 
 * Supports:
 * - YouTube embeds
 * - Vimeo embeds
 * - Local video files (HTML5 <video>)
 * - Transcript sync (highlight current segment)
 * 
 * Props:
 * - src: Video URL or YouTube/Vimeo ID
 * - type: 'youtube' | 'vimeo' | 'local'
 * - transcript?: Transcript segments
 * - onTimeUpdate?: Callback with current time
 * - autoPlay?: boolean
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Box, Paper, Typography, CircularProgress } from '@mui/material';
import { styled } from '@mui/material/styles';

// --- Types ---

export interface TranscriptSegment {
  text: string;
  start: number;
  end: number;
  speaker?: string;
}

export interface VideoPlayerProps {
  src: string;
  type: 'youtube' | 'vimeo' | 'local';
  title?: string;
  transcript?: TranscriptSegment[];
  onTimeUpdate?: (currentTime: number, segment?: TranscriptSegment) => void;
  autoPlay?: boolean;
  poster?: string; // Thumbnail for local video
}

// --- Styled Components ---

const VideoContainer = styled(Paper)(({ theme }) => ({
  position: 'relative',
  width: '100%',
  paddingBottom: '56.25%', // 16:9 aspect ratio
  backgroundColor: theme.palette.background.default,
  overflow: 'hidden',
  borderRadius: theme.shape.borderRadius,
}));

const VideoOverlay = styled('div')({
  position: 'absolute',
  top: 0,
  left: 0,
  width: '100%',
  height: '100%',
});

const TranscriptPanel = styled(Box)(({ theme }) => ({
  maxHeight: '300px',
  overflowY: 'auto',
  padding: theme.spacing(2),
  backgroundColor: theme.palette.background.paper,
  borderLeft: `1px solid ${theme.palette.divider}`,
}));

const TranscriptSegment = styled('div', {
  shouldForwardProp: (prop) => prop !== '$isActive',
})<{ $isActive: boolean }>(({ theme, $isActive }) => ({
  padding: theme.spacing(1),
  marginBottom: theme.spacing(0.5),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: $isActive ? theme.palette.action.selected : 'transparent',
  borderLeft: $isActive ? `3px solid ${theme.palette.primary.main}` : '3px solid transparent',
  transition: 'all 0.2s ease',
  cursor: 'pointer',
  '&:hover': {
    backgroundColor: theme.palette.action.hover,
  },
}));

// --- Helper Functions ---

const getYouTubeEmbedUrl = (videoId: string): string => {
  return `https://www.youtube.com/embed/${videoId}?enablejsapi=1&origin=${window.location.origin}`;
};

const getVimeoEmbedUrl = (videoId: string): string => {
  return `https://player.vimeo.com/video/${videoId}?api=1&origin=${window.location.origin}`;
};

const extractYouTubeId = (url: string): string => {
  const match = url.match(/(?:youtu\.be\/|youtube\.com(?:\/embed\/|\/v\/|\/watch\?v=|\/user\/\S+|\/ytscreeningroom\?v=|\/sandalsResorts#\w\/\w\/.*\/))([^&\n?#]+)/);
  return match?.[1] || url;
};

const extractVimeoId = (url: string): string => {
  const match = url.match(/vimeo\.com\/(\d+)/);
  return match?.[1] || url;
};

// --- Component ---

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  src,
  type,
  title,
  transcript,
  onTimeUpdate,
  autoPlay = false,
  poster,
}) => {
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const videoRef = useRef<HTMLVideoElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Get current active transcript segment
  const activeSegment = transcript?.find(
    (seg) => currentTime >= seg.start && currentTime <= seg.end
  );

  // Handle time updates for local video
  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current) {
      const time = videoRef.current.currentTime;
      setCurrentTime(time);
      onTimeUpdate?.(time, activeSegment);
    }
  }, [onTimeUpdate, activeSegment]);

  // Handle seeking from transcript click
  const handleSeekToTime = useCallback((time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      setCurrentTime(time);
      onTimeUpdate?.(time, transcript?.find((seg) => time >= seg.start && time <= seg.end));
    }
  }, [onTimeUpdate, transcript]);

  // Video event handlers
  const handlePlay = () => setIsPlaying(true);
  const handlePause = () => setIsPlaying(false);
  const handleLoaded = () => setIsLoading(false);

  // Render based on type
  const renderVideo = () => {
    switch (type) {
      case 'youtube': {
        const videoId = extractYouTubeId(src);
        return (
          <VideoOverlay>
            <iframe
              ref={iframeRef}
              src={getYouTubeEmbedUrl(videoId)}
              title={title || 'YouTube Video'}
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              style={{ width: '100%', height: '100%', position: 'absolute' }}
            />
          </VideoOverlay>
        );
      }

      case 'vimeo': {
        const videoId = extractVimeoId(src);
        return (
          <VideoOverlay>
            <iframe
              ref={iframeRef}
              src={getVimeoEmbedUrl(videoId)}
              title={title || 'Vimeo Video'}
              frameBorder="0"
              allow="autoplay; fullscreen; picture-in-picture"
              allowFullScreen
              style={{ width: '100%', height: '100%', position: 'absolute' }}
            />
          </VideoOverlay>
        );
      }

      case 'local':
      default:
        return (
          <video
            ref={videoRef}
            src={src}
            controls
            autoPlay={autoPlay}
            poster={poster}
            onTimeUpdate={handleTimeUpdate}
            onPlay={handlePlay}
            onPause={handlePause}
            onLoadedData={handleLoaded}
            style={{
              width: '100%',
              height: '100%',
              position: 'absolute',
              top: 0,
              left: 0,
            }}
          >
            Your browser does not support the video tag.
          </video>
        );
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Video Player */}
      <VideoContainer elevation={3}>
        {isLoading && type === 'local' && (
          <Box
            sx={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 1,
            }}
          >
            <CircularProgress />
          </Box>
        )}
        {renderVideo()}
      </VideoContainer>

      {/* Title */}
      {title && (
        <Typography variant="h6" component="h2">
          {title}
        </Typography>
      )}

      {/* Transcript Panel (if available) */}
      {transcript && transcript.length > 0 && (
        <TranscriptPanel>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Transcript
          </Typography>
          {transcript.map((seg, index) => {
            const isActive = currentTime >= seg.start && currentTime <= seg.end;
            return (
              <TranscriptSegment
                key={index}
                $isActive={isActive}
                onClick={() => handleSeekToTime(seg.start)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    handleSeekToTime(seg.start);
                  }
                }}
              >
                {seg.speaker && (
                  <Typography variant="caption" color="primary" sx={{ mr: 1 }}>
                    [{seg.speaker}]
                  </Typography>
                )}
                <Typography variant="body2">{seg.text}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {formatTime(seg.start)} - {formatTime(seg.end)}
                </Typography>
              </TranscriptSegment>
            );
          })}
        </TranscriptPanel>
      )}
    </Box>
  );
};

// --- Utility ---

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export default VideoPlayer;

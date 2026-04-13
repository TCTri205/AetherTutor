/**
 * AudioPlayer Component - Sprint 17: Media Microlearning
 * 
 * Features:
 * - HTML5 audio with custom controls
 * - Playback speed control (0.5x - 2x)
 * - Skip forward/backward (10s, 30s)
 * - Transcript sync (highlight current segment)
 * - Waveform visualization (placeholder)
 * 
 * Props:
 * - src: Audio file URL
 * - title?: Audio title
 * - transcript?: Transcript segments
 * - onTimeUpdate?: Callback with current time
 * - autoPlay?: boolean
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Slider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import SkipPreviousIcon from '@mui/icons-material/SkipPrevious';
import FastForwardIcon from '@mui/icons-material/FastForward';
import FastRewindIcon from '@mui/icons-material/FastRewind';

// --- Types ---

export interface TranscriptSegment {
  text: string;
  start: number;
  end: number;
  speaker?: string;
}

export interface AudioPlayerProps {
  src: string;
  title?: string;
  transcript?: TranscriptSegment[];
  onTimeUpdate?: (currentTime: number, segment?: TranscriptSegment) => void;
  autoPlay?: boolean;
}

// --- Styled Components ---

const PlayerContainer = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[3],
}));

const WaveformPlaceholder = styled(Box)(({ theme }) => ({
  height: '60px',
  backgroundColor: theme.palette.action.hover,
  borderRadius: theme.shape.borderRadius,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginBottom: theme.spacing(2),
  position: 'relative',
  overflow: 'hidden',
  '&::before': {
    content: '""',
    position: 'absolute',
    left: 0,
    top: 0,
    height: '100%',
    width: 'var(--progress, 0%)',
    backgroundColor: theme.palette.primary.main,
    opacity: 0.2,
    transition: 'width 0.1s linear',
  },
}));

const TranscriptPanel = styled(Box)(({ theme }) => ({
  maxHeight: '250px',
  overflowY: 'auto',
  padding: theme.spacing(2),
  backgroundColor: theme.palette.background.default,
  borderRadius: theme.shape.borderRadius,
  marginTop: theme.spacing(2),
}));

const TranscriptSegmentItem = styled('div', {
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

// --- Utility Functions ---

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// --- Component ---

const AudioPlayer: React.FC<AudioPlayerProps> = ({
  src,
  title,
  transcript,
  onTimeUpdate,
  autoPlay = false,
}) => {
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackRate, setPlaybackRate] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const audioRef = useRef<HTMLAudioElement>(null);

  // Get active transcript segment
  const activeSegment = transcript?.find(
    (seg) => currentTime >= seg.start && currentTime <= seg.end
  );

  // Handle time updates
  const handleTimeUpdate = useCallback(() => {
    if (audioRef.current) {
      const time = audioRef.current.currentTime;
      setCurrentTime(time);
      onTimeUpdate?.(time, activeSegment);
    }
  }, [onTimeUpdate, activeSegment]);

  // Handle metadata loaded
  const handleLoadedMetadata = useCallback(() => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
      setIsLoading(false);
    }
  }, []);

  // Handle playback
  const handlePlay = () => {
    audioRef.current?.play();
    setIsPlaying(true);
  };

  const handlePause = () => {
    audioRef.current?.pause();
    setIsPlaying(false);
  };

  const togglePlayPause = () => {
    isPlaying ? handlePause() : handlePlay();
  };

  // Handle seek
  const handleSeek = (value: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = value;
      setCurrentTime(value);
    }
  };

  // Handle skip
  const handleSkip = (seconds: number) => {
    const newTime = Math.max(0, Math.min(currentTime + seconds, duration));
    handleSeek(newTime);
  };

  // Handle playback speed
  const handlePlaybackRateChange = (rate: number) => {
    setPlaybackRate(rate);
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  };

  // Handle transcript click to seek
  const handleSeekToTime = useCallback((time: number) => {
    handleSeek(time);
  }, []);

  // Progress percentage for waveform
  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Hidden Audio Element */}
      <audio
        ref={audioRef}
        src={src}
        preload="metadata"
        autoPlay={autoPlay}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => setIsPlaying(false)}
      />

      {/* Player UI */}
      <PlayerContainer elevation={3}>
        {/* Title */}
        {title && (
          <Typography variant="h6" component="h2" sx={{ mb: 2 }}>
            {title}
          </Typography>
        )}

        {/* Waveform Placeholder */}
        <WaveformPlaceholder
          sx={{ '--progress': `${progressPercent}%` } as React.CSSProperties}
          role="progressbar"
          aria-valuenow={Math.round(progressPercent)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Audio playback progress"
        >
          {isLoading ? (
            <CircularProgress size={24} />
          ) : (
            <Typography variant="caption" color="text.secondary">
              🎵 Waveform visualization (coming soon)
            </Typography>
          )}
        </WaveformPlaceholder>

        {/* Time Display */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="caption" color="text.secondary">
            {formatTime(currentTime)}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {formatTime(duration)}
          </Typography>
        </Box>

        {/* Seek Slider */}
        <Slider
          value={currentTime}
          max={duration || 100}
          onChange={(_, value) => handleSeek(value as number)}
          aria-label="Seek audio"
          size="small"
          sx={{ mb: 2 }}
        />

        {/* Controls */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, justifyContent: 'center' }}>
          {/* Skip Back 10s */}
          <IconButton
            onClick={() => handleSkip(-10)}
            size="small"
            aria-label="Skip backward 10 seconds"
          >
            <FastRewindIcon />
          </IconButton>

          {/* Skip Back 30s */}
          <IconButton
            onClick={() => handleSkip(-30)}
            size="small"
            aria-label="Skip backward 30 seconds"
          >
            <SkipPreviousIcon />
          </IconButton>

          {/* Play/Pause */}
          <IconButton
            onClick={togglePlayPause}
            size="large"
            color="primary"
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <PauseIcon fontSize="large" /> : <PlayArrowIcon fontSize="large" />}
          </IconButton>

          {/* Skip Forward 30s */}
          <IconButton
            onClick={() => handleSkip(30)}
            size="small"
            aria-label="Skip forward 30 seconds"
          >
            <SkipNextIcon />
          </IconButton>

          {/* Skip Forward 10s */}
          <IconButton
            onClick={() => handleSkip(10)}
            size="small"
            aria-label="Skip forward 10 seconds"
          >
            <FastForwardIcon />
          </IconButton>

          {/* Playback Speed */}
          <FormControl size="small" sx={{ ml: 2, minWidth: 80 }}>
            <InputLabel id="playback-speed-label">Speed</InputLabel>
            <Select
              labelId="playback-speed-label"
              value={playbackRate}
              label="Speed"
              onChange={(e) => handlePlaybackRateChange(e.target.value as number)}
            >
              <MenuItem value={0.5}>0.5x</MenuItem>
              <MenuItem value={0.75}>0.75x</MenuItem>
              <MenuItem value={1}>1x</MenuItem>
              <MenuItem value={1.25}>1.25x</MenuItem>
              <MenuItem value={1.5}>1.5x</MenuItem>
              <MenuItem value={2}>2x</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </PlayerContainer>

      {/* Transcript Panel */}
      {transcript && transcript.length > 0 && (
        <TranscriptPanel>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Transcript
          </Typography>
          {transcript.map((seg, index) => {
            const isActive = currentTime >= seg.start && currentTime <= seg.end;
            return (
              <TranscriptSegmentItem
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
              </TranscriptSegmentItem>
            );
          })}
        </TranscriptPanel>
      )}
    </Box>
  );
};

export default AudioPlayer;

/**
 * MediaViewer Page - Sprint 17: Media Microlearning
 * 
 * Full media viewing experience with:
 * - Video/Audio player with transcript sync
 * - Side-by-side transcript viewer
 * - Responsive layout
 * - Keyboard shortcuts
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Grid,
  Typography,
  CircularProgress,
  Alert,
  IconButton,
  Breadcrumbs,
  Link,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';

import { VideoPlayer, AudioPlayer, TranscriptViewer } from '../../components/media';
import type { TranscriptSegment } from '../../components/media';

// --- Types ---

interface MediaDocument {
  id: string;
  filename: string;
  media_type: 'video' | 'audio';
  source_url?: string;
  file_path?: string;
}

interface TranscriptData {
  id: string;
  full_text: string;
  language: string;
  duration: number;
  segments: TranscriptSegment[];
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

// --- Styled Components ---

const PageContainer = styled(Container)(({ theme }) => ({
  paddingTop: theme.spacing(4),
  paddingBottom: theme.spacing(4),
}));

const LoadingContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  minHeight: '400px',
}));

// --- Component ---

const MediaViewer: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();

  const [mediaDoc, setMediaDoc] = useState<MediaDocument | null>(null);
  const [transcript, setTranscript] = useState<TranscriptData | null>(null);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch media document
  useEffect(() => {
    const fetchMediaDoc = async () => {
      if (!documentId) {
        setError('Document ID is required');
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        // TODO: Replace with actual API call
        // const response = await fetch(`/api/v1/documents/${documentId}`);
        // const data = await response.json();
        // setMediaDoc(data);

        // Mock data for now
        setMediaDoc({
          id: documentId,
          filename: 'Sample Video.mp4',
          media_type: 'video',
          source_url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        });

        // Fetch transcript
        // const transcriptResponse = await fetch(`/api/v1/media/${documentId}/transcript`);
        // const transcriptData = await transcriptResponse.json();
        // setTranscript(transcriptData);

        // Mock transcript
        setTranscript({
          id: '1',
          full_text: 'This is a sample transcript',
          language: 'en',
          duration: 300,
          segments: [
            { text: 'Welcome to this lecture.', start: 0, end: 5 },
            { text: 'Today we will discuss important concepts.', start: 5, end: 12 },
            { text: 'Let\'s start with the first topic.', start: 12, end: 18 },
            { text: 'This concept is fundamental to understanding.', start: 18, end: 25 },
            { text: 'Pay attention to the details.', start: 25, end: 32 },
          ],
          status: 'completed',
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load media');
      } finally {
        setIsLoading(false);
      }
    };

    fetchMediaDoc();
  }, [documentId]);

  // Handle time updates from player
  const handleTimeUpdate = useCallback((time: number) => {
    setCurrentTime(time);
  }, []);

  // Handle seek from transcript
  const handleSeek = useCallback((time: number) => {
    setCurrentTime(time);
    // The player will handle actual seeking
    // This is for transcript sync
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Space: toggle play/pause (TODO: implement)
      // Arrow Left: rewind 10s
      if (e.key === 'ArrowLeft') {
        handleSeek(Math.max(0, currentTime - 10));
      }
      // Arrow Right: forward 10s
      if (e.key === 'ArrowRight') {
        handleSeek(currentTime + 10);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentTime, handleSeek]);

  // Loading state
  if (isLoading) {
    return (
      <LoadingContainer>
        <CircularProgress />
      </LoadingContainer>
    );
  }

  // Error state
  if (error) {
    return (
      <PageContainer maxWidth="lg">
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <IconButton onClick={() => navigate(-1)} aria-label="Go back">
          <ArrowBackIcon />
        </IconButton>
      </PageContainer>
    );
  }

  // No media
  if (!mediaDoc) {
    return (
      <PageContainer maxWidth="lg">
        <Alert severity="warning">Media not found</Alert>
      </PageContainer>
    );
  }

  const isVideo = mediaDoc.media_type === 'video';
  const src = mediaDoc.source_url || mediaDoc.file_path || '';

  return (
    <PageContainer maxWidth="xl">
      {/* Breadcrumbs */}
      <Breadcrumbs separator={<NavigateNextIcon fontSize="small" />} sx={{ mb: 3 }}>
        <Link underline="hover" color="inherit" href="/dashboard" onClick={() => navigate('/dashboard')}>
          Dashboard
        </Link>
        <Link underline="hover" color="inherit" href="/vault" onClick={() => navigate('/vault')}>
          Vault
        </Link>
        <Typography color="text.primary">{mediaDoc.filename}</Typography>
      </Breadcrumbs>

      {/* Back Button */}
      <IconButton onClick={() => navigate(-1)} sx={{ mb: 2 }} aria-label="Go back">
        <ArrowBackIcon />
        <Typography variant="body2" sx={{ ml: 1 }}>
          Back
        </Typography>
      </IconButton>

      {/* Title */}
      <Typography variant="h4" component="h1" sx={{ mb: 3 }}>
        {mediaDoc.filename}
      </Typography>

      {/* Content Grid */}
      <Grid container spacing={3}>
        {/* Player Column */}
        <Grid item xs={12} md={transcript?.status === 'completed' ? 7 : 12}>
          {isVideo ? (
            <VideoPlayer
              src={src}
              type={src.includes('youtube.com') ? 'youtube' : src.includes('vimeo.com') ? 'vimeo' : 'local'}
              title={mediaDoc.filename}
              transcript={transcript?.status === 'completed' ? transcript?.segments : undefined}
              onTimeUpdate={handleTimeUpdate}
            />
          ) : (
            <AudioPlayer
              src={src}
              title={mediaDoc.filename}
              transcript={transcript?.status === 'completed' ? transcript?.segments : undefined}
              onTimeUpdate={handleTimeUpdate}
            />
          )}
        </Grid>

        {/* Transcript Column */}
        {transcript?.status === 'completed' && transcript.segments.length > 0 && (
          <Grid item xs={12} md={5}>
            <TranscriptViewer
              transcript={transcript.segments}
              currentTime={currentTime}
              title={mediaDoc.filename}
              language={transcript.language}
              duration={transcript.duration}
              onSeek={handleSeek}
              editable={true}
            />
          </Grid>
        )}

        {/* Transcript Loading/Pending */}
        {transcript && (transcript.status === 'pending' || transcript.status === 'processing') && (
          <Grid item xs={12} md={5}>
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <CircularProgress sx={{ mb: 2 }} />
              <Typography variant="body2" color="text.secondary">
                Transcript is being generated...
              </Typography>
            </Box>
          </Grid>
        )}

        {/* No Transcript */}
        {(!transcript || transcript.status === 'failed') && (
          <Grid item xs={12}>
            <Alert severity="info" sx={{ mt: 2 }}>
              No transcript available for this media.
              {transcript?.status === 'failed' && ` Error: ${transcript.error_message}`}
            </Alert>
          </Grid>
        )}
      </Grid>
    </PageContainer>
  );
};

export default MediaViewer;

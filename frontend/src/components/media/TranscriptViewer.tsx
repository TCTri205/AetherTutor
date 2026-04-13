/**
 * TranscriptViewer Component - Sprint 17: Media Microlearning
 * 
 * Standalone transcript viewer with:
 * - Sync playback (click to seek)
 * - Search/filter transcript text
 * - Speaker highlighting
 * - Export transcript (JSON, TXT)
 * - Edit mode (manual correction)
 * 
 * Can be used standalone or synced with VideoPlayer/AudioPlayer.
 */

import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  IconButton,
  Button,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextareaAutosize,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import SearchIcon from '@mui/icons-material/Search';
import DownloadIcon from '@mui/icons-material/Download';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';

// --- Types ---

export interface TranscriptSegment {
  text: string;
  start: number;
  end: number;
  speaker?: string;
}

export interface TranscriptViewerProps {
  transcript: TranscriptSegment[];
  currentTime?: number; // For sync playback
  title?: string;
  language?: string;
  duration?: number; // Total duration in seconds
  onSeek?: (time: number) => void; // Callback to sync with player
  onEdit?: (updatedTranscript: TranscriptSegment[]) => void; // Manual correction
  editable?: boolean; // Allow editing mode
}

// --- Styled Components ---

const ViewerContainer = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[2],
  maxHeight: '600px',
  display: 'flex',
  flexDirection: 'column',
}));

const TranscriptList = styled(Box)({
  flex: 1,
  overflowY: 'auto',
  paddingRight: '8px',
  marginTop: '16px',
});

const TranscriptSegmentItem = styled('div', {
  shouldForwardProp: (prop) => prop !== '$isActive' && prop !== '$isHighlighted',
})<{ $isActive: boolean; $isHighlighted: boolean }>(({ theme, $isActive, $isHighlighted }) => ({
  padding: theme.spacing(1.5),
  marginBottom: theme.spacing(1),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: $isActive
    ? theme.palette.action.selected
    : $isHighlighted
    ? theme.palette.action.hover
    : 'transparent',
  borderLeft: $isActive ? `4px solid ${theme.palette.primary.main}` : '4px solid transparent',
  transition: 'all 0.2s ease',
  cursor: 'pointer',
  '&:hover': {
    backgroundColor: theme.palette.action.hover,
  },
}));

const SearchBar = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
  marginBottom: theme.spacing(2),
}));

// --- Utility Functions ---

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function highlightText(text: string, query: string): React.ReactNode {
  if (!query) return text;

  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  const parts = text.split(regex);

  return parts.map((part, index) =>
    regex.test(part) ? (
      <Box
        key={index}
        component="span"
        sx={{
          backgroundColor: 'warning.light',
          color: 'warning.dark',
          px: 0.5,
          borderRadius: 1,
        }}
      >
        {part}
      </Box>
    ) : (
      part
    )
  );
}

// --- Component ---

const TranscriptViewer: React.FC<TranscriptViewerProps> = ({
  transcript,
  currentTime = 0,
  title,
  language = 'en',
  duration,
  onSeek,
  onEdit,
  editable = false,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editTranscript, setEditTranscript] = useState<string>('');
  const [exportDialogOpen, setExportDialogOpen] = useState<boolean>(false);

  // Filter segments by search query
  const filteredSegments = useMemo(() => {
    if (!searchQuery) return transcript;
    const query = searchQuery.toLowerCase();
    return transcript.filter(
      (seg) =>
        seg.text.toLowerCase().includes(query) ||
        seg.speaker?.toLowerCase().includes(query)
    );
  }, [transcript, searchQuery]);

  // Get active segment
  const activeSegmentIndex = transcript.findIndex(
    (seg) => currentTime >= seg.start && currentTime <= seg.end
  );

  // Handle segment click (seek)
  const handleSegmentClick = useCallback(
    (time: number) => {
      onSeek?.(time);
    },
    [onSeek]
  );

  // Handle edit mode
  const handleEditToggle = () => {
    if (isEditing) {
      // Save changes
      const lines = editTranscript.split('\n');
      const updatedTranscript: TranscriptSegment[] = transcript.map((seg, index) => ({
        ...seg,
        text: lines[index] || seg.text,
      }));
      onEdit?.(updatedTranscript);
    } else {
      // Enter edit mode
      setEditTranscript(transcript.map((seg) => seg.text).join('\n'));
    }
    setIsEditing(!isEditing);
  };

  const handleEditCancel = () => {
    setIsEditing(false);
    setEditTranscript('');
  };

  // Handle export
  const handleExport = (format: 'json' | 'txt') => {
    let content: string;
    let filename: string;
    let mimeType: string;

    if (format === 'json') {
      content = JSON.stringify({ title, language, duration, transcript }, null, 2);
      filename = `${title || 'transcript'}.json`;
      mimeType = 'application/json';
    } else {
      content = transcript
        .map((seg) => {
          const speaker = seg.speaker ? `[${seg.speaker}] ` : '';
          const timestamp = `[${formatTime(seg.start)} - ${formatTime(seg.end)}] `;
          return `${timestamp}${speaker}${seg.text}`;
        })
        .join('\n\n');
      filename = `${title || 'transcript'}.txt`;
      mimeType = 'text/plain';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    setExportDialogOpen(false);
  };

  // Get unique speakers
  const speakers = useMemo(() => {
    const speakerSet = new Set(transcript.map((seg) => seg.speaker).filter(Boolean));
    return Array.from(speakerSet);
  }, [transcript]);

  return (
    <ViewerContainer>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          {title && (
            <Typography variant="h6" component="h2">
              {title}
            </Typography>
          )}
          <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
            {language && (
              <Chip label={`🌐 ${language.toUpperCase()}`} size="small" variant="outlined" />
            )}
            {duration && (
              <Chip label={`⏱ ${formatTime(duration)}`} size="small" variant="outlined" />
            )}
            {speakers.length > 0 && (
              <Chip label={`👥 ${speakers.length} speakers`} size="small" variant="outlined" />
            )}
          </Box>
        </Box>

        {/* Actions */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          {editable && (
            <IconButton onClick={handleEditToggle} aria-label={isEditing ? 'Save' : 'Edit'}>
              {isEditing ? <SaveIcon /> : <EditIcon />}
            </IconButton>
          )}
          <IconButton onClick={() => setExportDialogOpen(true)} aria-label="Export transcript">
            <DownloadIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Search Bar */}
      <SearchBar>
        <SearchIcon color="action" />
        <TextField
          fullWidth
          size="small"
          placeholder="Search transcript..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          variant="outlined"
          aria-label="Search transcript"
        />
        {searchQuery && (
          <Typography variant="caption" color="text.secondary">
            {filteredSegments.length} / {transcript.length} segments
          </Typography>
        )}
      </SearchBar>

      {/* Edit Mode */}
      {isEditing ? (
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextareaAutosize
            minRows={20}
            value={editTranscript}
            onChange={(e) => setEditTranscript(e.target.value)}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '8px',
              border: '1px solid #ccc',
              fontFamily: 'inherit',
              fontSize: '14px',
            }}
          />
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
            <Button startIcon={<CancelIcon />} onClick={handleEditCancel}>
              Cancel
            </Button>
            <Button variant="contained" startIcon={<SaveIcon />} onClick={handleEditToggle}>
              Save Changes
            </Button>
          </Box>
        </Box>
      ) : (
        /* Transcript List */
        <TranscriptList>
          {filteredSegments.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
              {searchQuery ? 'No matching segments found' : 'No transcript available'}
            </Typography>
          ) : (
            filteredSegments.map((seg, index) => {
              const originalIndex = transcript.indexOf(seg);
              const isActive = originalIndex === activeSegmentIndex;
              const isHighlighted = searchQuery && seg.text.toLowerCase().includes(searchQuery.toLowerCase());

              return (
                <TranscriptSegmentItem
                  key={index}
                  $isActive={isActive}
                  $isHighlighted={$isHighlighted: isHighlighted}
                  onClick={() => handleSegmentClick(seg.start)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      handleSegmentClick(seg.start);
                    }
                  }}
                  aria-label={`Transcript segment at ${formatTime(seg.start)}`}
                >
                  {seg.speaker && (
                    <Chip
                      label={seg.speaker}
                      size="small"
                      color="primary"
                      variant="outlined"
                      sx={{ mr: 1, mb: 0.5 }}
                    />
                  )}
                  <Typography variant="body2" sx={{ mb: 0.5 }}>
                    {searchQuery
                      ? highlightText(seg.text, searchQuery)
                      : seg.text}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {formatTime(seg.start)} → {formatTime(seg.end)}
                  </Typography>
                </TranscriptSegmentItem>
              );
            })
          )}
        </TranscriptList>
      )}

      {/* Export Dialog */}
      <Dialog open={exportDialogOpen} onClose={() => setExportDialogOpen(false)}>
        <DialogTitle>Export Transcript</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', gap: 2, py: 2 }}>
            <Button
              variant="outlined"
              onClick={() => handleExport('txt')}
              startIcon={<DownloadIcon />}
            >
              TXT (Plain Text)
            </Button>
            <Button
              variant="outlined"
              onClick={() => handleExport('json')}
              startIcon={<DownloadIcon />}
            >
              JSON (Structured)
            </Button>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExportDialogOpen(false)}>Cancel</Button>
        </DialogActions>
      </Dialog>
    </ViewerContainer>
  );
};

export default TranscriptViewer;

/**
 * S17 Media Microlearning Components
 * 
 * Exports:
 * - VideoPlayer: YouTube/Vimeo/Local video with transcript sync
 * - AudioPlayer: Audio with playback controls & transcript sync
 * - TranscriptViewer: Standalone transcript with search, edit, export
 */

export { default as VideoPlayer } from './VideoPlayer';
export { default as AudioPlayer } from './AudioPlayer';
export { default as TranscriptViewer } from './TranscriptViewer';

// Re-export types
export type { TranscriptSegment } from './VideoPlayer';
export type { TranscriptSegment as AudioTranscriptSegment } from './AudioPlayer';
export type { TranscriptSegment as ViewerTranscriptSegment } from './TranscriptViewer';

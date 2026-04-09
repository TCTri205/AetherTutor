import { useEffect, useState, useMemo, useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  MarkerType,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  Plus,
  Search,
  Filter,
  Eye,
  Edit,
  Trash2,
  Link,
  Share2,
  X,
  Save,
  Loader2,
  List,
  GitBranch,
  ChevronLeft,
  Tag,
  Sparkles,
  ArrowUpRight,
  FilePlus,
  Clock,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent } from '../components/ui/Card';
import { cn } from '../lib/utils';
import { toast } from 'sonner';
import { useNotesStore } from '../store/notes';
import type { NoteListItem, NoteDetail, NoteCreate, NoteType, NoteLinkType } from '../types/api';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

type ViewMode = 'list' | 'editor' | 'graph';

const NOTE_TYPE_COLORS: Record<NoteType, string> = {
  fleeting: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  literature: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  permanent: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  project: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
};

const NOTE_TYPE_LABELS: Record<NoteType, string> = {
  fleeting: 'Nháp',
  literature: 'Literature',
  permanent: 'Permanent',
  project: 'Project',
};

export default function Zettelkasten() {
  const {
    notes,
    totalNotes,
    currentNote,
    isLoading,
    fetchNotes,
    fetchNoteById,
    createNote,
    updateNote,
    deleteNote,
    fetchGraph,
    graph,
    searchNotes,
    setSearchQuery,
    selectedNoteType,
    setSelectedNoteType,
    setCurrentNote,
  } = useNotesStore();

  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({ title: '', content: '', note_type: 'literature' as NoteType, tags: [] as string[] });
  const [newForm, setNewForm] = useState<NoteCreate>({ title: '', content: '', note_type: 'literature', tags: [] });
  const [showNewDialog, setShowNewDialog] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [tagInput, setTagInput] = useState('');

  // ReactFlow state
  const [rfNodes, setRfNodes] = useState<Node[]>([]);
  const [rfEdges, setRfEdges] = useState<Edge[]>([]);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  useEffect(() => {
    if (viewMode === 'graph') {
      fetchGraph();
    }
  }, [viewMode, fetchGraph]);

  // Convert note graph to ReactFlow format
  useEffect(() => {
    if (!graph) return;

    const nodeColors: Record<string, string> = {
      fleeting: '#eab308',
      literature: '#3b82f6',
      permanent: '#10b981',
      project: '#a855f7',
    };

    const nodes: Node[] = graph.nodes.map((n, i) => ({
      id: String(n.id),
      data: { label: n.title, type: n.note_type, tags: n.tags },
      position: { x: (i % 5) * 280, y: Math.floor(i / 5) * 160 },
      style: {
        background: `${nodeColors[n.note_type] || '#3b82f6'}15`,
        border: `1px solid ${nodeColors[n.note_type] || '#3b82f6'}40`,
        borderRadius: '12px',
        padding: '12px',
        minWidth: 200,
        maxWidth: 260,
        color: '#fff',
        fontSize: '13px',
        fontWeight: 600,
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    }));

    const edges: Edge[] = graph.edges.map((e) => ({
      id: `${e.source}-${e.target}`,
      source: String(e.source),
      target: String(e.target),
      label: e.link_type,
      labelStyle: { fontSize: 10, fill: '#94a3b8' },
      style: { stroke: '#475569', strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#475569' },
    }));

    setRfNodes(nodes);
    setRfEdges(edges);
  }, [graph]);

  const handleSelectNote = async (noteId: string) => {
    await fetchNoteById(noteId);
    setViewMode('editor');
    setIsEditing(false);
  };

  const handleSaveNote = async () => {
    if (!currentNote) return;
    await updateNote(currentNote.id, editForm);
    setIsEditing(false);
    toast.success('Đã lưu note');
  };

  const handleCreateNote = async () => {
    if (!newForm.title.trim() || !newForm.content.trim()) {
      toast.error('Vui lòng điền tiêu đề và nội dung');
      return;
    }
    await createNote(newForm);
    toast.success('Đã tạo note mới');
    setShowNewDialog(false);
    setNewForm({ title: '', content: '', note_type: 'literature', tags: [] });
  };

  const handleDeleteNote = async (noteId: string) => {
    if (!confirm('Xóa note này?')) return;
    await deleteNote(noteId);
    toast.success('Đã xóa note');
    if (currentNote?.id === noteId) {
      setViewMode('list');
    }
  };

  const handleSearch = useCallback(() => {
    if (searchInput.trim()) {
      searchNotes(searchInput);
    } else {
      fetchNotes();
    }
  }, [searchInput, searchNotes, fetchNotes]);

  const startEditing = () => {
    if (!currentNote) return;
    setEditForm({
      title: currentNote.title,
      content: currentNote.content,
      note_type: currentNote.note_type as NoteType,
      tags: [...currentNote.tags],
    });
    setIsEditing(true);
  };

  const addTag = () => {
    const tag = tagInput.trim();
    if (!tag) return;
    if (isEditing) {
      setEditForm({ ...editForm, tags: [...editForm.tags, tag] });
    } else {
      setNewForm({ ...newForm, tags: [...newForm.tags, tag] });
    }
    setTagInput('');
  };

  const removeTag = (idx: number, form: 'new' | 'edit') => {
    if (form === 'new') {
      setNewForm({ ...newForm, tags: newForm.tags.filter((_, i) => i !== idx) });
    } else {
      setEditForm({ ...editForm, tags: editForm.tags.filter((_, i) => i !== idx) });
    }
  };

  // ===== GRAPH VIEW =====
  if (viewMode === 'graph') {
    return (
      <div className="flex flex-col gap-4 h-[calc(100vh-180px)]">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" onClick={() => setViewMode('list')}>
              <ChevronLeft className="w-4 h-4 mr-2" />
              Về List
            </Button>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-primary" />
              Note Graph
            </h2>
          </div>
          <div className="flex gap-2">
            {(['fleeting', 'literature', 'permanent', 'project'] as NoteType[]).map((type) => (
              <Badge key={type} variant="outline" className={cn('text-[10px]', NOTE_TYPE_COLORS[type])}>
                {NOTE_TYPE_LABELS[type]}
              </Badge>
            ))}
          </div>
        </div>

        {/* ReactFlow Canvas */}
        <div className="flex-1 rounded-2xl overflow-hidden border border-white/10">
          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
            fitView
            attributionPosition="bottom-right"
          >
            <Background color="#334155" gap={16} />
            <Controls />
            <MiniMap
              nodeColor={(node) => {
                const type = node.data?.type as string;
                const colors: Record<string, string> = { fleeting: '#eab308', literature: '#3b82f6', permanent: '#10b981', project: '#a855f7' };
                return colors[type] || '#3b82f6';
              }}
              maskColor="rgba(0,0,0,0.4)"
              bgColor="#0f172a"
            />
          </ReactFlow>
        </div>
      </div>
    );
  }

  // ===== EDITOR VIEW =====
  if (viewMode === 'editor' && currentNote) {
    return (
      <div className="flex flex-col gap-4 max-w-5xl mx-auto pb-20">
        {/* Header */}
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={() => { setViewMode('list'); setCurrentNote(null); }}>
            <ChevronLeft className="w-4 h-4 mr-2" />
            Về danh sách
          </Button>
          <div className="flex gap-2">
            {!isEditing ? (
              <>
                <Button variant="outline" size="sm" onClick={startEditing}>
                  <Edit className="w-3.5 h-3.5 mr-2" />
                  Sửa
                </Button>
                <Button variant="ghost" size="sm" className="text-destructive/70" onClick={() => handleDeleteNote(currentNote.id)}>
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" size="sm" onClick={() => setIsEditing(false)}>Hủy</Button>
                <Button size="sm" onClick={handleSaveNote}>
                  <Save className="w-3.5 h-3.5 mr-2" />
                  Lưu
                </Button>
              </>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2">
            {isEditing ? (
              <Card className="border-primary/20">
                <CardContent className="p-6 space-y-4">
                  <input
                    className="w-full bg-transparent text-2xl font-bold text-white focus:outline-none"
                    value={editForm.title}
                    onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                    placeholder="Tiêu đề..."
                  />
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">Loại note</label>
                    <select
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm"
                      value={editForm.note_type}
                      onChange={(e) => setEditForm({ ...editForm, note_type: e.target.value as NoteType })}
                    >
                      <option value="fleeting">Nháp</option>
                      <option value="literature">Literature</option>
                      <option value="permanent">Permanent</option>
                      <option value="project">Project</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">Tags</label>
                    <div className="flex flex-wrap gap-2 mb-2">
                      {editForm.tags.map((tag, i) => (
                        <Badge key={i} variant="outline" className="flex items-center gap-1">
                          #{tag}
                          <button onClick={() => removeTag(i, 'edit')} className="hover:text-red-400">
                            <X className="w-3 h-3" />
                          </button>
                        </Badge>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input
                        className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm"
                        value={tagInput}
                        onChange={(e) => setTagInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                        placeholder="Thêm tag..."
                      />
                      <Button size="sm" onClick={addTag}>Thêm</Button>
                    </div>
                  </div>
                  <textarea
                    className="w-full bg-background border border-border rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none min-h-[400px] font-mono"
                    value={editForm.content}
                    onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                    placeholder="Nội dung (Markdown)..."
                  />
                </CardContent>
              </Card>
            ) : (
              <>
                {/* Preview */}
                <Card className="border-white/5">
                  <CardContent className="p-8 prose prose-invert prose-sm max-w-none">
                    <div className="flex items-center gap-2 mb-4">
                      <Badge variant="outline" className={NOTE_TYPE_COLORS[currentNote.note_type as NoteType]}>
                        {NOTE_TYPE_LABELS[currentNote.note_type as NoteType]}
                      </Badge>
                      {currentNote.tags.map((tag, i) => (
                        <Badge key={i} variant="outline" className="text-[10px]">#{tag}</Badge>
                      ))}
                    </div>
                    <h1 className="text-3xl font-bold text-white mb-6">{currentNote.title}</h1>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm, remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                    >
                      {currentNote.content}
                    </ReactMarkdown>
                  </CardContent>
                </Card>

                {/* Backlinks */}
                {(currentNote.incoming_links.length > 0 || currentNote.outgoing_links.length > 0) && (
                  <Card className="border-white/5 mt-6">
                    <CardContent className="p-6">
                      <h3 className="font-bold text-white mb-4 flex items-center gap-2">
                        <Link className="w-4 h-4 text-primary" />
                        Liên kết
                      </h3>
                      {currentNote.incoming_links.length > 0 && (
                        <div className="mb-4">
                          <p className="text-xs text-muted-foreground mb-2">Backlinks ({currentNote.incoming_links.length})</p>
                          <div className="space-y-2">
                            {currentNote.incoming_links.map((link) => (
                              <div key={link.id} className="flex items-center gap-2 text-sm">
                                <ArrowUpRight className="w-3.5 h-3.5 text-emerald-400" />
                                <span className="text-muted-foreground">Note ID: {String(link.source_note_id).slice(0, 8)}</span>
                                {link.context && <span className="text-xs text-white/60 truncate">{link.context}</span>}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {currentNote.outgoing_links.length > 0 && (
                        <div>
                          <p className="text-xs text-muted-foreground mb-2">Outgoing links ({currentNote.outgoing_links.length})</p>
                          <div className="space-y-2">
                            {currentNote.outgoing_links.map((link) => (
                              <div key={link.id} className="flex items-center gap-2 text-sm">
                                <ArrowUpRight className="w-3.5 h-3.5 text-blue-400" />
                                <span className="text-muted-foreground">→ Note ID: {String(link.target_note_id).slice(0, 8)}</span>
                                {link.context && <span className="text-xs text-white/60 truncate">{link.context}</span>}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </div>

          {/* Sidebar Info */}
          <div className="space-y-4">
            <Card className="border-white/5">
              <CardContent className="p-4 space-y-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Tạo lúc</p>
                  <p className="text-white">
                    {formatDistanceToNow(new Date(currentNote.created_at), { locale: vi })}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Cập nhật lúc</p>
                  <p className="text-white">
                    {formatDistanceToNow(new Date(currentNote.updated_at), { locale: vi })}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">ID</p>
                  <p className="text-muted-foreground font-mono text-xs">{String(currentNote.id).slice(0, 12)}...</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  // ===== LIST VIEW =====
  return (
    <div className="flex flex-col gap-8 max-w-6xl mx-auto pb-20">
      {/* Header */}
      <section className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="space-y-2">
          <h2 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
            <FileText className="w-8 h-8 text-primary" />
            Zettelkasten
          </h2>
          <p className="text-muted-foreground">
            Hệ thống ghi chú liên kết — xây dựng mạng lưới tri thức cá nhân.
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" size="lg" onClick={() => setViewMode('graph')}>
            <GitBranch className="w-4 h-4 mr-2" />
            Graph View
          </Button>
          <Button size="lg" onClick={() => setShowNewDialog(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Tạo Note
          </Button>
        </div>
      </section>

      {/* Search & Filter Bar */}
      <div className="flex flex-col md:flex-row gap-4 bg-white/5 p-4 rounded-2xl border border-white/5 glass">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            className="w-full bg-background border border-border rounded-xl px-10 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="Tìm kiếm notes..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
        </div>
        <Button variant="outline" onClick={handleSearch}>
          <Search className="w-4 h-4 mr-2" />
          Tìm
        </Button>
        <select
          className="bg-background border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
          value={selectedNoteType || ''}
          onChange={(e) => setSelectedNoteType(e.target.value || null)}
        >
          <option value="">Tất cả loại</option>
          <option value="fleeting">Nháp</option>
          <option value="literature">Literature</option>
          <option value="permanent">Permanent</option>
          <option value="project">Project</option>
        </select>
      </div>

      {/* Create Dialog */}
      {showNewDialog && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="w-full max-w-lg">
            <Card className="border-white/10">
              <CardContent className="p-6 space-y-4">
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <FilePlus className="w-5 h-5 text-primary" />
                  Tạo Note mới
                </h3>
                <input
                  className="w-full bg-background border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                  placeholder="Tiêu đề..."
                  value={newForm.title}
                  onChange={(e) => setNewForm({ ...newForm, title: e.target.value })}
                />
                <div className="flex gap-3">
                  <select
                    className="bg-background border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                    value={newForm.note_type}
                    onChange={(e) => setNewForm({ ...newForm, note_type: e.target.value as NoteType })}
                  >
                    <option value="fleeting">Nháp</option>
                    <option value="literature">Literature</option>
                    <option value="permanent">Permanent</option>
                    <option value="project">Project</option>
                  </select>
                  <div className="flex-1 flex gap-2">
                    <input
                      className="flex-1 bg-background border border-border rounded-xl px-4 py-2.5 text-sm"
                      placeholder="Tag..."
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                    />
                    <Button size="sm" onClick={addTag}>
                      <Tag className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
                {newForm.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {newForm.tags.map((tag, i) => (
                      <Badge key={i} variant="outline" className="flex items-center gap-1">
                        #{tag}
                        <button onClick={() => removeTag(i, 'new')} className="hover:text-red-400">
                          <X className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
                <textarea
                  className="w-full bg-background border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
                  rows={6}
                  placeholder="Nội dung (Markdown)..."
                  value={newForm.content}
                  onChange={(e) => setNewForm({ ...newForm, content: e.target.value })}
                />
                <div className="flex gap-3 justify-end">
                  <Button variant="ghost" onClick={() => setShowNewDialog(false)}>Hủy</Button>
                  <Button onClick={handleCreateNote} disabled={!newForm.title.trim() || !newForm.content.trim()}>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Tạo Note
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      )}

      {/* Notes List */}
      <div className="space-y-3">
        {isLoading && notes.length === 0
          ? Array.from({ length: 5 }).map((_, i) => (
              <Card key={i} className="h-20 border-white/5">
                <CardContent className="p-5 animate-pulse">
                  <div className="h-4 bg-white/10 rounded w-1/3 mb-2" />
                  <div className="h-3 bg-white/5 rounded w-1/4" />
                </CardContent>
              </Card>
            ))
          : notes.map((note) => (
              <Card
                key={note.id}
                className="border-white/5 hover:border-primary/20 transition-all cursor-pointer group"
                onClick={() => handleSelectNote(note.id)}
              >
                <CardContent className="p-5 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <Badge variant="outline" className={cn('text-[10px]', NOTE_TYPE_COLORS[note.note_type as NoteType])}>
                        {NOTE_TYPE_LABELS[note.note_type as NoteType]}
                      </Badge>
                      <h4 className="font-bold text-white truncate">{note.title}</h4>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatDistanceToNow(new Date(note.updated_at), { locale: vi })}
                      </span>
                      {note.tags.length > 0 && (
                        <span className="flex items-center gap-1">
                          <Tag className="w-3 h-3" />
                          {note.tags.slice(0, 3).join(', ')}
                          {note.tags.length > 3 && ` +${note.tags.length - 3}`}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                    <Button variant="secondary" size="sm" onClick={() => handleSelectNote(note.id)}>
                      <Eye className="w-3.5 h-3.5" />
                    </Button>
                    <Button variant="ghost" size="sm" className="text-destructive/70" onClick={() => handleDeleteNote(note.id)}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
      </div>

      {/* Empty state */}
      {!isLoading && notes.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 bg-white/[0.02] border-2 border-dashed border-white/5 rounded-3xl gap-6">
          <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center border border-white/10">
            <FileText className="w-10 h-10 text-muted-foreground opacity-30" />
          </div>
          <div className="text-center space-y-2">
            <p className="text-white font-bold text-lg">Chưa có note nào</p>
            <p className="text-muted-foreground">Bắt đầu xây dựng mạng lưới tri thức cá nhân.</p>
          </div>
          <Button size="lg" onClick={() => setShowNewDialog(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Tạo Note đầu tiên
          </Button>
        </div>
      )}

      {/* Total */}
      {totalNotes > 0 && (
        <p className="text-center text-xs text-muted-foreground">
          Hiển thị {notes.length} / {totalNotes} notes
        </p>
      )}
    </div>
  );
}

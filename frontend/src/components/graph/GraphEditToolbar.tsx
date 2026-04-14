import React from 'react';
import { 
  Edit3, 
  Plus, 
  RotateCcw, 
  RotateCw, 
  Save, 
  History, 
  MousePointer2,
  Trash2
} from 'lucide-react';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';
import './GraphEditToolbar.css';

interface GraphEditToolbarProps {
  isEditMode: boolean;
  onToggleEditMode: () => void;
  onAddNode: () => void;
  onUndo: () => void;
  onRedo?: () => void;
  onSaveVersion: () => void;
  onShowHistory: () => void;
  canUndo: boolean;
  canRedo: boolean;
  selection?: any;
  onDeleteSelection?: () => void;
}

export const GraphEditToolbar: React.FC<GraphEditToolbarProps> = ({
  isEditMode,
  onToggleEditMode,
  onAddNode,
  onUndo,
  onRedo,
  onSaveVersion,
  onShowHistory,
  canUndo,
  canRedo,
  selection,
  onDeleteSelection
}) => {
  return (
    <div className={cn(
      "graph-edit-toolbar glass flex items-center gap-2 p-2 rounded-xl shadow-lg border border-glass transition-all duration-300",
      isEditMode ? "edit-active" : ""
    )}>
      {/* Edit Mode Toggle */}
      <Button
        variant={isEditMode ? "primary" : "ghost"}
        size="sm"
        onClick={onToggleEditMode}
        className="gap-2 px-4"
        title={isEditMode ? "Thoát chế độ chỉnh sửa" : "Vào chế độ chỉnh sửa"}
      >
        <Edit3 size={18} />
        <span className="hidden md:inline">{isEditMode ? "Đang sửa" : "Chỉnh sửa"}</span>
      </Button>

      <div className="toolbar-divider h-6 w-px bg-border-glass mx-1" />

      {/* Editing Actions */}
      <div className={cn("flex items-center gap-2 overflow-hidden transition-all duration-300", isEditMode ? "w-auto opacity-100" : "w-0 opacity-0 pointer-events-none")}>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onAddNode}
          title="Thêm thực thể mới"
          className="hover:bg-accent-primary-muted hover:text-accent-primary"
        >
          <Plus size={18} />
        </Button>

        {selection && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onDeleteSelection}
            title="Xóa đối tượng đang chọn"
            className="hover:bg-accent-destructive-muted hover:text-accent-destructive text-accent-destructive/70"
          >
            <Trash2 size={18} />
          </Button>
        )}

        <div className="toolbar-divider h-6 w-px bg-border-glass mx-1" />

        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onUndo}
          disabled={!canUndo}
          title="Hoàn tác (Ctrl+Z)"
        >
          <RotateCcw size={18} />
        </Button>

        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onRedo}
          disabled={!canRedo}
          title="Làm lại (Ctrl+Y)"
        >
          <RotateCw size={18} />
        </Button>

        <div className="toolbar-divider h-6 w-px bg-border-glass mx-1" />

        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onSaveVersion}
          title="Lưu phiên bản (Snapshot)"
        >
          <Save size={18} />
        </Button>
      </div>

      {/* View/History Actions */}
      <Button
        variant="ghost"
        size="icon-sm"
        onClick={onShowHistory}
        title="Lịch sử phiên bản"
      >
        <History size={18} />
      </Button>
    </div>
  );
};

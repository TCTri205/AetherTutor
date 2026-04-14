import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/Dialog';
import { Button } from '../ui/Button';

interface CreateNodeDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string; type: string; description: string }) => void;
}

export const CreateNodeDialog: React.FC<CreateNodeDialogProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [name, setName] = useState('');
  const [type, setType] = useState('CONCEPT');
  const [description, setDescription] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSubmit({ name: name.trim(), type: type.trim(), description: description.trim() });
    setName('');
    setDescription('');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Thêm thực thể mới</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="grid gap-4 py-4">
          <div className="grid gap-2">
            <label htmlFor="name" className="text-sm font-medium text-white">Tên thực thể</label>
            <input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-accent-primary"
              placeholder="VD: Trí tuệ nhân tạo"
              required
            />
          </div>
          <div className="grid gap-2">
            <label htmlFor="type" className="text-sm font-medium text-white">Loại thực thể</label>
            <select
              id="type"
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-accent-primary"
            >
              <option value="CONCEPT">Concept</option>
              <option value="PERSON">Person</option>
              <option value="ORGANIZATION">Organization</option>
              <option value="LOCATION">Location</option>
              <option value="EVENT">Event</option>
              <option value="PROCESS">Process</option>
            </select>
          </div>
          <div className="grid gap-2">
            <label htmlFor="description" className="text-sm font-medium text-white">Mô tả</label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="flex min-h-[80px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-accent-primary"
              placeholder="Nhập mô tả ngắn gọn..."
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose}>Hủy</Button>
            <Button type="submit" variant="primary">Thêm</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

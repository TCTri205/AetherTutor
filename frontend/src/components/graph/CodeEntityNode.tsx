/**
 * CodeEntityNode — Custom ReactFlow node hiển thị code snippet.
 *
 * Features:
 * - Hiển thị code với syntax highlighting (basic, không dùng prism.js để nhẹ)
 * - Lazy-load: chỉ render code khi user click/expand
 * - Copy to clipboard
 * - Hiển thị metadata: file type, line count, entity type
 */
import { useState, memo } from 'react';
import { Handle, Position } from 'reactflow';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Copy, Check, FileCode, Class, FunctionSquare } from 'lucide-react';
import { toast } from 'sonner';

interface CodeEntityNodeProps {
  id: string;
  data: {
    label: string;
    entityType: string; // Module, Class, Function
    codeSnippet?: string;
    fileType?: string; // .py, .js, .ts
    lineCount?: number;
    fileName?: string;
    description?: string;
  };
}

// Basic syntax highlighting bằng cách tokenize đơn giản
function highlightCode(code: string, fileType: string): string {
  const ext = fileType || '.py';

  // Keywords cho Python
  const pythonKeywords = ['def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'with', 'as', 'async', 'await', 'yield', 'lambda', 'pass', 'break', 'continue', 'raise', 'in', 'and', 'or', 'not', 'is', 'None', 'True', 'False'];

  // Keywords cho JS/TS
  const jsKeywords = ['function', 'const', 'let', 'var', 'class', 'import', 'export', 'from', 'return', 'if', 'else', 'for', 'while', 'try', 'catch', 'async', 'await', 'new', 'this', 'typeof', 'instanceof', 'switch', 'case', 'break', 'continue', 'throw', 'default', 'true', 'false', 'null', 'undefined'];

  const keywords = ext === '.py' ? pythonKeywords : jsKeywords;

  // Escape HTML
  let highlighted = code
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Highlight strings
  highlighted = highlighted.replace(
    /(["'`])(?:(?=(\\?))\2.)*?\1/g,
    '<span class="text-green-400">$&</span>'
  );

  // Highlight comments
  if (ext === '.py') {
    highlighted = highlighted.replace(
      /(#.*$)/gm,
      '<span class="text-gray-500">$&</span>'
    );
  } else {
    highlighted = highlighted.replace(
      /(\/\/.*$)/gm,
      '<span class="text-gray-500">$&</span>'
    );
    highlighted = highlighted.replace(
      /(\/\*[\s\S]*?\*\/)/g,
      '<span class="text-gray-500">$&</span>'
    );
  }

  // Highlight keywords
  keywords.forEach(kw => {
    const regex = new RegExp(`\\b(${kw})\\b`, 'g');
    highlighted = highlighted.replace(
      regex,
      '<span class="text-purple-400 font-semibold">$1</span>'
    );
  });

  // Highlight function/class names
  highlighted = highlighted.replace(
    /\b([A-Z][a-zA-Z0-9_]*)\b/g,
    '<span class="text-yellow-300">$1</span>'
  );

  return highlighted;
}

const CodeEntityNode = memo(({ id, data }: CodeEntityNodeProps) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const getIcon = () => {
    switch (data.entityType) {
      case 'Class':
        return <Class className="w-4 h-4 text-yellow-400" />;
      case 'Function':
        return <FunctionSquare className="w-4 h-4 text-blue-400" />;
      default:
        return <FileCode className="w-4 h-4 text-green-400" />;
    }
  };

  const getBorderColor = () => {
    switch (data.entityType) {
      case 'Class':
        return 'border-yellow-400/50';
      case 'Function':
        return 'border-blue-400/50';
      default:
        return 'border-green-400/50';
    }
  };

  const handleCopy = async () => {
    if (data.codeSnippet) {
      await navigator.clipboard.writeText(data.codeSnippet);
      setCopied(true);
      toast.success('Đã copy code snippet');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const lineLimit = 50; // Chỉ hiển thị 50 dòng đầu khi expand
  const codeLines = data.codeSnippet?.split('\n') || [];
  const truncatedCode = codeLines.length > lineLimit
    ? codeLines.slice(0, lineLimit).join('\n') + '\n# ... (truncated)'
    : data.codeSnippet || '';

  const highlightedCode = highlightCode(truncatedCode, data.fileType || '.py');

  return (
    <div className={`rounded-lg border-2 ${getBorderColor()} bg-bg-elevated shadow-lg min-w-[200px] max-w-[350px]`}>
      {/* Connection handles */}
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-accent" />
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-accent" />

      {/* Header */}
      <div
        className="p-3 cursor-pointer hover:bg-bg-secondary/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {getIcon()}
            <span className="font-semibold text-text-primary text-sm truncate">
              {data.label}
            </span>
          </div>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-text-secondary" />
          ) : (
            <ChevronDown className="w-4 h-4 text-text-secondary" />
          )}
        </div>

        {/* Metadata */}
        <div className="flex items-center gap-2 mt-2 text-xs text-text-secondary">
          {data.fileType && (
            <span className="px-1.5 py-0.5 rounded bg-bg-tertiary font-mono">
              {data.fileType}
            </span>
          )}
          {data.lineCount && (
            <span>{data.lineCount} dòng</span>
          )}
          {data.fileName && (
            <span className="truncate" title={data.fileName}>{data.fileName}</span>
          )}
        </div>

        {data.description && (
          <p className="text-xs text-text-secondary mt-1 line-clamp-2">
            {data.description}
          </p>
        )}
      </div>

      {/* Code snippet (lazy-loaded on expand) */}
      <AnimatePresence>
        {isExpanded && data.codeSnippet && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border-primary">
              {/* Toolbar */}
              <div className="flex items-center justify-between p-2 bg-bg-secondary">
                <span className="text-xs text-text-secondary">
                  {codeLines.length} dòng
                </span>
                <button
                  className="flex items-center gap-1 text-xs text-text-secondary hover:text-text-primary transition-colors"
                  onClick={handleCopy}
                >
                  {copied ? (
                    <>
                      <Check className="w-3 h-3 text-green-400" />
                      <span className="text-green-400">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>

              {/* Code block */}
              <pre className="p-3 text-xs font-mono overflow-auto max-h-[400px] bg-bg-tertiary text-text-primary">
                <code dangerouslySetInnerHTML={{ __html: highlightedCode }} />
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});

CodeEntityNode.displayName = 'CodeEntityNode';

export default CodeEntityNode;

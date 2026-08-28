import { useState, useRef, useEffect } from 'react';
import { IconSend, IconSparkles, IconPaperclip, IconFile, IconX } from './Icons';

const MessageInput = ({ onSendMessage, selectedModel, isGenerating }) => {
  const [text, setText] = useState('');
  const [attachedFile, setAttachedFile] = useState(null); // { file_id, filename, result, status }
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [uploadError, setUploadError] = useState(null);

  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const modelDisplayName = selectedModel?.name || selectedModel?.model || 'Qwen2.5-Coder';
  const taskLabel = selectedModel?.type || selectedModel?.task || 'Coding';

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [text]);

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);
    setUploadStatus(`Uploading & processing ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file);
    if (text.trim()) {
      formData.append('prompt', text.trim());
    }

    try {
      const res = await fetch('http://localhost:8000/api/files/upload', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Upload failed with status ${res.status}`);
      }

      const data = await res.json();
      if (data.status === 'success') {
        setAttachedFile({
          file_id: data.file_id,
          filename: data.filename,
          size: file.size,
          result: data.result
        });
        setUploadStatus('');
      } else {
        throw new Error('Upload returned unsuccessful status');
      }
    } catch (err) {
      console.error('File upload error:', err);
      setUploadError(err.message || 'File processing failed');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleRemoveFile = () => {
    setAttachedFile(null);
    setUploadError(null);
    setUploadStatus('');
  };

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if ((!text.trim() && !attachedFile) || isGenerating || isUploading) return;
    
    // Send message along with attached file data
    onSendMessage(text, attachedFile);
    
    setText('');
    setAttachedFile(null);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="input-area-container">
      {/* File Preview Card */}
      {attachedFile && (
        <div className="composer-attached-file-card">
          <div className="composer-att-left">
            <div className="composer-att-icon-box">
              <IconFile size={18} />
            </div>
            <div className="composer-att-info">
              <span className="composer-att-filename">{attachedFile.filename}</span>
              <div className="composer-att-sub">
                <span className="composer-att-badge">{attachedFile.result?.file_type?.toUpperCase() || 'FILE'}</span>
                {attachedFile.size > 0 && <span className="composer-att-size">• {formatFileSize(attachedFile.size)}</span>}
                <span className="composer-att-ready">✓ Processed & Ready</span>
              </div>
            </div>
          </div>
          <button
            type="button"
            className="composer-att-remove-btn"
            onClick={handleRemoveFile}
            title="Remove attached file"
          >
            <IconX size={14} />
          </button>
        </div>
      )}


      {/* Uploading Status Banner */}
      {isUploading && (
        <div className="upload-status-banner">
          <span className="upload-spinner"></span>
          <span>{uploadStatus}</span>
        </div>
      )}

      {/* Upload Error Banner */}
      {uploadError && (
        <div className="upload-error-banner">
          <span>⚠️ {uploadError}</span>
          <button type="button" onClick={() => setUploadError(null)} className="dismiss-err-btn">
            <IconX size={12} />
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="input-box-wrapper">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          placeholder={
            isGenerating 
              ? `${modelDisplayName} is generating locally...` 
              : `Ask ${modelDisplayName} (${taskLabel}) or attach a file... [Press Enter to send]`
          }
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isGenerating || isUploading}
          rows={1}
        />

        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          style={{ display: 'none' }}
          accept=".jpg,.jpeg,.png,.webp,.pdf,.docx,.pptx,.xlsx,.xls,.csv,.txt,.md"
        />

        <div className="input-actions-bar">
          <div className="input-actions-left">
            <button
              type="button"
              className="attach-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isGenerating || isUploading}
              title="Attach File (Images, PDF, DOCX, PPTX, XLSX, CSV, TXT, MD)"
            >
              <IconPaperclip size={16} />
              <span>Attach</span>
            </button>

            <div className="input-model-info">
              <IconSparkles size={14} style={{ color: 'var(--accent-cyan)' }} />
              <span>Active Model:</span>
              <span className="input-model-tag">{modelDisplayName}</span>
            </div>
          </div>

          <button
            type="submit"
            className="send-button"
            disabled={(!text.trim() && !attachedFile) || isGenerating || isUploading}
            title="Send Message"
          >
            <span>Send</span>
            <IconSend size={14} />
          </button>
        </div>
      </form>
      <div className="input-footer-note">
        Sovereign Agentic AI Workbench • Integrated Document & Vision Processing
      </div>
    </div>
  );
};

export default MessageInput;

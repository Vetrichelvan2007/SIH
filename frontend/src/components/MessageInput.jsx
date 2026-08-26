import { useState, useRef, useEffect } from 'react';
import { IconSend, IconSparkles } from './Icons';

const MessageInput = ({ onSendMessage, selectedModel, isGenerating }) => {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  const modelDisplayName = selectedModel?.name || selectedModel?.model || 'Qwen2.5-Coder';
  const taskLabel = selectedModel?.type || selectedModel?.task || 'Coding';

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [text]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!text.trim() || isGenerating) return;
    onSendMessage(text);
    setText('');
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

  return (
    <div className="input-area-container">
      <form onSubmit={handleSubmit} className="input-box-wrapper">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          placeholder={
            isGenerating 
              ? `${modelDisplayName} is generating locally...` 
              : `Ask ${modelDisplayName} (${taskLabel})... [Press Enter to send]`
          }
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isGenerating}
          rows={1}
        />

        <div className="input-actions-bar">
          <div className="input-model-info">
            <IconSparkles size={14} style={{ color: 'var(--accent-cyan)' }} />
            <span>Active Model:</span>
            <span className="input-model-tag">{modelDisplayName}</span>
          </div>

          <button
            type="submit"
            className="send-button"
            disabled={!text.trim() || isGenerating}
            title="Send Message"
          >
            <span>Send</span>
            <IconSend size={14} />
          </button>
        </div>
      </form>
      <div className="input-footer-note">
        Sovereign Agentic AI Workbench • 100% Local Enterprise On-Premise Model Execution
      </div>
    </div>
  );
};

export default MessageInput;

import { useState } from 'react';
import { IconBot, IconUser, IconCopy, IconCheck } from './Icons';
import ExecutionPipeline from './ExecutionPipeline';

// Code Block Sub-component with Copy Button
const CodeBlock = ({ language, code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-wrapper">
      <div className="code-header">
        <span className="code-language">{language || 'code'}</span>
        <button 
          type="button" 
          className={`copy-button ${copied ? 'copied' : ''}`}
          onClick={handleCopy}
          title="Copy code to clipboard"
        >
          {copied ? (
            <>
              <IconCheck size={13} />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <IconCopy size={13} />
              <span>Copy code</span>
            </>
          )}
        </button>
      </div>
      <pre className="code-body">
        <code>{code}</code>
      </pre>
    </div>
  );
};

// Formatter for rich text, code blocks, and markdown elements
const FormattedMessageText = ({ text }) => {
  if (!text) return null;

  // Split by code blocks ```lang ... ```
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: text.substring(lastIndex, match.index)
      });
    }

    parts.push({
      type: 'code',
      language: match[1] || 'plaintext',
      code: match[2].trimEnd()
    });

    lastIndex = codeBlockRegex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push({
      type: 'text',
      content: text.substring(lastIndex)
    });
  }

  return (
    <div>
      {parts.map((part, index) => {
        if (part.type === 'code') {
          return <CodeBlock key={index} language={part.language} code={part.code} />;
        }

        const lines = part.content.split('\n');
        return (
          <div key={index}>
            {lines.map((line, lIdx) => {
              if (!line.trim() && lIdx > 0 && lIdx < lines.length - 1) {
                return <div key={lIdx} style={{ height: '8px' }}></div>;
              }

              const formattedLine = renderInlineFormatting(line);
              return (
                <p key={lIdx} style={{ margin: '3px 0' }}>
                  {formattedLine}
                </p>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};

// Helper function for inline markdown rendering (**bold** and `code`)
function renderInlineFormatting(text) {
  const parts = [];
  const regex = /(\*\*.*?\*\*|`.*?`)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={match.index} style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code key={match.index} className="inline-code">
          {token.slice(1, -1)}
        </code>
      );
    }

    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}

// Format model display name to prevent "undefined" or stale fallbacks
const formatModelDisplayName = (modelStr) => {
  if (!modelStr || modelStr === 'undefined') return 'Phi-4 Mini';
  if (typeof modelStr === 'object') {
    return modelStr.name || modelStr.id || 'Phi-4 Mini';
  }
  const lower = String(modelStr).toLowerCase();
  if (lower.includes('phi')) return 'Phi-4 Mini';
  if (lower.includes('coder')) return 'Qwen2.5-Coder';
  if (lower.includes('qwen') && lower.includes('1.5')) return 'Qwen2.5 1.5B';
  if (lower.includes('qwen')) return 'Qwen2.5-Coder';
  return modelStr;
};

const ChatMessage = ({ message }) => {
  const isUser = message.sender === 'user';
  const modelDisplayName = formatModelDisplayName(message.modelName || message.model);

  return (
    <div className={`message-row ${isUser ? 'user' : 'ai'}`}>
      <div className={`avatar ${isUser ? 'user' : 'ai'}`}>
        {isUser ? <IconUser size={18} /> : <IconBot size={18} />}
      </div>

      <div className="message-content-wrapper">
        <div className="message-meta">
          <span>{isUser ? 'You' : 'Sovereign Agent'}</span>
          {!isUser && (
            <span className="meta-model-tag">{modelDisplayName}</span>
          )}
          <span>• {message.timestamp || 'Just now'}</span>
        </div>

        {/* Render Execution Pipeline if present on active generating AI message */}
        {!isUser && message.pipeline && (
          <ExecutionPipeline 
            currentStage={message.pipeline.stage}
            completedStages={message.pipeline.completedStages || []}
            taskLabel={message.pipeline.taskLabel || 'Coding'}
            modelName={modelDisplayName}
            metrics={message.pipeline.metrics}
            isComplete={message.pipeline.isComplete}
            error={message.pipeline.error}
          />
        )}

        {/* Message bubble content */}
        {(message.text || isUser) && (
          <div className="message-bubble">
            <FormattedMessageText text={message.text} />
          </div>
        )}

        {/* Timing metrics footer badge for completed assistant messages */}
        {!isUser && message.metrics?.total_response_time && (
          <div className="message-response-time-badge">
            <span className="time-badge-icon">⚡</span>
            <span>Generated locally · </span>
            <span className="time-badge-highlight">Completed in {message.metrics.total_response_time}s</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;

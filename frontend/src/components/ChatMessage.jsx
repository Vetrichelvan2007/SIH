import { useState } from 'react';
import { IconBot, IconUser, IconCopy, IconCheck, IconShield, IconDocument } from './Icons';
import ExecutionPipeline from './ExecutionPipeline';
import AgentTrace from './AgentTrace';

// Helper to sanitize display text (removes internal system attachment prefixes)
function sanitizeDisplayText(text) {
  if (!text) return '';
  if (text.includes('--- ATTACHED FILE CONTEXT')) {
    const parts = text.split('--- ATTACHED FILE CONTEXT');
    const lastPart = parts[parts.length - 1];
    const endHeaderIdx = lastPart.lastIndexOf('---');
    if (endHeaderIdx !== -1) {
      const promptOnly = lastPart.substring(endHeaderIdx + 3).trim();
      if (promptOnly) return promptOnly;
    }
  }
  return text;
}

function extractAttachmentContext(message) {
  if (message.attachedFile) {
    return {
      filename: message.attachedFile.filename,
      type: message.attachedFile.result?.file_type || 'file',
      pages: message.attachedFile.result?.pages || message.attachedFile.result?.page_count
    };
  }
  if (message.trace && message.trace.context_sources) {
    const docSrc = message.trace.context_sources.find(s => s.type === 'document_attachment' || s.source === 'attachment_resolver');
    if (docSrc) {
      return {
        filename: docSrc.content_summary || 'Attached Document',
        type: docSrc.type || 'document'
      };
    }
  }
  return null;
}

function extractVisionSummary(message) {
  if (!message || !message.trace || !message.trace.steps) return null;
  const vStep = message.trace.steps.find(s => s.component === 'vision_processor' || s.model === 'qwen2.5vl:3b' || s.action === 'vision_page_analysis');
  if (vStep) {
    return vStep.output_summary || vStep.input_summary;
  }
  return null;
}

function formatModelDisplayName(modelStr) {
  if (!modelStr) return 'Phi-4 Mini';
  if (typeof modelStr === 'object') {
    return modelStr.name || modelStr.id || 'Phi-4 Mini';
  }
  const lower = String(modelStr).toLowerCase();
  if (lower.includes('phi')) return 'Phi-4 Mini';
  if (lower.includes('coder')) return 'Qwen2.5-Coder';
  if (lower.includes('qwen') && lower.includes('1.5')) return 'Qwen2.5 1.5B';
  if (lower.includes('qwen')) return 'Qwen2.5-Coder';
  return String(modelStr);
}

const ChatMessage = ({ message }) => {
  if (!message) return null;
  const isUser = message.sender === 'user';
  const modelDisplayName = formatModelDisplayName(message.modelName || message.model);
  const attachmentInfo = extractAttachmentContext(message);
  const visionSummary = extractVisionSummary(message);


  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && (
        <div className="message-avatar">
          <IconShield size={18} />
        </div>
      )}

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

        {/* Document & Processing Pipeline Card */}
        {!isUser && (attachmentInfo || visionSummary) && (
          <div className="doc-processing-pipeline-card">
            <div className="doc-pipeline-header">
              <div className="doc-pipeline-title-group">
                <IconDocument size={16} className="doc-pipeline-icon" />
                <span>Document & Processing Pipeline</span>
              </div>
              <span className="doc-pipeline-badge">✓ Active Attachment Context</span>
            </div>

            <div className="doc-pipeline-body">
              {attachmentInfo && (
                <div className="doc-pipeline-item">
                  <span className="doc-item-badge">{attachmentInfo.type?.toUpperCase()}</span>
                  <span className="doc-item-name">{attachmentInfo.filename}</span>
                  {attachmentInfo.pages && <span className="doc-item-pages">• {attachmentInfo.pages} Pages Extracted</span>}
                </div>
              )}

              {visionSummary && (
                <div className="doc-pipeline-vision-box">
                  <span className="vision-box-tag">👁️ Qwen2.5-VL-3B Visual Analysis:</span>
                  <p className="vision-box-text">{visionSummary}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Attached file chip on user message */}
        {isUser && message.attachedFile && (
          <div className="user-attachment-card">
            <div className="user-att-left">
              <IconDocument size={16} className="user-att-icon" />
              <span className="user-att-name">{message.attachedFile.filename}</span>
            </div>
            <span className="user-att-badge">{message.attachedFile.result?.file_type?.toUpperCase() || 'FILE'}</span>
          </div>
        )}

        {/* Message bubble content */}
        {(message.text || isUser) && (
          <div className={isUser ? "message-bubble" : "message-card"}>
            <FormattedMessageText text={message.text} />
          </div>
        )}

        {/* Agent Execution Trace */}
        {!isUser && message.trace && (
          <AgentTrace trace={message.trace} />
        )}

        {/* Timing metrics footer badge for completed assistant messages */}
        {!isUser && message.metrics?.total_response_time && (
          <div className="message-response-time-badge">
            <span className="time-badge-icon">⚡</span>
            <span>Generated locally {message.route ? `(${message.route}) ` : ''}• </span>
            <span className="time-badge-highlight">Completed in {message.metrics.total_response_time}s</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;


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

// Formatter for rich text, code blocks, bullet lists, and markdown elements
const FormattedMessageText = ({ text }) => {
  const cleanText = sanitizeDisplayText(text);
  if (!cleanText) return null;

  // Split by code blocks ```lang ... ```
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(cleanText)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: cleanText.substring(lastIndex, match.index)
      });
    }

    parts.push({
      type: 'code',
      language: match[1] || 'plaintext',
      code: match[2].trimEnd()
    });

    lastIndex = codeBlockRegex.lastIndex;
  }

  if (lastIndex < cleanText.length) {
    parts.push({
      type: 'text',
      content: cleanText.substring(lastIndex)
    });
  }

  return (
    <div className="formatted-message-body">
      {parts.map((part, index) => {
        if (part.type === 'code') {
          return <CodeBlock key={index} language={part.language} code={part.code} />;
        }

        const lines = part.content.split('\n');
        return (
          <div key={index} className="text-block">
            {lines.map((line, lIdx) => {
              const trimmed = line.trim();
              if (!trimmed && lIdx > 0 && lIdx < lines.length - 1) {
                return <div key={lIdx} style={{ height: '8px' }}></div>;
              }

              // Headers: # ## ###
              if (trimmed.startsWith('### ')) {
                return <h3 key={lIdx} className="msg-h3">{renderInlineFormatting(trimmed.substring(4))}</h3>;
              }
              if (trimmed.startsWith('## ')) {
                return <h2 key={lIdx} className="msg-h2">{renderInlineFormatting(trimmed.substring(3))}</h2>;
              }
              if (trimmed.startsWith('# ')) {
                return <h1 key={lIdx} className="msg-h1">{renderInlineFormatting(trimmed.substring(2))}</h1>;
              }

              // Bullet points: - or *
              if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                return (
                  <div key={lIdx} className="msg-bullet-item">
                    <span className="bullet-dot">•</span>
                    <span>{renderInlineFormatting(trimmed.substring(2))}</span>
                  </div>
                );
              }

              // Numbered list: 1. 2.
              const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
              if (numMatch) {
                return (
                  <div key={lIdx} className="msg-bullet-item">
                    <span className="bullet-num">{numMatch[1]}.</span>
                    <span>{renderInlineFormatting(numMatch[2])}</span>
                  </div>
                );
              }

              return (
                <p key={lIdx} className="msg-paragraph">
                  {renderInlineFormatting(line)}
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
        <strong key={match.index} className="inline-bold">
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

  return parts;
}


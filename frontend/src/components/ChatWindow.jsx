import { useRef, useEffect } from 'react';
import { IconMenu } from './Icons';
import ModelSelector from './ModelSelector';
import ModelStatus from './ModelStatus';
import WelcomeScreen from './WelcomeScreen';
import ChatMessage from './ChatMessage';
import MessageInput from './MessageInput';

const ChatWindow = ({
  activeSession,
  selectedModel,
  onSelectModel,
  modelStatus,
  onSendMessage,
  onSelectPrompt,
  onToggleSidebar
}) => {
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom on message updates
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [activeSession?.messages, modelStatus]);

  const messages = activeSession?.messages || [];
  const isGenerating = modelStatus === 'generating' || modelStatus === 'loading';

  return (
    <main className="chat-workspace">
      {/* Header Bar */}
      <header className="chat-header">
        <div className="header-left">
          <button 
            type="button" 
            className="sidebar-toggle-btn" 
            onClick={onToggleSidebar}
            title="Toggle Sidebar"
          >
            <IconMenu size={18} />
          </button>

          <span className="header-session-title">
            {activeSession?.title || 'Sovereign Workspace'}
          </span>
        </div>

        <div className="header-right">
          <ModelSelector 
            selectedModel={selectedModel} 
            onSelectModel={onSelectModel} 
          />

          <ModelStatus status={modelStatus} />
        </div>
      </header>

      {/* Main Conversation Stream / Welcome Screen */}
      {messages.length === 0 ? (
        <WelcomeScreen 
          onSelectPrompt={onSelectPrompt} 
          selectedModel={selectedModel} 
        />
      ) : (
        <div className="chat-messages-container">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {/* Typing Indicator pulse during response generation */}
          {isGenerating && (
            <div className="message-row ai animate-fade-in">
              <div className="avatar ai">
                <span>AI</span>
              </div>
              <div className="message-content-wrapper">
                <div className="message-meta">
                  <span>Sovereign Agent</span>
                  <span className="meta-model-tag">{selectedModel.model}</span>
                </div>
                <div className="message-bubble" style={{ color: 'var(--accent-cyan)', fontStyle: 'italic' }}>
                  Processing locally via {selectedModel.model}...
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input Footer */}
      <MessageInput 
        onSendMessage={onSendMessage} 
        selectedModel={selectedModel}
        isGenerating={isGenerating}
      />
    </main>
  );
};

export default ChatWindow;

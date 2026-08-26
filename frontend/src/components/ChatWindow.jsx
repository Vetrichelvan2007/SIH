import { useRef, useEffect } from 'react';
import { IconMenu } from './Icons';
import ModelSelector from './ModelSelector';
import ModelStatus from './ModelStatus';
import WelcomeScreen from './WelcomeScreen';
import ChatMessage from './ChatMessage';
import MessageInput from './MessageInput';
import ModelTransitionPanel from './ModelTransitionPanel';

const ChatWindow = ({
  activeSession,
  selectedTask,
  onSelectTask,
  models = [],
  selectedModel,
  modelStatus,
  onSendMessage,
  onSelectPrompt,
  onToggleSidebar,
  isSwitchingModel = false,
  modelSwitchLogs = [],
  targetSwitchModelName = ''
}) => {
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom on message updates
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [activeSession?.messages, modelStatus]);

  const messages = activeSession?.messages || [];
  const isGenerating = modelStatus === 'generating' || modelStatus === 'loading' || isSwitchingModel;

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
            selectedTask={selectedTask}
            onSelectTask={onSelectTask}
            models={models}
            selectedModel={selectedModel}
            disabled={isSwitchingModel || isGenerating}
          />

          <ModelStatus status={isSwitchingModel ? 'loading' : modelStatus} />
        </div>
      </header>

      {/* Model Transition Modal when switching local models */}
      {isSwitchingModel && (
        <ModelTransitionPanel 
          targetModelName={targetSwitchModelName || selectedModel?.name || 'Qwen2.5-Coder'}
          logs={modelSwitchLogs}
          isComplete={modelSwitchLogs.some((l) => l.status === 'ready')}
        />
      )}

      {/* Main Conversation Stream / Welcome Screen */}
      {messages.length === 0 ? (
        <WelcomeScreen 
          onSelectPrompt={onSelectPrompt} 
        />
      ) : (
        <div className="chat-messages-container">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {/* Typing Indicator pulse during response generation */}
          {isGenerating && !isSwitchingModel && (
            <div className="message-row ai animate-fade-in">
              <div className="avatar ai">
                <span>AI</span>
              </div>
              <div className="message-content-wrapper">
                <div className="message-meta">
                  <span>Sovereign Agent</span>
                  <span className="meta-model-tag">{selectedModel?.name || selectedModel?.model || 'Qwen2.5-Coder'}</span>
                </div>
                <div className="message-bubble" style={{ color: 'var(--accent-cyan)', fontStyle: 'italic' }}>
                  Processing locally via {selectedModel?.name || selectedModel?.model || 'local Ollama model'}...
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

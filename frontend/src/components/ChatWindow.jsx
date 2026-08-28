import { useRef, useEffect } from 'react';
import { IconMenu, IconShield } from './Icons';
import ModelSelector from './ModelSelector';
import ModelStatus from './ModelStatus';
import WelcomeScreen from './WelcomeScreen';
import ChatMessage from './ChatMessage';
import MessageInput from './MessageInput';
import ModelTransitionPanel from './ModelTransitionPanel';

function formatHeaderTitle(session) {
  if (!session || !session.title) return 'Sovereign Workspace';
  const raw = session.title.trim();
  if (raw.includes('--- ATTACHED FILE CONTEXT') || raw.includes('ATTACHED FILE CONTEXT')) {
    const match = raw.match(/Attached file:\s*([^\n\r]+)/i);
    if (match && match[1]) {
      return `Document: ${match[1].trim()}`;
    }
    return 'Document Intelligence Workspace';
  }
  return raw;
}

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
  targetSwitchModelName = '',
  multiModelMode = false,
  onToggleMultiModel,
  currentExecution = null
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

  const currentDisplayModel = currentExecution?.selectedModel || (multiModelMode ? 'Selecting Model...' : (selectedModel?.name || 'Phi-4 Mini'));

  return (
    <main className="main-content">
      {/* Top Header Bar */}
      <header className="top-header">
        <div className="header-left">
          <button 
            type="button" 
            className="mobile-menu-toggle" 
            onClick={onToggleSidebar}
            title="Toggle Sidebar"
          >
            <IconMenu size={20} />
          </button>

          <div className="header-title-box">
            <span className="header-chat-title">
              {formatHeaderTitle(activeSession)}
            </span>
            <span className="header-subtitle">
              On-Premise AI Workspace with Document & Vision Processing
            </span>
          </div>
        </div>


        <div className="header-right">
          <ModelSelector 
            selectedTask={selectedTask}
            onSelectTask={onSelectTask}
            models={models}
            selectedModel={selectedModel}
            disabled={isSwitchingModel || isGenerating}
            multiModelMode={multiModelMode}
            onToggleMultiModel={onToggleMultiModel}
          />

          <ModelStatus status={isSwitchingModel ? 'loading' : modelStatus} />
        </div>
      </header>

      {/* Model Transition Modal when switching local models */}
      {isSwitchingModel && (
        <ModelTransitionPanel 
          targetModelName={targetSwitchModelName || selectedModel?.name || 'Phi-4 Mini'}
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
        <div className="messages-wrapper">
          <div className="messages-content-area">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}

            {/* Typing Indicator pulse during response generation */}
            {isGenerating && !isSwitchingModel && (
              <div className="message-row assistant animate-fade-in">
                <div className="message-avatar">
                  <IconShield size={18} />
                </div>
                <div className="message-content-wrapper">
                  <div className="message-meta">
                    <span>Sovereign Agent</span>
                    <span className="meta-model-tag">{currentDisplayModel}</span>
                  </div>
                  <div className="message-card" style={{ color: 'var(--primary)', fontStyle: 'italic' }}>
                    {currentExecution?.selectedModel
                      ? `${currentExecution.selectedModel} is processing locally...`
                      : (multiModelMode ? 'Selecting model and processing locally...' : `Processing locally via ${selectedModel?.name || 'Phi-4 Mini'}...`)}
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
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

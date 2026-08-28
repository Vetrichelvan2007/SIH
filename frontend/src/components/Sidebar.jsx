import { useState } from 'react';
import { IconShield, IconPlus, IconMessage, IconTrash, IconCpu, IconCheck, IconPencil, IconX, IconSearch } from './Icons';
import LoadedModels from './LoadedModels';
import SystemResources from './SystemResources';

function formatSidebarTitle(session) {
  if (!session || !session.title) return 'New Conversation';
  const raw = session.title.trim();
  if (raw.includes('--- ATTACHED FILE CONTEXT') || raw.includes('ATTACHED FILE CONTEXT')) {
    const match = raw.match(/Attached file:\s*([^\n\r]+)/i);
    if (match && match[1]) {
      return `Doc: ${match[1].trim()}`;
    }
    return 'Document QA';
  }
  return raw;
}

const Sidebar = ({ 
  sessions, 
  activeSessionId, 
  onSelectSession, 
  onNewChat, 
  onDeleteSession,
  onRenameSession,
  models = [],
  selectedTask,
  onSelectTask,
  systemStatus = null,
  modelsStatus = null,
  isSwitchingModel = false,
  targetSwitchModelName = '',
  isMobileOpen,
  onCloseMobile,
  multiModelMode = false,
  onToggleMultiModel,
  modelStatus = 'ready',
  onRefreshTelemetry,
  toggleError = null
}) => {
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [confirmingDeleteId, setConfirmingDeleteId] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  const handleStartRename = (e, session) => {
    e.stopPropagation();
    setEditingId(session.id);
    setEditTitle(formatSidebarTitle(session));
    setConfirmingDeleteId(null);
  };

  const handleSaveRename = (e, sessionId) => {
    if (e) e.stopPropagation();
    if (editTitle && editTitle.trim()) {
      if (onRenameSession) {
        onRenameSession(sessionId, editTitle.trim());
      }
    }
    setEditingId(null);
  };

  const handleConfirmDelete = (e, sessionId) => {
    e.stopPropagation();
    if (onDeleteSession) {
      onDeleteSession(sessionId);
    }
    setConfirmingDeleteId(null);
  };

  const gpu = systemStatus?.gpu;
  const cpu = systemStatus?.cpu;
  const ollama = systemStatus?.ollama;

  const rawGpuName = gpu?.available ? gpu.name : 'NVIDIA GeForce RTX 3050 6GB';
  const cleanGpuName = rawGpuName.replace('Laptop GPU', '').replace('GeForce ', '').trim();
  const isOllamaConnected = ollama?.status === 'running';


  const activeModelDisplay = systemStatus?.active_model 
    ? (systemStatus.active_model.includes('qwen') ? 'Qwen2.5-Coder' : (systemStatus.active_model.includes('phi') ? 'Phi-4 Mini' : systemStatus.active_model))
    : 'None Loaded';

  const filteredSessions = sessions ? sessions.filter(s => 
    !searchTerm || (s.title && s.title.toLowerCase().includes(searchTerm.toLowerCase()))
  ) : [];

  return (
    <aside className={`sidebar ${isMobileOpen ? 'mobile-open' : ''}`}>
      {/* 1. Header Branding & New Chat */}
      <div className="sidebar-header">
        <div className="sidebar-brand-row">
          <div className="brand-icon">
            <IconShield size={20} />
          </div>
          <div className="brand-info">
            <span className="brand-title">Sovereign AI</span>
            <span className="brand-badge">
              <span className="brand-badge-dot"></span> ON-PREMISE
            </span>
          </div>
        </div>

        <button 
          type="button" 
          className="new-chat-btn"
          onClick={() => {
            onNewChat();
            if (onCloseMobile) onCloseMobile();
          }}
        >
          <IconPlus size={16} />
          <span>New Chat</span>
        </button>
      </div>

      {/* 2. Scrollable Body */}
      <div className="sidebar-scroll-area">
        {/* Chat History Section */}
        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <span className="sidebar-section-title">CHAT HISTORY</span>
          </div>

          {sessions && sessions.length > 3 && (
            <div className="chat-search-box">
              <IconSearch size={14} className="search-icon" />
              <input 
                type="text"
                placeholder="Search chats..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="chat-search-input"
              />
              {searchTerm && (
                <button type="button" onClick={() => setSearchTerm('')} className="clear-search-btn">
                  <IconX size={12} />
                </button>
              )}
            </div>
          )}

          {filteredSessions && filteredSessions.length > 0 ? (
            <div className="chat-history-list">
              {filteredSessions.map((session) => {
                const isActive = session.id === activeSessionId;
                const isEditing = editingId === session.id;
                const isConfirming = confirmingDeleteId === session.id;

                return (
                  <div
                    key={session.id}
                    className={`history-item ${isActive ? 'active' : ''} ${isEditing ? 'editing' : ''}`}
                    onClick={() => {
                      if (!isEditing && !isConfirming) {
                        onSelectSession(session.id);
                        if (onCloseMobile) onCloseMobile();
                      }
                    }}
                  >
                    <div className="history-title-wrap">
                      <IconMessage size={14} className="history-msg-icon" />
                      
                      {isEditing ? (
                        <input
                          type="text"
                          className="history-edit-input"
                          value={editTitle}
                          autoFocus
                          onChange={(e) => setEditTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveRename(e, session.id);
                            if (e.key === 'Escape') setEditingId(null);
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <span className="history-title" title={session.title}>
                          {formatSidebarTitle(session)}
                        </span>
                      )}
                    </div>

                    <div className="history-item-actions" onClick={(e) => e.stopPropagation()}>
                      {isEditing ? (
                        <>
                          <button
                            type="button"
                            className="history-action-btn"
                            title="Save title"
                            onClick={(e) => handleSaveRename(e, session.id)}
                          >
                            <IconCheck size={13} style={{ color: 'var(--success)' }} />
                          </button>
                          <button
                            type="button"
                            className="history-action-btn"
                            title="Cancel edit"
                            onClick={(e) => { e.stopPropagation(); setEditingId(null); }}
                          >
                            <IconX size={13} />
                          </button>
                        </>
                      ) : isConfirming ? (
                        <>
                          <button
                            type="button"
                            className="history-action-btn confirm-delete"
                            title="Confirm delete"
                            onClick={(e) => handleConfirmDelete(e, session.id)}
                          >
                            Delete
                          </button>
                          <button
                            type="button"
                            className="history-action-btn cancel-delete"
                            title="Cancel delete"
                            onClick={(e) => { e.stopPropagation(); setConfirmingDeleteId(null); }}
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            type="button"
                            className="history-action-btn"
                            title="Rename chat"
                            onClick={(e) => handleStartRename(e, session)}
                          >
                            <IconPencil size={13} />
                          </button>
                          <button
                            type="button"
                            className="history-action-btn delete"
                            title="Delete chat"
                            onClick={(e) => {
                              e.stopPropagation();
                              setConfirmingDeleteId(session.id);
                              setEditingId(null);
                            }}
                          >
                            <IconTrash size={13} />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty-history-text">No previous conversations</div>
          )}
        </div>

        {/* Loaded Models Section */}
        <LoadedModels 
          models={modelsStatus?.models || []}
          isSwitchingModel={isSwitchingModel}
          targetSwitchModelName={targetSwitchModelName}
          modelStatus={modelStatus}
          multiModelMode={multiModelMode}
          onRefreshTelemetry={onRefreshTelemetry}
        />

        {/* System Resources Section */}
        <SystemResources 
          system={modelsStatus?.system}
        />

        {/* Local Compute Node Section */}
        <div className="sidebar-section">
          <div className="sidebar-section-title">LOCAL COMPUTE NODE</div>
          <div className="compute-node-card">
            <div className="compute-card-header">
              <div className="compute-card-title">
                <IconCpu size={14} className="compute-cpu-icon" />
                <span>Local GPU Node</span>
              </div>
              <span className="live-status-pill">
                <span className="live-dot"></span> LIVE
              </span>
            </div>

            <div className="compute-card-body">
              <div className="compute-info-row">
                <span className="compute-label">GPU:</span>
                <span className="compute-val" title={rawGpuName}>{cleanGpuName}</span>
              </div>


              <div className="compute-info-row">
                <span className="compute-label">CPU Usage:</span>
                <span className="compute-val mono">{cpu?.usage || 0}%</span>
              </div>

              <div className="compute-info-row">
                <span className="compute-label">Active Model:</span>
                <span className="compute-val active-model-text">
                  ● {activeModelDisplay}
                </span>
              </div>

              <div className="compute-info-row">
                <span className="compute-label">Ollama Service:</span>
                <span className={`compute-val status-${isOllamaConnected ? 'online' : 'offline'}`}>
                  {isOllamaConnected ? '● Connected' : '● Disconnected'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;

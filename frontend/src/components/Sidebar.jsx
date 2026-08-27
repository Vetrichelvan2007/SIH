import { IconShield, IconPlus, IconMessage, IconTrash, IconCpu, IconCheck } from './Icons';
import LoadedModels from './LoadedModels';
import SystemResources from './SystemResources';

const Sidebar = ({ 
  sessions, 
  activeSessionId, 
  onSelectSession, 
  onNewChat, 
  onDeleteSession,
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
  onToggleMultiModel
}) => {
  // Parse live metrics safely
  const gpu = systemStatus?.gpu;
  const cpu = systemStatus?.cpu;
  const ollama = systemStatus?.ollama;

  const gpuName = gpu?.available ? gpu.name : 'Local GPU / CPU';
  const isOllamaConnected = ollama?.status === 'running';

  const activeModelDisplay = systemStatus?.active_model 
    ? (systemStatus.active_model.includes('qwen') ? 'Qwen2.5-Coder' : (systemStatus.active_model.includes('phi') ? 'Phi-4 Mini' : systemStatus.active_model))
    : 'None Loaded';

  return (
    <aside className={`sidebar ${isMobileOpen ? 'mobile-open' : ''}`}>
      {/* 1. Fixed Header Area */}
      <div className="sidebar-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="brand-icon">
            <IconShield size={22} />
          </div>
          <div className="brand-info">
            <span className="brand-title">Sovereign AI</span>
            <span className="brand-badge">
              <span className="brand-badge-dot"></span> On-Premise
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
          <IconPlus size={18} />
          <span>New Chat</span>
        </button>
      </div>

      {/* 2. ONE Scroll Container for ALL Sidebar Content */}
      <div className="sidebar-scroll-area">
        {/* Multi-Model Mode Toggle Card */}
        <div className="sidebar-section">
          <div 
            onClick={() => onToggleMultiModel && onToggleMultiModel(!multiModelMode)}
            style={{
              background: multiModelMode ? 'rgba(6, 182, 212, 0.12)' : 'var(--bg-card)',
              border: multiModelMode ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '8px 10px',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '11px', fontWeight: 600, color: multiModelMode ? 'var(--accent-cyan)' : 'var(--text-secondary)' }}>
                MULTI-MODEL MODE
              </span>
              <span style={{ fontSize: '10px', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', background: multiModelMode ? 'var(--accent-cyan)' : 'rgba(255,255,255,0.1)', color: multiModelMode ? '#000' : 'var(--text-muted)' }}>
                {multiModelMode ? 'ON' : 'OFF'}
              </span>
            </div>
            <div style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '3px' }}>
              {multiModelMode ? 'Qwen2.5 1.5B Router active' : 'Single model mode (0 overhead)'}
            </div>
            {multiModelMode && (
              <div style={{ fontSize: '9.5px', color: 'var(--accent-emerald)', marginTop: '3px', fontWeight: 500 }}>
                ✓ Safety: RAM ≥1GB, VRAM ≥500MB
              </div>
            )}
          </div>
        </div>

        {/* Chat History List (Renders ONLY if chat sessions exist) */}
        {sessions && sessions.length > 0 && (
          <div className="sidebar-section">
            <div className="sidebar-section-title">
              Chat History
            </div>
            <div className="chat-history-list">
              {sessions.map((session) => {
                const isActive = session.id === activeSessionId;
                return (
                  <div
                    key={session.id}
                    className={`history-item ${isActive ? 'active' : ''}`}
                    onClick={() => {
                      onSelectSession(session.id);
                      if (onCloseMobile) onCloseMobile();
                    }}
                  >
                    <div className="history-title-wrap">
                      <IconMessage size={14} style={{ color: isActive ? 'var(--accent-cyan)' : 'var(--text-muted)' }} />
                      <span className="history-title" title={session.title}>
                        {session.title || 'New Conversation'}
                      </span>
                    </div>
                    
                    <button
                      type="button"
                      className="delete-session-btn"
                      title="Delete chat session"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(session.id);
                      }}
                    >
                      <IconTrash size={13} />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Loaded Models Section */}
        <LoadedModels 
          models={modelsStatus?.models || []}
          isSwitchingModel={isSwitchingModel}
          targetSwitchModelName={targetSwitchModelName}
        />

        {/* System Resources Section */}
        <SystemResources 
          system={modelsStatus?.system}
        />

        {/* Available Models Section */}
        <div className="sidebar-section">
          <div className="sidebar-section-title">
            Available Models
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {models.map((m) => {
              const isSelected = selectedTask === m.task;
              return (
                <div
                  key={m.id}
                  onClick={() => onSelectTask(m.task)}
                  style={{
                    background: isSelected ? 'var(--bg-card-active)' : 'var(--bg-card)',
                    border: isSelected ? '1px solid var(--border-accent)' : '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '7px 10px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '10.5px', color: 'var(--text-muted)' }}>
                    <span>{m.type}</span>
                    <span 
                      style={{ 
                        color: m.available ? 'var(--accent-emerald)' : 'var(--accent-rose)', 
                        fontWeight: 600, 
                        fontSize: '9.5px' 
                      }}
                    >
                      {m.status || (m.available ? 'Available' : 'Unavailable')}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                    {m.available && <IconCheck size={12} style={{ color: 'var(--accent-emerald)' }} />}
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.name || m.id}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Local Compute Node Section (Normal document flow directly following Available Models) */}
        <div className="sidebar-section">
          <div className="system-status-card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <IconCpu size={14} style={{ color: 'var(--accent-cyan)' }} />
                <span>LOCAL COMPUTE NODE</span>
              </div>
              <span style={{ fontSize: '10px', color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span className="brand-badge-dot"></span> LIVE
              </span>
            </div>

            {/* GPU Info */}
            {gpu?.available && (
              <div style={{ fontSize: '10.5px', color: 'var(--text-secondary)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={gpuName}>
                GPU: {gpuName}
              </div>
            )}

            {gpu?.available && (
              <div className="system-metric">
                <span>GPU UTILIZATION</span>
                <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{gpu?.utilization || 0}%</span>
              </div>
            )}

            <div className="system-metric">
              <span>CPU USAGE</span>
              <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{cpu?.usage || 0}%</span>
            </div>

            <div className="system-metric" style={{ marginTop: '2px' }}>
              <span>ACTIVE MODEL</span>
              <span style={{ color: active_model_name_color(activeModelDisplay), fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                ● {activeModelDisplay}
              </span>
            </div>

            <div className="system-metric">
              <span>OLLAMA</span>
              <span style={{ color: isOllamaConnected ? 'var(--accent-emerald)' : 'var(--accent-rose)', fontWeight: 600 }}>
                ● {isOllamaConnected ? 'CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>

            <div className="system-metric" style={{ marginTop: '2px', fontSize: '9.5px', color: 'var(--text-muted)' }}>
              <span>PERIMETER</span>
              <span style={{ color: 'var(--accent-cyan)' }}>LOCAL INFERENCE</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};

function active_model_name_color(name) {
  if (name === 'None Loaded') return 'var(--text-muted)';
  return 'var(--accent-cyan)';
}

export default Sidebar;

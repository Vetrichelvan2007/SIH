import { IconShield, IconPlus, IconMessage, IconTrash, IconCpu, IconCheck } from './Icons';

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
  isMobileOpen,
  onCloseMobile
}) => {
  // Parse live metrics safely
  const gpu = systemStatus?.gpu;
  const cpu = systemStatus?.cpu;
  const ram = systemStatus?.ram;
  const ollama = systemStatus?.ollama;

  const gpuName = gpu?.available ? gpu.name : 'Local GPU / CPU';
  const vramUsedGb = gpu?.available ? (gpu.vram_used_mb / 1024).toFixed(1) : '0.0';
  const vramTotalGb = gpu?.available ? (gpu.vram_total_mb / 1024).toFixed(1) : '0.0';
  const vramPercent = gpu?.available && gpu.vram_total_mb > 0 
    ? Math.min(100, Math.round((gpu.vram_used_mb / gpu.vram_total_mb) * 100)) 
    : 0;

  const ramUsedGb = ram?.used_mb ? (ram.used_mb / 1024).toFixed(1) : '0.0';
  const ramTotalGb = ram?.total_mb ? (ram.total_mb / 1024).toFixed(1) : '0.0';

  const isOllamaConnected = ollama?.status === 'running';

  const activeModelDisplay = systemStatus?.active_model 
    ? (systemStatus.active_model.includes('qwen') ? 'Qwen2.5-Coder' : (systemStatus.active_model.includes('phi') ? 'Phi-4 Mini' : systemStatus.active_model))
    : 'None Loaded';

  return (
    <aside className={`sidebar ${isMobileOpen ? 'mobile-open' : ''}`}>
      {/* Brand Header */}
      <div className="sidebar-header">
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

      {/* New Chat Button */}
      <div className="sidebar-action-container">
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

      {/* Chat History List */}
      <div className="sidebar-section-title">
        Chat History
      </div>

      <div className="chat-history-list">
        {sessions.length === 0 ? (
          <div style={{ padding: '12px', fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center' }}>
            No chat history yet.
          </div>
        ) : (
          sessions.map((session) => {
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
                  <IconMessage size={15} style={{ color: isActive ? 'var(--accent-cyan)' : 'var(--text-muted)' }} />
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
                  <IconTrash size={14} />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Available Models Section */}
      <div className="sidebar-section-title" style={{ marginTop: '12px' }}>
        Available Models
      </div>
      <div style={{ padding: '0 12px 12px 12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
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
                padding: '8px 10px',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
                <span>{m.type}</span>
                <span 
                  style={{ 
                    color: m.available ? 'var(--accent-emerald)' : 'var(--accent-rose)', 
                    fontWeight: 600, 
                    fontSize: '10px' 
                  }}
                >
                  {m.status || (m.available ? 'Available' : 'Unavailable')}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {m.available && <IconCheck size={13} style={{ color: 'var(--accent-emerald)' }} />}
                <span>{m.name || m.id}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Real Live System Monitor (Local Compute Node) */}
      <div className="sidebar-footer">
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
          
          <div className="system-metric">
            <span>GPU VRAM</span>
            <span style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>{vramUsedGb} / {vramTotalGb} GB</span>
          </div>
          <div className="metric-bar">
            <div className="metric-fill" style={{ width: `${vramPercent}%` }}></div>
          </div>

          <div className="system-metric" style={{ marginTop: '2px' }}>
            <span>GPU UTILIZATION</span>
            <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{gpu?.utilization || 0}%</span>
          </div>

          <div className="system-metric">
            <span>CPU USAGE</span>
            <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{cpu?.usage || 0}%</span>
          </div>

          <div className="system-metric">
            <span>SYSTEM RAM</span>
            <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{ramUsedGb} / {ramTotalGb} GB</span>
          </div>

          <div className="system-metric" style={{ marginTop: '4px' }}>
            <span>ACTIVE MODEL</span>
            <span style={{ color: active_model_name_color(activeModelDisplay), fontWeight: 600 }}>● {activeModelDisplay}</span>
          </div>

          <div className="system-metric">
            <span>OLLAMA</span>
            <span style={{ color: isOllamaConnected ? 'var(--accent-emerald)' : 'var(--accent-rose)', fontWeight: 600 }}>
              ● {isOllamaConnected ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>

          <div className="system-metric" style={{ marginTop: '2px', fontSize: '10px', color: 'var(--text-muted)' }}>
            <span>PERIMETER</span>
            <span style={{ color: 'var(--accent-cyan)' }}>LOCAL INFERENCE</span>
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

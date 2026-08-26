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
  isMobileOpen,
  onCloseMobile
}) => {
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

      {/* Footer System Specs */}
      <div className="sidebar-footer">
        <div className="system-status-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)' }}>
            <IconCpu size={14} style={{ color: 'var(--accent-cyan)' }} />
            <span>Local Compute Node</span>
          </div>
          
          <div className="system-metric">
            <span>GPU VRAM</span>
            <span style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>3.8 / 16 GB</span>
          </div>
          <div className="metric-bar">
            <div className="metric-fill" style={{ width: '24%' }}></div>
          </div>

          <div className="system-metric" style={{ marginTop: '4px' }}>
            <span>Network Perimeter</span>
            <span style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>AIR-GAPPED</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;

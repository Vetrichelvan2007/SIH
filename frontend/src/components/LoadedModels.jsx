const getStatusBadge = (status) => {
  const upper = (status || '').toUpperCase();
  switch (upper) {
    case 'ACTIVE':
      return { label: 'Active', className: 'status-indicator active', dotColor: 'var(--accent-emerald)', bg: 'rgba(16, 185, 129, 0.15)' };
    case 'LOADED':
      return { label: 'Loaded', className: 'status-indicator loaded', dotColor: 'var(--accent-cyan)', bg: 'rgba(6, 182, 212, 0.15)' };
    case 'LOADING':
      return { label: 'Loading', className: 'status-indicator loading', dotColor: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' };
    case 'UNLOADING':
      return { label: 'Unloading', className: 'status-indicator unloading', dotColor: '#f97316', bg: 'rgba(249, 115, 22, 0.15)' };
    case 'FAILED':
      return { label: 'Failed', className: 'status-indicator failed', dotColor: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)' };
    default:
      return { label: upper || 'Unknown', className: 'status-indicator', dotColor: 'var(--text-muted)', bg: 'rgba(255, 255, 255, 0.08)' };
  }
};

const formatMemoryMb = (mb) => {
  if (mb === undefined || mb === null) return '0 MB';
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(1)} GB`;
  }
  return `${Math.round(mb)} MB`;
};

const LoadedModels = ({ models = [], isSwitchingModel = false, targetSwitchModelName = '' }) => {
  return (
    <div className="sidebar-section">
      <div className="sidebar-section-title" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>Loaded Models</span>
        <span className="loaded-count-badge">
          {models.length} {models.length === 1 ? 'Model' : 'Models'}
        </span>
      </div>

      <div className="loaded-models-list">
        {models.length === 0 && !isSwitchingModel ? (
          <div className="empty-loaded-models">
            No models currently loaded.
          </div>
        ) : (
          <>
            {models.map((m, idx) => {
              const badge = getStatusBadge(m.status);
              const ramText = formatMemoryMb(m.ram_usage_mb);
              const vramText = formatMemoryMb(m.vram_usage_mb);

              return (
                <div key={idx} className="loaded-model-card">
                  <div className="loaded-model-header">
                    <div className="loaded-model-title-wrap">
                      <span 
                        className="status-dot-pulse" 
                        style={{ backgroundColor: badge.dotColor }}
                        title={`Status: ${badge.label}`}
                      />
                      <span className="loaded-model-name" title={m.name}>
                        {m.name}
                      </span>
                    </div>

                    <span 
                      className="status-pill-badge"
                      style={{ backgroundColor: badge.bg, color: badge.dotColor }}
                    >
                      {badge.label}
                    </span>
                  </div>

                  <div className="loaded-model-meta">
                    <span className="loaded-model-role">
                      Role: <strong>{m.role_display || m.role || 'Main Model'}</strong>
                    </span>

                    <div className="loaded-model-specs">
                      <span className="spec-item">
                        RAM: <strong>{ramText}</strong>
                      </span>
                      <span className="spec-item-divider">•</span>
                      <span className="spec-item">
                        VRAM: <strong>{vramText}</strong>
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Render transition card if a model is currently being loaded */}
            {isSwitchingModel && (
              <div className="loaded-model-card switching">
                <div className="loaded-model-header">
                  <div className="loaded-model-title-wrap">
                    <span className="status-dot-pulse loading" style={{ backgroundColor: '#f59e0b' }} />
                    <span className="loaded-model-name">{targetSwitchModelName || 'Switching Model'}</span>
                  </div>
                  <span className="status-pill-badge" style={{ backgroundColor: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b' }}>
                    LOADING
                  </span>
                </div>
                <div className="loaded-model-meta" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Allocating memory in background...
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default LoadedModels;

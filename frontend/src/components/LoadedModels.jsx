import React, { useState } from 'react';

const getStatusBadge = (status, isProtected) => {
  if (isProtected || status === 'PROTECTED') {
    return { label: 'Protected', className: 'status-indicator protected', dotColor: 'var(--primary)', bg: 'var(--primary-light)' };
  }
  const upper = (status || '').toUpperCase();
  switch (upper) {
    case 'ACTIVE':
      return { label: 'Active', className: 'status-indicator active', dotColor: 'var(--success)', bg: 'var(--success-bg)' };
    case 'LOADED':
      return { label: 'Loaded', className: 'status-indicator loaded', dotColor: 'var(--primary)', bg: 'var(--primary-light)' };
    case 'LOADING':
      return { label: 'Loading', className: 'status-indicator loading', dotColor: 'var(--warning)', bg: 'var(--warning-bg)' };
    case 'UNLOADING':
      return { label: 'Unloading', className: 'status-indicator unloading', dotColor: 'var(--warning)', bg: 'var(--warning-bg)' };
    case 'FAILED':
      return { label: 'Failed', className: 'status-indicator failed', dotColor: 'var(--error)', bg: 'var(--error-bg)' };
    default:
      return { label: upper || 'Unknown', className: 'status-indicator', dotColor: 'var(--text-muted)', bg: 'var(--surface-secondary)' };
  }
};


const formatMemoryMb = (mb) => {
  if (mb === undefined || mb === null) return '0 MB';
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(1)} GB`;
  }
  return `${Math.round(mb)} MB`;
};

const LoadedModels = ({
  models = [],
  isSwitchingModel = false,
  targetSwitchModelName = '',
  modelStatus = 'ready',
  multiModelMode = false,
  onRefreshTelemetry
}) => {
  const [unloadingMap, setUnloadingMap] = useState({});
  const [confirmModal, setConfirmModal] = useState(null); // { modelName, isRouter }
  const [errorMsg, setErrorMsg] = useState(null);

  const isGenerating = modelStatus === 'generating' || modelStatus === 'loading' || isSwitchingModel;

  const isRouterModel = (modelName = '') => {
    const lower = modelName.toLowerCase();
    return lower.includes('1.5b') || lower.includes('router') || lower.includes('qwen2.5:1.5');
  };

  const handleUnloadClick = (modelName, isProtected) => {
    if (isGenerating) return;
    const isRouter = (multiModelMode && isProtected) || isRouterModel(modelName);
    setConfirmModal({ modelName, isRouter });
  };

  const executeUnload = async (modelName) => {
    setConfirmModal(null);
    setUnloadingMap((prev) => ({ ...prev, [modelName]: true }));
    setErrorMsg(null);

    try {
      const res = await fetch('http://localhost:8000/api/models/unload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: modelName })
      });
      const data = await res.json();
      if (data.success) {
        if (onRefreshTelemetry) {
          onRefreshTelemetry();
        }
      } else {
        setErrorMsg(data.message || `Failed to unload ${modelName}.`);
      }
    } catch (err) {
      setErrorMsg(`Failed to unload ${modelName}. Server connection error.`);
    } finally {
      setUnloadingMap((prev) => ({ ...prev, [modelName]: false }));
    }
  };

  return (
    <div className="sidebar-section">
      <div className="sidebar-section-title" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>Loaded Models</span>
        <span className="loaded-count-badge">
          {models.length} {models.length === 1 ? 'Model' : 'Models'}
        </span>
      </div>

      {errorMsg && (
        <div className="unload-error-banner" style={{ padding: '6px 10px', margin: '4px 0 8px 0', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.4)', borderRadius: '6px', fontSize: '11px', color: '#fca5a5', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} style={{ background: 'none', border: 'none', color: '#fca5a5', cursor: 'pointer', fontWeight: 'bold' }}>×</button>
        </div>
      )}

      <div className="loaded-models-list">
        {models.length === 0 && !isSwitchingModel ? (
          <div className="empty-loaded-models">
            No models currently loaded.
          </div>
        ) : (
          <>
            {models.map((m, idx) => {
              const isUnloadingThis = unloadingMap[m.name];
              const badge = isUnloadingThis
                ? { label: 'Unloading...', className: 'status-indicator unloading', dotColor: '#f97316', bg: 'rgba(249, 115, 22, 0.15)' }
                : getStatusBadge(m.status, m.protected);

              const ramText = formatMemoryMb(m.ram_usage_mb);
              const vramText = formatMemoryMb(m.vram_usage_mb);

              return (
                <div key={idx} className={`loaded-model-card ${isUnloadingThis ? 'unloading' : ''}`}>
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

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span 
                        className="status-pill-badge"
                        style={{ backgroundColor: badge.bg, color: badge.dotColor }}
                      >
                        {badge.label}
                      </span>

                      {/* Unload Button */}
                      <button
                        className="model-unload-btn"
                        disabled={isGenerating || isUnloadingThis}
                        onClick={() => handleUnloadClick(m.name, m.protected)}
                        title={isGenerating ? "Currently generating..." : `Unload ${m.name} from RAM/VRAM`}
                      >
                        {isUnloadingThis ? (
                          "Unloading..."
                        ) : isGenerating ? (
                          "Generating..."
                        ) : (
                          "Unload"
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="loaded-model-meta">
                    <span className="loaded-model-role">
                      Role: <strong>{m.role_display || m.role || 'Main Model'}</strong>
                      {m.protected && (
                        <span style={{ marginLeft: '6px', fontSize: '9.5px', color: 'var(--accent-cyan)', fontWeight: 600 }}>
                          • Always Loaded
                        </span>
                      )}
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

      {/* Confirmation Modal */}
      {confirmModal && (
        <div className="modal-backdrop" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }}>
          <div className="modal-dialog" style={{ background: '#0f172a', border: confirmModal.isRouter ? '1px solid #f59e0b' : '1px solid var(--border-subtle)', borderRadius: '12px', padding: '20px', maxWidth: '420px', width: '90%', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.5)' }}>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '15px', color: confirmModal.isRouter ? '#f59e0b' : 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              {confirmModal.isRouter ? "⚠️ Router Warning: Unload Qwen2.5 1.5B?" : `Unload ${confirmModal.modelName}?`}
            </h4>

            <p style={{ margin: '0 0 16px 0', fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              {confirmModal.isRouter ? (
                "Qwen2.5 1.5B is the active Query Router. Unloading it will temporarily disable multi-model routing. The router will be loaded again automatically when the next multi-model query is processed."
              ) : (
                `This will remove ${confirmModal.modelName} from RAM/VRAM. It will automatically load again if needed.`
              )}
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                onClick={() => setConfirmModal(null)}
                style={{ padding: '6px 14px', background: 'rgba(255, 255, 255, 0.08)', border: '1px solid var(--border-subtle)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '12px', cursor: 'pointer' }}
              >
                Cancel
              </button>

              <button
                onClick={() => executeUnload(confirmModal.modelName)}
                style={{
                  padding: '6px 14px',
                  background: confirmModal.isRouter ? '#d97706' : '#e11d48',
                  border: 'none',
                  borderRadius: '6px',
                  color: '#ffffff',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                {confirmModal.isRouter ? "Unload Anyway" : "Unload"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoadedModels;

import { IconCheck } from './Icons';

const ModelTransitionPanel = ({ 
  targetModelName = 'Phi-4 Mini',
  logs = [],
  isComplete = false
}) => {
  return (
    <div className="model-transition-overlay">
      <div className="model-transition-card animate-fade-in">
        <div className="transition-header">
          <div className="transition-title-wrap">
            <span className="transition-bolt">⚡</span>
            <span>MODEL TRANSITION PIPELINE</span>
          </div>
          {isComplete ? (
            <span className="transition-badge ready">READY</span>
          ) : (
            <span className="transition-badge switching">SWITCHING</span>
          )}
        </div>

        <div className="transition-subtitle">
          Target Model: <strong>{targetModelName}</strong>
        </div>

        <div className="transition-logs-list">
          {logs.map((log, index) => {
            const isFinished = log.status === 'ready' || log.status === 'unloaded';
            const isError = log.status === 'error';
            const isActive = index === logs.length - 1 && !isComplete && !isError;

            return (
              <div key={index} className={`transition-log-item ${isFinished ? 'finished' : isActive ? 'active' : ''}`}>
                <div className="transition-step-icon">
                  {isFinished && <span className="icon-check"><IconCheck size={12} /></span>}
                  {isActive && <span className="icon-pulse">◉</span>}
                  {!isFinished && !isActive && <span className="icon-pending">○</span>}
                </div>
                <span className="transition-log-msg">{log.message}</span>
              </div>
            );
          })}
        </div>

        <div className="transition-footer-note">
          {isComplete 
            ? '✓ Model verified and loaded into GPU memory.' 
            : 'Please wait while VRAM memory is released and allocated...'}
        </div>
      </div>
    </div>
  );
};

export default ModelTransitionPanel;

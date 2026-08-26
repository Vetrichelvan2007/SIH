const ModelStatus = ({ status = 'ready' }) => {
  const getStatusLabel = () => {
    switch (status) {
      case 'loading':
        return 'Loading';
      case 'generating':
        return 'Generating';
      case 'ready':
      default:
        return 'Ready';
    }
  };

  return (
    <div className="status-pill" title={`Model Status: ${getStatusLabel()}`}>
      <span className={`status-dot ${status}`}></span>
      <span style={{ color: status === 'generating' ? 'var(--accent-cyan)' : 'var(--text-secondary)' }}>
        {getStatusLabel()}
      </span>
    </div>
  );
};

export default ModelStatus;

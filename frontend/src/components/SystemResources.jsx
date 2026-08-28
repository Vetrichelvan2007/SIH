const formatMb = (mb) => {
  if (mb === undefined || mb === null || isNaN(mb)) return '0 MB';
  if (mb >= 1024) {
    const gb = (mb / 1024).toFixed(1);
    return `${gb.replace(/\.0$/, '')} GB`;
  }
  return `${Math.round(mb)} MB`;
};

const SystemResources = ({ system = null }) => {
  const ramTotal = formatMb(system?.ram_total_mb);
  const ramUsed = formatMb(system?.ram_used_mb);
  const ramAvail = formatMb(system?.ram_available_mb);
  const ramReserve = formatMb(system?.ram_reserve_mb || 1024);

  const vramTotal = formatMb(system?.vram_total_mb);
  const vramUsed = formatMb(system?.vram_used_mb);
  const vramAvail = formatMb(system?.vram_available_mb);
  const vramReserve = formatMb(system?.vram_reserve_mb || 500);

  const hasGpu = Boolean(system?.vram_total_mb && system.vram_total_mb > 0);

  const ramPercent = system?.ram_total_mb > 0 
    ? Math.min(100, Math.round((system.ram_used_mb / system.ram_total_mb) * 100)) 
    : 0;

  const vramPercent = hasGpu && system.vram_total_mb > 0 
    ? Math.min(100, Math.round((system.vram_used_mb / system.vram_total_mb) * 100)) 
    : 0;

  return (
    <div className="sidebar-section">
      <div className="sidebar-section-title">
        System Resources
      </div>

      <div className="resources-card">
        {/* RAM Block */}
        <div className="resource-group">
          <div className="resource-header">
            <span className="resource-name">RAM</span>
            <span className="resource-bar-val">{ramPercent}%</span>
          </div>
          <div className="metric-bar">
            <div className="metric-fill" style={{ width: `${ramPercent}%`, backgroundColor: 'var(--primary)' }} />
          </div>

          <div className="resource-grid">
            <div className="res-grid-item">
              <span className="res-label">Total:</span>
              <span className="res-value">{ramTotal}</span>
            </div>
            <div className="res-grid-item">
              <span className="res-label">Used:</span>
              <span className="res-value">{ramUsed}</span>
            </div>
            <div className="res-grid-item">
              <span className="res-label">Available:</span>
              <span className="res-value highlight-avail">{ramAvail}</span>
            </div>
            <div className="res-grid-item">
              <span className="res-label">Safety Reserve:</span>
              <span className="res-value highlight-reserve">{ramReserve}</span>
            </div>
          </div>
        </div>

        {/* VRAM Block */}
        <div className="resource-group" style={{ marginTop: '10px' }}>
          <div className="resource-header">
            <span className="resource-name">VRAM</span>
            <span className="resource-bar-val">{hasGpu ? `${vramPercent}%` : 'N/A'}</span>
          </div>
          {hasGpu && (
            <div className="metric-bar">
              <div className="metric-fill" style={{ width: `${vramPercent}%`, backgroundColor: '#a855f7' }} />
            </div>
          )}
          <div className="resource-grid">
            <div className="res-grid-item">
              <span className="res-label">Total:</span>
              <span className="res-value">{hasGpu ? vramTotal : 'N/A (CPU)'}</span>
            </div>
            <div className="res-grid-item">
              <span className="res-label">Used:</span>
              <span className="res-value">{hasGpu ? vramUsed : '0 MB'}</span>
            </div>
            <div className="res-grid-item">
              <span className="res-label">Available:</span>
              <span className="res-value highlight-avail">{hasGpu ? vramAvail : 'N/A'}</span>
            </div>
            <div className="res-grid-item">
              <span className="res-label">Safety Reserve:</span>
              <span className="res-value highlight-reserve">{vramReserve}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemResources;

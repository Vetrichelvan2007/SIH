import { useState, useRef, useEffect } from 'react';
import { IconChevronDown, IconCheck, IconCode, IconMessage } from './Icons';

const ModelSelector = ({ 
  selectedTask, 
  onSelectTask, 
  models = [], 
  selectedModel, 
  disabled = false,
  multiModelMode = false,
  onToggleMultiModel
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      {/* Multi-Model Mode Toggle Switch */}
      <div 
        className={`multi-model-toggle-container ${multiModelMode ? 'active' : ''}`}
        title={multiModelMode ? "Multi-Model Mode ON: Routing active via Qwen2.5 1.5B Router" : "Multi-Model Mode OFF: Single-model mode active (0 overhead)"}
        onClick={() => !disabled && onToggleMultiModel && onToggleMultiModel(!multiModelMode)}
      >
        <span className="multi-model-label">Multi-Model Mode</span>
        <div className={`toggle-switch-track ${multiModelMode ? 'on' : 'off'}`}>
          <div className="toggle-switch-thumb" />
        </div>
        {multiModelMode ? (
          <span className="multi-model-badge active">Qwen2.5 1.5B Router</span>
        ) : (
          <span className="multi-model-badge inactive">OFF</span>
        )}
      </div>
      {/* Quick Task Switcher Buttons */}
      <div style={{ display: 'flex', background: 'var(--surface-secondary)', padding: '3px', borderRadius: '8px', border: '1px solid var(--border)', opacity: disabled ? 0.5 : 1, pointerEvents: disabled ? 'none' : 'auto' }}>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onSelectTask('coding')}
          style={{
            background: selectedTask === 'coding' ? 'var(--primary)' : 'transparent',
            color: selectedTask === 'coding' ? '#FFFFFF' : 'var(--text-secondary)',
            border: 'none',
            borderRadius: '6px',
            padding: '5px 12px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: disabled ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'all 0.15s ease'
          }}
        >
          <IconCode size={13} />
          <span>Coding</span>
        </button>

        <button
          type="button"
          disabled={disabled}
          onClick={() => onSelectTask('question')}
          style={{
            background: selectedTask === 'question' ? 'var(--primary)' : 'transparent',
            color: selectedTask === 'question' ? '#FFFFFF' : 'var(--text-secondary)',
            border: 'none',
            borderRadius: '6px',
            padding: '5px 12px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: disabled ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'all 0.15s ease'
          }}
        >
          <IconMessage size={13} />
          <span>Question / General</span>
        </button>
      </div>


      {/* Model Status Dropdown Trigger */}
      <div className="model-selector-wrapper" ref={dropdownRef} style={{ opacity: disabled ? 0.5 : 1, pointerEvents: disabled ? 'none' : 'auto' }}>
        <button 
          type="button" 
          disabled={disabled}
          className="model-selector-trigger" 
          onClick={() => !disabled && setIsOpen(!isOpen)}
          aria-haspopup="true"
          aria-expanded={isOpen}
        >
          <span className="model-pill-badge">{selectedModel?.id || 'qwen2.5-coder'}</span>
          <IconChevronDown size={14} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && !disabled && (
          <div className="model-dropdown-menu">
            <div className="dropdown-header">
              Available Local Models
            </div>
            {models.map((item) => {
              const isSelected = selectedTask === item.task;
              return (
                <div
                  key={item.id}
                  className={`model-option-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => {
                    onSelectTask(item.task);
                    setIsOpen(false);
                  }}
                >
                  <div className="option-top-row">
                    <span className="option-task-name">{item.type}</span>
                    <span 
                      style={{ 
                        fontSize: '10px', 
                        padding: '2px 6px', 
                        borderRadius: '4px',
                        fontWeight: 600,
                        backgroundColor: item.available ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                        color: item.available ? 'var(--accent-emerald)' : 'var(--accent-rose)'
                      }}
                    >
                      {item.status || (item.available ? 'Available' : 'Unavailable')}
                    </span>
                  </div>
                  <div className="option-model-id" style={{ marginTop: '2px' }}>
                    {item.name || item.id}
                  </div>
                  <div className="option-desc" style={{ marginTop: '4px' }}>
                    {item.description}
                  </div>
                  {isSelected && (
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                      <IconCheck size={14} style={{ color: 'var(--accent-cyan)' }} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default ModelSelector;

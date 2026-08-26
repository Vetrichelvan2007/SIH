import { useState, useRef, useEffect } from 'react';
import { MODEL_OPTIONS } from '../mock/mockData';
import { IconChevronDown, IconCheck } from './Icons';

const ModelSelector = ({ selectedModel, onSelectModel }) => {
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
    <div className="model-selector-wrapper" ref={dropdownRef}>
      <button 
        type="button" 
        className="model-selector-trigger" 
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="true"
        aria-expanded={isOpen}
      >
        <span style={{ color: 'var(--text-muted)', fontSize: '11.5px' }}>Task:</span>
        <span style={{ fontWeight: 600 }}>{selectedModel.task}</span>
        <span className="model-pill-badge">{selectedModel.model}</span>
        <IconChevronDown size={14} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="model-dropdown-menu">
          <div className="dropdown-header">
            Select Task & Local Model
          </div>
          {MODEL_OPTIONS.map((item) => {
            const isSelected = selectedModel.id === item.id;
            return (
              <div
                key={item.id}
                className={`model-option-card ${isSelected ? 'selected' : ''} ${item.disabled ? 'disabled' : ''}`}
                onClick={() => {
                  if (!item.disabled) {
                    onSelectModel(item);
                    setIsOpen(false);
                  }
                }}
              >
                <div className="option-top-row">
                  <span className="option-task-name">{item.task}</span>
                  {item.disabled ? (
                    <span className="option-badge-disabled">Coming Soon</span>
                  ) : (
                    <span className="option-model-id">{item.model}</span>
                  )}
                </div>
                <div className="option-desc">
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
  );
};

export default ModelSelector;

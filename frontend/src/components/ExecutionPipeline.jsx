import { useState } from 'react';
import { IconCheck, IconChevronDown } from './Icons';

const STAGE_ORDER = [
  'query_received',
  'backend_processing',
  'multi_model_routing',
  'resource_safety_check',
  'route_classified',
  'task_selected',
  'model_selected',
  'ollama_connecting',
  'ollama_processing',
  'receiving_response',
  'completed'
];

const DEFAULT_STEPS = [
  { id: 'query_received', label: 'Query received' },
  { id: 'backend_processing', label: 'Request sent to backend' },
  { id: 'task_selected', label: 'Task identified' },
  { id: 'model_selected', label: 'Model selected' },
  { id: 'ollama_connecting', label: 'Connecting to local Ollama' },
  { id: 'ollama_processing', label: 'Model processing locally' },
  { id: 'receiving_response', label: 'Receiving model response' },
  { id: 'completed', label: 'Response complete' }
];

const MULTI_MODEL_STEPS = [
  { id: 'query_received', label: 'Query received' },
  { id: 'backend_processing', label: 'Request sent to backend' },
  { id: 'multi_model_routing', label: 'Invoking Qwen2.5 1.5B Router' },
  { id: 'resource_safety_check', label: 'RAM & VRAM Safety Check (RAM >= 1GB, VRAM >= 500MB)' },
  { id: 'route_classified', label: 'Route Classified' },
  { id: 'model_selected', label: 'Route Model Selected' },
  { id: 'ollama_connecting', label: 'Connecting to local Ollama' },
  { id: 'ollama_processing', label: 'Model processing locally' },
  { id: 'receiving_response', label: 'Receiving model response' },
  { id: 'completed', label: 'Response complete' }
];

const ExecutionPipeline = ({ 
  currentStage, 
  completedStages = [], 
  taskLabel = 'Coding', 
  modelName = 'Qwen2.5-Coder', 
  metrics = null, 
  isComplete = false,
  error = null 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const isMultiModelRun = completedStages.includes('multi_model_routing') || currentStage === 'multi_model_routing' || currentStage === 'route_classified' || completedStages.includes('route_classified');
  const activeSteps = isMultiModelRun ? MULTI_MODEL_STEPS : DEFAULT_STEPS;

  // Helper to determine step status ('completed', 'active', 'pending', 'error')
  const getStepStatus = (stepId, index) => {
    if (error && (currentStage === stepId || completedStages.includes(stepId))) {
      return 'error';
    }
    if (completedStages.includes(stepId) || isComplete) {
      return 'completed';
    }
    if (currentStage === stepId) {
      return 'active';
    }
    const currentIdx = STAGE_ORDER.indexOf(currentStage);
    if (currentIdx !== -1 && index < currentIdx) {
      return 'completed';
    }
    return 'pending';
  };

  const getDynamicLabel = (stepId, baseLabel) => {
    if (stepId === 'task_selected') {
      return `Task identified: ${taskLabel}`;
    }
    if (stepId === 'model_selected') {
      return `Model selected: ${modelName}`;
    }
    if (stepId === 'ollama_processing') {
      return `${modelName} is processing locally...`;
    }
    return baseLabel;
  };

  const totalTimeText = metrics?.total_response_time 
    ? `${metrics.total_response_time}s` 
    : null;

  // Render collapsed summary bar when execution is complete
  if (isComplete && !isExpanded) {
    return (
      <div 
        className="pipeline-summary-bar"
        onClick={() => setIsExpanded(true)}
        title="Click to view execution details"
      >
        <div className="summary-badge-left">
          <span className="badge-icon-check"><IconCheck size={12} /></span>
          <span className="summary-title">Generated locally</span>
          <span className="summary-divider">•</span>
          <span className="summary-model">{modelName}</span>
        </div>

        <div className="summary-badge-right">
          {totalTimeText && (
            <span className="summary-time">Completed in {totalTimeText}</span>
          )}
          <IconChevronDown size={14} className="summary-expand-icon" />
        </div>
      </div>
    );
  }

  return (
    <div className={`pipeline-card ${isComplete ? 'completed-card' : ''}`}>
      <div className="pipeline-header" onClick={() => isComplete && setIsExpanded(false)}>
        <div className="pipeline-title-group">
          <span className="pipeline-bolt">⚡</span>
          <span className="pipeline-title">Local Execution Pipeline</span>
          {isComplete && <span className="pipeline-status-tag">Completed</span>}
        </div>
        {isComplete && (
          <div className="pipeline-collapse-trigger">
            <span>Collapse</span>
            <IconChevronDown size={14} className="rotate-180" />
          </div>
        )}
      </div>

      <div className="pipeline-steps-list">
        {activeSteps.map((step, index) => {
          const status = getStepStatus(step.id, index);
          const label = getDynamicLabel(step.id, step.label);

          return (
            <div key={step.id} className={`pipeline-step-item ${status}`}>
              <div className="step-indicator">
                {status === 'completed' && <span className="icon-completed">✓</span>}
                {status === 'active' && <span className="icon-active-dot">◉</span>}
                {status === 'pending' && <span className="icon-pending">○</span>}
                {status === 'error' && <span className="icon-error">✕</span>}
              </div>
              <span className="step-label">{label}</span>
            </div>
          );
        })}

        {error && (
          <div className="pipeline-error-box">
            <span className="error-icon">✕</span>
            <span className="error-text">{error}</span>
          </div>
        )}
      </div>

      {metrics && metrics.total_response_time && (
        <div className="pipeline-metrics-bar">
          <span className="metric-item">Total Response Time: <strong>{metrics.total_response_time}s</strong></span>
          {metrics.backend_time && <span className="metric-sub">Backend: {metrics.backend_time}s</span>}
          {metrics.model_time && <span className="metric-sub">Model Processing: {metrics.model_time}s</span>}
        </div>
      )}
    </div>
  );
};

export default ExecutionPipeline;

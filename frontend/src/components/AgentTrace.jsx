import { useState } from 'react';
import { IconCheck, IconChevronDown, IconSparkles, IconX } from './Icons';

// Human-friendly mapping for internal step actions/components
const HUMAN_LABELS = {
  conversation_state_resolution: 'Conversation State',
  attachment_reference_resolution: 'Attachment Resolved',
  input_type_detection: 'Input Type Detection',
  user_intent_classification: 'Intent Classified',
  direct_model_selection: 'Model Selected',
  final_response_generation: 'Response Generated',
  document_processing: 'Document Processing',
  vision_page_analysis: 'Vision Analysis',
  context_building: 'Context Window Built',
  query_received: 'Query Received'
};

function formatStepTitle(step) {
  if (!step) return 'Execution Step';
  if (step.action && HUMAN_LABELS[step.action]) {
    return HUMAN_LABELS[step.action];
  }
  if (step.component && HUMAN_LABELS[step.component]) {
    return HUMAN_LABELS[step.component];
  }
  // Convert snake_case or clean up string
  const raw = step.action || step.component || 'Step';
  return raw
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function formatStepSubtext(step) {
  if (!step) return '';
  if (step.output_summary && !step.output_summary.includes('---')) {
    return step.output_summary;
  }
  if (step.input_summary && !step.input_summary.includes('---')) {
    return step.input_summary;
  }
  if (step.model) return `Executed via ${step.model}`;
  return 'Completed successfully';
}

const StepDetailModal = ({ step, onClose }) => {
  if (!step) return null;
  const title = formatStepTitle(step);

  return (
    <div className="trace-modal-backdrop" onClick={onClose}>
      <div className="trace-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="trace-modal-header">
          <div className="trace-modal-title">
            <span className="step-type-tag">{step.type?.toUpperCase() || 'STEP'}</span>
            <h4>{title}</h4>
          </div>
          <button type="button" className="trace-modal-close" onClick={onClose}>
            <IconX size={16} />
          </button>
        </div>

        <div className="trace-modal-body">
          <div className="trace-detail-grid">
            <div className="trace-detail-item">
              <span className="detail-label">Action / Step:</span>
              <span className="detail-value highlight">{title}</span>
            </div>

            {step.model && (
              <div className="trace-detail-item">
                <span className="detail-label">AI Model:</span>
                <span className="detail-value model-tag">{step.model}</span>
              </div>
            )}

            <div className="trace-detail-item">
              <span className="detail-label">Status:</span>
              <span className={`detail-value status-${step.status}`}>
                {step.status === 'completed' ? '✓ Completed' : step.status === 'failed' ? '✕ Failed' : '◉ Active'}
              </span>
            </div>

            <div className="trace-detail-item">
              <span className="detail-label">Duration:</span>
              <span className="detail-value">{step.duration_ms ? `${(step.duration_ms / 1000).toFixed(2)}s` : '0.00s'}</span>
            </div>
          </div>

          <div className="trace-payload-section">
            <div className="payload-box">
              <span className="payload-box-title">Execution Context:</span>
              <p className="payload-text">{formatStepSubtext(step)}</p>
            </div>

            {(step.output_summary || step.error) && (
              <div className="payload-box">
                <span className="payload-box-title">Output Details:</span>
                <p className={`payload-text ${step.status === 'failed' ? 'error' : ''}`}>
                  {step.output_summary || (step.error ? `Error: ${step.error}` : 'No output summary')}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const AgentTrace = ({ trace }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedStep, setSelectedStep] = useState(null);

  if (!trace || !trace.steps || trace.steps.length === 0) {
    return null;
  }

  const steps = trace.steps;
  const contextSources = trace.context_sources || [];
  const finalGenerator = trace.final_generator || 'Phi-4 Mini';
  const totalMs = trace.timing_summary?.total_ms || 0;
  const totalTimeStr = totalMs ? `${(totalMs / 1000).toFixed(2)}s` : '';

  return (
    <div className="agent-trace-container">
      {/* Collapsed Bar Header */}
      <div 
        className={`agent-trace-header ${isExpanded ? 'expanded' : ''}`}
        onClick={() => setIsExpanded(!isExpanded)}
        title="Click to view transparent Agent Execution Trace"
      >
        <div className="trace-header-left">
          <span className="trace-gear-icon">⚙</span>
          <span className="trace-title">Agent Execution Trace</span>
          <span className="trace-steps-count">{steps.length} Steps</span>
          {totalTimeStr && (
            <span className="trace-total-time">• Completed in {totalTimeStr}</span>
          )}
        </div>

        <div className="trace-header-right">
          <IconChevronDown size={14} className={`trace-chevron ${isExpanded ? 'rotate-180' : ''}`} />
        </div>
      </div>

      {/* Expanded Trace Body */}
      {isExpanded && (
        <div className="agent-trace-body">
          {/* Horizontal Step Timeline Bar */}
          <div className="trace-horizontal-timeline">
            {steps.map((step, idx) => {
              const isFailed = step.status === 'failed';
              const title = formatStepTitle(step);
              const durationStr = step.duration_ms ? `${(step.duration_ms / 1000).toFixed(2)}s` : '0.00s';

              return (
                <div key={step.step_id || idx} className="timeline-node-item">
                  <div 
                    className={`timeline-node-card ${isFailed ? 'failed' : ''}`}
                    onClick={() => setSelectedStep(step)}
                    title="Click to inspect step details"
                  >
                    <div className="node-top-row">
                      <span className={`node-status-dot ${step.status}`}>
                        {isFailed ? '✕' : step.status === 'completed' ? '✓' : '●'}
                      </span>
                      <span className="node-title">{title}</span>
                    </div>
                    <span className="node-subtext">{step.model || formatStepSubtext(step)}</span>
                    <div className="node-footer-row">
                      <span className="node-duration">{durationStr}</span>
                      <span className="node-inspect-btn">Inspect →</span>
                    </div>
                  </div>
                  {idx < steps.length - 1 && <span className="timeline-connector">→</span>}
                </div>
              );
            })}
          </div>

          {/* Sources Used Pills Section */}
          {contextSources.length > 0 && (
            <div className="trace-sources-section">
              <span className="sources-label">Sources Used</span>
              <div className="sources-pills-list">
                {contextSources.map((src, i) => (
                  <span key={i} className="source-pill">
                    [{src.source || src.type}]
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Final Generator Footer Bar */}
          <div className="trace-footer-bar">
            <span className="trace-footer-gen-label">Final Generator: <strong>{finalGenerator}</strong></span>
            {totalTimeStr && <span className="trace-footer-time">Completed in {totalTimeStr}</span>}
          </div>
        </div>
      )}

      {/* Interactive Step Inspector Modal */}
      {selectedStep && (
        <StepDetailModal 
          step={selectedStep} 
          onClose={() => setSelectedStep(null)} 
        />
      )}
    </div>
  );
};

export default AgentTrace;

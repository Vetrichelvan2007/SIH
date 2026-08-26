// Task and Model Specifications
export const MODEL_OPTIONS = [
  {
    id: 'general',
    task: 'Question / General',
    model: 'Phi-4-mini',
    badge: 'Ready',
    status: 'ready',
    disabled: false,
    description: 'Optimized for fast reasoning, Q&A, and general on-premise AI synthesis.',
    icon: 'message'
  },
  {
    id: 'coding',
    task: 'Coding',
    model: 'Qwen2.5-Coder',
    badge: 'Ready',
    status: 'ready',
    disabled: false,
    description: 'State-of-the-art coding, code generation, refactoring, and debugging.',
    icon: 'code'
  },
  {
    id: 'document',
    task: 'Document Analysis',
    model: 'Coming Soon / Placeholder',
    badge: 'Coming Soon',
    status: 'disabled',
    disabled: true,
    description: 'Enterprise OCR, PDF processing, and RAG document extraction.',
    icon: 'document'
  },
  {
    id: 'vision',
    task: 'Vision',
    model: 'Coming Soon / Placeholder',
    badge: 'Coming Soon',
    status: 'disabled',
    disabled: true,
    description: 'Multimodal image analysis, object detection, and visual inspection.',
    icon: 'vision'
  }
];

// Initial Chat Sessions for demonstration
export const INITIAL_SESSIONS = [
  {
    id: 'session-1',
    title: 'Sovereign On-Premise Workspace',
    task: 'Coding',
    model: 'Qwen2.5-Coder',
    updatedAt: 'Just now',
    messages: []
  }
];

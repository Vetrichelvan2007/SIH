// Task and Model Specifications
export const MODEL_OPTIONS = [
  {
    id: 'coding',
    task: 'Coding',
    taskKey: 'coding',
    model: 'qwen2.5-coder',
    name: 'Qwen2.5-Coder',
    badge: 'Coding Model',
    status: 'Available',
    available: true,
    disabled: false,
    description: 'State-of-the-art coding, code generation, refactoring, and debugging.',
    icon: 'code'
  },
  {
    id: 'question',
    task: 'Question / General',
    taskKey: 'question',
    model: 'phi4-mini',
    name: 'Phi-4 Mini',
    badge: 'General QA',
    status: 'Available',
    available: true,
    disabled: false,
    description: 'Optimized for fast reasoning, Q&A, and general on-premise AI synthesis.',
    icon: 'message'
  }
];

// Initial Chat Sessions for demonstration
export const INITIAL_SESSIONS = [
  {
    id: 'session-1',
    title: 'Sovereign On-Premise Workspace',
    task: 'Coding',
    model: 'qwen2.5-coder',
    updatedAt: 'Just now',
    messages: []
  }
];

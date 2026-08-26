import { IconShield, IconCode, IconSparkles, IconDocument, IconMessage } from './Icons';

const WelcomeScreen = ({ onSelectPrompt }) => {
  const suggestions = [
    {
      icon: <IconCode size={18} />,
      title: 'Generate FastAPI Code',
      prompt: 'Write an asynchronous FastAPI endpoint with JWT authentication and Pydantic validation.',
      taskTarget: 'coding'
    },
    {
      icon: <IconSparkles size={18} />,
      title: 'Phi-4 Architecture Overview',
      prompt: 'Explain the core architectural differences and reasoning optimizations in Phi-4-mini.',
      taskTarget: 'general'
    },
    {
      icon: <IconMessage size={18} />,
      title: 'On-Premise Deployment Strategy',
      prompt: 'What hardware specs are recommended for hosting local quantized 7B models on air-gapped servers?',
      taskTarget: 'general'
    },
    {
      icon: <IconDocument size={18} />,
      title: 'RAG Pipeline Design',
      prompt: 'How can I build a localized vector store indexing pipeline using Python and FAISS?',
      taskTarget: 'coding'
    }
  ];

  return (
    <div className="welcome-container animate-fade-in">
      <div className="welcome-logo">
        <IconShield size={38} />
      </div>

      <h1 className="welcome-title">Sovereign On-Premise AI Workbench</h1>
      <p className="welcome-subtitle">
        Secure, enterprise-grade agentic intelligence running 100% on local hardware. No cloud egress, zero data logging, air-gapped performance.
      </p>

      <div className="suggestion-grid">
        {suggestions.map((item, index) => (
          <div 
            key={index} 
            className="suggestion-card"
            onClick={() => onSelectPrompt(item.prompt, item.taskTarget)}
          >
            <div className="card-icon-wrap">
              {item.icon}
            </div>
            <div className="card-title">{item.title}</div>
            <div className="card-prompt">{item.prompt}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default WelcomeScreen;

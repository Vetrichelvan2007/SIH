import { useState } from 'react';
import { MODEL_OPTIONS, INITIAL_SESSIONS } from './mock/mockData';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import './App.css';

function App() {
  const [sessions, setSessions] = useState(INITIAL_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState(INITIAL_SESSIONS[0]?.id || 'session-1');
  const [selectedModel, setSelectedModel] = useState(MODEL_OPTIONS[1]); // Default: Coding -> Qwen2.5-Coder
  const [modelStatus, setModelStatus] = useState('ready'); // 'ready' | 'loading' | 'generating'
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Get active session object
  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0];

  // Handler to create a brand new chat session
  const handleNewChat = async () => {
    const newId = `session-${Date.now()}`;
    const newSession = {
      id: newId,
      title: 'New Conversation',
      task: selectedModel.task,
      model: selectedModel.model,
      updatedAt: 'Just now',
      messages: []
    };
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newId);

    try {
      await fetch("http://localhost:8000/new-chat", { method: "POST" });
    } catch (err) {
      console.warn("Could not reset backend conversation context:", err);
    }
  };

  // Handler to switch active session
  const handleSelectSession = (id) => {
    setActiveSessionId(id);
    const targetSession = sessions.find((s) => s.id === id);
    if (targetSession) {
      // Sync model if session matched a specific model
      const matched = MODEL_OPTIONS.find((m) => m.model === targetSession.model);
      if (matched && !matched.disabled) {
        setSelectedModel(matched);
      }
    }
  };

  // Handler to delete a session
  const handleDeleteSession = (id) => {
    const remaining = sessions.filter((s) => s.id !== id);
    setSessions(remaining);
    if (activeSessionId === id && remaining.length > 0) {
      setActiveSessionId(remaining[0].id);
    }
  };

  // Handler to switch model/task selection
  const handleSelectModel = (modelOption) => {
    if (modelOption.disabled) return;
    setSelectedModel(modelOption);
    
    // Update active session metadata if empty
    if (activeSession && activeSession.messages.length === 0) {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId
            ? { ...s, task: modelOption.task, model: modelOption.model }
            : s
        )
      );
    }
  };

  // Handler to send a message via real FastAPI backend (http://localhost:8000/chat)
  const handleSendMessage = async (userText) => {
    if (!userText.trim() || modelStatus !== 'ready') return;

    const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: userText,
      timestamp: timeString
    };

    // Auto-title empty sessions
    let updatedTitle = activeSession?.title;
    if (!activeSession || activeSession.title === 'New Conversation' || activeSession.messages.length === 0) {
      updatedTitle = userText.length > 32 ? `${userText.slice(0, 32)}...` : userText;
    }

    // 1. Append user message to active session
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === activeSessionId) {
          return {
            ...s,
            title: updatedTitle,
            messages: [...s.messages, userMessage]
          };
        }
        return s;
      })
    );

    // 2. Set Status -> Loading
    setModelStatus('loading');

    try {
      // 3. Send real POST request to FastAPI backend connected to local Ollama Qwen2.5-Coder
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          query: userText,
          task: "coding"
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Backend returned HTTP status ${response.status}`);
      }

      const data = await response.json();
      const aiResponseText = data.response;
      const responseModel = data.model || 'qwen2.5-coder';

      const aiMessage = {
        id: `ai-${Date.now()}`,
        sender: 'ai',
        model: responseModel,
        task: 'Coding',
        text: aiResponseText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === activeSessionId) {
            return {
              ...s,
              messages: [...s.messages, aiMessage]
            };
          }
          return s;
        })
      );
    } catch (err) {
      console.error("Error communicating with FastAPI backend:", err);
      const errorMessage = {
        id: `err-${Date.now()}`,
        sender: 'ai',
        model: 'qwen2.5-coder',
        task: 'Error',
        text: `⚠️ **FastAPI Backend Error**\n\nCould not fetch response from \`http://localhost:8000/chat\`.\n\n**Details**: ${err.message || 'Make sure the FastAPI server is running via `uvicorn main:app --reload --port 8000` and Ollama is active.'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === activeSessionId) {
            return {
              ...s,
              messages: [...s.messages, errorMessage]
            };
          }
          return s;
        })
      );
    } finally {
      setModelStatus('ready');
    }
  };

  // Quick suggestion card click handler
  const handleSelectPrompt = (promptText, taskTarget) => {
    if (taskTarget === 'coding') {
      setSelectedModel(MODEL_OPTIONS[1]);
    } else if (taskTarget === 'general') {
      setSelectedModel(MODEL_OPTIONS[0]);
    }
    setTimeout(() => {
      handleSendMessage(promptText);
    }, 50);
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Workspace */}
      <ChatWindow
        activeSession={activeSession}
        selectedModel={selectedModel}
        onSelectModel={handleSelectModel}
        modelStatus={modelStatus}
        onSendMessage={handleSendMessage}
        onSelectPrompt={handleSelectPrompt}
        onToggleSidebar={() => setIsMobileSidebarOpen((prev) => !prev)}
      />
    </div>
  );
}

export default App;

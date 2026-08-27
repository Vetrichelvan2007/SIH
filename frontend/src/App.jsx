import { useState, useEffect } from 'react';
import { MODEL_OPTIONS, INITIAL_SESSIONS } from './mock/mockData';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import './App.css';

function App() {
  const [sessions, setSessions] = useState(INITIAL_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState(INITIAL_SESSIONS[0]?.id || 'session-1');
  const [models, setModels] = useState(MODEL_OPTIONS);
  const [selectedTask, setSelectedTask] = useState('coding'); // 'coding' | 'question'
  const [modelStatus, setModelStatus] = useState('ready'); // 'ready' | 'loading' | 'generating'
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Multi-Model Mode State (Default: OFF)
  const [multiModelMode, setMultiModelMode] = useState(false);

  // Real-time System Telemetry & Model Switching States
  const [systemStatus, setSystemStatus] = useState(null);
  const [modelsStatus, setModelsStatus] = useState(null);
  const [isSwitchingModel, setIsSwitchingModel] = useState(false);
  const [modelSwitchLogs, setModelSwitchLogs] = useState([]);
  const [targetSwitchModelName, setTargetSwitchModelName] = useState('');

  // Dedicated Request Execution State (Cleared at beginning of EVERY request)
  const [currentExecution, setCurrentExecution] = useState({
    requestId: null,
    route: null,
    selectedModel: null,
    status: null
  });

  // Helper to fetch live summary of all chats from backend /api/chats
  const fetchChatsList = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/chats");
      if (res.ok) {
        const data = await res.json();
        if (data.chats && Array.isArray(data.chats)) {
          return data.chats.map(c => ({
            id: c.chat_id,
            title: c.title || 'New Conversation',
            updatedAt: c.updated_at ? new Date(c.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Just now',
            messages: []
          }));
        }
      }
    } catch (err) {
      console.warn("Could not fetch chats from backend:", err);
    }
    return [];
  };

  // Helper to load full conversation detail for a given chat_id
  const loadChatDetails = async (chatId) => {
    if (!chatId) return;
    try {
      const res = await fetch(`http://localhost:8000/api/chats/${chatId}`);
      if (res.ok) {
        const data = await res.json();
        const formattedMessages = (data.messages || []).map(m => {
          const isUser = m.role === 'user';
          const timeStr = m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Just now';
          return {
            id: m.message_id,
            sender: isUser ? 'user' : 'ai',
            text: m.content,
            timestamp: timeStr,
            model: m.model_used || 'phi4-mini',
            modelName: m.model_used || 'Phi-4 Mini',
            route: m.route,
            metrics: m.response_time ? { total_response_time: m.response_time } : null,
            pipeline: !isUser ? {
              stage: 'completed',
              completedStages: ['query_received', 'backend_processing', 'model_selected', 'completed'],
              taskLabel: m.route ? `Route [${m.route}]` : 'General',
              modelName: m.model_used || 'Phi-4 Mini',
              isComplete: true,
              metrics: m.response_time ? { total_response_time: m.response_time } : null,
              error: null
            } : null
          };
        });

        setSessions(prev => {
          const exists = prev.some(s => s.id === chatId);
          if (exists) {
            return prev.map(s => s.id === chatId ? { ...s, title: data.title, messages: formattedMessages } : s);
          } else {
            return [{ id: data.chat_id, title: data.title, updatedAt: data.updated_at, messages: formattedMessages }, ...prev];
          }
        });
      }
    } catch (err) {
      console.warn(`Could not load details for chat ${chatId}:`, err);
    }
  };

  // Refresh sidebar chat list while preserving currently loaded active messages
  const refreshChatList = async () => {
    const list = await fetchChatsList();
    if (list.length > 0) {
      setSessions(prev => {
        return list.map(item => {
          const existing = prev.find(p => p.id === item.id);
          return existing ? { ...item, messages: existing.messages } : item;
        });
      });
    }
  };

  // Helper to fetch live detailed model status from /api/models/status
  const fetchModelsStatus = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/models/status");
      if (res.ok) {
        const data = await res.json();
        setModelsStatus(data);
      }
    } catch (err) {
      console.warn("Could not fetch models status from backend:", err);
    }
  };

  // 1. Initial Mount: Load model availability, multi-model status, and persistent SQLite chat history
  useEffect(() => {
    const fetchAvailableModels = async () => {
      try {
        const response = await fetch("http://localhost:8000/models");
        if (response.ok) {
          const data = await response.json();
          if (data.models && Array.isArray(data.models)) {
            setModels(data.models);
          }
        }
      } catch (err) {
        console.warn("Could not fetch local model availability from FastAPI backend:", err);
      }
    };

    const fetchMultiModelStatus = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/multi-model/status");
        if (res.ok) {
          const data = await res.json();
          setMultiModelMode(Boolean(data.multi_model_mode));
        }
      } catch (err) {
        console.warn("Could not fetch Multi-Model Mode status:", err);
      }
    };

    const initChatHistory = async () => {
      const chatList = await fetchChatsList();
      if (chatList.length > 0) {
        setSessions(chatList);
        const savedActiveId = localStorage.getItem('active_chat_id');
        const targetId = (savedActiveId && chatList.some(c => c.id === savedActiveId))
          ? savedActiveId
          : chatList[0].id;

        setActiveSessionId(targetId);
        loadChatDetails(targetId);
      } else {
        const freshId = `session-${Date.now()}`;
        const freshSession = {
          id: freshId,
          title: 'New Conversation',
          messages: []
        };
        setSessions([freshSession]);
        setActiveSessionId(freshId);
      }
    };

    fetchAvailableModels();
    fetchMultiModelStatus();
    fetchModelsStatus();
    initChatHistory();
  }, []);

  // Handler to toggle Multi-Model Mode ON/OFF
  const handleToggleMultiModel = async (enabled) => {
    const targetState = Boolean(enabled);
    setMultiModelMode(targetState);
    try {
      await fetch("http://localhost:8000/api/multi-model/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: targetState })
      });
      fetchModelsStatus();
    } catch (err) {
      console.error("Failed to toggle Multi-Model Mode on backend:", err);
    }
  };

  // 2. Poll live real-time system status every 2 seconds with clean useEffect interval cleanup
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/system/status");
        if (res.ok) {
          const data = await res.json();
          setSystemStatus(data);
        }
      } catch (err) {
        console.warn("System telemetry poll offline:", err);
        setSystemStatus((prev) => (prev ? { ...prev, ollama: { status: 'offline', loaded_models: [] } } : null));
      }
      fetchModelsStatus();
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  // Compute selected model object based on current selectedTask
  const selectedModel = models.find((m) => m.task === selectedTask) || models[0];

  // Get active session object
  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0];

  // Real Model Lifecycle Transition Handler (POST /api/models/switch)
  const handleSelectTask = async (taskKey) => {
    if (isSwitchingModel || modelStatus !== 'ready') return;

    const targetModelId = taskKey === 'coding' ? 'qwen2.5-coder' : 'phi4-mini';
    const targetModelDisplayName = taskKey === 'coding' ? 'Qwen2.5-Coder' : 'Phi-4 Mini';

    setTargetSwitchModelName(targetModelDisplayName);
    setIsSwitchingModel(true);
    setModelSwitchLogs([
      { status: 'checking_current_model', message: `Checking current VRAM allocation for ${targetModelDisplayName}...` }
    ]);

    try {
      const response = await fetch("http://localhost:8000/api/models/switch", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          model: targetModelId
        })
      });

      if (!response.ok) {
        throw new Error(`Backend returned HTTP status ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;

          const jsonString = trimmed.replace(/^data:\s*/, "");
          if (!jsonString) continue;

          try {
            const event = JSON.parse(jsonString);
            if (event.type === 'model_switch') {
              setModelSwitchLogs((prev) => [...prev, event]);
            }
          } catch (err) {
            console.warn("Failed to parse model switch SSE JSON line:", err);
          }
        }
      }
    } catch (err) {
      console.error("Error switching models:", err);
      setModelSwitchLogs((prev) => [
        ...prev,
        { status: 'error', message: `✕ Transition failed: ${err.message}` }
      ]);
    } finally {
      setSelectedTask(taskKey);
      setTimeout(() => {
        setIsSwitchingModel(false);
      }, 1000);
    }
  };

  // Handler to create a brand new chat session
  const handleNewChat = () => {
    const newId = `session-${Date.now()}`;
    const newSession = {
      id: newId,
      title: 'New Conversation',
      messages: []
    };
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newId);
    localStorage.setItem('active_chat_id', newId);
  };

  // Handler to switch active session
  const handleSelectSession = (id) => {
    setActiveSessionId(id);
    localStorage.setItem('active_chat_id', id);
    loadChatDetails(id);
  };

  // Handler to delete a session
  const handleDeleteSession = async (id) => {
    try {
      await fetch(`http://localhost:8000/api/chats/${id}`, { method: "DELETE" });
    } catch (err) {
      console.warn(`Failed to delete chat ${id} on backend:`, err);
    }

    const remaining = sessions.filter((s) => s.id !== id);
    setSessions(remaining);

    if (activeSessionId === id) {
      if (remaining.length > 0) {
        const nextId = remaining[0].id;
        setActiveSessionId(nextId);
        localStorage.setItem('active_chat_id', nextId);
        loadChatDetails(nextId);
      } else {
        handleNewChat();
      }
    }
  };

  // Handler to rename a session title
  const handleRenameSession = async (id, newTitle) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, title: newTitle } : s))
    );
    try {
      await fetch(`http://localhost:8000/api/chats/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle })
      });
    } catch (err) {
      console.warn(`Failed to rename chat ${id} on backend:`, err);
    }
  };

  // Handler to send a chat message and consume SSE stream
  const handleSendMessage = async (userText) => {
    if (!userText.trim() || modelStatus !== 'ready' || isSwitchingModel) return;

    const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMsgId = `user-${Date.now()}`;
    const aiMsgId = `ai-${Date.now()}`;
    const reqId = `req-${Date.now()}`;
    const currentChatId = activeSessionId;

    // Reset request-specific execution state at start of EVERY request
    setCurrentExecution({
      requestId: reqId,
      route: null,
      selectedModel: multiModelMode ? null : (selectedModel?.name || 'Phi-4 Mini'),
      status: 'query_received'
    });

    const userMessage = {
      id: userMsgId,
      sender: 'user',
      text: userText,
      timestamp: timeString
    };

    const taskLabel = selectedTask === 'coding' ? 'Coding' : 'Question / General';
    const initialModelDisplayName = multiModelMode ? 'Selecting Model...' : (selectedModel?.name || (selectedTask === 'coding' ? 'Qwen2.5-Coder' : 'Phi-4 Mini'));
    const initialModelId = selectedModel?.id || (selectedTask === 'coding' ? 'qwen2.5-coder' : 'phi4-mini');

    // Create initial streaming AI message with live pipeline state
    const initialAiMessage = {
      id: aiMsgId,
      sender: 'ai',
      model: initialModelId,
      modelName: initialModelDisplayName,
      task: taskLabel,
      text: '',
      pipeline: {
        stage: 'query_received',
        completedStages: ['query_received'],
        taskLabel: taskLabel,
        modelName: initialModelDisplayName,
        isComplete: false,
        metrics: null,
        error: null
      },
      metrics: null,
      timestamp: timeString
    };

    // Auto-title empty sessions (limit ~35 chars)
    let updatedTitle = activeSession?.title;
    if (!activeSession || activeSession.title === 'New Conversation' || !activeSession.messages || activeSession.messages.length === 0) {
      const cleanPrompt = userText.trim();
      updatedTitle = cleanPrompt.length > 35 ? `${cleanPrompt.slice(0, 35).trim()}...` : cleanPrompt;
    }

    // 1. Append user & AI placeholder message to active session
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === currentChatId) {
          return {
            ...s,
            title: updatedTitle,
            messages: [...(s.messages || []), userMessage, initialAiMessage]
          };
        }
        return s;
      })
    );

    // 2. Set Status -> Generating
    setModelStatus('generating');

    const startTime = performance.now();

    try {
      // 3. Initiate SSE connection to FastAPI backend with chat_id
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: userText,
          task: selectedTask,
          multi_model_mode: multiModelMode,
          chat_id: currentChatId
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Backend returned HTTP status ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;

          const jsonString = trimmed.replace(/^data:\s*/, "");
          if (!jsonString) continue;

          try {
            const event = JSON.parse(jsonString);

            // Handle SSE Event Types
            if (event.type === 'status') {
              if (event.route) {
                setCurrentExecution((prev) => ({ ...prev, route: event.route }));
              }
              if (event.model_name || event.model) {
                const newModelName = event.model_name || event.model;
                setCurrentExecution((prev) => ({ ...prev, selectedModel: newModelName, status: event.stage }));
              }

              setSessions((prev) =>
                prev.map((s) => {
                  if (s.id === currentChatId) {
                    return {
                      ...s,
                      messages: s.messages.map((m) => {
                        if (m.id === aiMsgId && m.pipeline) {
                          const updatedCompleted = Array.from(
                            new Set([...m.pipeline.completedStages, event.stage])
                          );
                          const updatedModelName = event.model_name || m.modelName;
                          const updatedModelId = event.model || m.model;
                          return {
                            ...m,
                            model: updatedModelId,
                            modelName: updatedModelName,
                            pipeline: {
                              ...m.pipeline,
                              stage: event.stage,
                              completedStages: updatedCompleted,
                              taskLabel: event.task_label || m.pipeline.taskLabel,
                              modelName: updatedModelName
                            }
                          };
                        }
                        return m;
                      })
                    };
                  }
                  return s;
                })
              );
            } else if (event.type === 'token') {
              setSessions((prev) =>
                prev.map((s) => {
                  if (s.id === currentChatId) {
                    return {
                      ...s,
                      messages: s.messages.map((m) => {
                        if (m.id === aiMsgId) {
                          return {
                            ...m,
                            text: m.text + event.content
                          };
                        }
                        return m;
                      })
                    };
                  }
                  return s;
                })
              );
            } else if (event.type === 'complete') {
              const endTime = performance.now();
              const calcTime = parseFloat(((endTime - startTime) / 1000).toFixed(2));
              const finalMetrics = event.metrics || { total_response_time: calcTime };
              const finalModelName = event.model_name || event.model;
              const finalModelId = event.model || event.model_name;

              if (finalModelName) {
                setCurrentExecution((prev) => ({ ...prev, selectedModel: finalModelName, status: 'completed' }));
              }

              setSessions((prev) =>
                prev.map((s) => {
                  if (s.id === currentChatId) {
                    return {
                      ...s,
                      messages: s.messages.map((m) => {
                        if (m.id === aiMsgId) {
                          const newModelName = finalModelName || m.modelName;
                          const newModelId = finalModelId || m.model;
                          return {
                            ...m,
                            model: newModelId,
                            modelName: newModelName,
                            metrics: finalMetrics,
                            pipeline: {
                              ...m.pipeline,
                              stage: 'completed',
                              modelName: newModelName,
                              isComplete: true,
                              metrics: finalMetrics
                            }
                          };
                        }
                        return m;
                      })
                    };
                  }
                  return s;
                })
              );

              // Refresh chat history list to update timestamps and move active chat to top
              refreshChatList();
            } else if (event.type === 'error') {
              setSessions((prev) =>
                prev.map((s) => {
                  if (s.id === currentChatId) {
                    return {
                      ...s,
                      messages: s.messages.map((m) => {
                        if (m.id === aiMsgId && m.pipeline) {
                          return {
                            ...m,
                            pipeline: {
                              ...m.pipeline,
                              error: event.message
                            }
                          };
                        }
                        return m;
                      })
                    };
                  }
                  return s;
                })
              );
            }
          } catch (err) {
            console.warn("Failed to parse SSE JSON line:", err);
          }
        }
      }
    } catch (err) {
      console.error("Error consuming SSE stream:", err);
      const endTime = performance.now();
      const errTime = parseFloat(((endTime - startTime) / 1000).toFixed(2));

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === currentChatId) {
            return {
              ...s,
              messages: s.messages.map((m) => {
                if (m.id === aiMsgId) {
                  return {
                    ...m,
                    text: m.text || `⚠️ **Execution Error**\n\n${err.message || 'Could not connect to FastAPI server.'}`,
                    pipeline: {
                      ...m.pipeline,
                      error: err.message || 'Connection failed'
                    },
                    metrics: { total_response_time: errTime }
                  };
                }
                return m;
              })
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
    const targetTask = taskTarget === 'coding' ? 'coding' : 'question';
    handleSelectTask(targetTask);
    setTimeout(() => {
      handleSendMessage(promptText);
    }, 1500);
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
        onRenameSession={handleRenameSession}
        models={models}
        selectedTask={selectedTask}
        onSelectTask={handleSelectTask}
        systemStatus={systemStatus}
        modelsStatus={modelsStatus}
        isSwitchingModel={isSwitchingModel}
        targetSwitchModelName={targetSwitchModelName}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
        multiModelMode={multiModelMode}
        onToggleMultiModel={handleToggleMultiModel}
      />

      {/* Main Workspace */}
      <ChatWindow
        activeSession={activeSession}
        selectedTask={selectedTask}
        onSelectTask={handleSelectTask}
        models={models}
        selectedModel={selectedModel}
        modelStatus={modelStatus}
        onSendMessage={handleSendMessage}
        onSelectPrompt={handleSelectPrompt}
        onToggleSidebar={() => setIsMobileSidebarOpen((prev) => !prev)}
        isSwitchingModel={isSwitchingModel}
        modelSwitchLogs={modelSwitchLogs}
        targetSwitchModelName={targetSwitchModelName}
        multiModelMode={multiModelMode}
        onToggleMultiModel={handleToggleMultiModel}
        currentExecution={currentExecution}
      />
    </div>
  );
}

export default App;

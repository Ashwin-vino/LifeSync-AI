import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, Trash2, Bot, User, CornerDownLeft } from 'lucide-react';
import { api, ChatMessage } from '../api/client';
import { WorkspaceType } from './Sidebar';

interface UnifiedChatProps {
  workspace: WorkspaceType;
  title?: string;
  subtitle?: string;
  suggestedPrompts?: string[];
}

export const UnifiedChat: React.FC<UnifiedChatProps> = ({
  workspace,
  title = 'LifeSync AI Intelligence',
  subtitle = 'Grounded with FalkorDB persistent memory & Supabase biometrics',
  suggestedPrompts = [
    "Analyze today's total recovery score and suggest training volume.",
    "How does my protein intake today align with lean muscle progression?",
    "Plan a 45-minute strength session targeting chest and triceps."
  ]
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const loadHistory = async () => {
    try {
      const history = await api.getChatHistory(workspace);
      setMessages(history);
    } catch (e) {
      console.error('Failed to load chat history:', e);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [workspace]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = async (messageText?: string) => {
    const textToSend = messageText || input;
    if (!textToSend.trim() || loading) return;

    const userMsg: ChatMessage = {
      role: 'user',
      content: textToSend,
      workspace: workspace,
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!messageText) setInput('');
    setLoading(true);

    try {
      const historyPayload = messages.slice(-6).map(m => ({
        role: m.role,
        content: m.content
      }));

      const res = await api.sendMessage({
        message: textToSend,
        workspace,
        history: historyPayload
      });

      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: res.reply,
        workspace: workspace,
        created_at: new Date().toISOString(),
        metadata: { model: res.model }
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${err.message || 'Unable to connect to Gemini'}`,
          workspace: workspace,
          created_at: new Date().toISOString()
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearHistory = async () => {
    try {
      await api.clearChatHistory(workspace);
      setMessages([]);
    } catch (err) {
      console.error('Clear failed:', err);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#111111] border border-[#222222] rounded overflow-hidden">
      {/* Chat Header */}
      <div className="px-4 py-3 border-b border-[#222222] flex items-center justify-between bg-[#141414]">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#C0C0C0]" />
          <div>
            <h3 className="text-xs font-semibold text-white tracking-wide">{title}</h3>
            <p className="text-[10px] text-[#737373]">{subtitle}</p>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            onClick={handleClearHistory}
            className="flex items-center gap-1 px-2 py-1 text-[11px] text-[#737373] hover:text-[#D4D4D4] rounded hover:bg-[#1E1E1E] transition-colors"
            title="Clear workspace conversation"
          >
            <Trash2 className="w-3 h-3" />
            <span className="hidden sm:inline">Clear</span>
          </button>
        )}
      </div>

      {/* Message List */}
      <div ref={scrollRef} className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
            <div className="w-10 h-10 rounded-full bg-[#1A1A1A] border border-[#2B2B2B] flex items-center justify-center">
              <Bot className="w-5 h-5 text-[#9E9E9E]" />
            </div>
            <div className="max-w-md space-y-1">
              <p className="text-xs font-medium text-white">How can LifeSync assist you today?</p>
              <p className="text-[11px] text-[#737373]">
                Your workouts, meals, recovery biometrics, and FalkorDB knowledge graph are loaded into context.
              </p>
            </div>

            {/* Suggested Prompts */}
            <div className="w-full max-w-lg space-y-2 pt-2">
              <span className="text-[10px] uppercase tracking-wider text-[#555555] font-semibold">
                Suggested Prompts
              </span>
              <div className="grid gap-2">
                {suggestedPrompts.map((p, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(p)}
                    className="w-full text-left p-2.5 rounded bg-[#161616] hover:bg-[#1C1C1C] border border-[#262626] hover:border-[#383838] text-[11px] text-[#BBBBBB] hover:text-white transition-colors"
                  >
                    "{p}"
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((m, idx) => {
            const isUser = m.role === 'user';
            return (
              <div
                key={idx}
                className={`flex gap-3 text-xs leading-relaxed ${
                  isUser ? 'justify-end' : 'justify-start'
                }`}
              >
                {!isUser && (
                  <div className="w-6 h-6 rounded bg-[#1E1E1E] border border-[#333333] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Bot className="w-3.5 h-3.5 text-[#CCCCCC]" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded p-3 text-xs ${
                    isUser
                      ? 'bg-[#1C1C1C] text-white border border-[#333333]'
                      : 'bg-[#141414] text-[#E0E0E0] border border-[#242424]'
                  }`}
                >
                  <div className="whitespace-pre-wrap font-sans">{m.content}</div>
                  <div className="mt-1 text-[9px] text-[#666666] flex items-center justify-end gap-1">
                    {m.metadata?.model && <span>{m.metadata.model}</span>}
                  </div>
                </div>
                {isUser && (
                  <div className="w-6 h-6 rounded bg-[#2A2A2A] border border-[#404040] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <User className="w-3.5 h-3.5 text-white" />
                  </div>
                )}
              </div>
            );
          })
        )}

        {loading && (
          <div className="flex gap-3 text-xs">
            <div className="w-6 h-6 rounded bg-[#1E1E1E] border border-[#333333] flex items-center justify-center flex-shrink-0">
              <Bot className="w-3.5 h-3.5 text-[#CCCCCC]" />
            </div>
            <div className="bg-[#141414] border border-[#242424] rounded px-3 py-2 text-xs text-[#888888] flex items-center gap-2">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#666666] animate-pulse" />
                <span className="w-1.5 h-1.5 rounded-full bg-[#666666] animate-pulse delay-150" />
                <span className="w-1.5 h-1.5 rounded-full bg-[#666666] animate-pulse delay-300" />
              </div>
              <span className="text-[11px] text-[#777777]">Synthesizing live telemetry...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="p-3 border-t border-[#222222] bg-[#141414]">
        <div className="relative flex items-center">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask LifeSync AI (${workspace} intelligence)...`}
            rows={1}
            className="w-full pl-3 pr-10 py-2.5 text-xs bg-[#1A1A1A] border border-[#2F2F2F] focus:border-[#4B4B4B] rounded text-white resize-none placeholder:text-[#666666]"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="absolute right-2 p-1.5 rounded bg-[#EDEDED] text-[#0A0A0A] hover:bg-white disabled:opacity-30 disabled:hover:bg-[#EDEDED] transition-colors"
          >
            <CornerDownLeft className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import {
  Brain,
  X,
  Trash2,
  Edit2,
  Check,
  Plus,
  RefreshCw,
  Server,
  Sparkles
} from 'lucide-react';
import { api, MemoryFact } from '../api/client';

interface MemoryInspectorModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MemoryInspectorModal: React.FC<MemoryInspectorModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [memories, setMemories] = useState<MemoryFact[]>([]);
  const [graphStats, setGraphStats] = useState<{ connected: boolean; nodes: number; edges: number } | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  
  // New Fact Form
  const [showAddForm, setShowAddForm] = useState(false);
  const [newType, setNewType] = useState('goal');
  const [newContent, setNewContent] = useState('');
  const [savingNew, setSavingNew] = useState(false);

  const loadData = async () => {
    try {
      const [facts, stats] = await Promise.allSettled([
        api.getMemories('active'),
        api.getGraphStats()
      ]);
      if (facts.status === 'fulfilled') setMemories(facts.value);
      if (stats.status === 'fulfilled') setGraphStats(stats.value);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleStartEdit = (m: MemoryFact) => {
    setEditingId(m.id);
    setEditText(m.content);
  };

  const handleSaveEdit = async (id: string) => {
    if (!editText.trim()) return;
    try {
      await api.correctMemory(id, editText);
      setEditingId(null);
      await loadData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteMemory(id);
      await loadData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddFact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;
    setSavingNew(true);
    try {
      await api.addMemory({
        fact_type: newType,
        content: newContent,
        provenance: 'explicit_user_statement',
        tags: [newType]
      });
      setNewContent('');
      setShowAddForm(false);
      await loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setSavingNew(false);
    }
  };

  const getProvenanceBadge = (prov: string) => {
    if (prov === 'explicit_user_statement') {
      return { label: 'Confirmed Statement', cls: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' };
    }
    if (prov === 'verified_activity_record') {
      return { label: 'Verified Activity', cls: 'text-blue-400 bg-blue-500/10 border-blue-500/20' };
    }
    return { label: 'AI Inference', cls: 'text-amber-400 bg-amber-500/10 border-amber-500/20' };
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-[#121212] border border-[#2D2D2D] rounded shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-5 py-4 border-b border-[#242424] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-[#1C1C1C] border border-[#333333] flex items-center justify-center">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">Cross-Agent Persistent Memory</h2>
              <p className="text-[11px] text-[#737373]">
                Inspect, verify, or correct facts remembered across all workspaces
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => loadData()}
              className="p-1.5 rounded text-[#737373] hover:text-white hover:bg-[#202020] transition-colors"
              title="Refresh memories"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded text-[#737373] hover:text-white hover:bg-[#202020] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Telemetry Bar */}
        <div className="px-5 py-2.5 bg-[#0D0D0D] border-b border-[#222222] flex items-center justify-between text-[11px] text-[#888888]">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-[#A1A1A1]" /> FalkorDB Graph:
              <span className="font-mono text-white">
                {graphStats?.nodes || 0} nodes • {graphStats?.edges || 0} relationships
              </span>
            </span>
            <span className="text-[#444444]">•</span>
            <span className="flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-emerald-400" /> 768-dim Vector Index Active
            </span>
          </div>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="flex items-center gap-1 text-[11px] text-[#D4D4D4] hover:text-white font-medium"
          >
            <Plus className="w-3 h-3" /> {showAddForm ? 'Cancel' : 'Add Memory'}
          </button>
        </div>

        {/* Add Memory Form */}
        {showAddForm && (
          <form onSubmit={handleAddFact} className="p-4 bg-[#161616] border-b border-[#242424] space-y-3">
            <div className="flex gap-2">
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
                className="w-32 px-2.5 py-1.5 text-xs bg-[#121212] border border-[#333333] rounded text-white"
              >
                <option value="goal">Goal</option>
                <option value="preference">Preference</option>
                <option value="injury">Injury / Flag</option>
                <option value="habit">Habit</option>
              </select>
              <input
                type="text"
                placeholder="e.g. Bench press target 100kg by December"
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                required
                className="flex-1 px-3 py-1.5 text-xs bg-[#121212] border border-[#333333] rounded text-white"
              />
              <button
                type="submit"
                disabled={savingNew}
                className="px-3.5 py-1.5 text-xs bg-[#EDEDED] text-[#0A0A0A] font-semibold rounded hover:bg-white disabled:opacity-50"
              >
                {savingNew ? 'Saving...' : 'Add'}
              </button>
            </div>
          </form>
        )}

        {/* Memory List */}
        <div className="p-5 overflow-y-auto space-y-2.5 flex-1 divide-y divide-[#1F1F1F]">
          {memories.length === 0 ? (
            <div className="text-center py-12 space-y-2 text-xs text-[#737373]">
              <Brain className="w-8 h-8 text-[#444444] mx-auto" />
              <p>No persistent memories stored yet.</p>
              <p className="text-[11px] text-[#555555]">
                State goals or injuries in chat, log workouts, or use the 'Add Memory' button above.
              </p>
            </div>
          ) : (
            memories.map((m) => {
              const badge = getProvenanceBadge(m.provenance);
              const isEditing = editingId === m.id;

              return (
                <div key={m.id} className="pt-2.5 first:pt-0 space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-[9px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded border ${badge.cls}`}>
                        {badge.label}
                      </span>
                      <span className="text-[10px] text-[#737373] uppercase tracking-wide">
                        {m.fact_type}
                      </span>
                      <span className="text-[10px] text-[#555555] font-mono">
                        {Math.round(m.confidence * 100)}% confidence
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      {isEditing ? (
                        <button
                          onClick={() => handleSaveEdit(m.id)}
                          className="p-1 text-emerald-400 hover:text-white"
                          title="Save correction"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleStartEdit(m)}
                          className="p-1 text-[#737373] hover:text-white"
                          title="Correct memory"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(m.id)}
                        className="p-1 text-[#737373] hover:text-rose-400"
                        title="Delete from memory"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {isEditing ? (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        className="flex-1 px-2.5 py-1 text-xs bg-[#1A1A1A] border border-[#3A3A3A] rounded text-white"
                        autoFocus
                      />
                      <button
                        onClick={() => setEditingId(null)}
                        className="text-[11px] text-[#888888] hover:text-white px-2"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="text-xs text-[#D8D8D8] leading-relaxed">
                      {m.content}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

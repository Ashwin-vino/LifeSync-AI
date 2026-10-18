import React, { useState, useEffect } from 'react';
import {
  Moon,
  Droplets,
  HeartPulse,
  Activity,
  Plus,
  X,
  Zap,
  Edit3,
  Trash2,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  HelpCircle
} from 'lucide-react';
import { api, RecoveryLog, RecoveryOverview, UserProfile } from '../api/client';
import { UnifiedChat } from '../components/UnifiedChat';

interface RecoveryWorkspaceProps {
  profile: UserProfile | null;
}

export const RecoveryWorkspace: React.FC<RecoveryWorkspaceProps> = ({ profile }) => {
  const [overview, setOverview] = useState<RecoveryOverview | null>(null);
  const [showLogModal, setShowLogModal] = useState(false);
  const [editingLog, setEditingLog] = useState<RecoveryLog | null>(null);

  // Form state for creating
  const [dateStr, setDateStr] = useState(new Date().toISOString().split('T')[0]);
  const [sleepHours, setSleepHours] = useState(7.5);
  const [sleepQuality, setSleepQuality] = useState('good');
  const [restingHr, setRestingHr] = useState<number | undefined>(undefined);
  const [hrvMs, setHrvMs] = useState<number | undefined>(undefined);
  const [hydrationLiters, setHydrationLiters] = useState(2.8);
  const [sorenessLevel, setSorenessLevel] = useState(2);
  const [fatigueLevel, setFatigueLevel] = useState(2);
  const [stressLevel, setStressLevel] = useState(3);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  // AI Recommendations State
  const [recommendations, setRecommendations] = useState<string[]>([]);
  const [recCautions, setRecCautions] = useState<string[]>([]);
  const [recFactors, setRecFactors] = useState<string[]>([]);
  const [loadingRecs, setLoadingRecs] = useState(false);

  const loadOverview = async () => {
    try {
      const data = await api.getRecoveryOverview();
      setOverview(data);
    } catch (e) {
      console.error('Failed to load recovery overview:', e);
    }
  };

  useEffect(() => {
    loadOverview();
  }, []);

  const handleSaveRecovery = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.logRecovery({
        date: dateStr,
        sleep_hours: sleepHours,
        sleep_quality: sleepQuality,
        resting_hr: restingHr ? Number(restingHr) : undefined,
        hrv_ms: hrvMs ? Number(hrvMs) : undefined,
        hydration_liters: hydrationLiters,
        soreness_level: sorenessLevel,
        fatigue_level: fatigueLevel,
        stress_level: stressLevel,
        notes: notes || undefined,
      });
      setShowLogModal(false);
      setNotes('');
      await loadOverview();
    } catch (err) {
      console.error('Failed to save recovery log:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateRecovery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingLog) return;
    setSaving(true);
    try {
      await api.updateRecoveryLog(editingLog.id, {
        sleep_hours: editingLog.sleep_hours ? Number(editingLog.sleep_hours) : undefined,
        sleep_quality: editingLog.sleep_quality,
        resting_hr: editingLog.resting_hr ? Number(editingLog.resting_hr) : undefined,
        hrv_ms: editingLog.hrv_ms ? Number(editingLog.hrv_ms) : undefined,
        hydration_liters: editingLog.hydration_liters ? Number(editingLog.hydration_liters) : undefined,
        soreness_level: editingLog.soreness_level ? Number(editingLog.soreness_level) : undefined,
        fatigue_level: editingLog.fatigue_level ? Number(editingLog.fatigue_level) : undefined,
        stress_level: editingLog.stress_level ? Number(editingLog.stress_level) : undefined,
        notes: editingLog.notes || undefined,
      });
      setEditingLog(null);
      await loadOverview();
    } catch (err) {
      console.error('Failed to update recovery log:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRecovery = async (id: string) => {
    try {
      await api.deleteRecoveryLog(id);
      await loadOverview();
    } catch (err) {
      console.error('Failed to delete recovery log:', err);
    }
  };

  const handleFetchRecommendations = async () => {
    setLoadingRecs(true);
    try {
      const res = await api.getRecoveryRecommendations();
      setRecommendations(res.recommendations || []);
      setRecCautions(res.cautions || []);
      setRecFactors(res.factors_considered || []);
    } catch (err) {
      console.error('Failed to fetch recovery recommendations:', err);
    } finally {
      setLoadingRecs(false);
    }
  };

  const today = overview?.today_log;
  const score = today?.recovery_score ?? (overview?.average_recovery_score ? Math.round(overview.average_recovery_score) : null);
  const sleep = today?.sleep_hours;
  const hydration = today?.hydration_liters;
  const soreness = today?.soreness_level;
  const fatigue = today?.fatigue_level;
  const restingHeartRate = today?.resting_hr;
  const hrv = today?.hrv_ms;

  const getReadinessBadge = (val: number | null) => {
    if (val === null) return { label: 'Uncalibrated', color: 'text-[#888888] bg-[#1F1F1F] border-[#333333]' };
    if (val >= 80) return { label: 'Optimal / Prime', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' };
    if (val >= 60) return { label: 'Adequate Readiness', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' };
    return { label: 'Fatigued / Rest Advised', color: 'text-rose-400 bg-rose-500/10 border-rose-500/20' };
  };

  const badge = getReadinessBadge(score);

  return (
    <div className="h-full flex flex-col xl:flex-row gap-4 p-4 sm:p-6 overflow-y-auto bg-[#0A0A0A]">
      {/* Left Column: Biometrics, Recovery Scores & Logs */}
      <div className="flex-1 space-y-4">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-[#141414] border border-[#262626] rounded">
          <div>
            <h2 className="text-sm font-semibold text-white tracking-wide">Autonomic Recovery & Readiness</h2>
            <p className="text-[11px] text-[#737373]">
              Sleep architecture, hydration adherence, muscle soreness, and fatigue synthesis
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleFetchRecommendations}
              disabled={loadingRecs}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-[#1F1F1F] border border-[#333333] hover:border-[#555555] text-white rounded transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              {loadingRecs ? 'Synthesizing...' : 'AI Recommendations'}
            </button>
            <button
              onClick={() => setShowLogModal(true)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs bg-[#EDEDED] text-[#0A0A0A] font-semibold rounded hover:bg-white transition-colors"
            >
              <Plus className="w-3.5 h-3.5" /> Log Daily Recovery
            </button>
          </div>
        </div>

        {/* AI Recovery Recommendations Banner */}
        {recommendations.length > 0 && (
          <div className="p-4 bg-[#141414] border border-[#303030] rounded space-y-2.5">
            <div className="flex items-center justify-between border-b border-[#242424] pb-2">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <h3 className="text-xs font-semibold text-white">Grounded Recovery Recommendations</h3>
              </div>
              <button
                onClick={() => setRecommendations([])}
                className="text-[10px] text-[#737373] hover:text-white"
              >
                Dismiss
              </button>
            </div>
            {recFactors.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {recFactors.map((f, idx) => (
                  <span
                    key={idx}
                    className="text-[10px] px-2 py-0.5 bg-[#1F1F1F] border border-[#2E2E2E] rounded text-[#A3A3A3]"
                  >
                    {f}
                  </span>
                ))}
              </div>
            )}
            <ul className="space-y-1.5 text-xs text-[#D4D4D4]">
              {recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
            {recCautions.length > 0 && (
              <div className="pt-2 border-t border-[#222222] space-y-1">
                {recCautions.map((caution, idx) => (
                  <div key={idx} className="flex items-center gap-1.5 text-[10px] text-[#888888]">
                    <AlertTriangle className="w-3 h-3 text-amber-500/80 shrink-0" />
                    <span>{caution}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Readiness Score Hero Card */}
        <div className="p-5 bg-[#141414] border border-[#262626] rounded flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded border ${badge.color}`}>
                {badge.label}
              </span>
              <span className="text-[10px] text-[#737373]">
                {today ? `Logged for ${today.date}` : 'Awaiting today\'s log (showing 7-day average)'}
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold font-mono text-white">
                {score !== null ? score : '—'}
              </span>
              <span className="text-sm text-[#737373]">/ 100 Readiness Score</span>
            </div>
            <p className="text-xs text-[#A3A3A3] max-w-md">
              {score === null
                ? 'No recovery metrics logged yet. Record sleep duration and soreness to compute an objective readiness score.'
                : score >= 80
                ? 'Autonomic recovery capacity is high. Systemic nervous system fatigue is low and progressive overload is well-tolerated today.'
                : score >= 60
                ? 'Moderate readiness balance. Suitable for standard volume; pay close attention to hydration and post-workout protein timing.'
                : 'Elevated fatigue or soreness detected. Prioritize active recovery, mobility, low-intensity cardio, and restorative sleep.'}
            </p>
          </div>

          {/* Biometric Snapshot Pill Matrix */}
          <div className="grid grid-cols-2 gap-2 text-xs sm:w-64">
            <div className="p-2.5 bg-[#181818] border border-[#2B2B2B] rounded">
              <div className="text-[10px] text-[#737373] flex items-center gap-1">
                <Moon className="w-3 h-3 text-[#A3A3A3]" /> Sleep Logged
              </div>
              <div className="text-sm font-semibold font-mono text-white mt-0.5">
                {sleep !== undefined ? `${sleep}h` : <span className="text-[#666666] text-xs font-normal">Unrecorded</span>}
                <span className="text-[10px] text-[#737373]"> / {profile?.sleep_target_hours || 8}h</span>
              </div>
            </div>

            <div className="p-2.5 bg-[#181818] border border-[#2B2B2B] rounded">
              <div className="text-[10px] text-[#737373] flex items-center gap-1">
                <Droplets className="w-3 h-3 text-[#A3A3A3]" /> Hydration
              </div>
              <div className="text-sm font-semibold font-mono text-white mt-0.5">
                {hydration !== undefined ? `${hydration}L` : <span className="text-[#666666] text-xs font-normal">Unrecorded</span>}
                <span className="text-[10px] text-[#737373]"> / {profile?.water_target_liters || 3.0}L</span>
              </div>
            </div>

            <div className="p-2.5 bg-[#181818] border border-[#2B2B2B] rounded">
              <div className="text-[10px] text-[#737373] flex items-center gap-1">
                <HeartPulse className="w-3 h-3 text-[#A3A3A3]" /> Soreness • Fatigue
              </div>
              <div className="text-sm font-semibold font-mono text-white mt-0.5">
                {soreness !== undefined ? `${soreness}/5` : '—'} • {fatigue !== undefined ? `${fatigue}/5` : '—'}
              </div>
            </div>

            <div className="p-2.5 bg-[#181818] border border-[#2B2B2B] rounded">
              <div className="text-[10px] text-[#737373] flex items-center gap-1">
                <Activity className="w-3 h-3 text-[#A3A3A3]" /> Resting HR • HRV
              </div>
              <div className="text-sm font-semibold font-mono text-white mt-0.5">
                {restingHeartRate ? `${restingHeartRate}bpm` : '—'} • {hrv ? `${hrv}ms` : '—'}
              </div>
            </div>
          </div>
        </div>

        {/* Missing Data Disclosure Banner */}
        {overview?.missing_metrics && overview.missing_metrics.length > 0 && (
          <div className="p-3 bg-[#141414] border border-[#262626] rounded flex items-center justify-between text-xs text-[#888888]">
            <div className="flex items-center gap-2">
              <HelpCircle className="w-3.5 h-3.5 text-[#666666]" />
              <span>
                Missing today: <span className="text-[#A3A3A3]">{overview.missing_metrics.join(', ')}</span>. LifeSync AI evaluates only verified user-logged data.
              </span>
            </div>
            <button
              onClick={() => setShowLogModal(true)}
              className="text-[11px] text-white hover:underline"
            >
              Log Now
            </button>
          </div>
        )}

        {/* Weekly Trend Table / Visual with Edit and Delete */}
        <div className="p-4 bg-[#141414] border border-[#262626] rounded space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#999999]">
              7-Day Recovery & Sleep History
            </span>
            <span className="text-[11px] text-[#737373]">
              Avg Sleep: {overview?.average_sleep ?? '—'}h • Avg Readiness: {overview?.average_recovery_score ? Math.round(overview.average_recovery_score) : '—'}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-[11px]">
              <thead>
                <tr className="text-[#666666] border-b border-[#222222]">
                  <th className="pb-2 font-medium">Date</th>
                  <th className="pb-2 font-medium">Readiness Score</th>
                  <th className="pb-2 font-medium">Sleep</th>
                  <th className="pb-2 font-medium">Quality</th>
                  <th className="pb-2 font-medium">Hydration</th>
                  <th className="pb-2 font-medium">Soreness</th>
                  <th className="pb-2 font-medium">Fatigue</th>
                  <th className="pb-2 font-medium">HR / HRV</th>
                  <th className="pb-2 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1F1F1F]">
                {overview?.weekly_logs && overview.weekly_logs.length > 0 ? (
                  overview.weekly_logs.map((log) => (
                    <tr key={log.id} className="text-[#C5C5C5] hover:bg-[#181818]/50">
                      <td className="py-2.5 font-mono text-white">{log.date}</td>
                      <td className="py-2.5 font-mono">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                          (log.recovery_score || 0) >= 80 ? 'text-emerald-400 bg-emerald-500/10' :
                          (log.recovery_score || 0) >= 60 ? 'text-amber-400 bg-amber-500/10' :
                          'text-rose-400 bg-rose-500/10'
                        }`}>
                          {log.recovery_score ?? '—'} / 100
                        </span>
                      </td>
                      <td className="py-2.5 font-mono">{log.sleep_hours ? `${log.sleep_hours}h` : '—'}</td>
                      <td className="py-2.5 capitalize">{log.sleep_quality || '—'}</td>
                      <td className="py-2.5 font-mono">{log.hydration_liters ? `${log.hydration_liters}L` : '—'}</td>
                      <td className="py-2.5 font-mono">{log.soreness_level ? `${log.soreness_level}/5` : '—'}</td>
                      <td className="py-2.5 font-mono">{log.fatigue_level ? `${log.fatigue_level}/5` : '—'}</td>
                      <td className="py-2.5 font-mono text-[10px] text-[#737373]">
                        {log.resting_hr ? `${log.resting_hr}bpm` : '—'} / {log.hrv_ms ? `${log.hrv_ms}ms` : '—'}
                      </td>
                      <td className="py-2.5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => setEditingLog(log)}
                            className="p-1 text-[#777777] hover:text-white rounded hover:bg-[#222222]"
                            title="Edit recovery log"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteRecovery(log.id)}
                            className="p-1 text-[#777777] hover:text-rose-400 rounded hover:bg-[#222222]"
                            title="Delete recovery log"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={9} className="py-6 text-center text-[#666666]">
                      No previous recovery logs recorded. Use the "Log Daily Recovery" button above to record today's sleep and biometrics.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Targeted Recovery Protocols */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="p-3.5 bg-[#141414] border border-[#262626] rounded space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-white">
              <Droplets className="w-4 h-4 text-blue-400" /> Hydration & Electrolytes
            </div>
            <p className="text-[11px] text-[#888888]">
              Target 500ml water upon waking with sodium/potassium electrolytes. Maintain 35-40ml per kg of body mass on training days.
            </p>
          </div>

          <div className="p-3.5 bg-[#141414] border border-[#262626] rounded space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-white">
              <Zap className="w-4 h-4 text-amber-400" /> Autonomic Down-Regulation
            </div>
            <p className="text-[11px] text-[#888888]">
              Perform 5 minutes of box breathing (4s in, 4s hold, 4s out, 4s hold) post-workout or 45 minutes prior to sleep to elevate parasympathetic tone.
            </p>
          </div>
        </div>
      </div>

      {/* Right Column: AI Recovery Scientist Chat */}
      <div className="w-full xl:w-[420px] min-h-[500px] flex flex-col">
        <UnifiedChat
          workspace="recovery"
          title="LifeSync AI • Recovery Scientist"
          subtitle="Autonomic regulation, sleep hygiene & systemic fatigue mitigation"
          suggestedPrompts={[
            "My hamstrings and glutes have a soreness level of 4/5 after training. What recovery modalities help fastest?",
            "What bedtime routine changes can increase deep slow-wave sleep duration?",
            "How does yesterday's workout intensity correlate with my current recovery score?",
            "Should I modify today's planned workout given my reported fatigue level?"
          ]}
        />
      </div>

      {/* Log Recovery Modal */}
      {showLogModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#141414] border border-[#2D2D2D] rounded shadow-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[#242424] flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">Log Recovery Biometrics</h2>
                <p className="text-[11px] text-[#737373]">Computes evidence-based readiness score</p>
              </div>
              <button
                onClick={() => setShowLogModal(false)}
                className="p-1 rounded text-[#737373] hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveRecovery} className="p-5 space-y-3.5 max-h-[80vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-[#A3A3A3] mb-1">Date</label>
                  <input
                    type="date"
                    value={dateStr}
                    onChange={(e) => setDateStr(e.target.value)}
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-[#A3A3A3] mb-1">Sleep Quality</label>
                  <select
                    value={sleepQuality}
                    onChange={(e) => setSleepQuality(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                  >
                    <option value="excellent">Excellent (Deep & Restful)</option>
                    <option value="good">Good (Normal)</option>
                    <option value="fair">Fair (Interrupted)</option>
                    <option value="poor">Poor (Restless/Short)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Sleep Duration (hours)</label>
                  <input
                    type="number"
                    step="0.25"
                    min="1"
                    max="18"
                    value={sleepHours}
                    onChange={(e) => setSleepHours(Number(e.target.value))}
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Hydration (liters)</label>
                  <input
                    type="number"
                    step="0.25"
                    min="0"
                    max="10"
                    value={hydrationLiters}
                    onChange={(e) => setHydrationLiters(Number(e.target.value))}
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="flex justify-between text-[11px] text-[#A3A3A3] mb-1">
                    <span>Muscle Soreness</span>
                    <span className="font-mono text-white">{sorenessLevel}/5</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={sorenessLevel}
                    onChange={(e) => setSorenessLevel(Number(e.target.value))}
                    className="w-full accent-white bg-[#222222]"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-[11px] text-[#A3A3A3] mb-1">
                    <span>Fatigue Level</span>
                    <span className="font-mono text-white">{fatigueLevel}/5</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={fatigueLevel}
                    onChange={(e) => setFatigueLevel(Number(e.target.value))}
                    className="w-full accent-white bg-[#222222]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Resting HR (bpm, optional)</label>
                  <input
                    type="number"
                    min="35"
                    max="140"
                    placeholder="e.g. 54"
                    value={restingHr || ''}
                    onChange={(e) => setRestingHr(e.target.value ? Number(e.target.value) : undefined)}
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">HRV rMSSD (ms, optional)</label>
                  <input
                    type="number"
                    min="10"
                    max="200"
                    placeholder="e.g. 68"
                    value={hrvMs || ''}
                    onChange={(e) => setHrvMs(e.target.value ? Number(e.target.value) : undefined)}
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-[11px] text-[#A3A3A3] mb-1">
                  <span>Perceived Stress Level</span>
                  <span className="font-mono text-white">{stressLevel}/5</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={stressLevel}
                  onChange={(e) => setStressLevel(Number(e.target.value))}
                  className="w-full accent-white bg-[#222222]"
                />
              </div>

              <div>
                <label className="block text-[11px] text-[#A3A3A3] mb-1">Recovery Notes (Optional)</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Sleep interruptions, soreness locations, caffeine cutoff..."
                  rows={2}
                  className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-[#242424]">
                <button
                  type="button"
                  onClick={() => setShowLogModal(false)}
                  className="px-3 py-1.5 text-xs text-[#888888] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-1.5 text-xs bg-[#EDEDED] text-[#0A0A0A] font-semibold rounded hover:bg-white disabled:opacity-50 transition-colors"
                >
                  {saving ? 'Calculating Score...' : 'Save & Calculate Score'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Recovery Modal */}
      {editingLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#141414] border border-[#2D2D2D] rounded shadow-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[#242424] flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">Edit Recovery Entry ({editingLog.date})</h2>
                <p className="text-[11px] text-[#737373]">Update recorded biometrics and recompute readiness</p>
              </div>
              <button
                onClick={() => setEditingLog(null)}
                className="p-1 rounded text-[#737373] hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleUpdateRecovery} className="p-5 space-y-3.5 max-h-[80vh] overflow-y-auto">
              <div>
                <label className="block text-[11px] font-medium text-[#A3A3A3] mb-1">Sleep Quality</label>
                <select
                  value={editingLog.sleep_quality || 'good'}
                  onChange={(e) => setEditingLog({ ...editingLog, sleep_quality: e.target.value })}
                  className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                >
                  <option value="excellent">Excellent (Deep & Restful)</option>
                  <option value="good">Good (Normal)</option>
                  <option value="fair">Fair (Interrupted)</option>
                  <option value="poor">Poor (Restless/Short)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Sleep Duration (hours)</label>
                  <input
                    type="number"
                    step="0.25"
                    min="1"
                    max="18"
                    value={editingLog.sleep_hours || 7.5}
                    onChange={(e) => setEditingLog({ ...editingLog, sleep_hours: Number(e.target.value) })}
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Hydration (liters)</label>
                  <input
                    type="number"
                    step="0.25"
                    min="0"
                    max="10"
                    value={editingLog.hydration_liters || 2.5}
                    onChange={(e) => setEditingLog({ ...editingLog, hydration_liters: Number(e.target.value) })}
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="flex justify-between text-[11px] text-[#A3A3A3] mb-1">
                    <span>Muscle Soreness</span>
                    <span className="font-mono text-white">{editingLog.soreness_level || 1}/5</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={editingLog.soreness_level || 1}
                    onChange={(e) => setEditingLog({ ...editingLog, soreness_level: Number(e.target.value) })}
                    className="w-full accent-white bg-[#222222]"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-[11px] text-[#A3A3A3] mb-1">
                    <span>Fatigue Level</span>
                    <span className="font-mono text-white">{editingLog.fatigue_level || 1}/5</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={editingLog.fatigue_level || 1}
                    onChange={(e) => setEditingLog({ ...editingLog, fatigue_level: Number(e.target.value) })}
                    className="w-full accent-white bg-[#222222]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Resting HR (bpm)</label>
                  <input
                    type="number"
                    min="35"
                    max="140"
                    value={editingLog.resting_hr || ''}
                    onChange={(e) => setEditingLog({ ...editingLog, resting_hr: e.target.value ? Number(e.target.value) : undefined })}
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">HRV rMSSD (ms)</label>
                  <input
                    type="number"
                    min="10"
                    max="200"
                    value={editingLog.hrv_ms || ''}
                    onChange={(e) => setEditingLog({ ...editingLog, hrv_ms: e.target.value ? Number(e.target.value) : undefined })}
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] text-[#A3A3A3] mb-1">Notes</label>
                <textarea
                  value={editingLog.notes || ''}
                  onChange={(e) => setEditingLog({ ...editingLog, notes: e.target.value })}
                  placeholder="Optional notes"
                  rows={2}
                  className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-[#242424]">
                <button
                  type="button"
                  onClick={() => setEditingLog(null)}
                  className="px-3 py-1.5 text-xs text-[#888888] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-1.5 text-xs bg-[#EDEDED] text-[#0A0A0A] font-semibold rounded hover:bg-white disabled:opacity-50 transition-colors"
                >
                  {saving ? 'Updating...' : 'Update & Recompute'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

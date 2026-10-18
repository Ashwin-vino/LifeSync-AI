import React, { useState, useEffect } from 'react';
import {
  Dumbbell,
  Plus,
  Search,
  Clock,
  Flame,
  TrendingUp,
  X,
  ChevronRight,
  Layers,
  Trash2,
  Edit2,
  Sparkles,
  Play,
  Activity,
  ShieldCheck,
  Info
} from 'lucide-react';
import {
  api,
  WorkoutItem,
  ExerciseItem,
  WorkoutExercise,
  WorkoutPlan,
  WorkoutAnalytics
} from '../api/client';
import { UnifiedChat } from '../components/UnifiedChat';

export const WorkoutWorkspace: React.FC = () => {
  // Workouts & Analytics State
  const [workouts, setWorkouts] = useState<WorkoutItem[]>([]);
  const [analytics, setAnalytics] = useState<WorkoutAnalytics | null>(null);

  // Active Plan State
  const [activePlan, setActivePlan] = useState<WorkoutPlan | null>(null);
  const [generatingPlan, setGeneratingPlan] = useState(false);
  const [planFocus, setPlanFocus] = useState('Upper Body Hypertrophy');
  const [planDuration, setPlanDuration] = useState(45);
  const [showPlanModal, setShowPlanModal] = useState(false);

  // Log / Live Session Modal
  const [showLogModal, setShowLogModal] = useState(false);
  const [editingWorkoutId, setEditingWorkoutId] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('Strength');
  const [duration, setDuration] = useState(45);
  const [calories, setCalories] = useState<number | undefined>(350);
  const [rpe, setRpe] = useState<number>(7);
  const [notes, setNotes] = useState('');
  const [currentPlanId, setCurrentPlanId] = useState<string | undefined>(undefined);
  const [exercises, setExercises] = useState<Omit<WorkoutExercise, 'id'>[]>([
    { exercise_name: 'Barbell Bench Press', sets: 4, reps: 8, weight_kg: 80, status: 'completed', source: 'wger_verified', notes: 'Felt solid' }
  ]);
  const [saving, setSaving] = useState(false);

  // wger Search & Library Modal
  const [showWgerModal, setShowWgerModal] = useState(false);
  const [wgerQuery, setWgerQuery] = useState('');
  const [wgerCategory, setWgerCategory] = useState<string>('');
  const [wgerResults, setWgerResults] = useState<ExerciseItem[]>([]);
  const [searchingWger, setSearchingWger] = useState(false);

  // Timer for active workout
  const [timerActive, setTimerActive] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    let interval: any;
    if (timerActive) {
      interval = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    }
    return () => clearInterval(interval);
  }, [timerActive]);

  const loadData = async () => {
    try {
      const [wData, planData, aData] = await Promise.all([
        api.getWorkouts(25, 'completed'),
        api.getActiveWorkoutPlan(),
        api.getWorkoutAnalytics()
      ]);
      setWorkouts(wData);
      setActivePlan(planData);
      setAnalytics(aData);
    } catch (e) {
      console.error('Error loading workout data:', e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Search wger exercises
  const handleSearchWger = async (cat?: string) => {
    setSearchingWger(true);
    try {
      const targetCat = cat !== undefined ? cat : wgerCategory;
      const items = await api.searchExercises(wgerQuery, targetCat || undefined, 40);
      setWgerResults(items);
    } catch (e) {
      console.error('Error searching wger:', e);
    } finally {
      setSearchingWger(false);
    }
  };

  const handleSelectWgerExercise = (item: ExerciseItem) => {
    setExercises((prev) => [
      ...prev,
      {
        exercise_name: item.name,
        target_muscle: item.category,
        sets: 3,
        reps: 10,
        weight_kg: 50,
        status: 'completed',
        source: item.source || 'wger_verified',
        notes: item.muscles.length > 0 ? `Target: ${item.muscles.slice(0, 2).join(', ')}` : ''
      }
    ]);
    setShowWgerModal(false);
    setWgerQuery('');
  };

  // Plan Generation
  const handleGeneratePlan = async () => {
    setGeneratingPlan(true);
    try {
      const plan = await api.generateWorkoutPlan({
        focus: planFocus,
        duration_target: planDuration
      });
      setActivePlan(plan);
      setShowPlanModal(false);
    } catch (e) {
      console.error('Error generating workout plan:', e);
    } finally {
      setGeneratingPlan(false);
    }
  };

  // Start Interactive Workout from Plan
  const handleStartWorkoutFromPlan = async (plan: WorkoutPlan) => {
    setCurrentPlanId(plan.id);
    setTitle(plan.title);
    setCategory(plan.category);
    setDuration(plan.estimated_duration_minutes);
    setCalories(Math.round(plan.estimated_duration_minutes * 7.5));
    setRpe(7);
    setNotes(plan.explanation);

    const convertedExercises = plan.exercises.map((p) => {
      // Parse reps (e.g. "8-10" -> 10)
      const parsedReps = parseInt(p.reps.split('-')[0]) || 10;
      return {
        exercise_name: p.name,
        target_muscle: p.target_muscle,
        sets: p.sets,
        reps: parsedReps,
        weight_kg: p.suggested_weight_kg || 0,
        status: 'completed' as const,
        source: p.source,
        notes: p.notes || ''
      };
    });

    setExercises(convertedExercises.length > 0 ? convertedExercises : [
      { exercise_name: 'Barbell Bench Press', sets: 4, reps: 8, weight_kg: 80, status: 'completed', source: 'wger_verified' }
    ]);

    setEditingWorkoutId(null);
    setElapsedSeconds(0);
    setTimerActive(true);
    setShowLogModal(true);

    try {
      await api.startWorkoutSession(plan.id);
    } catch (e) {
      console.warn('Session start recorded locally:', e);
    }
  };

  // Manual Log Open
  const handleOpenManualLog = () => {
    setEditingWorkoutId(null);
    setCurrentPlanId(undefined);
    setTitle('Strength & Conditioning');
    setCategory('Strength');
    setDuration(45);
    setCalories(350);
    setRpe(7);
    setNotes('');
    setExercises([
      { exercise_name: 'Barbell Squat', sets: 4, reps: 8, weight_kg: 90, status: 'completed', source: 'wger_verified' }
    ]);
    setShowLogModal(true);
  };

  // Edit Existing Workout
  const handleEditWorkout = (w: WorkoutItem) => {
    setEditingWorkoutId(w.id);
    setCurrentPlanId(undefined);
    setTitle(w.title);
    setCategory(w.category);
    setDuration(w.duration_minutes);
    setCalories(w.calories_burned || 300);
    setRpe(w.rpe || 7);
    setNotes(w.notes || '');
    setExercises(
      w.workout_exercises.map((ex) => ({
        exercise_name: ex.exercise_name,
        target_muscle: ex.target_muscle,
        sets: ex.sets,
        reps: ex.reps,
        weight_kg: ex.weight_kg,
        status: (ex.status as any) || 'completed',
        source: ex.source || 'wger_verified',
        notes: ex.notes || ''
      }))
    );
    setShowLogModal(true);
  };

  // Delete Workout (across Supabase and FalkorDB graph)
  const handleDeleteWorkout = async (id: string) => {
    if (!confirm('Are you sure you want to delete this workout? This will synchronize deletion across Supabase and FalkorDB graph memory.')) {
      return;
    }
    try {
      await api.deleteWorkout(id);
      await loadData();
    } catch (e) {
      console.error('Error deleting workout:', e);
      alert('Failed to delete workout.');
    }
  };

  // Exercise Row Management
  const addExerciseRow = () => {
    setExercises((prev) => [
      ...prev,
      { exercise_name: '', sets: 3, reps: 10, weight_kg: 0, status: 'completed', source: 'custom' }
    ]);
  };

  const removeExerciseRow = (idx: number) => {
    setExercises((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateExercise = (idx: number, field: keyof Omit<WorkoutExercise, 'id'>, val: any) => {
    setExercises((prev) => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], [field]: val };
      return copy;
    });
  };

  // Submit Workout
  const handleSubmitWorkout = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    setTimerActive(false);

    try {
      const validExercises = exercises.filter((ex) => ex.exercise_name.trim().length > 0);
      const computedDuration = timerActive && elapsedSeconds > 60 ? Math.round(elapsedSeconds / 60) : duration;

      if (editingWorkoutId) {
        await api.updateWorkout(editingWorkoutId, {
          title,
          category,
          duration_minutes: computedDuration,
          calories_burned: calories,
          rpe,
          notes,
          exercises: validExercises
        });
      } else {
        await api.logWorkout({
          title,
          category,
          duration_minutes: computedDuration,
          calories_burned: calories,
          rpe,
          status: 'completed',
          plan_id: currentPlanId,
          notes,
          exercises: validExercises
        });
      }

      setShowLogModal(false);
      setEditingWorkoutId(null);
      await loadData();
    } catch (err) {
      console.error('Error saving workout:', err);
      alert('Failed to save workout session.');
    } finally {
      setSaving(false);
    }
  };

  // Helper format seconds
  const formatTimer = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = sec % 60;
    return `${mins}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="h-full flex flex-col xl:flex-row gap-4 p-4 sm:p-6 overflow-y-auto">
      {/* Main Column: Plan, Telemetry, History */}
      <div className="flex-1 space-y-4">
        {/* Workspace Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-[#121212] border border-[#242424] rounded">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-white tracking-wide">Workout AI • Performance & Training</h2>
              <span className="text-[10px] px-2 py-0.5 rounded bg-[#1C1C1C] text-emerald-400 border border-[#2E2E2E] flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" /> wger Verified
              </span>
            </div>
            <p className="text-[11px] text-[#737373] mt-0.5">
              Biomechanically sound programming, live set tracking, volume progression, and cross-agent memory synchronization
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => {
                setShowWgerModal(true);
                if (wgerResults.length === 0) {
                  handleSearchWger('');
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] hover:border-[#505050] text-[#D4D4D4] rounded transition-colors"
            >
              <Search className="w-3.5 h-3.5" /> Exercise Library
            </button>
            <button
              onClick={() => setShowPlanModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-[#1F1F1F] border border-[#383838] hover:border-[#555555] text-white font-medium rounded transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Generate Plan
            </button>
            <button
              onClick={handleOpenManualLog}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs bg-[#EDEDED] text-[#0A0A0A] font-semibold rounded hover:bg-white transition-colors"
            >
              <Plus className="w-3.5 h-3.5" /> Log Workout
            </button>
          </div>
        </div>

        {/* Telemetry Cards Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3.5 bg-[#141414] border border-[#262626] rounded">
            <div className="flex items-center justify-between text-[#888888] mb-1">
              <span className="text-[11px] font-medium">Completed Sessions</span>
              <Layers className="w-3.5 h-3.5 text-[#A3A3A3]" />
            </div>
            <div className="text-xl font-bold font-mono text-white">
              {analytics ? analytics.total_sessions : workouts.length}
            </div>
            <div className="text-[10px] text-[#666666] mt-0.5">Persisted in Supabase & FalkorDB</div>
          </div>

          <div className="p-3.5 bg-[#141414] border border-[#262626] rounded">
            <div className="flex items-center justify-between text-[#888888] mb-1">
              <span className="text-[11px] font-medium">Total Volume Tonnage</span>
              <TrendingUp className="w-3.5 h-3.5 text-[#A3A3A3]" />
            </div>
            <div className="text-xl font-bold font-mono text-white">
              {analytics ? analytics.total_volume_kg.toLocaleString() : '0'}{' '}
              <span className="text-xs font-normal text-[#737373]">kg</span>
            </div>
            <div className="text-[10px] text-[#666666] mt-0.5">Cumulative sets × reps × weight</div>
          </div>

          <div className="p-3.5 bg-[#141414] border border-[#262626] rounded">
            <div className="flex items-center justify-between text-[#888888] mb-1">
              <span className="text-[11px] font-medium">Training Minutes</span>
              <Clock className="w-3.5 h-3.5 text-[#A3A3A3]" />
            </div>
            <div className="text-xl font-bold font-mono text-white">
              {analytics ? analytics.total_minutes : '0'}{' '}
              <span className="text-xs font-normal text-[#737373]">m</span>
            </div>
            <div className="text-[10px] text-[#666666] mt-0.5">Active under-tension time</div>
          </div>

          <div className="p-3.5 bg-[#141414] border border-[#262626] rounded">
            <div className="flex items-center justify-between text-[#888888] mb-1">
              <span className="text-[11px] font-medium">Average Exertion</span>
              <Activity className="w-3.5 h-3.5 text-[#A3A3A3]" />
            </div>
            <div className="text-xl font-bold font-mono text-white">
              {analytics && analytics.average_rpe > 0 ? `RPE ${analytics.average_rpe}` : 'RPE 7.0'}
            </div>
            <div className="text-[10px] text-[#666666] mt-0.5">Scale 1-10 rate of exertion</div>
          </div>
        </div>

        {/* 7-Day Training Volume Progression Mini-Chart */}
        {analytics && analytics.recent_7_days_volume.length > 0 && (
          <div className="p-4 bg-[#141414] border border-[#262626] rounded space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-white tracking-wide">7-Day Work Volume Progression</span>
              <span className="text-[11px] text-[#737373]">Tonnage (kg) per calendar day</span>
            </div>
            <div className="grid grid-cols-7 gap-2 pt-2 items-end h-24">
              {analytics.recent_7_days_volume.map((day, idx) => {
                const maxVol = Math.max(...analytics.recent_7_days_volume.map((d) => d.volume_kg), 1000);
                const heightPct = Math.max(Math.round((day.volume_kg / maxVol) * 100), 8);
                const dateLabel = day.date.slice(5); // MM-DD

                return (
                  <div key={idx} className="flex flex-col items-center h-full justify-end group">
                    <div className="text-[9px] text-[#888888] opacity-0 group-hover:opacity-100 transition-opacity mb-1 font-mono">
                      {day.volume_kg > 0 ? `${Math.round(day.volume_kg)}kg` : 'Rest'}
                    </div>
                    <div
                      style={{ height: `${heightPct}%` }}
                      className={`w-full rounded-t transition-all duration-300 ${
                        day.volume_kg > 0
                          ? 'bg-neutral-200 group-hover:bg-white'
                          : 'bg-[#222222]'
                      }`}
                    />
                    <span className="text-[10px] text-[#666666] mt-1 font-mono">{dateLabel}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Today's Workout Plan Section */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#999999] flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Today's Scheduled Workout Plan
            </span>
            {activePlan && (
              <span className="text-[10px] px-2 py-0.5 rounded bg-[#1A1A1A] border border-[#303030] text-[#A3A3A3]">
                Status: {activePlan.status.toUpperCase()}
              </span>
            )}
          </div>

          {activePlan ? (
            <div className="p-4 bg-[#141414] border border-[#2A2A2A] rounded space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#222222] pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                    <h3 className="text-sm font-semibold text-white tracking-wide">{activePlan.title}</h3>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-[#202020] text-[#CCCCCC] border border-[#333333]">
                      {activePlan.category}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#888888] mt-1">{activePlan.summary}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleStartWorkoutFromPlan(activePlan)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-[#EDEDED] text-[#0A0A0A] font-semibold rounded hover:bg-white transition-colors"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" /> Start Session
                  </button>
                </div>
              </div>

              {/* Rationale / Explanation */}
              <div className="p-2.5 bg-[#101010] border border-[#222222] rounded flex items-start gap-2 text-[11px] text-[#AAAAAA]">
                <Info className="w-4 h-4 text-[#888888] shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-white">Coach Rationale: </span>
                  {activePlan.explanation}
                </div>
              </div>

              {/* Planned Exercise Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[11px]">
                  <thead>
                    <tr className="text-[#666666] border-b border-[#222222]">
                      <th className="pb-1.5 font-medium">Exercise</th>
                      <th className="pb-1.5 font-medium">Target</th>
                      <th className="pb-1.5 font-medium">Sets</th>
                      <th className="pb-1.5 font-medium">Reps</th>
                      <th className="pb-1.5 font-medium">Rest</th>
                      <th className="pb-1.5 font-medium">Source</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1A1A1A]">
                    {activePlan.exercises.map((ex, i) => (
                      <tr key={i} className="text-[#CCCCCC]">
                        <td className="py-2 font-medium text-white">
                          {ex.name}
                          {ex.notes && <div className="text-[10px] text-[#737373]">{ex.notes}</div>}
                        </td>
                        <td className="py-2 text-[#999999]">{ex.target_muscle}</td>
                        <td className="py-2 font-mono">{ex.sets}</td>
                        <td className="py-2 font-mono">{ex.reps}</td>
                        <td className="py-2 font-mono text-[#888888]">{ex.rest_seconds}s</td>
                        <td className="py-2">
                          <span
                            className={`text-[9px] px-1.5 py-0.5 rounded border ${
                              ex.source === 'wger_verified'
                                ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800/50'
                                : 'bg-[#1C1C1C] text-[#999999] border-[#333333]'
                            }`}
                          >
                            {ex.source === 'wger_verified' ? 'wger verified' : 'AI suggested'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Warmup & Cooldown preview */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-[#202020] text-[10px]">
                <div className="p-2 bg-[#0E0E0E] rounded border border-[#1F1F1F]">
                  <span className="font-semibold text-[#888888] block mb-1">Dynamic Warm-Up:</span>
                  <ul className="list-disc list-inside text-[#AAAAAA] space-y-0.5">
                    {activePlan.warmup.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
                <div className="p-2 bg-[#0E0E0E] rounded border border-[#1F1F1F]">
                  <span className="font-semibold text-[#888888] block mb-1">Cooldown & Decompression:</span>
                  <ul className="list-disc list-inside text-[#AAAAAA] space-y-0.5">
                    {activePlan.cooldown.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-5 bg-[#121212] border border-[#242424] rounded flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="space-y-1 text-center sm:text-left">
                <div className="text-xs font-semibold text-white">No active workout scheduled for today</div>
                <div className="text-[11px] text-[#737373]">
                  Generate an individualized routine tailored to your recovery state, previous volume, and goals.
                </div>
              </div>
              <div className="flex items-center gap-2 flex-wrap justify-center">
                <button
                  onClick={() => {
                    setPlanFocus('Upper Body Hypertrophy');
                    handleGeneratePlan();
                  }}
                  className="px-2.5 py-1 text-xs bg-[#1A1A1A] hover:bg-[#222222] border border-[#303030] text-[#D4D4D4] rounded"
                >
                  Push Focus
                </button>
                <button
                  onClick={() => {
                    setPlanFocus('Lower Body Posterior Chain');
                    handleGeneratePlan();
                  }}
                  className="px-2.5 py-1 text-xs bg-[#1A1A1A] hover:bg-[#222222] border border-[#303030] text-[#D4D4D4] rounded"
                >
                  Leg Focus
                </button>
                <button
                  onClick={() => setShowPlanModal(true)}
                  className="px-3 py-1 text-xs bg-[#EDEDED] text-[#0A0A0A] font-semibold rounded hover:bg-white"
                >
                  Custom Plan
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Logged Workouts Feed */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#999999]">
              Verified Training Sessions
            </span>
            <span className="text-[11px] text-[#666666]">{workouts.length} completed</span>
          </div>

          {workouts.length === 0 ? (
            <div className="p-8 bg-[#121212] border border-[#242424] rounded text-center space-y-2">
              <Dumbbell className="w-8 h-8 text-[#555555] mx-auto" />
              <p className="text-xs text-[#888888]">No completed workouts logged yet.</p>
              <p className="text-[11px] text-[#555555]">
                Start today's scheduled plan or manually log a session to record training activity to your memory graph.
              </p>
            </div>
          ) : (
            workouts.map((w) => {
              const sessionVol = (w.workout_exercises || []).reduce(
                (sum, ex) => sum + (ex.sets * ex.reps * ex.weight_kg),
                0
              );

              return (
                <div key={w.id} className="p-4 bg-[#141414] border border-[#262626] rounded space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-[#222222] pb-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="w-2 h-2 rounded-full bg-emerald-500" />
                      <h3 className="text-xs font-semibold text-white tracking-wide">{w.title}</h3>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-[#1F1F1F] text-[#A1A1A1] border border-[#303030]">
                        {w.category}
                      </span>
                      {w.rpe && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-[#191919] text-amber-400 border border-[#333333]">
                          RPE {w.rpe}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-[#737373]">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" /> {w.duration_minutes}m
                      </span>
                      {w.calories_burned && (
                        <span className="flex items-center gap-1">
                          <Flame className="w-3 h-3" /> {w.calories_burned} kcal
                        </span>
                      )}
                      {sessionVol > 0 && (
                        <span className="flex items-center gap-1 font-mono text-[#A3A3A3]">
                          <TrendingUp className="w-3 h-3" /> {sessionVol.toLocaleString()} kg
                        </span>
                      )}
                      <span>{new Date(w.created_at).toLocaleDateString()}</span>
                      <div className="flex items-center gap-1 pl-2 border-l border-[#242424]">
                        <button
                          onClick={() => handleEditWorkout(w)}
                          title="Edit Workout"
                          className="p-1 hover:text-white rounded hover:bg-[#202020]"
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => handleDeleteWorkout(w.id)}
                          title="Delete Workout"
                          className="p-1 hover:text-rose-400 rounded hover:bg-[#202020]"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Exercises breakdown */}
                  {w.workout_exercises && w.workout_exercises.length > 0 && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-[11px]">
                        <thead>
                          <tr className="text-[#666666] border-b border-[#222222]">
                            <th className="pb-1.5 font-medium">Exercise</th>
                            <th className="pb-1.5 font-medium">Sets</th>
                            <th className="pb-1.5 font-medium">Reps</th>
                            <th className="pb-1.5 font-medium">Weight (kg)</th>
                            <th className="pb-1.5 font-medium">Tonnage</th>
                            <th className="pb-1.5 font-medium">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#1F1F1F]">
                          {w.workout_exercises.map((ex, i) => (
                            <tr key={i} className="text-[#C5C5C5]">
                              <td className="py-1.5 font-medium text-white">{ex.exercise_name}</td>
                              <td className="py-1.5 font-mono">{ex.sets}</td>
                              <td className="py-1.5 font-mono">{ex.reps}</td>
                              <td className="py-1.5 font-mono">{ex.weight_kg} kg</td>
                              <td className="py-1.5 font-mono text-[#888888]">
                                {(ex.sets * ex.reps * ex.weight_kg).toLocaleString()} kg
                              </td>
                              <td className="py-1.5">
                                <span
                                  className={`text-[9px] px-1.5 py-0.5 rounded ${
                                    ex.status === 'skipped'
                                      ? 'bg-rose-950/40 text-rose-400'
                                      : ex.status === 'modified'
                                      ? 'bg-amber-950/40 text-amber-400'
                                      : 'bg-[#1F1F1F] text-[#AAAAAA]'
                                  }`}
                                >
                                  {ex.status || 'completed'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {w.notes && (
                    <div className="text-[11px] text-[#777777] italic bg-[#101010] p-2 rounded border border-[#222222]">
                      "{w.notes}"
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Column: AI Workout Coach Chat */}
      <div className="w-full xl:w-[420px] min-h-[500px] flex flex-col">
        <UnifiedChat
          workspace="workout"
          title="LifeSync AI • Strength Coach"
          subtitle="Biomechanics, progressive overload & training programming"
          suggestedPrompts={[
            "Analyze my recent workout volume and suggest progressive overload steps.",
            "I'm feeling fatigued in my lower back. What squat alternatives should I do?",
            "Structure a 5-day hypertrophy split targeting upper chest and lats."
          ]}
        />
      </div>

      {/* Log / Interactive Session Modal */}
      {showLogModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-[#121212] border border-[#2D2D2D] rounded shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="px-5 py-4 border-b border-[#242424] flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-semibold text-white">
                    {editingWorkoutId ? 'Edit Completed Workout' : 'Live Workout Session & Logging'}
                  </h2>
                  {timerActive && (
                    <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3 animate-spin" /> {formatTimer(elapsedSeconds)}
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-[#737373]">
                  Synchronizes verified training activity to Supabase and FalkorDB graph memory
                </p>
              </div>
              <button
                onClick={() => {
                  setShowLogModal(false);
                  setTimerActive(false);
                }}
                className="p-1 rounded text-[#737373] hover:text-white hover:bg-[#202020]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmitWorkout} className="p-5 space-y-4 max-h-[80vh] overflow-y-auto">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-[#A3A3A3] mb-1">Workout Title</label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Upper Body Push A"
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-[#A3A3A3] mb-1">Category</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                  >
                    <option value="Strength">Strength</option>
                    <option value="Hypertrophy">Hypertrophy</option>
                    <option value="Cardio">Cardio</option>
                    <option value="Mobility">Mobility & Restorative</option>
                    <option value="HIIT">HIIT / Conditioning</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Duration (minutes)</label>
                  <input
                    type="number"
                    value={duration}
                    onChange={(e) => setDuration(Number(e.target.value))}
                    min="1"
                    max="300"
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Est. Calories Burned</label>
                  <input
                    type="number"
                    value={calories || 0}
                    onChange={(e) => setCalories(Number(e.target.value))}
                    min="0"
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Perceived Exertion (RPE)</label>
                  <select
                    value={rpe}
                    onChange={(e) => setRpe(Number(e.target.value))}
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                  >
                    <option value={5}>RPE 5 (Warmup / Light)</option>
                    <option value={6}>RPE 6 (4 reps in reserve)</option>
                    <option value={7}>RPE 7 (3 reps in reserve)</option>
                    <option value={8}>RPE 8 (2 reps in reserve)</option>
                    <option value={9}>RPE 9 (1 rep in reserve)</option>
                    <option value={10}>RPE 10 (Maximum Effort)</option>
                  </select>
                </div>
              </div>

              {/* Exercise Table with status toggles */}
              <div className="pt-2 border-t border-[#222222]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] uppercase tracking-wider text-[#666666] font-semibold">
                    Exercises Performed
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setShowWgerModal(true)}
                      className="text-[11px] text-[#8E8E8E] hover:text-white flex items-center gap-1"
                    >
                      <Search className="w-3 h-3" /> wger Library
                    </button>
                    <button
                      type="button"
                      onClick={addExerciseRow}
                      className="text-[11px] text-[#EDEDED] hover:underline flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" /> Add Exercise
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  {exercises.map((ex, idx) => (
                    <div
                      key={idx}
                      className={`p-2.5 rounded border transition-colors ${
                        ex.status === 'skipped'
                          ? 'bg-[#141010] border-[#382020] opacity-60'
                          : 'bg-[#171717] border-[#2B2B2B]'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          placeholder="Exercise name"
                          value={ex.exercise_name}
                          onChange={(e) => updateExercise(idx, 'exercise_name', e.target.value)}
                          className="flex-1 px-2 py-1 text-xs bg-[#101010] border border-[#333333] rounded text-white"
                          required
                        />
                        <input
                          type="number"
                          placeholder="Sets"
                          value={ex.sets}
                          onChange={(e) => updateExercise(idx, 'sets', Number(e.target.value))}
                          className="w-14 px-2 py-1 text-xs bg-[#101010] border border-[#333333] rounded text-white text-center"
                          min="1"
                        />
                        <input
                          type="number"
                          placeholder="Reps"
                          value={ex.reps}
                          onChange={(e) => updateExercise(idx, 'reps', Number(e.target.value))}
                          className="w-14 px-2 py-1 text-xs bg-[#101010] border border-[#333333] rounded text-white text-center"
                          min="1"
                        />
                        <input
                          type="number"
                          placeholder="Weight (kg)"
                          value={ex.weight_kg}
                          onChange={(e) => updateExercise(idx, 'weight_kg', Number(e.target.value))}
                          className="w-20 px-2 py-1 text-xs bg-[#101010] border border-[#333333] rounded text-white text-center"
                          min="0"
                          step="0.5"
                        />
                        <select
                          value={ex.status || 'completed'}
                          onChange={(e) => updateExercise(idx, 'status', e.target.value)}
                          className="px-2 py-1 text-[11px] bg-[#101010] border border-[#333333] rounded text-[#CCCCCC]"
                        >
                          <option value="completed">Completed</option>
                          <option value="modified">Modified</option>
                          <option value="skipped">Skipped</option>
                        </select>
                        {exercises.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeExerciseRow(idx)}
                            className="p-1 text-[#777777] hover:text-rose-400"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-[11px] text-[#A3A3A3] mb-1">Session Notes (Optional)</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Notes on fatigue, progressive overload, biomechanics..."
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
                  {saving ? 'Recording to Graph Memory...' : editingWorkoutId ? 'Update Workout' : 'Finish & Record Session'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Plan Generation Modal */}
      {showPlanModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#121212] border border-[#2D2D2D] rounded shadow-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[#242424] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <h2 className="text-sm font-semibold text-white">Generate Workout Plan</h2>
              </div>
              <button
                onClick={() => setShowPlanModal(false)}
                className="p-1 rounded text-[#737373] hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div>
                <label className="block text-[11px] font-medium text-[#A3A3A3] mb-1">Focus & Target Split</label>
                <input
                  type="text"
                  value={planFocus}
                  onChange={(e) => setPlanFocus(e.target.value)}
                  placeholder="e.g. Upper Body Push, Posterior Chain, Mobility"
                  className="w-full px-3 py-2 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-[#A3A3A3] mb-1">Target Duration (minutes)</label>
                <input
                  type="number"
                  value={planDuration}
                  onChange={(e) => setPlanDuration(Number(e.target.value))}
                  min="15"
                  max="120"
                  className="w-full px-3 py-2 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                />
              </div>

              <div className="p-3 bg-[#171717] rounded border border-[#262626] text-[11px] text-[#888888]">
                Workout AI automatically injects your persistent goals, previous workouts, recovery readiness, and reported injuries into the prompt.
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowPlanModal(false)}
                  className="px-3 py-1.5 text-xs text-[#888888] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleGeneratePlan}
                  disabled={generatingPlan}
                  className="px-4 py-1.5 text-xs bg-[#EDEDED] text-[#0A0A0A] font-semibold rounded hover:bg-white disabled:opacity-50"
                >
                  {generatingPlan ? 'Synthesizing Plan...' : 'Generate Plan'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* wger Exercise Library Search Modal */}
      {showWgerModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-xl bg-[#121212] border border-[#2D2D2D] rounded shadow-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[#242424] flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-semibold text-white">wger Exercise Library</h2>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800">
                    Official API
                  </span>
                </div>
                <p className="text-[11px] text-[#737373]">Live search across 900+ verified exercises</p>
              </div>
              <button
                onClick={() => setShowWgerModal(false)}
                className="p-1 rounded text-[#737373] hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 space-y-3">
              {/* Category Pills */}
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px]">
                {['', 'Chest', 'Back', 'Legs', 'Arms', 'Shoulders', 'Abs', 'Cardio'].map((cat) => (
                  <button
                    key={cat}
                    onClick={() => {
                      setWgerCategory(cat);
                      handleSearchWger(cat);
                    }}
                    className={`px-2.5 py-1 rounded whitespace-nowrap transition-colors ${
                      wgerCategory === cat
                        ? 'bg-white text-black font-semibold'
                        : 'bg-[#1C1C1C] text-[#AAAAAA] hover:bg-[#252525] border border-[#2C2C2C]'
                    }`}
                  >
                    {cat || 'All Categories'}
                  </button>
                ))}
              </div>

              {/* Search input */}
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Search bench press, deadlift, squat, pull-up, curls..."
                  value={wgerQuery}
                  onChange={(e) => setWgerQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearchWger()}
                  className="flex-1 px-3 py-2 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                />
                <button
                  onClick={() => handleSearchWger()}
                  disabled={searchingWger}
                  className="px-3.5 py-2 text-xs bg-[#242424] hover:bg-[#303030] border border-[#383838] text-white rounded font-medium"
                >
                  {searchingWger ? 'Searching...' : 'Search'}
                </button>
              </div>

              {/* Results List */}
              <div className="max-h-80 overflow-y-auto space-y-1.5 divide-y divide-[#1A1A1A]">
                {wgerResults.map((ex) => (
                  <div
                    key={ex.id}
                    onClick={() => handleSelectWgerExercise(ex)}
                    className="p-2.5 rounded hover:bg-[#1A1A1A] cursor-pointer flex items-center justify-between transition-colors group"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-white group-hover:text-emerald-400 transition-colors">
                          {ex.name}
                        </span>
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-[#202020] text-emerald-400 border border-[#303030]">
                          {ex.source === 'wger_verified' ? 'wger verified' : 'local cache'}
                        </span>
                      </div>
                      <div className="text-[10px] text-[#737373]">
                        {ex.category} • {ex.muscles?.join(', ') || 'General'}
                        {ex.equipment && ex.equipment.length > 0 && ` • Eq: ${ex.equipment.join(', ')}`}
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-[#555555] group-hover:text-white transition-colors" />
                  </div>
                ))}
                {wgerResults.length === 0 && !searchingWger && (
                  <div className="text-center py-8 text-xs text-[#666666]">
                    No exercises found matching your query.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

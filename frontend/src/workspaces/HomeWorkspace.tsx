import React, { useEffect, useState } from 'react';
import {
  Flame,
  Moon,
  Dumbbell,
  Clock,
  ArrowRight,
  Sparkles,
  CheckCircle2,
} from 'lucide-react';
import { UnifiedChat } from '../components/UnifiedChat';
import {
  api,
  UserProfile,
  HealthResponse,
  DailyWellnessOverview,
} from '../api/client';
import { WorkspaceType } from '../components/Sidebar';

interface HomeWorkspaceProps {
  profile: UserProfile | null;
  health: HealthResponse | null;
  onNavigate: (workspace: WorkspaceType) => void;
}

export const HomeWorkspace: React.FC<HomeWorkspaceProps> = ({
  profile,
  health,
  onNavigate,
}) => {
  const [overview, setOverview] = useState<DailyWellnessOverview | null>(null);

  const loadOverview = async () => {
    try {
      const data = await api.getHomeOverview();
      setOverview(data);
    } catch (e) {
      console.error('Failed to load home overview:', e);
    }
  };

  useEffect(() => {
    loadOverview();
  }, []);

  const todayRecovery = overview?.today_recovery;
  const recoveryScore = todayRecovery?.recovery_score ?? null;
  const sleepHours = todayRecovery?.sleep_hours;
  const hydrationLiters = todayRecovery?.hydration_liters;

  const todayMacros = overview?.today_macros || { calories: 0, protein: 0, carbs: 0, fat: 0, fiber: 0 };
  const macroTargets = overview?.macro_targets || {
    calorie_target: profile?.calorie_target || 2200,
    protein_target: profile?.protein_target || 160,
    carbs_target: profile?.carbs_target || 220,
    fat_target: profile?.fat_target || 65,
  };

  const todayWorkouts = overview?.today_workouts || [];
  const activePlan = overview?.active_workout_plan;

  return (
    <div className="h-full flex flex-col lg:flex-row gap-4 p-4 sm:p-6 overflow-y-auto bg-[#0A0A0A]">
      {/* Left Column: Unified AI Conversation */}
      <div className="flex-1 min-h-[500px] lg:min-h-0 flex flex-col">
        <UnifiedChat
          workspace="home"
          title="LifeSync AI Assistant"
          subtitle="Your daily health & wellness companion"
          suggestedPrompts={[
            "How am I doing today overall?",
            "Should I train hard today or take it easy?",
            "What's a quick high-protein dinner idea?",
            "How can I improve my sleep tonight?"
          ]}
        />
      </div>

      {/* Right Column: Telemetry & Activity Timeline */}
      <div className="w-full lg:w-[420px] flex flex-col gap-4">
        {/* Today's Wellness Snapshot */}
        <div className="p-4 bg-[#141414] border border-[#262626] rounded space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#999999]">
              Today's Performance Snapshot
            </span>
            <span className="text-[10px] text-[#666666]">
              {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            {/* Recovery Readiness Card */}
            <div
              onClick={() => onNavigate('recovery')}
              className="p-3 bg-[#181818] border border-[#2B2B2B] hover:border-[#3D3D3D] rounded cursor-pointer transition-colors"
            >
              <div className="flex items-center justify-between text-[#888888] mb-1">
                <span className="text-[11px] font-medium flex items-center gap-1.5">
                  <Moon className="w-3.5 h-3.5 text-[#B0B0B0]" /> Recovery
                </span>
                <span className="text-[10px] text-emerald-400 font-mono">
                  {overview?.readiness_status.split(' ')[0] || 'Adequate'}
                </span>
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-xl font-bold font-mono text-white">
                  {recoveryScore !== null ? recoveryScore : '—'}
                </span>
                <span className="text-[10px] text-[#737373]">/ 100</span>
              </div>
              <div className="text-[10px] text-[#888888] mt-1">
                {sleepHours ? `${sleepHours}h sleep` : 'Sleep unlogged'} • {hydrationLiters ? `${hydrationLiters}L water` : 'Hydration unlogged'}
              </div>
            </div>

            {/* Nutrition Calorie Card */}
            <div
              onClick={() => onNavigate('nutrition')}
              className="p-3 bg-[#181818] border border-[#2B2B2B] hover:border-[#3D3D3D] rounded cursor-pointer transition-colors"
            >
              <div className="flex items-center justify-between text-[#888888] mb-1">
                <span className="text-[11px] font-medium flex items-center gap-1.5">
                  <Flame className="w-3.5 h-3.5 text-[#B0B0B0]" /> Nutrition
                </span>
                <span className="text-[10px] text-[#A3A3A3] font-mono">
                  {Math.round((todayMacros.calories / (macroTargets.calorie_target || 1)) * 100)}%
                </span>
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-xl font-bold font-mono text-white">
                  {Math.round(todayMacros.calories)}
                </span>
                <span className="text-[10px] text-[#737373]">/ {macroTargets.calorie_target} kcal</span>
              </div>
              <div className="text-[10px] text-[#888888] mt-1">
                {Math.round(todayMacros.protein)}g / {macroTargets.protein_target}g Protein
              </div>
            </div>
          </div>

          {/* Training Session / Plan Highlight */}
          <div
            onClick={() => onNavigate('workout')}
            className="p-3 bg-[#181818] border border-[#2B2B2B] hover:border-[#3D3D3D] rounded flex items-center justify-between cursor-pointer transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded bg-[#222222] border border-[#333333] flex items-center justify-center shrink-0">
                <Dumbbell className="w-3.5 h-3.5 text-[#D4D4D4]" />
              </div>
              <div>
                <div className="text-xs font-medium text-white">
                  {todayWorkouts.length > 0
                    ? todayWorkouts[0].title
                    : activePlan
                    ? `Ready: ${activePlan.title}`
                    : 'No workout logged today'}
                </div>
                <div className="text-[10px] text-[#737373]">
                  {todayWorkouts.length > 0
                    ? `${todayWorkouts[0].category} • ${todayWorkouts[0].duration_minutes} min • ${todayWorkouts[0].workout_exercises?.length || 0} exercises`
                    : activePlan
                    ? `${activePlan.plan_data?.category || 'Strength'} • ${activePlan.plan_data?.estimated_duration_minutes || 45} min`
                    : 'Tap to generate a plan or log training'}
                </div>
              </div>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-[#737373]" />
          </div>
        </div>

        {/* AI Cross-Workspace Synthesis Insights */}
        {overview?.ai_insights && overview.ai_insights.length > 0 && (
          <div className="p-4 bg-[#141414] border border-[#262626] rounded space-y-2.5">
            <div className="flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-xs font-semibold uppercase tracking-wider text-[#999999]">
                Today's Highlights
              </span>
            </div>
            <div className="space-y-2">
              {overview.ai_insights.map((insight, idx) => (
                <div key={idx} className="flex items-start gap-2 text-xs text-[#D4D4D4]">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                  <span>{insight}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Live Infrastructure Status */}
        <div className="p-4 bg-[#141414] border border-[#262626] rounded space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#999999]">
              Connected Systems
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#1C1C1C] text-[#888888] border border-[#2D2D2D]">
              Real-time
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div className="p-2 bg-[#171717] border border-[#262626] rounded flex flex-col">
              <span className="text-[10px] text-[#737373]">Database</span>
              <span className="font-medium text-white flex items-center gap-1 mt-0.5">
                <span className={`w-1.5 h-1.5 rounded-full ${health?.services.supabase?.status === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'}`} /> Supabase
              </span>
              <span className="text-[9px] text-[#666666] font-mono mt-0.5">
                {health?.services.supabase?.latency_ms ? `${health.services.supabase.latency_ms}ms` : 'PostgreSQL RLS'}
              </span>
            </div>

            <div className="p-2 bg-[#171717] border border-[#262626] rounded flex flex-col">
              <span className="text-[10px] text-[#737373]">Persistent Memory</span>
              <span className="font-medium text-white flex items-center gap-1 mt-0.5">
                <span className={`w-1.5 h-1.5 rounded-full ${health?.services.falkordb?.status === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'}`} /> FalkorDB
              </span>
              <span className="text-[9px] text-[#666666] font-mono mt-0.5">
                {health?.services.falkordb?.latency_ms ? `${health.services.falkordb.latency_ms}ms` : 'Graph Engine'}
              </span>
            </div>

            <div className="p-2 bg-[#171717] border border-[#262626] rounded flex flex-col">
              <span className="text-[10px] text-[#737373]">AI Synthesis</span>
              <span className="font-medium text-white flex items-center gap-1 mt-0.5">
                <span className={`w-1.5 h-1.5 rounded-full ${health?.services.gemini?.status === 'healthy' ? 'bg-emerald-500' : 'bg-rose-500'}`} /> Gemini 3.8
              </span>
              <span className="text-[9px] text-[#666666] font-mono mt-0.5">Flash Model</span>
            </div>

            <div className="p-2 bg-[#171717] border border-[#262626] rounded flex flex-col">
              <span className="text-[10px] text-[#737373]">Exercise & Food</span>
              <span className="font-medium text-white flex items-center gap-1 mt-0.5">
                <span className={`w-1.5 h-1.5 rounded-full ${health?.services.wger?.status === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'}`} /> wger & USDA
              </span>
              <span className="text-[9px] text-[#666666] font-mono mt-0.5">Live Databases</span>
            </div>
          </div>
        </div>

        {/* Recent Activity Log */}
        <div className="p-4 bg-[#141414] border border-[#262626] rounded space-y-3 flex-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-[#999999]">
            Recent Meals & Activity
          </span>
          <div className="space-y-2 text-xs">
            {overview?.today_meals && overview.today_meals.length > 0 ? (
              overview.today_meals.slice(0, 3).map((m) => (
                <div key={m.id} className="flex items-start gap-2.5 p-2 bg-[#171717] border border-[#262626] rounded">
                  <Flame className="w-3.5 h-3.5 text-[#888888] mt-0.5" />
                  <div className="flex-1">
                    <div className="text-[11px] font-medium text-white">{m.name}</div>
                    <div className="text-[10px] text-[#777777]">
                      {m.meal_type} • {m.calories} kcal • {m.protein}g Protein
                    </div>
                  </div>
                </div>
              ))
            ) : todayWorkouts.length > 0 ? (
              todayWorkouts.slice(0, 3).map((w) => (
                <div key={w.id} className="flex items-start gap-2.5 p-2 bg-[#171717] border border-[#262626] rounded">
                  <Clock className="w-3.5 h-3.5 text-[#888888] mt-0.5" />
                  <div className="flex-1">
                    <div className="text-[11px] font-medium text-white">{w.title}</div>
                    <div className="text-[10px] text-[#777777]">
                      {w.category} • {w.duration_minutes}m • {new Date(w.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-6 text-[11px] text-[#666666]">
                No activity logged yet today. Use Workout, Nutrition, or Recovery to log items.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

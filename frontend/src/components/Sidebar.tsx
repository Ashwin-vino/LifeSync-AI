import React from 'react';
import {
  Home,
  Dumbbell,
  Utensils,
  Moon,
  PanelLeftClose,
  PanelLeft,
  Activity,
  Sparkles,
  Server,
  Database,
  Brain
} from 'lucide-react';
import { HealthResponse } from '../api/client';

export type WorkspaceType = 'home' | 'workout' | 'nutrition' | 'recovery';

interface SidebarProps {
  currentWorkspace: WorkspaceType;
  onSelectWorkspace: (workspace: WorkspaceType) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  health: HealthResponse | null;
  onRefreshHealth: () => void;
  onOpenMemoryModal?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentWorkspace,
  onSelectWorkspace,
  collapsed,
  onToggleCollapse,
  health,
  onRefreshHealth,
  onOpenMemoryModal,
}) => {
  const workspaces: { id: WorkspaceType; label: string; icon: React.ReactNode; desc: string }[] = [
    {
      id: 'home',
      label: 'Home',
      icon: <Home className="w-4 h-4" />,
      desc: 'AI Assistant & Daily Summary',
    },
    {
      id: 'workout',
      label: 'Workout',
      icon: <Dumbbell className="w-4 h-4" />,
      desc: 'Athletic Training & Logs',
    },
    {
      id: 'nutrition',
      label: 'Nutrition',
      icon: <Utensils className="w-4 h-4" />,
      desc: 'Macro Tracking & USDA Database',
    },
    {
      id: 'recovery',
      label: 'Recovery',
      icon: <Moon className="w-4 h-4" />,
      desc: 'Sleep, HRV & Readiness',
    },
  ];

  const allHealthy = health?.status === 'healthy';

  return (
    <aside
      className={`fixed md:static inset-y-0 left-0 z-40 flex flex-col bg-[#0E0E0E] border-r border-[#262626] transition-all duration-200 select-none ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Brand & Collapse Header */}
      <div className="h-14 px-3 flex items-center justify-between border-b border-[#222222]">
        {!collapsed && (
          <div className="flex items-center gap-2.5 px-2">
            <div className="w-7 h-7 rounded bg-[#1C1C1C] border border-[#333333] flex items-center justify-center">
              <Activity className="w-4 h-4 text-[#E5E5E5]" />
            </div>
            <div className="flex flex-col">
              <span className="text-xs font-semibold tracking-wider uppercase text-[#E5E5E5]">
                LifeSync AI
              </span>
              <span className="text-[10px] text-[#737373] tracking-wide">
                Intelligence Platform
              </span>
            </div>
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="p-2 rounded text-[#8E8E8E] hover:text-[#EDEDED] hover:bg-[#1A1A1A] transition-colors ml-auto"
        >
          {collapsed ? <PanelLeft className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 py-4 px-2 space-y-1">
        <div className={`px-2 pb-2 text-[10px] uppercase tracking-wider text-[#666666] font-medium ${collapsed ? 'text-center' : ''}`}>
          {collapsed ? '•' : 'Workspaces'}
        </div>
        {workspaces.map((ws) => {
          const isActive = currentWorkspace === ws.id;
          return (
            <button
              key={ws.id}
              onClick={() => onSelectWorkspace(ws.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded text-left transition-colors ${
                isActive
                  ? 'bg-[#1E1E1E] text-white border border-[#333333]'
                  : 'text-[#A1A1A1] hover:text-white hover:bg-[#151515] border border-transparent'
              }`}
              title={ws.label}
            >
              <div
                className={`flex-shrink-0 ${
                  isActive ? 'text-white' : 'text-[#8E8E8E]'
                }`}
              >
                {ws.icon}
              </div>
              {!collapsed && (
                <div className="flex flex-col overflow-hidden">
                  <span className="text-xs font-medium tracking-wide truncate">{ws.label}</span>
                  <span className="text-[10px] text-[#666666] truncate">{ws.desc}</span>
                </div>
              )}
            </button>
          );
        })}
        {/* Persistent Memory Inspector */}
        <div className="pt-3 mt-2 border-t border-[#1C1C1C]">
          <button
            onClick={onOpenMemoryModal}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded text-left transition-colors text-[#A1A1A1] hover:text-white hover:bg-[#151515] border border-transparent"
            title="Inspect & Correct Stored Memories"
          >
            <div className="flex-shrink-0 text-[#8E8E8E]">
              <Brain className="w-4 h-4" />
            </div>
            {!collapsed && (
              <div className="flex flex-col overflow-hidden">
                <span className="text-xs font-medium tracking-wide truncate">Persistent Memory</span>
                <span className="text-[10px] text-[#666666] truncate">Inspect & Correct Facts</span>
              </div>
            )}
          </button>
        </div>
      </div>

      {/* Live System Integration Telemetry */}
      <div className="p-3 border-t border-[#222222] bg-[#0A0A0A]">
        {!collapsed ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-wider text-[#666666] font-medium">
                Live Subsystems
              </span>
              <button
                onClick={onRefreshHealth}
                className="text-[10px] text-[#8E8E8E] hover:text-white transition-colors"
                title="Refresh system status"
              >
                Sync
              </button>
            </div>
            <div className="space-y-1.5 text-[11px]">
              <div className="flex items-center justify-between text-[#8E8E8E]">
                <span className="flex items-center gap-1.5">
                  <Database className="w-3 h-3 text-[#A1A1A1]" /> Supabase
                </span>
                <span className="flex items-center gap-1 text-[10px] text-[#A3A3A3]">
                  <span className={`w-1.5 h-1.5 rounded-full ${health?.services.supabase?.status === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                  {health?.services.supabase?.latency_ms ? `${health.services.supabase.latency_ms}ms` : 'Ready'}
                </span>
              </div>
              <div className="flex items-center justify-between text-[#8E8E8E]">
                <span className="flex items-center gap-1.5">
                  <Server className="w-3 h-3 text-[#A1A1A1]" /> FalkorDB Graph
                </span>
                <span className="flex items-center gap-1 text-[10px] text-[#A3A3A3]">
                  <span className={`w-1.5 h-1.5 rounded-full ${health?.services.falkordb?.status === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                  {health?.services.falkordb?.latency_ms ? `${health.services.falkordb.latency_ms}ms` : 'Ready'}
                </span>
              </div>
              <div className="flex items-center justify-between text-[#8E8E8E]">
                <span className="flex items-center gap-1.5">
                  <Sparkles className="w-3 h-3 text-[#A1A1A1]" /> Gemini 3.8
                </span>
                <span className="flex items-center gap-1 text-[10px] text-[#A3A3A3]">
                  <span className={`w-1.5 h-1.5 rounded-full ${health?.services.gemini?.status === 'healthy' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                  Live
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex justify-center" title="All systems connected">
            <span
              className={`w-2 h-2 rounded-full ${
                allHealthy ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
          </div>
        )}
      </div>
    </aside>
  );
};

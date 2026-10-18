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
import { useAuth } from '../context/AuthContext';

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
  const { user, openAuthModal } = useAuth();
  const userAvatar = user?.user_metadata?.avatar_url || user?.user_metadata?.picture;
  const userName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User';

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

      {/* User Google Authentication Quick-Action */}
      <div className="p-3 border-t border-[#222222] bg-[#0E0E0E]">
        {!collapsed ? (
          user ? (
            <button
              onClick={openAuthModal}
              className="w-full flex items-center gap-2.5 p-2 rounded-lg bg-[#161616] hover:bg-[#1E1E1E] border border-[#262626] hover:border-[#383838] transition-colors text-left"
              title="Manage account & sign out"
            >
              {userAvatar ? (
                <img
                  src={userAvatar}
                  alt={userName}
                  className="w-6 h-6 rounded-full object-cover border border-[#404040]"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <div className="w-6 h-6 rounded-full bg-[#262626] flex items-center justify-center text-[10px] font-semibold text-white">
                  {userName[0]?.toUpperCase() || 'U'}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-[#EAEAEA] truncate">{userName}</p>
                <p className="text-[10px] text-[#787878] truncate flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Google Verified
                </p>
              </div>
            </button>
          ) : (
            <button
              id="sidebar-google-signin-btn"
              onClick={openAuthModal}
              className="w-full flex items-center justify-center gap-2 p-2 rounded-lg bg-[#161616] hover:bg-[#1E1E1E] border border-[#2D2D2D] hover:border-[#404040] text-xs font-medium text-[#EDEDED] transition-colors shadow-sm"
            >
              <svg className="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
                />
                <path
                  fill="#34A853"
                  d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.34 24 12 24z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
                />
                <path
                  fill="#EA4335"
                  d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.34 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
                />
              </svg>
              <span>Continue with Google</span>
            </button>
          )
        ) : (
          <div className="flex justify-center">
            {user ? (
              <button
                onClick={openAuthModal}
                className="relative"
                title={`Logged in as ${user.email}`}
              >
                {userAvatar ? (
                  <img
                    src={userAvatar}
                    alt={userName}
                    className="w-6 h-6 rounded-full object-cover border border-[#404040]"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <div className="w-6 h-6 rounded-full bg-[#262626] flex items-center justify-center text-[10px] font-semibold text-white">
                    {userName[0]?.toUpperCase() || 'U'}
                  </div>
                )}
                <span className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-500 border border-[#0A0A0A]" />
              </button>
            ) : (
              <button
                onClick={openAuthModal}
                className="p-1 rounded hover:bg-[#202020]"
                title="Sign in with Google"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.34 24 12 24z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.34 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
                  />
                </svg>
              </button>
            )}
          </div>
        )}
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

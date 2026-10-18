import React from 'react';
import { Menu, Settings } from 'lucide-react';
import { WorkspaceType } from './Sidebar';
import { UserProfile } from '../api/client';

interface HeaderProps {
  currentWorkspace: WorkspaceType;
  profile: UserProfile | null;
  onOpenProfileModal: () => void;
  onToggleMobileSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentWorkspace,
  profile,
  onOpenProfileModal,
  onToggleMobileSidebar,
}) => {
  const titles: Record<WorkspaceType, { title: string; subtitle: string }> = {
    home: {
      title: 'Home Intelligence',
      subtitle: 'Unified AI, daily snapshot & cross-domain telemetry',
    },
    workout: {
      title: 'Athletic Performance',
      subtitle: 'Volume programming, exercise logs & wger exercise registry',
    },
    nutrition: {
      title: 'Nutritional Intake',
      subtitle: 'Macro distribution & USDA FoodData Central integration',
    },
    recovery: {
      title: 'Rest & Autonomic Recovery',
      subtitle: 'Sleep metrics, hydration status & readiness index',
    },
  };

  const current = titles[currentWorkspace];

  return (
    <header className="h-14 px-4 sm:px-6 bg-[#0E0E0E] border-b border-[#222222] flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleMobileSidebar}
          className="md:hidden p-2 text-[#8E8E8E] hover:text-white rounded hover:bg-[#1A1A1A]"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-sm font-semibold tracking-tight text-[#EAEAEA]">
            {current.title}
          </h1>
          <p className="text-[11px] text-[#737373] hidden sm:block">
            {current.subtitle}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        <button
          onClick={onOpenProfileModal}
          className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-[#161616] border border-[#2D2D2D] hover:border-[#404040] text-xs text-[#D4D4D4] transition-colors"
        >
          <div className="w-5 h-5 rounded-full bg-[#262626] flex items-center justify-center text-[10px] text-white font-medium">
            {profile?.display_name ? profile.display_name[0].toUpperCase() : 'A'}
          </div>
          <span className="font-medium hidden sm:inline">
            {profile?.display_name || 'Ashwin'}
          </span>
          <Settings className="w-3.5 h-3.5 text-[#888888] ml-0.5" />
        </button>
      </div>
    </header>
  );
};

import React from 'react';
import { Menu, Settings } from 'lucide-react';
import { WorkspaceType } from './Sidebar';
import { UserProfile } from '../api/client';
import { useAuth } from '../context/AuthContext';

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
  const { user, openAuthModal } = useAuth();

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
  const userAvatar = user?.user_metadata?.avatar_url || user?.user_metadata?.picture;
  const displayName =
    user?.user_metadata?.full_name ||
    user?.user_metadata?.name ||
    profile?.display_name ||
    user?.email?.split('@')[0] ||
    'Ashwin';

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
        {user ? (
          /* Authenticated User Pill */
          <div className="flex items-center gap-1.5">
            <button
              onClick={openAuthModal}
              title={`Authenticated as ${user.email} (click to view account)`}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#161616] border border-[#2D2D2D] hover:border-[#444444] text-xs text-[#D4D4D4] transition-colors"
            >
              {userAvatar ? (
                <img
                  src={userAvatar}
                  alt={displayName}
                  className="w-5 h-5 rounded-full object-cover border border-[#404040]"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <div className="w-5 h-5 rounded-full bg-[#262626] flex items-center justify-center text-[10px] text-white font-medium">
                  {displayName[0]?.toUpperCase() || 'U'}
                </div>
              )}
              <span className="font-medium hidden sm:inline max-w-[120px] truncate">
                {displayName}
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 hidden sm:inline" />
            </button>

            <button
              onClick={onOpenProfileModal}
              title="Daily Target Settings"
              className="p-1.5 rounded-lg bg-[#161616] border border-[#2D2D2D] hover:border-[#404040] text-[#888888] hover:text-[#EAEAEA] transition-colors"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        ) : (
          /* Unauthenticated State: Continue with Google / Sign In */
          <div className="flex items-center gap-2">
            <button
              id="header-google-signin-btn"
              onClick={openAuthModal}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#161616] hover:bg-[#202020] border border-[#2D2D2D] hover:border-[#454545] text-xs font-medium text-[#EDEDED] transition-colors shadow-sm"
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

            <button
              onClick={onOpenProfileModal}
              title="Daily Target Settings"
              className="p-1.5 rounded-lg bg-[#161616] border border-[#2D2D2D] hover:border-[#404040] text-[#888888] hover:text-[#EAEAEA] transition-colors"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};

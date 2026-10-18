import React from 'react';
import { X, ShieldCheck, LogOut, Loader2, AlertCircle, Sparkles, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const AuthModal: React.FC = () => {
  const {
    user,
    loading,
    error,
    authModalOpen,
    closeAuthModal,
    signInWithGoogle,
    signOut,
    clearError,
  } = useAuth();

  if (!authModalOpen) return null;

  const userAvatar = user?.user_metadata?.avatar_url || user?.user_metadata?.picture;
  const userName = user?.user_metadata?.full_name || user?.user_metadata?.name || user?.email?.split('@')[0] || 'User';
  const userEmail = user?.email || '';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in"
      onClick={closeAuthModal}
    >
      <div
        className="w-full max-w-md bg-[#121212] border border-[#262626] rounded-xl shadow-2xl overflow-hidden relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#222222] bg-[#161616]">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <h2 className="text-sm font-semibold tracking-wide text-[#EDEDED] uppercase">
              {user ? 'Account & Authentication' : 'Sign in to LifeSync AI'}
            </h2>
          </div>
          <button
            onClick={closeAuthModal}
            className="p-1 rounded text-[#888888] hover:text-white hover:bg-[#242424] transition-colors"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          {/* Error Banner */}
          {error && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-200 text-xs">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium">Authentication Error</p>
                <p className="text-rose-300/90 mt-0.5">{error}</p>
              </div>
              <button
                onClick={clearError}
                className="text-rose-400 hover:text-white text-xs font-semibold px-1"
              >
                ✕
              </button>
            </div>
          )}

          {user ? (
            /* Signed In View */
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-[#181818] border border-[#282828] flex items-center gap-3.5">
                {userAvatar ? (
                  <img
                    src={userAvatar}
                    alt={userName}
                    className="w-12 h-12 rounded-full border border-[#3A3A3A] object-cover"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <div className="w-12 h-12 rounded-full bg-[#2A2A2A] border border-[#3A3A3A] flex items-center justify-center text-base font-semibold text-white">
                    {userName[0]?.toUpperCase() || 'U'}
                  </div>
                )}

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <p className="text-sm font-medium text-[#F0F0F0] truncate">{userName}</p>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                  </div>
                  <p className="text-xs text-[#8A8A8A] truncate">{userEmail}</p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-[#222222] text-[#A0A0A0] border border-[#303030]">
                      Google OAuth
                    </span>
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-950/50 text-emerald-300 border border-emerald-800/40">
                      Supabase Authenticated
                    </span>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-[#141414] border border-[#202020] space-y-1.5 text-xs text-[#9E9E9E]">
                <div className="flex items-center gap-2 text-[#D0D0D0] font-medium">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>Secure Cross-Agent Memory Sync Active</span>
                </div>
                <p className="text-[11px] leading-relaxed text-[#787878]">
                  Your authenticated session transmits verified JWT bearer credentials directly to the FastAPI backend, isolating workouts, USDA nutrition logs, and FalkorDB knowledge graph memory to your account.
                </p>
              </div>

              <div className="pt-2 flex items-center gap-3">
                <button
                  type="button"
                  onClick={signOut}
                  disabled={loading}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#1C1C1C] hover:bg-[#252525] border border-[#333333] hover:border-[#444444] text-xs font-medium text-[#EDEDED] transition-colors disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin text-[#A0A0A0]" />
                  ) : (
                    <LogOut className="w-4 h-4 text-[#A0A0A0]" />
                  )}
                  <span>Sign Out</span>
                </button>

                <button
                  type="button"
                  onClick={closeAuthModal}
                  className="flex-1 px-4 py-2.5 rounded-lg bg-white hover:bg-[#EAEAEA] text-black text-xs font-semibold transition-colors"
                >
                  Return to Dashboard
                </button>
              </div>
            </div>
          ) : (
            /* Signed Out View */
            <div className="space-y-4">
              <div className="text-center space-y-1.5">
                <div className="w-10 h-10 rounded-full bg-[#1E1E1E] border border-[#303030] flex items-center justify-center mx-auto mb-2 text-[#E0E0E0]">
                  <Sparkles className="w-5 h-5 text-emerald-400" />
                </div>
                <h3 className="text-base font-semibold text-[#FAFAFA]">Welcome to LifeSync AI</h3>
                <p className="text-xs text-[#8A8A8A] max-w-xs mx-auto leading-relaxed">
                  Sign in with your Google account to unlock multi-agent persistent memory, biometrics synchronization, and personalized recommendations.
                </p>
              </div>

              {/* Continue with Google Button */}
              <div className="pt-2">
                <button
                  type="button"
                  id="google-signin-btn"
                  onClick={signInWithGoogle}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-lg bg-[#1B1B1B] hover:bg-[#242424] active:bg-[#2B2B2B] border border-[#333333] hover:border-[#4B4B4B] text-sm font-medium text-[#FFFFFF] shadow-sm transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed group"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin text-[#999999]" />
                  ) : (
                    <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24">
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
                  )}
                  <span>
                    {loading ? 'Connecting with Google...' : 'Continue with Google'}
                  </span>
                </button>
              </div>

              {/* Privacy and Security Footnote */}
              <div className="pt-2 border-t border-[#1F1F1F]">
                <div className="flex items-center justify-center gap-1.5 text-[11px] text-[#666666]">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#555555]" />
                  <span>Secured by Supabase Auth with PostgreSQL RLS</span>
                </div>
                <p className="text-[10px] text-center text-[#555555] mt-1">
                  Works seamlessly on both localhost and production Vercel domains.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

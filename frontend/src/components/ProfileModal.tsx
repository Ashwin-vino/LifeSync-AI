import React, { useState, useEffect } from 'react';
import { X, Save, Check, LogOut } from 'lucide-react';
import { UserProfile } from '../api/client';
import { useAuth } from '../context/AuthContext';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  profile: UserProfile | null;
  onSave: (data: Partial<UserProfile>) => Promise<void>;
}

export const ProfileModal: React.FC<ProfileModalProps> = ({
  isOpen,
  onClose,
  profile,
  onSave,
}) => {
  const { user, signInWithGoogle, signOut, loading: authLoading } = useAuth();
  const [formData, setFormData] = useState<Partial<UserProfile>>({
    display_name: '',
    primary_goal: '',
    calorie_target: 2200,
    protein_target: 160,
    carbs_target: 220,
    fat_target: 65,
    sleep_target_hours: 8.0,
    water_target_liters: 3.0,
  });
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (profile) {
      setFormData({
        display_name: profile.display_name || user?.user_metadata?.full_name || '',
        primary_goal: profile.primary_goal,
        calorie_target: profile.calorie_target,
        protein_target: profile.protein_target,
        carbs_target: profile.carbs_target,
        fat_target: profile.fat_target,
        sleep_target_hours: profile.sleep_target_hours,
        water_target_liters: profile.water_target_liters,
      });
    } else if (user) {
      setFormData((prev) => ({
        ...prev,
        display_name: prev.display_name || user.user_metadata?.full_name || user.email?.split('@')[0] || '',
      }));
    }
  }, [profile, user]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(formData);
      setSavedSuccess(true);
      setTimeout(() => {
        setSavedSuccess(false);
        onClose();
      }, 700);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-md bg-[#121212] border border-[#2D2D2D] rounded shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="px-5 py-4 border-b border-[#242424] flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white">Profile & Target Metrics</h2>
            <p className="text-[11px] text-[#737373]">Configure baseline targets for AI grounding</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-[#737373] hover:text-white hover:bg-[#202020]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Authentication Quick-Status Card */}
        <div className="px-5 pt-4 pb-0">
          <div className="p-3 rounded bg-[#161616] border border-[#262626] flex items-center justify-between gap-3">
            {user ? (
              <>
                <div className="flex items-center gap-2.5 min-w-0">
                  {user.user_metadata?.avatar_url ? (
                    <img
                      src={user.user_metadata.avatar_url}
                      alt="Avatar"
                      className="w-7 h-7 rounded-full object-cover border border-[#3A3A3A]"
                      referrerPolicy="no-referrer"
                    />
                  ) : (
                    <div className="w-7 h-7 rounded-full bg-[#262626] flex items-center justify-center text-xs font-semibold text-white">
                      {(user.email || 'U')[0].toUpperCase()}
                    </div>
                  )}
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-[#EAEAEA] truncate">
                      {user.user_metadata?.full_name || user.email}
                    </p>
                    <p className="text-[10px] text-[#787878] truncate flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      Google Authenticated
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={signOut}
                  disabled={authLoading}
                  className="flex items-center gap-1.5 px-2.5 py-1 text-[11px] rounded bg-[#202020] hover:bg-[#2B2B2B] text-[#B0B0B0] hover:text-white border border-[#333333] transition-colors"
                >
                  <LogOut className="w-3 h-3" />
                  <span>Sign Out</span>
                </button>
              </>
            ) : (
              <>
                <div className="text-xs text-[#9E9E9E]">
                  <p className="text-[#D4D4D4] font-medium text-xs">Guest Mode</p>
                  <p className="text-[10px] text-[#707070]">Sign in to sync data across devices</p>
                </div>
                <button
                  type="button"
                  onClick={signInWithGoogle}
                  disabled={authLoading}
                  className="flex items-center gap-2 px-2.5 py-1.5 text-xs rounded bg-[#222222] hover:bg-[#2A2A2A] text-white border border-[#383838] transition-colors"
                >
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24">
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
                  <span>Google Sign In</span>
                </button>
              </>
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-[#A3A3A3] mb-1">
                Display Name
              </label>
              <input
                type="text"
                value={formData.display_name || ''}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white focus:border-[#555555]"
                required
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[#A3A3A3] mb-1">
                Primary Goal
              </label>
              <input
                type="text"
                value={formData.primary_goal || ''}
                onChange={(e) => setFormData({ ...formData, primary_goal: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white focus:border-[#555555]"
                placeholder="Strength, Fat Loss, etc."
              />
            </div>
          </div>

          <div className="pt-2 border-t border-[#222222]">
            <span className="text-[10px] uppercase tracking-wider text-[#666666] font-semibold">
              Daily Macro & Calorie Targets
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] text-[#A3A3A3] mb-1">Calories (kcal)</label>
              <input
                type="number"
                value={formData.calorie_target || 2200}
                onChange={(e) => setFormData({ ...formData, calorie_target: Number(e.target.value) })}
                className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                min="1000"
                max="8000"
              />
            </div>
            <div>
              <label className="block text-[11px] text-[#A3A3A3] mb-1">Protein (g)</label>
              <input
                type="number"
                value={formData.protein_target || 160}
                onChange={(e) => setFormData({ ...formData, protein_target: Number(e.target.value) })}
                className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                min="30"
                max="400"
              />
            </div>
            <div>
              <label className="block text-[11px] text-[#A3A3A3] mb-1">Carbohydrates (g)</label>
              <input
                type="number"
                value={formData.carbs_target || 220}
                onChange={(e) => setFormData({ ...formData, carbs_target: Number(e.target.value) })}
                className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                min="20"
                max="800"
              />
            </div>
            <div>
              <label className="block text-[11px] text-[#A3A3A3] mb-1">Fat (g)</label>
              <input
                type="number"
                value={formData.fat_target || 65}
                onChange={(e) => setFormData({ ...formData, fat_target: Number(e.target.value) })}
                className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                min="10"
                max="250"
              />
            </div>
          </div>

          <div className="pt-2 border-t border-[#222222]">
            <span className="text-[10px] uppercase tracking-wider text-[#666666] font-semibold">
              Recovery Baselines
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] text-[#A3A3A3] mb-1">Sleep Target (hours)</label>
              <input
                type="number"
                step="0.5"
                value={formData.sleep_target_hours || 8.0}
                onChange={(e) => setFormData({ ...formData, sleep_target_hours: Number(e.target.value) })}
                className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                min="4"
                max="14"
              />
            </div>
            <div>
              <label className="block text-[11px] text-[#A3A3A3] mb-1">Water Target (liters)</label>
              <input
                type="number"
                step="0.25"
                value={formData.water_target_liters || 3.0}
                onChange={(e) => setFormData({ ...formData, water_target_liters: Number(e.target.value) })}
                className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                min="1"
                max="10"
              />
            </div>
          </div>

          <div className="pt-4 flex items-center justify-end gap-2 border-t border-[#242424]">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs text-[#999999] hover:text-white rounded hover:bg-[#1E1E1E]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs bg-[#EDEDED] text-[#0A0A0A] font-medium rounded hover:bg-white disabled:opacity-50 transition-colors"
            >
              {savedSuccess ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-600" /> Saved
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" /> {saving ? 'Saving...' : 'Save Targets'}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import { Sidebar, WorkspaceType } from './components/Sidebar';
import { Header } from './components/Header';
import { ProfileModal } from './components/ProfileModal';
import { MemoryInspectorModal } from './components/MemoryInspectorModal';
import { AuthModal } from './components/AuthModal';
import { HomeWorkspace } from './workspaces/HomeWorkspace';
import { WorkoutWorkspace } from './workspaces/WorkoutWorkspace';
import { NutritionWorkspace } from './workspaces/NutritionWorkspace';
import { RecoveryWorkspace } from './workspaces/RecoveryWorkspace';
import { api, HealthResponse, UserProfile } from './api/client';
import { AuthProvider, useAuth } from './context/AuthContext';

const AppContent: React.FC = () => {
  const { user } = useAuth();
  const [currentWorkspace, setCurrentWorkspace] = useState<WorkspaceType>('home');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [memoryModalOpen, setMemoryModalOpen] = useState(false);

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);

  const refreshHealth = async () => {
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (e) {
      console.error('Health check failed:', e);
    }
  };

  const loadProfile = async () => {
    try {
      const p = await api.getProfile();
      setProfile(p);
    } catch (e) {
      console.error('Profile load failed:', e);
    }
  };

  // Reload profile and telemetry on mount and when authentication changes
  useEffect(() => {
    refreshHealth();
    loadProfile();
  }, [user]);

  const handleSaveProfile = async (updatedData: Partial<UserProfile>) => {
    const updated = await api.updateProfile(updatedData);
    setProfile(updated);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0A0A0A] text-[#EDEDED]">
      {/* Desktop / Collapsible Sidebar */}
      <div className="hidden md:flex flex-shrink-0">
        <Sidebar
          currentWorkspace={currentWorkspace}
          onSelectWorkspace={setCurrentWorkspace}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          health={health}
          onRefreshHealth={refreshHealth}
          onOpenMemoryModal={() => setMemoryModalOpen(true)}
        />
      </div>

      {/* Mobile Drawer Backdrop & Sidebar */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/80 md:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        >
          <div
            className="w-64 h-full"
            onClick={(e) => e.stopPropagation()}
          >
            <Sidebar
              currentWorkspace={currentWorkspace}
              onSelectWorkspace={(ws) => {
                setCurrentWorkspace(ws);
                setMobileSidebarOpen(false);
              }}
              collapsed={false}
              onToggleCollapse={() => setMobileSidebarOpen(false)}
              health={health}
              onRefreshHealth={refreshHealth}
              onOpenMemoryModal={() => {
                setMobileSidebarOpen(false);
                setMemoryModalOpen(true);
              }}
            />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header
          currentWorkspace={currentWorkspace}
          profile={profile}
          onOpenProfileModal={() => setProfileModalOpen(true)}
          onToggleMobileSidebar={() => setMobileSidebarOpen(true)}
        />

        <main className="flex-1 min-h-0 bg-[#0A0A0A] overflow-hidden">
          {currentWorkspace === 'home' && (
            <HomeWorkspace
              profile={profile}
              health={health}
              onNavigate={(ws) => setCurrentWorkspace(ws)}
            />
          )}
          {currentWorkspace === 'workout' && <WorkoutWorkspace />}
          {currentWorkspace === 'nutrition' && <NutritionWorkspace profile={profile} />}
          {currentWorkspace === 'recovery' && <RecoveryWorkspace profile={profile} />}
        </main>
      </div>

      {/* User Profile Modal */}
      <ProfileModal
        isOpen={profileModalOpen}
        onClose={() => setProfileModalOpen(false)}
        profile={profile}
        onSave={handleSaveProfile}
      />

      {/* Cross-Agent Memory Inspector Modal */}
      <MemoryInspectorModal
        isOpen={memoryModalOpen}
        onClose={() => setMemoryModalOpen(false)}
      />

      {/* Google OAuth & Account Modal */}
      <AuthModal />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;

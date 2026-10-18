import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, Session, AuthChangeEvent } from '@supabase/supabase-js';
import { supabase, signInWithGoogle as sbSignInWithGoogle, signOutUser as sbSignOutUser } from '../api/supabase';

export interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  error: string | null;
  authModalOpen: boolean;
  openAuthModal: () => void;
  closeAuthModal: () => void;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;

    // 1. Initial session restoration on mount / page refresh
    async function restoreSession() {
      try {
        setLoading(true);
        const { data, error: sessionError } = await supabase.auth.getSession();
        if (sessionError) {
          console.warn('Supabase restoreSession warning:', sessionError.message);
          if (isMounted) setError(sessionError.message);
        } else if (isMounted && data.session) {
          setSession(data.session);
          setUser(data.session.user);
        }
      } catch (err: any) {
        console.error('Unexpected error during session recovery:', err);
        if (isMounted) setError(err?.message || 'Failed to restore authentication session.');
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    restoreSession();

    // 2. Realtime listener for Auth changes (OAuth return, token refresh, sign in, sign out)
    const { data: authListener } = supabase.auth.onAuthStateChange(
      (event: AuthChangeEvent, currentSession: Session | null) => {
        if (!isMounted) return;

        setSession(currentSession);
        setUser(currentSession?.user ?? null);
        setLoading(false);

        if (event === 'SIGNED_IN') {
          setError(null);
          setAuthModalOpen(false);
          // Clean URL hash/params if present from OAuth redirect
          if (window.location.hash || window.location.search.includes('code=')) {
            window.history.replaceState({}, document.title, window.location.pathname);
          }
        } else if (event === 'SIGNED_OUT') {
          setError(null);
        }
      }
    );

    return () => {
      isMounted = false;
      authListener.subscription.unsubscribe();
    };
  }, []);

  const openAuthModal = () => setAuthModalOpen(true);
  const closeAuthModal = () => {
    setAuthModalOpen(false);
    setError(null);
  };

  const clearError = () => setError(null);

  const signInWithGoogle = async () => {
    setLoading(true);
    setError(null);
    try {
      await sbSignInWithGoogle();
      // Browser will redirect to Google Accounts sign-in page
    } catch (err: any) {
      console.error('Google sign-in error:', err);
      setError(err?.message || 'Failed to initiate Google authentication.');
      setLoading(false);
    }
  };

  const signOut = async () => {
    setLoading(true);
    setError(null);
    try {
      await sbSignOutUser();
      setUser(null);
      setSession(null);
    } catch (err: any) {
      console.error('Sign-out error:', err);
      setError(err?.message || 'Failed to sign out.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        loading,
        error,
        authModalOpen,
        openAuthModal,
        closeAuthModal,
        signInWithGoogle,
        signOut,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

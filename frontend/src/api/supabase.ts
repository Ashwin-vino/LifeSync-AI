import { createClient, SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl =
  (import.meta.env.VITE_SUPABASE_URL as string) ||
  (import.meta.env.SUPABASE_URL as string) ||
  '';

const supabaseAnonKey =
  (import.meta.env.VITE_SUPABASE_ANON_KEY as string) ||
  (import.meta.env.SUPABASE_ANON_KEY as string) ||
  '';

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    'Supabase URL or Anon Key is missing in frontend environment. Please configure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.'
  );
}

export const supabase: SupabaseClient = createClient(
  supabaseUrl || 'https://placeholder.supabase.co',
  supabaseAnonKey || 'placeholder_anon_key',
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  }
);

/**
 * Initiates official Google OAuth sign-in with Supabase.
 * Automatically resolves the current origin (localhost in development,
 * vercel production domain in deployment).
 */
export async function signInWithGoogle(customRedirectUrl?: string) {
  // Use current window location origin as redirect base
  const origin = window.location.origin;
  const redirectTo = customRedirectUrl || `${origin}/`;

  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo,
      queryParams: {
        access_type: 'offline',
        prompt: 'consent',
      },
    },
  });

  if (error) {
    throw error;
  }

  return data;
}

/**
 * Signs out the current user session and clears local auth tokens.
 */
export async function signOutUser() {
  const { error } = await supabase.auth.signOut();
  if (error) {
    throw error;
  }
}

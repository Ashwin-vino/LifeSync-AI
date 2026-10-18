// Typed LifeSync AI API Client

export interface ServiceHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency_ms?: number;
  details?: string;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  environment: string;
  version: string;
  services: {
    supabase?: ServiceHealth;
    falkordb?: ServiceHealth;
    gemini?: ServiceHealth;
    wger?: ServiceHealth;
    usda?: ServiceHealth;
    [key: string]: ServiceHealth | undefined;
  };
}

export interface UserProfile {
  id: string;
  user_id: string;
  display_name: string;
  primary_goal: string;
  activity_level: string;
  calorie_target: number;
  protein_target: number;
  carbs_target: number;
  fat_target: number;
  water_target_liters: number;
  sleep_target_hours: number;
  created_at: string;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  workspace: string;
  created_at?: string;
  metadata?: Record<string, any>;
}

export interface WorkoutExercise {
  id?: string;
  exercise_name: string;
  target_muscle?: string;
  sets: number;
  reps: number;
  weight_kg: number;
  notes?: string;
  status?: 'completed' | 'skipped' | 'modified' | 'planned';
  source?: string;
  rest_seconds?: number;
}

export interface WorkoutItem {
  id: string;
  user_id: string;
  title: string;
  category: string;
  duration_minutes: number;
  calories_burned?: number;
  rpe?: number;
  status?: string;
  notes?: string;
  created_at: string;
  workout_exercises: WorkoutExercise[];
}

export interface PlannedExercise {
  name: string;
  target_muscle: string;
  sets: number;
  reps: string;
  rest_seconds: number;
  suggested_weight_kg?: number | null;
  notes?: string;
  wger_id?: string | null;
  source: string;
}

export interface WorkoutPlan {
  id?: string;
  user_id?: string;
  title: string;
  category: string;
  summary: string;
  warmup: string[];
  exercises: PlannedExercise[];
  cooldown: string[];
  estimated_duration_minutes: number;
  status: 'planned' | 'in_progress' | 'completed';
  explanation: string;
  created_at?: string;
}

export interface WorkoutAnalytics {
  total_sessions: number;
  total_volume_kg: number;
  total_minutes: number;
  average_rpe: number;
  category_distribution: Record<string, number>;
  recent_7_days_volume: { date: string; volume_kg: number; sessions: number }[];
}

export interface ExerciseItem {
  id: string;
  name: string;
  category: string;
  muscles: string[];
  equipment: string[];
  description?: string;
  source?: string;
}

export interface MealItem {
  id: string;
  user_id: string;
  meal_type: 'breakfast' | 'lunch' | 'dinner' | 'snack';
  name: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber?: number;
  serving_size?: number;
  serving_unit?: string;
  source?: string;
  fdc_id?: string;
  notes?: string;
  date: string;
  items?: any[];
  created_at: string;
}

export interface NutritionDaySummary {
  date: string;
  total_calories: number;
  total_protein: number;
  total_carbs: number;
  total_fat: number;
  total_fiber?: number;
  calorie_target: number;
  protein_target: number;
  carbs_target: number;
  fat_target: number;
  meals: MealItem[];
}

export interface USDAFoodItem {
  fdcId: string;
  description: string;
  brandOwner?: string;
  servingSize: number;
  servingUnit: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber?: number;
  source?: string;
}

export interface RecoveryLog {
  id: string;
  user_id: string;
  date: string;
  recovery_score?: number;
  sleep_hours?: number;
  sleep_quality?: string;
  resting_hr?: number;
  hrv_ms?: number;
  hydration_liters?: number;
  soreness_level?: number;
  fatigue_level?: number;
  stress_level?: number;
  notes?: string;
  created_at: string;
}

export interface RecoveryOverview {
  today_log?: RecoveryLog;
  weekly_logs: RecoveryLog[];
  average_sleep?: number;
  average_recovery_score?: number;
  hydration_status: string;
  readiness_status: string;
  missing_metrics?: string[];
}

export interface DailyWellnessOverview {
  date: string;
  user_profile?: Record<string, any>;
  today_recovery?: RecoveryLog | null;
  today_meals: MealItem[];
  today_macros: {
    calories: number;
    protein: number;
    carbs: number;
    fat: number;
    fiber: number;
  };
  macro_targets: {
    calorie_target: number;
    protein_target: number;
    carbs_target: number;
    fat_target: number;
  };
  today_workouts: WorkoutItem[];
  active_workout_plan?: any;
  recent_memory_facts: any[];
  readiness_status: string;
  ai_insights: string[];
}

const BASE_URL = (import.meta.env.VITE_API_URL as string) || '';

function getAuthToken(): string | null {
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith('sb-') || key.includes('auth-token') || key === 'supabase.auth.token')) {
        const raw = localStorage.getItem(key);
        if (raw) {
          try {
            const parsed = JSON.parse(raw);
            if (parsed.access_token) return parsed.access_token;
            if (parsed.currentSession?.access_token) return parsed.currentSession.access_token;
          } catch {
            if (raw.startsWith('ey')) return raw;
          }
        }
      }
    }
  } catch {
    // ignore
  }
  return null;
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

  const res = await fetch(`${BASE_URL}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API error ${res.status}: ${errorText}`);
  }

  return res.json();
}

export const api = {
  // Health
  getHealth: () => fetchJson<HealthResponse>('/api/health'),

  // Profile
  getProfile: () => fetchJson<UserProfile>('/api/profile'),
  updateProfile: (data: Partial<UserProfile>) =>
    fetchJson<UserProfile>('/api/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  // Chat
  sendMessage: (payload: { message: string; workspace: string; history?: any[] }) =>
    fetchJson<{ reply: string; workspace: string; model: string; error?: boolean }>('/api/chat/message', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getChatHistory: (workspace: string) => fetchJson<ChatMessage[]>(`/api/chat/history/${workspace}`),
  clearChatHistory: (workspace: string) =>
    fetchJson<{ status: string }>(`/api/chat/history/${workspace}`, { method: 'DELETE' }),

  // Workout
  getWorkouts: (limit: number = 20, status: string = 'completed') =>
    fetchJson<WorkoutItem[]>(`/api/workout/list?limit=${limit}&status=${status}`),
  getWorkout: (id: string) => fetchJson<WorkoutItem>(`/api/workout/session/${id}`),
  logWorkout: (data: {
    title: string;
    category: string;
    duration_minutes: number;
    calories_burned?: number;
    rpe?: number;
    status?: string;
    plan_id?: string;
    notes?: string;
    exercises: Omit<WorkoutExercise, 'id'>[];
  }) =>
    fetchJson<WorkoutItem>('/api/workout/log', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateWorkout: (
    id: string,
    data: {
      title?: string;
      category?: string;
      duration_minutes?: number;
      calories_burned?: number;
      rpe?: number;
      status?: string;
      notes?: string;
      exercises?: Omit<WorkoutExercise, 'id'>[];
    }
  ) =>
    fetchJson<WorkoutItem>(`/api/workout/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  deleteWorkout: (id: string) =>
    fetchJson<{ status: string; id: string; success: boolean }>(`/api/workout/${id}`, {
      method: 'DELETE',
    }),
  generateWorkoutPlan: (data: {
    focus?: string;
    duration_target?: number;
    equipment_available?: string[];
    notes?: string;
  }) =>
    fetchJson<WorkoutPlan>('/api/workout/generate-plan', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  getActiveWorkoutPlan: () => fetchJson<WorkoutPlan | null>('/api/workout/active-plan'),
  startWorkoutSession: (plan_id?: string) =>
    fetchJson<{ status: string; plan_id?: string }>('/api/workout/start-session', {
      method: 'POST',
      body: JSON.stringify({ plan_id }),
    }),
  getWorkoutAnalytics: () => fetchJson<WorkoutAnalytics>('/api/workout/analytics'),
  searchExercises: (q: string = '', category?: string, limit: number = 50, offset: number = 0) => {
    let url = `/api/workout/exercises?q=${encodeURIComponent(q)}&limit=${limit}&offset=${offset}`;
    if (category) {
      url += `&category=${encodeURIComponent(category)}`;
    }
    return fetchJson<ExerciseItem[]>(url);
  },
  getSingleExercise: (id: string) => fetchJson<ExerciseItem>(`/api/workout/exercises/${id}`),
  getExerciseCategories: () => fetchJson<{ id: number; name: string }[]>('/api/workout/categories'),

  // Nutrition
  getNutritionSummary: (dateStr?: string) =>
    fetchJson<NutritionDaySummary>(`/api/nutrition/summary${dateStr ? `?date_str=${dateStr}` : ''}`),
  getMeal: (id: string) => fetchJson<MealItem>(`/api/nutrition/meal/${id}`),
  logMeal: (data: {
    meal_type: string;
    name: string;
    calories: number;
    protein: number;
    carbs: number;
    fat: number;
    fiber?: number;
    serving_size?: number;
    serving_unit?: string;
    source?: string;
    fdc_id?: string;
    notes?: string;
    date?: string;
    items?: any[];
  }) =>
    fetchJson<MealItem>('/api/nutrition/log', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateMeal: (
    id: string,
    data: {
      meal_type?: string;
      name?: string;
      calories?: number;
      protein?: number;
      carbs?: number;
      fat?: number;
      fiber?: number;
      serving_size?: number;
      serving_unit?: string;
      notes?: string;
      date?: string;
    }
  ) =>
    fetchJson<MealItem>(`/api/nutrition/meal/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  deleteMeal: (id: string) => fetchJson<{ status: string; id: string; success: boolean }>(`/api/nutrition/meal/${id}`, { method: 'DELETE' }),
  searchFoods: (q: string) => fetchJson<USDAFoodItem[]>(`/api/nutrition/search-foods?q=${encodeURIComponent(q)}`),
  getFoodDetails: (fdcId: string) => fetchJson<USDAFoodItem>(`/api/nutrition/food/${fdcId}`),
  getNutritionRecommendations: (goal?: string) =>
    fetchJson<{ recommendations: string[]; daily_summary: Record<string, any>; context_considered: string[] }>(
      `/api/nutrition/recommendations${goal ? `?goal=${encodeURIComponent(goal)}` : ''}`
    ),

  // Recovery
  getRecoveryOverview: () => fetchJson<RecoveryOverview>('/api/recovery/overview'),
  getRecoveryLog: (id: string) => fetchJson<RecoveryLog>(`/api/recovery/log/${id}`),
  logRecovery: (data: {
    date: string;
    sleep_hours: number;
    sleep_quality: string;
    resting_hr?: number;
    hrv_ms?: number;
    hydration_liters: number;
    soreness_level: number;
    fatigue_level?: number;
    stress_level: number;
    notes?: string;
  }) =>
    fetchJson<RecoveryLog>('/api/recovery/log', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateRecoveryLog: (
    id: string,
    data: {
      sleep_hours?: number;
      sleep_quality?: string;
      resting_hr?: number;
      hrv_ms?: number;
      hydration_liters?: number;
      soreness_level?: number;
      fatigue_level?: number;
      stress_level?: number;
      notes?: string;
    }
  ) =>
    fetchJson<RecoveryLog>(`/api/recovery/log/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  deleteRecoveryLog: (id: string) =>
    fetchJson<{ status: string; id: string; success: boolean }>(`/api/recovery/log/${id}`, {
      method: 'DELETE',
    }),
  getRecoveryRecommendations: () =>
    fetchJson<{ recommendations: string[]; recovery_score?: number; factors_considered: string[]; cautions: string[] }>(
      '/api/recovery/recommendations'
    ),

  // Home AI Unified Overview
  getHomeOverview: (dateStr?: string) =>
    fetchJson<DailyWellnessOverview>(`/api/home/overview${dateStr ? `?date_str=${dateStr}` : ''}`),

  // Cross-Agent Memory
  getMemories: (status: string = 'active') => fetchJson<MemoryFact[]>(`/api/memory/facts?status=${status}`),
  addMemory: (data: { fact_type: string; content: string; provenance?: string; tags?: string[] }) =>
    fetchJson<MemoryFact>('/api/memory/facts', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  correctMemory: (id: string, content: string) =>
    fetchJson<{ status: string }>(`/api/memory/facts/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),
  deleteMemory: (id: string) => fetchJson<{ status: string }>(`/api/memory/facts/${id}`, { method: 'DELETE' }),
  getGraphStats: () => fetchJson<{ connected: boolean; nodes: number; edges: number }>('/api/memory/graph-stats'),
};

export interface MemoryFact {
  id: string;
  fact_type: string;
  content: string;
  provenance: string;
  confidence: number;
  tags: string[];
  status: string;
  created_at?: string;
}


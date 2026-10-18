import React, { useState, useEffect } from 'react';
import {
  Plus,
  Search,
  Flame,
  Trash2,
  Edit3,
  X,
  Coffee,
  Sun,
  Sunset,
  Cookie,
  ChevronRight,
  Sparkles,
  CheckCircle2,
} from 'lucide-react';
import { api, MealItem, NutritionDaySummary, USDAFoodItem, UserProfile } from '../api/client';
import { UnifiedChat } from '../components/UnifiedChat';

interface NutritionWorkspaceProps {
  profile: UserProfile | null;
}

export const NutritionWorkspace: React.FC<NutritionWorkspaceProps> = ({ profile }) => {
  const [summary, setSummary] = useState<NutritionDaySummary | null>(null);
  const [showLogModal, setShowLogModal] = useState(false);
  const [showUSDAModal, setShowUSDAModal] = useState(false);
  const [editingMeal, setEditingMeal] = useState<MealItem | null>(null);

  // USDA Search state
  const [usdaQuery, setUsdaQuery] = useState('');
  const [usdaResults, setUsdaResults] = useState<USDAFoodItem[]>([]);
  const [searchingUSDA, setSearchingUSDA] = useState(false);
  const [selectedUSDAFood, setSelectedUSDAFood] = useState<USDAFoodItem | null>(null);
  const [selectedMealType, setSelectedMealType] = useState('lunch');
  const [servingsMultiplier, setServingsMultiplier] = useState(1.0);
  const [usdaNotes, setUsdaNotes] = useState('');

  // Manual Meal Form
  const [manualMealType, setManualMealType] = useState('lunch');
  const [manualName, setManualName] = useState('');
  const [manualCalories, setManualCalories] = useState(450);
  const [manualProtein, setManualProtein] = useState(35);
  const [manualCarbs, setManualCarbs] = useState(45);
  const [manualFat, setManualFat] = useState(12);
  const [manualFiber, setManualFiber] = useState(5);
  const [manualServingSize, setManualServingSize] = useState(1);
  const [manualServingUnit, setManualServingUnit] = useState('serving');
  const [manualNotes, setManualNotes] = useState('');
  const [savingMeal, setSavingMeal] = useState(false);

  // AI Recommendations State
  const [recommendations, setRecommendations] = useState<string[]>([]);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [recommendationContext, setRecommendationContext] = useState<string[]>([]);

  const loadSummary = async () => {
    try {
      const data = await api.getNutritionSummary();
      setSummary(data);
    } catch (e) {
      console.error('Failed to load nutrition summary:', e);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  const handleSearchUSDA = async () => {
    if (!usdaQuery.trim()) return;
    setSearchingUSDA(true);
    try {
      const results = await api.searchFoods(usdaQuery);
      setUsdaResults(results);
    } catch (e) {
      console.error('Failed to search foods:', e);
    } finally {
      setSearchingUSDA(false);
    }
  };

  const handleLogUSDAFood = async () => {
    if (!selectedUSDAFood) return;
    setSavingMeal(true);
    try {
      const multiplier = Number(servingsMultiplier) || 1.0;
      await api.logMeal({
        meal_type: selectedMealType,
        name: selectedUSDAFood.description,
        calories: Math.round(selectedUSDAFood.calories * multiplier),
        protein: Math.round(selectedUSDAFood.protein * multiplier * 10) / 10,
        carbs: Math.round(selectedUSDAFood.carbs * multiplier * 10) / 10,
        fat: Math.round(selectedUSDAFood.fat * multiplier * 10) / 10,
        fiber: Math.round((selectedUSDAFood.fiber || 0) * multiplier * 10) / 10,
        serving_size: Math.round(selectedUSDAFood.servingSize * multiplier * 10) / 10,
        serving_unit: selectedUSDAFood.servingUnit || 'g',
        source: selectedUSDAFood.source || 'usda_verified',
        fdc_id: selectedUSDAFood.fdcId,
        notes: usdaNotes || undefined,
        items: [{
          fdcId: selectedUSDAFood.fdcId,
          brand: selectedUSDAFood.brandOwner,
          portion: `${selectedUSDAFood.servingSize * multiplier} ${selectedUSDAFood.servingUnit}`
        }]
      });
      setShowUSDAModal(false);
      setSelectedUSDAFood(null);
      setUsdaQuery('');
      setUsdaResults([]);
      setUsdaNotes('');
      await loadSummary();
    } catch (err) {
      console.error('Failed to log USDA food:', err);
    } finally {
      setSavingMeal(false);
    }
  };

  const handleLogManualMeal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualName.trim()) return;
    setSavingMeal(true);
    try {
      await api.logMeal({
        meal_type: manualMealType,
        name: manualName,
        calories: manualCalories,
        protein: manualProtein,
        carbs: manualCarbs,
        fat: manualFat,
        fiber: manualFiber,
        serving_size: manualServingSize,
        serving_unit: manualServingUnit,
        notes: manualNotes || undefined,
        source: 'manual_entry'
      });
      setShowLogModal(false);
      setManualName('');
      setManualNotes('');
      await loadSummary();
    } catch (err) {
      console.error('Failed to log manual meal:', err);
    } finally {
      setSavingMeal(false);
    }
  };

  const handleUpdateMeal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMeal) return;
    setSavingMeal(true);
    try {
      await api.updateMeal(editingMeal.id, {
        name: editingMeal.name,
        meal_type: editingMeal.meal_type,
        calories: Number(editingMeal.calories),
        protein: Number(editingMeal.protein),
        carbs: Number(editingMeal.carbs),
        fat: Number(editingMeal.fat),
        fiber: Number(editingMeal.fiber || 0),
        serving_size: Number(editingMeal.serving_size || 1),
        serving_unit: editingMeal.serving_unit || 'serving',
        notes: editingMeal.notes || undefined
      });
      setEditingMeal(null);
      await loadSummary();
    } catch (err) {
      console.error('Failed to update meal:', err);
    } finally {
      setSavingMeal(false);
    }
  };

  const handleDeleteMeal = async (id: string) => {
    try {
      await api.deleteMeal(id);
      await loadSummary();
    } catch (err) {
      console.error('Failed to delete meal:', err);
    }
  };

  const handleFetchRecommendations = async () => {
    setLoadingRecommendations(true);
    try {
      const res = await api.getNutritionRecommendations(profile?.primary_goal);
      setRecommendations(res.recommendations || []);
      setRecommendationContext(res.context_considered || []);
    } catch (err) {
      console.error('Failed to fetch recommendations:', err);
    } finally {
      setLoadingRecommendations(false);
    }
  };

  const cals = summary?.total_calories || 0;
  const calTarget = profile?.calorie_target || summary?.calorie_target || 2200;
  const p = summary?.total_protein || 0;
  const pTarget = profile?.protein_target || summary?.protein_target || 160;
  const c = summary?.total_carbs || 0;
  const cTarget = profile?.carbs_target || summary?.carbs_target || 220;
  const f = summary?.total_fat || 0;
  const fTarget = profile?.fat_target || summary?.fat_target || 65;
  const fiber = summary?.total_fiber || 0;
  const fiberTarget = 35;

  const mealSections = [
    { type: 'breakfast', label: 'Breakfast', icon: <Coffee className="w-4 h-4 text-[#A3A3A3]" /> },
    { type: 'lunch', label: 'Lunch', icon: <Sun className="w-4 h-4 text-[#A3A3A3]" /> },
    { type: 'dinner', label: 'Dinner', icon: <Sunset className="w-4 h-4 text-[#A3A3A3]" /> },
    { type: 'snack', label: 'Snacks & Fuel', icon: <Cookie className="w-4 h-4 text-[#A3A3A3]" /> },
  ];

  return (
    <div className="h-full flex flex-col xl:flex-row gap-4 p-4 sm:p-6 overflow-y-auto bg-[#0A0A0A]">
      {/* Left Column: Macro Analytics & Meal Cards */}
      <div className="flex-1 space-y-4">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-[#141414] border border-[#262626] rounded">
          <div>
            <h2 className="text-sm font-semibold text-white tracking-wide">Macro Tracking & Nutrition</h2>
            <p className="text-[11px] text-[#737373]">
              USDA FoodData Central live search with verified macro profiles & workout-integrated fueling
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleFetchRecommendations}
              disabled={loadingRecommendations}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-[#1F1F1F] border border-[#333333] hover:border-[#555555] text-white rounded transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              {loadingRecommendations ? 'Synthesizing...' : 'AI Recommendations'}
            </button>
            <button
              onClick={() => {
                setShowUSDAModal(true);
                if (usdaResults.length === 0) {
                  api.searchFoods('chicken breast').then(setUsdaResults).catch(() => {});
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] hover:border-[#505050] text-[#D4D4D4] rounded transition-colors"
            >
              <Search className="w-3.5 h-3.5" /> USDA Search
            </button>
            <button
              onClick={() => setShowLogModal(true)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs bg-[#EDEDED] text-[#0A0A0A] font-semibold rounded hover:bg-white transition-colors"
            >
              <Plus className="w-3.5 h-3.5" /> Quick Meal
            </button>
          </div>
        </div>

        {/* AI Recommendations Banner (if triggered) */}
        {recommendations.length > 0 && (
          <div className="p-4 bg-[#141414] border border-[#303030] rounded space-y-2.5">
            <div className="flex items-center justify-between border-b border-[#242424] pb-2">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <h3 className="text-xs font-semibold text-white">Personalized Fueling Guidance</h3>
              </div>
              <button
                onClick={() => setRecommendations([])}
                className="text-[10px] text-[#737373] hover:text-white"
              >
                Dismiss
              </button>
            </div>
            {recommendationContext.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {recommendationContext.map((ctx, idx) => (
                  <span
                    key={idx}
                    className="text-[10px] px-2 py-0.5 bg-[#1F1F1F] border border-[#2E2E2E] rounded text-[#A3A3A3]"
                  >
                    {ctx}
                  </span>
                ))}
              </div>
            )}
            <ul className="space-y-1.5 text-xs text-[#D4D4D4]">
              {recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Macro Target Progress Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Calories */}
          <div className="p-3.5 bg-[#141414] border border-[#262626] rounded">
            <div className="flex items-center justify-between text-[#888888] mb-1">
              <span className="text-[11px] font-medium">Energy</span>
              <Flame className="w-3.5 h-3.5 text-[#B0B0B0]" />
            </div>
            <div className="text-xl font-bold font-mono text-white">
              {Math.round(cals)} <span className="text-xs text-[#737373]">/ {calTarget} kcal</span>
            </div>
            <div className="w-full bg-[#202020] h-1.5 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-[#D4D4D4] h-full rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, (cals / (calTarget || 1)) * 100)}%` }}
              />
            </div>
            <div className="text-[10px] text-[#737373] mt-1.5 flex justify-between">
              <span>{Math.round(calTarget - cals)} kcal left</span>
              <span>{Math.round((cals / (calTarget || 1)) * 100)}%</span>
            </div>
          </div>

          {/* Protein */}
          <div className="p-3.5 bg-[#141414] border border-[#262626] rounded">
            <div className="flex items-center justify-between text-[#888888] mb-1">
              <span className="text-[11px] font-medium">Protein</span>
              <span className="text-[10px] text-[#A3A3A3] font-mono">{pTarget}g</span>
            </div>
            <div className="text-xl font-bold font-mono text-white">
              {Math.round(p)} <span className="text-xs text-[#737373]">g</span>
            </div>
            <div className="w-full bg-[#202020] h-1.5 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-emerald-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, (p / (pTarget || 1)) * 100)}%` }}
              />
            </div>
            <div className="text-[10px] text-[#737373] mt-1.5 flex justify-between">
              <span>{Math.max(0, Math.round(pTarget - p))}g left</span>
              <span>{Math.round((p / (pTarget || 1)) * 100)}%</span>
            </div>
          </div>

          {/* Carbs */}
          <div className="p-3.5 bg-[#141414] border border-[#262626] rounded">
            <div className="flex items-center justify-between text-[#888888] mb-1">
              <span className="text-[11px] font-medium">Carbohydrates</span>
              <span className="text-[10px] text-[#A3A3A3] font-mono">{cTarget}g</span>
            </div>
            <div className="text-xl font-bold font-mono text-white">
              {Math.round(c)} <span className="text-xs text-[#737373]">g</span>
            </div>
            <div className="w-full bg-[#202020] h-1.5 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-amber-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, (c / (cTarget || 1)) * 100)}%` }}
              />
            </div>
            <div className="text-[10px] text-[#737373] mt-1.5 flex justify-between">
              <span>{Math.max(0, Math.round(cTarget - c))}g left</span>
              <span>{Math.round((c / (cTarget || 1)) * 100)}%</span>
            </div>
          </div>

          {/* Fat */}
          <div className="p-3.5 bg-[#141414] border border-[#262626] rounded">
            <div className="flex items-center justify-between text-[#888888] mb-1">
              <span className="text-[11px] font-medium">Fat</span>
              <span className="text-[10px] text-[#A3A3A3] font-mono">{fTarget}g</span>
            </div>
            <div className="text-xl font-bold font-mono text-white">
              {Math.round(f)} <span className="text-xs text-[#737373]">g</span>
            </div>
            <div className="w-full bg-[#202020] h-1.5 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-blue-400 h-full rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, (f / (fTarget || 1)) * 100)}%` }}
              />
            </div>
            <div className="text-[10px] text-[#737373] mt-1.5 flex justify-between">
              <span>{Math.max(0, Math.round(fTarget - f))}g left</span>
              <span>{Math.round((f / (fTarget || 1)) * 100)}%</span>
            </div>
          </div>

          {/* Fiber */}
          <div className="p-3.5 bg-[#141414] border border-[#262626] rounded col-span-2 lg:col-span-1">
            <div className="flex items-center justify-between text-[#888888] mb-1">
              <span className="text-[11px] font-medium">Fiber</span>
              <span className="text-[10px] text-[#A3A3A3] font-mono">{fiberTarget}g</span>
            </div>
            <div className="text-xl font-bold font-mono text-white">
              {Math.round(fiber)} <span className="text-xs text-[#737373]">g</span>
            </div>
            <div className="w-full bg-[#202020] h-1.5 rounded-full mt-2 overflow-hidden">
              <div
                className="bg-teal-400 h-full rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, (fiber / (fiberTarget || 1)) * 100)}%` }}
              />
            </div>
            <div className="text-[10px] text-[#737373] mt-1.5 flex justify-between">
              <span>{Math.max(0, Math.round(fiberTarget - fiber))}g left</span>
              <span>{Math.round((fiber / (fiberTarget || 1)) * 100)}%</span>
            </div>
          </div>
        </div>

        {/* Meal Logs by Category */}
        <div className="space-y-3">
          {mealSections.map((sec) => {
            const mealsInSec = (summary?.meals || []).filter((m) => m.meal_type.toLowerCase() === sec.type);
            const secCals = mealsInSec.reduce((acc, m) => acc + Number(m.calories || 0), 0);
            const secProtein = mealsInSec.reduce((acc, m) => acc + Number(m.protein || 0), 0);

            return (
              <div key={sec.type} className="p-4 bg-[#141414] border border-[#262626] rounded space-y-2.5">
                <div className="flex items-center justify-between border-b border-[#222222] pb-2">
                  <div className="flex items-center gap-2">
                    {sec.icon}
                    <h3 className="text-xs font-semibold text-white tracking-wide">{sec.label}</h3>
                  </div>
                  <div className="text-[11px] text-[#888888] font-mono">
                    {Math.round(secCals)} kcal • {Math.round(secProtein)}g P
                  </div>
                </div>

                {mealsInSec.length === 0 ? (
                  <div className="py-2 text-[11px] text-[#666666]">
                    No meals logged for {sec.label.toLowerCase()} today.
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {mealsInSec.map((meal) => (
                      <div
                        key={meal.id}
                        className="p-2.5 bg-[#181818] border border-[#2B2B2B] rounded flex items-center justify-between hover:border-[#383838] transition-colors"
                      >
                        <div className="flex-1 pr-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium text-white">{meal.name}</span>
                            {meal.source === 'usda_verified' ? (
                              <span className="text-[9px] px-1.5 py-0.2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded font-medium">
                                USDA Verified
                              </span>
                            ) : (
                              <span className="text-[9px] px-1.5 py-0.2 bg-[#222222] text-[#888888] border border-[#333333] rounded">
                                Custom Log
                              </span>
                            )}
                          </div>
                          <div className="text-[10px] text-[#777777] font-mono mt-0.5">
                            {meal.calories} kcal • {meal.protein}g P • {meal.carbs}g C • {meal.fat}g F
                            {meal.fiber ? ` • ${meal.fiber}g Fiber` : ''}
                            {meal.serving_size ? ` • ${meal.serving_size} ${meal.serving_unit || 'g'}` : ''}
                          </div>
                          {meal.notes && (
                            <div className="text-[10px] text-[#888888] italic mt-0.5">
                              "{meal.notes}"
                            </div>
                          )}
                        </div>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => setEditingMeal(meal)}
                            className="p-1 text-[#777777] hover:text-white rounded hover:bg-[#222222] transition-colors"
                            title="Edit meal"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteMeal(meal.id)}
                            className="p-1 text-[#777777] hover:text-rose-400 rounded hover:bg-[#222222] transition-colors"
                            title="Delete meal"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Right Column: AI Nutritionist Chat */}
      <div className="w-full xl:w-[420px] min-h-[500px] flex flex-col">
        <UnifiedChat
          workspace="nutrition"
          title="LifeSync AI • Nutrition Coach"
          subtitle="Daily macros, healthy meals & nutrition tips"
          suggestedPrompts={[
            "I have 35g of protein left today. What's a quick meal idea?",
            "What should I eat after my workout today?",
            "How many calories are in 2 eggs and a slice of toast?",
            "How can I easily get more fiber into my diet?"
          ]}
        />
      </div>

      {/* USDA Live Search & Log Modal */}
      {showUSDAModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-xl bg-[#141414] border border-[#2D2D2D] rounded shadow-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[#242424] flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">USDA FoodData Central</h2>
                <p className="text-[11px] text-[#737373]">Live search across authentic verified nutrient records</p>
              </div>
              <button
                onClick={() => setShowUSDAModal(false)}
                className="p-1 rounded text-[#737373] hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 space-y-3">
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Search chicken breast, greek yogurt, oats, salmon, avocado..."
                  value={usdaQuery}
                  onChange={(e) => setUsdaQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearchUSDA()}
                  className="flex-1 px-3 py-2 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white focus:outline-none focus:border-[#555555]"
                />
                <button
                  onClick={handleSearchUSDA}
                  disabled={searchingUSDA}
                  className="px-3.5 py-2 text-xs bg-[#242424] hover:bg-[#303030] border border-[#383838] text-white rounded font-medium transition-colors"
                >
                  {searchingUSDA ? 'Searching...' : 'Search'}
                </button>
              </div>

              {selectedUSDAFood ? (
                <div className="p-3.5 bg-[#181818] border border-[#333333] rounded space-y-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.2 rounded font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {selectedUSDAFood.source === 'usda_verified' ? 'USDA Verified' : 'AI Estimated'}
                        </span>
                        {selectedUSDAFood.brandOwner && (
                          <span className="text-[10px] text-[#737373]">{selectedUSDAFood.brandOwner}</span>
                        )}
                      </div>
                      <h4 className="text-xs font-semibold text-white mt-1">{selectedUSDAFood.description}</h4>
                      <p className="text-[10px] text-[#737373]">
                        Standard reference base: {selectedUSDAFood.servingSize} {selectedUSDAFood.servingUnit}
                      </p>
                    </div>
                    <button
                      onClick={() => setSelectedUSDAFood(null)}
                      className="text-[11px] text-[#888888] hover:text-white"
                    >
                      Change
                    </button>
                  </div>

                  <div className="grid grid-cols-5 gap-2 text-center text-xs font-mono py-2 bg-[#121212] rounded border border-[#262626]">
                    <div>
                      <div className="text-[10px] text-[#737373]">Calories</div>
                      <div className="font-bold text-white">
                        {Math.round(selectedUSDAFood.calories * servingsMultiplier)} kcal
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-[#737373]">Protein</div>
                      <div className="font-bold text-emerald-400">
                        {Math.round(selectedUSDAFood.protein * servingsMultiplier * 10) / 10}g
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-[#737373]">Carbs</div>
                      <div className="font-bold text-amber-400">
                        {Math.round(selectedUSDAFood.carbs * servingsMultiplier * 10) / 10}g
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-[#737373]">Fat</div>
                      <div className="font-bold text-blue-400">
                        {Math.round(selectedUSDAFood.fat * servingsMultiplier * 10) / 10}g
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-[#737373]">Fiber</div>
                      <div className="font-bold text-teal-400">
                        {Math.round((selectedUSDAFood.fiber || 0) * servingsMultiplier * 10) / 10}g
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2.5">
                    <div>
                      <label className="block text-[11px] text-[#A3A3A3] mb-1">Meal Section</label>
                      <select
                        value={selectedMealType}
                        onChange={(e) => setSelectedMealType(e.target.value)}
                        className="w-full px-2.5 py-1.5 text-xs bg-[#121212] border border-[#333333] rounded text-white"
                      >
                        <option value="breakfast">Breakfast</option>
                        <option value="lunch">Lunch</option>
                        <option value="dinner">Dinner</option>
                        <option value="snack">Snack</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#A3A3A3] mb-1">Serving Multiplier</label>
                      <input
                        type="number"
                        step="0.25"
                        min="0.25"
                        max="10"
                        value={servingsMultiplier}
                        onChange={(e) => setServingsMultiplier(Number(e.target.value))}
                        className="w-full px-2.5 py-1.5 text-xs bg-[#121212] border border-[#333333] rounded text-white font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#A3A3A3] mb-1">Calculated Grams</label>
                      <div className="px-2.5 py-1.5 text-xs bg-[#121212] border border-[#2B2B2B] rounded text-[#A3A3A3] font-mono">
                        {Math.round(selectedUSDAFood.servingSize * servingsMultiplier)} {selectedUSDAFood.servingUnit}
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] text-[#A3A3A3] mb-1">Optional Notes</label>
                    <input
                      type="text"
                      placeholder="e.g. Cooked in olive oil, post-workout"
                      value={usdaNotes}
                      onChange={(e) => setUsdaNotes(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs bg-[#121212] border border-[#333333] rounded text-white"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2 border-t border-[#262626]">
                    <button
                      onClick={handleLogUSDAFood}
                      disabled={savingMeal}
                      className="px-4 py-1.5 text-xs bg-[#EDEDED] text-[#0A0A0A] font-semibold rounded hover:bg-white disabled:opacity-50 transition-colors"
                    >
                      {savingMeal ? 'Logging...' : 'Log Verified Food'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="max-h-72 overflow-y-auto space-y-1.5 divide-y divide-[#1A1A1A]">
                  {usdaResults.map((item) => (
                    <div
                      key={item.fdcId}
                      onClick={() => setSelectedUSDAFood(item)}
                      className="p-2.5 rounded hover:bg-[#1A1A1A] cursor-pointer flex items-center justify-between transition-colors"
                    >
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-semibold text-white">{item.description}</span>
                          <span className="text-[9px] px-1.5 py-0.2 rounded font-medium bg-[#222222] text-[#888888] border border-[#333333]">
                            {item.source === 'usda_verified' ? 'USDA Verified' : 'AI Estimated'}
                          </span>
                        </div>
                        <div className="text-[10px] text-[#737373] mt-0.5">
                          {item.brandOwner ? `${item.brandOwner} • ` : ''}
                          {item.calories} kcal • {item.protein}g P • {item.carbs}g C • {item.fat}g F
                          {item.fiber ? ` • ${item.fiber}g Fiber` : ''}
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-[#555555]" />
                    </div>
                  ))}
                  {usdaResults.length === 0 && !searchingUSDA && (
                    <div className="text-center py-8 text-xs text-[#666666]">
                      Search any food item or brand to fetch verified USDA nutrients.
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Manual Quick Meal Modal */}
      {showLogModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#141414] border border-[#2D2D2D] rounded shadow-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[#242424] flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">Quick Log Meal</h2>
                <p className="text-[11px] text-[#737373]">Enter custom meal name and macronutrients</p>
              </div>
              <button
                onClick={() => setShowLogModal(false)}
                className="p-1 rounded text-[#737373] hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleLogManualMeal} className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-[#A3A3A3] mb-1">Meal Section</label>
                  <select
                    value={manualMealType}
                    onChange={(e) => setManualMealType(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                  >
                    <option value="breakfast">Breakfast</option>
                    <option value="lunch">Lunch</option>
                    <option value="dinner">Dinner</option>
                    <option value="snack">Snack</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-[#A3A3A3] mb-1">Meal Name</label>
                  <input
                    type="text"
                    value={manualName}
                    onChange={(e) => setManualName(e.target.value)}
                    placeholder="e.g. Steak & Roasted Potatoes"
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Calories (kcal)</label>
                  <input
                    type="number"
                    value={manualCalories}
                    onChange={(e) => setManualCalories(Number(e.target.value))}
                    min="0"
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Protein (g)</label>
                  <input
                    type="number"
                    value={manualProtein}
                    onChange={(e) => setManualProtein(Number(e.target.value))}
                    min="0"
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Carbohydrates (g)</label>
                  <input
                    type="number"
                    value={manualCarbs}
                    onChange={(e) => setManualCarbs(Number(e.target.value))}
                    min="0"
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Fat (g)</label>
                  <input
                    type="number"
                    value={manualFat}
                    onChange={(e) => setManualFat(Number(e.target.value))}
                    min="0"
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Fiber (g)</label>
                  <input
                    type="number"
                    value={manualFiber}
                    onChange={(e) => setManualFiber(Number(e.target.value))}
                    min="0"
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Portion</label>
                  <div className="flex gap-1.5">
                    <input
                      type="number"
                      value={manualServingSize}
                      onChange={(e) => setManualServingSize(Number(e.target.value))}
                      className="w-16 px-2 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                    />
                    <input
                      type="text"
                      value={manualServingUnit}
                      onChange={(e) => setManualServingUnit(e.target.value)}
                      placeholder="unit"
                      className="flex-1 px-2 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-[11px] text-[#A3A3A3] mb-1">Notes</label>
                <input
                  type="text"
                  placeholder="Optional context, seasoning, ingredients..."
                  value={manualNotes}
                  onChange={(e) => setManualNotes(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-[#242424]">
                <button
                  type="button"
                  onClick={() => setShowLogModal(false)}
                  className="px-3 py-1.5 text-xs text-[#888888] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingMeal}
                  className="px-4 py-1.5 text-xs bg-[#EDEDED] text-[#0A0A0A] font-semibold rounded hover:bg-white disabled:opacity-50 transition-colors"
                >
                  {savingMeal ? 'Logging...' : 'Log Meal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Meal Modal */}
      {editingMeal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#141414] border border-[#2D2D2D] rounded shadow-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[#242424] flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">Edit Logged Meal</h2>
                <p className="text-[11px] text-[#737373]">Adjust meal macros, serving or category</p>
              </div>
              <button
                onClick={() => setEditingMeal(null)}
                className="p-1 rounded text-[#737373] hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleUpdateMeal} className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-[#A3A3A3] mb-1">Meal Section</label>
                  <select
                    value={editingMeal.meal_type}
                    onChange={(e) => setEditingMeal({ ...editingMeal, meal_type: e.target.value as any })}
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                  >
                    <option value="breakfast">Breakfast</option>
                    <option value="lunch">Lunch</option>
                    <option value="dinner">Dinner</option>
                    <option value="snack">Snack</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-[#A3A3A3] mb-1">Meal Name</label>
                  <input
                    type="text"
                    value={editingMeal.name}
                    onChange={(e) => setEditingMeal({ ...editingMeal, name: e.target.value })}
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Calories (kcal)</label>
                  <input
                    type="number"
                    value={editingMeal.calories}
                    onChange={(e) => setEditingMeal({ ...editingMeal, calories: Number(e.target.value) })}
                    min="0"
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Protein (g)</label>
                  <input
                    type="number"
                    value={editingMeal.protein}
                    onChange={(e) => setEditingMeal({ ...editingMeal, protein: Number(e.target.value) })}
                    min="0"
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Carbohydrates (g)</label>
                  <input
                    type="number"
                    value={editingMeal.carbs}
                    onChange={(e) => setEditingMeal({ ...editingMeal, carbs: Number(e.target.value) })}
                    min="0"
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Fat (g)</label>
                  <input
                    type="number"
                    value={editingMeal.fat}
                    onChange={(e) => setEditingMeal({ ...editingMeal, fat: Number(e.target.value) })}
                    min="0"
                    required
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Fiber (g)</label>
                  <input
                    type="number"
                    value={editingMeal.fiber || 0}
                    onChange={(e) => setEditingMeal({ ...editingMeal, fiber: Number(e.target.value) })}
                    min="0"
                    className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#A3A3A3] mb-1">Serving Size & Unit</label>
                  <div className="flex gap-1.5">
                    <input
                      type="number"
                      value={editingMeal.serving_size || 1}
                      onChange={(e) => setEditingMeal({ ...editingMeal, serving_size: Number(e.target.value) })}
                      className="w-16 px-2 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white font-mono"
                    />
                    <input
                      type="text"
                      value={editingMeal.serving_unit || 'serving'}
                      onChange={(e) => setEditingMeal({ ...editingMeal, serving_unit: e.target.value })}
                      className="flex-1 px-2 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-[11px] text-[#A3A3A3] mb-1">Notes</label>
                <input
                  type="text"
                  value={editingMeal.notes || ''}
                  onChange={(e) => setEditingMeal({ ...editingMeal, notes: e.target.value })}
                  placeholder="Optional notes"
                  className="w-full px-2.5 py-1.5 text-xs bg-[#1A1A1A] border border-[#333333] rounded text-white"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-[#242424]">
                <button
                  type="button"
                  onClick={() => setEditingMeal(null)}
                  className="px-3 py-1.5 text-xs text-[#888888] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingMeal}
                  className="px-4 py-1.5 text-xs bg-[#EDEDED] text-[#0A0A0A] font-semibold rounded hover:bg-white disabled:opacity-50 transition-colors"
                >
                  {savingMeal ? 'Updating...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

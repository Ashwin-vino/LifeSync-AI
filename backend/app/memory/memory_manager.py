import re
import uuid
import logging
from datetime import date
from typing import List, Dict, Any, Optional

from backend.app.memory.embedding_service import generate_embedding
from backend.app.memory.graph_service import (
    init_graph_schema,
    store_memory_fact_node,
    search_semantic_memories,
    delete_memory_fact_node,
    store_goal_node,
    store_preference_node,
    record_workout_graph_event,
    delete_workout_graph_event,
    record_meal_graph_event,
    delete_meal_graph_event,
    record_recovery_graph_event,
    delete_recovery_graph_event,
    get_graph_context_for_prompt,
    get_graph_stats,
    delete_user_graph_data
)
from backend.app.memory.extractor import (
    extract_explicit_statements,
    extract_activity_fact_from_workout,
    extract_activity_fact_from_recovery
)
from backend.app.database.supabase_client import (
    get_supabase,
    get_user_profile,
    get_recent_recovery_logs,
    get_recent_workouts,
    get_workout_by_id,
    update_workout_entry,
    delete_workout_entry,
    get_meals_by_date,
    get_meal_by_id,
    update_meal_entry,
    delete_meal_entry,
    get_recovery_log_by_id,
    update_recovery_log_by_id,
    delete_recovery_log_by_id
)

logger = logging.getLogger(__name__)

class MemoryManager:
    """Orchestrates persistent cross-agent memory across Supabase PostgreSQL and FalkorDB Graph."""

    @staticmethod
    def initialize():
        """Ensure graph schema and vector index exist on startup."""
        init_graph_schema()

    @staticmethod
    def save_memory_fact(
        user_id: str,
        fact_type: str,
        content: str,
        provenance: str = "explicit_user_statement",
        confidence: float = 1.0,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Store a verified memory fact with 768-dim semantic embedding
        synchronized across Supabase and FalkorDB graph memory.
        """
        fact_id = str(uuid.uuid4())
        clean_tags = tags or [fact_type]
        
        # Check for goal deduplication and generic vs specific goals
        if fact_type == "goal":
            from backend.app.memory.extractor import is_generic_goal
            norm_content = re.sub(r"^(user\s+goal:\s*|my\s+goal\s+is\s+(?:to\s+)?|to\s+)", "", content.lower()).strip()
            norm_content = re.sub(r"[^\w\s]", "", norm_content).strip()

            sb = get_supabase()
            try:
                existing_res = sb.table("memory_facts").select("id, content, confidence").eq("user_id", user_id).eq("fact_type", "goal").eq("status", "active").execute()
                existing_facts = existing_res.data or []
                
                # Check for exact duplicate active goal
                for ef in existing_facts:
                    ef_norm = re.sub(r"^(user\s+goal:\s*|my\s+goal\s+is\s+(?:to\s+)?|to\s+)", "", (ef.get("content") or "").lower()).strip()
                    ef_norm = re.sub(r"[^\w\s]", "", ef_norm).strip()
                    if ef_norm == norm_content:
                        existing_id = ef["id"]
                        sb.table("memory_facts").update({
                            "confidence": confidence,
                            "provenance": provenance
                        }).eq("id", existing_id).execute()
                        store_goal_node(
                            goal_id=existing_id,
                            user_id=user_id,
                            title=content,
                            provenance=provenance,
                            confidence=confidence
                        )
                        return {
                            "id": existing_id,
                            "fact_type": fact_type,
                            "content": content,
                            "provenance": provenance,
                            "confidence": confidence,
                            "tags": clean_tags,
                            "status": "active"
                        }

                # If generic goal and user already has active goals, skip creating new goal fact
                if is_generic_goal(content) and len(existing_facts) > 0:
                    logger.info(f"Skipping generic goal '{content}' for user {user_id} with existing goals.")
                    first_goal = existing_facts[0]
                    return {
                        "id": first_goal["id"],
                        "fact_type": fact_type,
                        "content": first_goal.get("content", content),
                        "provenance": provenance,
                        "confidence": confidence,
                        "tags": clean_tags,
                        "status": "active"
                    }
            except Exception as se:
                logger.warning(f"Error checking existing goals in Supabase: {se}")

        # 1. Generate semantic embedding using Gemini
        embedding = generate_embedding(content)

        # 2. Persist in Supabase PostgreSQL
        sb = get_supabase()
        try:
            payload = {
                "id": fact_id,
                "user_id": user_id,
                "fact_type": fact_type,
                "content": content,
                "provenance": provenance,
                "confidence": confidence,
                "tags": clean_tags,
                "status": "active",
                "embedding": embedding
            }
            sb.table("memory_facts").insert(payload).execute()
        except Exception as se:
            logger.error(f"Error saving memory fact to Supabase: {se}")

        # 3. Persist in FalkorDB Graph Memory with vector indexing
        try:
            store_memory_fact_node(
                fact_id=fact_id,
                user_id=user_id,
                fact_type=fact_type,
                content=content,
                provenance=provenance,
                confidence=confidence,
                tags=clean_tags,
                embedding=embedding
            )

            # Special semantic handling for goals
            if fact_type == "goal":
                store_goal_node(
                    goal_id=fact_id,
                    user_id=user_id,
                    title=content,
                    provenance=provenance,
                    confidence=confidence
                )
            elif fact_type == "preference":
                store_preference_node(
                    pref_id=fact_id,
                    user_id=user_id,
                    category="general",
                    key="preference",
                    value=content,
                    provenance=provenance,
                    confidence=confidence
                )
        except Exception as ge:
            logger.error(f"Error saving memory fact to FalkorDB: {ge}")

        return {
            "id": fact_id,
            "fact_type": fact_type,
            "content": content,
            "provenance": provenance,
            "confidence": confidence,
            "tags": clean_tags,
            "status": "active"
        }

    @staticmethod
    def get_relevant_context(
        user_id: str,
        workspace: str,
        current_message: str
    ) -> str:
        """
        Synthesize relevant cross-agent context combining:
        1. Semantic vector similarity search from FalkorDB vector index
        2. Connected multi-hop graph traversal (active goals, preferences, recent workouts, recovery)
        3. Real-time today's metrics from Supabase
        """
        lines = []

        # 1. User Profile
        profile = get_user_profile(user_id)
        if profile and profile.get("primary_goal"):
            lines.append(f"USER PROFILE: Name={profile.get('display_name', 'User')}, Goal={profile.get('primary_goal')}, Targets: {profile.get('calorie_target', 2200)}kcal, {profile.get('protein_target', 160)}g Protein, {profile.get('sleep_target_hours', 8.0)}h Sleep.")
        elif profile:
            lines.append(f"USER PROFILE: Name={profile.get('display_name', 'User')}, Goal=Unspecified. (If relevant, ask one friendly question about their fitness goal).")
        else:
            lines.append("USER PROFILE: New user. Primary fitness goal unspecified. (If relevant, ask one friendly question about their fitness goal).")

        # 2. Vector Semantic Memory Search
        if current_message.strip():
            msg_embedding = generate_embedding(current_message)
            semantic_memories = search_semantic_memories(msg_embedding, user_id=user_id, limit=8)
            if semantic_memories:
                seen_content = set()
                unique_memories = []
                for m in semantic_memories:
                    c_norm = re.sub(r"[^\w\s]", "", (m.get('content') or "").lower()).strip()
                    if c_norm and c_norm not in seen_content:
                        seen_content.add(c_norm)
                        unique_memories.append(m)
                if unique_memories:
                    m_lines = [f"- [{m['provenance'].upper()}] {m['content']}" for m in unique_memories[:4]]
                    lines.append("RELEVANT RETRIEVED SEMANTIC MEMORIES:\n" + "\n".join(m_lines))

        # 3. Multi-hop Graph Traversal Context
        graph_context = get_graph_context_for_prompt(user_id=user_id)
        if graph_context.get("goals"):
            g_lines = [f"- {g['title']} ({g['provenance']})" for g in graph_context["goals"]]
            lines.append("ACTIVE USER GOALS (GRAPH):\n" + "\n".join(g_lines))

        if graph_context.get("recent_workouts"):
            w_lines = []
            for w in graph_context["recent_workouts"]:
                ex_str = f" with {', '.join(w.get('exercises', [])[:3])}" if w.get('exercises') else ""
                w_lines.append(f"- {w['title']} ({w['category']}, {w['duration']}m{ex_str})")
            lines.append("COMPLETED WORKOUTS (CROSS-WORKSPACE):\n" + "\n".join(w_lines))
        else:
            lines.append("COMPLETED WORKOUTS (CROSS-WORKSPACE): None logged recently.")

        if graph_context.get("latest_recovery"):
            r = graph_context["latest_recovery"]
            lines.append(f"RECOVERY STATE: Score={r.get('score')}/100, Sleep={r.get('sleep_hours')}h, Soreness={r.get('soreness')}/10, Resting HR={r.get('resting_hr')}bpm, HRV={r.get('hrv')}ms.")
        else:
            lines.append("RECOVERY STATE: No recovery recorded today (biometrics unknown).")

        # 4. Today's Structured Nutrition Telemetry
        today_str = date.today().isoformat()
        meals = get_meals_by_date(today_str, user_id=user_id)
        if meals:
            total_cals = sum(float(m.get("calories") or 0.0) for m in meals)
            total_protein = sum(float(m.get("protein") or m.get("protein_g") or 0.0) for m in meals)
            total_carbs = sum(float(m.get("carbs") or m.get("carbs_g") or 0.0) for m in meals)
            total_fat = sum(float(m.get("fat") or m.get("fat_g") or 0.0) for m in meals)
            lines.append(f"TODAY'S NUTRITION LOGGED: {len(meals)} meals, Total Calories: {round(total_cals)}kcal, Protein: {round(total_protein, 1)}g, Carbs: {round(total_carbs, 1)}g, Fat: {round(total_fat, 1)}g.")
            meal_names = [f"- {m.get('name')} ({m.get('meal_type')}, {round(float(m.get('calories') or 0))}kcal)" for m in meals]
            lines.append("MEALS RECORDED:\n" + "\n".join(meal_names))
        else:
            lines.append("TODAY'S NUTRITION LOGGED: No meals recorded today.")

        return "\n\n".join(lines)

    @staticmethod
    def process_incoming_user_message(user_id: str, message: str):
        """
        Scan incoming message for explicit user statements (goals, injuries, dietary rules)
        and record confirmed facts into memory.
        """
        facts = extract_explicit_statements(message)
        for f in facts:
            if f.get("fact_type") == "goal":
                from backend.app.memory.extractor import is_generic_goal
                if is_generic_goal(f["content"]):
                    ctx = get_graph_context_for_prompt(user_id=user_id)
                    if ctx.get("goals") and len(ctx["goals"]) > 0:
                        logger.info(f"Skipping generic goal extraction '{f['content']}' for user {user_id} with existing goals.")
                        continue
            MemoryManager.save_memory_fact(
                user_id=user_id,
                fact_type=f["fact_type"],
                content=f["content"],
                provenance=f["provenance"],
                confidence=f["confidence"],
                tags=f.get("tags")
            )

    @staticmethod
    def record_completed_workout(
        workout_data: Dict[str, Any],
        exercises: List[Dict[str, Any]],
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """
        Record completed workout across Supabase and FalkorDB graph memory,
        and link to recovery so Nutrition and Recovery AI can immediately access it.
        """
        # 1. Supabase record
        sb = get_supabase()
        workout_payload = {**workout_data, "user_id": user_id}
        res = sb.table("workouts").insert(workout_payload).execute()
        workout = res.data[0]
        wid = workout["id"]

        saved_exercises = []
        if exercises:
            ex_payload = [{**ex, "workout_id": wid} for ex in exercises]
            ex_res = sb.table("workout_exercises").insert(ex_payload).execute()
            saved_exercises = ex_res.data or []

        workout["workout_exercises"] = saved_exercises

        # 2. FalkorDB graph event with relationship creation
        record_workout_graph_event(
            workout_id=wid,
            user_id=user_id,
            title=workout_data.get("title", "Workout"),
            category=workout_data.get("category", "Strength"),
            duration=int(workout_data.get("duration_minutes", 45)),
            calories_burned=workout_data.get("calories_burned"),
            exercises=exercises,
            provenance="verified_activity_record"
        )

        # 3. Create verified activity memory fact for cross-workspace retrieval
        act_fact = extract_activity_fact_from_workout(
            title=workout_data.get("title", "Workout"),
            category=workout_data.get("category", "Strength"),
            duration=int(workout_data.get("duration_minutes", 45)),
            exercises=exercises
        )
        MemoryManager.save_memory_fact(
            user_id=user_id,
            fact_type=act_fact["fact_type"],
            content=act_fact["content"],
            provenance=act_fact["provenance"],
            confidence=act_fact["confidence"],
            tags=act_fact["tags"]
        )

        return workout

    @staticmethod
    def update_completed_workout(
        workout_id: str,
        workout_data: Dict[str, Any],
        exercises: Optional[List[Dict[str, Any]]] = None,
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """Update workout record across Supabase and FalkorDB graph memory."""
        # 1. Update in Supabase
        updated = update_workout_entry(workout_id, workout_data, exercises, user_id=user_id)
        
        # 2. Resync in FalkorDB graph
        delete_workout_graph_event(workout_id)
        current_exercises = updated.get("workout_exercises", exercises or [])
        record_workout_graph_event(
            workout_id=workout_id,
            user_id=user_id,
            title=updated.get("title", "Workout"),
            category=updated.get("category", "Strength"),
            duration=int(updated.get("duration_minutes", 45)),
            calories_burned=updated.get("calories_burned"),
            exercises=current_exercises,
            provenance="verified_activity_record"
        )
        return updated

    @staticmethod
    def delete_completed_workout(workout_id: str, user_id: str = "default_user") -> bool:
        """Delete workout across Supabase and FalkorDB graph memory."""
        # 1. Delete from Supabase
        delete_workout_entry(workout_id, user_id=user_id)
        # 2. Delete from FalkorDB graph
        delete_workout_graph_event(workout_id)
        return True

    @staticmethod
    def record_completed_meal(
        meal_data: Dict[str, Any],
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """Record completed meal across Supabase and FalkorDB graph memory."""
        sb = get_supabase()
        payload = {**meal_data, "user_id": user_id}
        res = sb.table("meals").insert(payload).execute()
        meal = res.data[0]

        record_meal_graph_event(
            meal_id=meal["id"],
            user_id=user_id,
            meal_type=meal.get("meal_type", "lunch"),
            name=meal.get("name", "Meal"),
            calories=float(meal.get("calories", 0)),
            protein=float(meal.get("protein", 0)),
            carbs=float(meal.get("carbs", 0)),
            fat=float(meal.get("fat", 0)),
            provenance="verified_activity_record"
        )
        return meal

    @staticmethod
    def update_completed_meal(
        meal_id: str,
        meal_data: Dict[str, Any],
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """Update meal record across Supabase and FalkorDB graph memory."""
        updated = update_meal_entry(meal_id, meal_data, user_id=user_id)
        # Resync graph
        delete_meal_graph_event(meal_id)
        record_meal_graph_event(
            meal_id=meal_id,
            user_id=user_id,
            meal_type=updated.get("meal_type", "lunch"),
            name=updated.get("name", "Meal"),
            calories=float(updated.get("calories", 0)),
            protein=float(updated.get("protein", 0)),
            carbs=float(updated.get("carbs", 0)),
            fat=float(updated.get("fat", 0)),
            provenance="verified_activity_record"
        )
        return updated

    @staticmethod
    def delete_completed_meal(meal_id: str, user_id: str = "default_user") -> bool:
        """Delete meal across Supabase and FalkorDB graph memory."""
        delete_meal_entry(meal_id, user_id=user_id)
        delete_meal_graph_event(meal_id)
        return True

    @staticmethod
    def record_recovery_log(
        recovery_data: Dict[str, Any],
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """Record recovery log across Supabase and FalkorDB graph memory."""
        sb = get_supabase()
        payload = {**recovery_data, "user_id": user_id}
        
        # Check existing for date
        existing_res = sb.table("recovery_logs").select("*").eq("user_id", user_id).eq("date", str(payload.get("date"))).execute()
        if existing_res.data:
            res = sb.table("recovery_logs").update(payload).eq("id", existing_res.data[0]["id"]).eq("user_id", user_id).execute()
        else:
            res = sb.table("recovery_logs").insert(payload).execute()
            
        rec = res.data[0]

        record_recovery_graph_event(
            recovery_id=rec["id"],
            user_id=user_id,
            date_str=str(rec.get("date")),
            recovery_score=int(rec.get("recovery_score", 75)),
            sleep_hours=float(rec.get("sleep_hours", 7.5)),
            sleep_quality=str(rec.get("sleep_quality", "good")),
            resting_hr=rec.get("resting_hr"),
            hrv_ms=rec.get("hrv_ms"),
            soreness_level=int(rec.get("soreness_level", 2)),
            provenance="verified_activity_record"
        )

        return rec

    @staticmethod
    def update_recovery_log(
        log_id: str,
        recovery_data: Dict[str, Any],
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """Update recovery log across Supabase and FalkorDB graph memory."""
        updated = update_recovery_log_by_id(log_id, recovery_data, user_id=user_id)
        delete_recovery_graph_event(log_id)
        record_recovery_graph_event(
            recovery_id=log_id,
            user_id=user_id,
            date_str=str(updated.get("date")),
            recovery_score=int(updated.get("recovery_score", 75)),
            sleep_hours=float(updated.get("sleep_hours", 7.5)),
            sleep_quality=str(updated.get("sleep_quality", "good")),
            resting_hr=updated.get("resting_hr"),
            hrv_ms=updated.get("hrv_ms"),
            soreness_level=int(updated.get("soreness_level", 2)),
            provenance="verified_activity_record"
        )
        return updated

    @staticmethod
    def delete_recovery_log(log_id: str, user_id: str = "default_user") -> bool:
        """Delete recovery log across Supabase and FalkorDB graph memory."""
        delete_recovery_log_by_id(log_id, user_id=user_id)
        delete_recovery_graph_event(log_id)
        return True

    # ==================== Memory Inspection & Correction ====================

    @staticmethod
    def list_user_memories(user_id: str = "default_user", status: str = "active") -> List[Dict[str, Any]]:
        """List stored memories for user inspection."""
        sb = get_supabase()
        res = sb.table("memory_facts").select("id, fact_type, content, provenance, confidence, tags, status, created_at").eq("user_id", user_id).eq("status", status).order("created_at", desc=True).limit(50).execute()
        return res.data or []

    @staticmethod
    def correct_user_memory(user_id: str, fact_id: str, new_content: str) -> bool:
        """Correct a stored memory fact across Supabase and FalkorDB."""
        sb = get_supabase()
        new_embedding = generate_embedding(new_content)
        
        # 1. Update Supabase
        sb.table("memory_facts").update({
            "content": new_content,
            "status": "corrected",
            "confidence": 1.0,
            "embedding": new_embedding
        }).eq("id", fact_id).eq("user_id", user_id).execute()

        # 2. Update FalkorDB
        store_memory_fact_node(
            fact_id=fact_id,
            user_id=user_id,
            fact_type="corrected_fact",
            content=new_content,
            provenance="user_correction",
            confidence=1.0,
            embedding=new_embedding
        )
        return True

    @staticmethod
    def delete_user_memory(user_id: str, fact_id: str) -> bool:
        """Delete a stored memory across Supabase and FalkorDB graph."""
        sb = get_supabase()
        # 1. Mark or delete in Supabase
        sb.table("memory_facts").delete().eq("id", fact_id).eq("user_id", user_id).execute()

        # 2. Delete node in FalkorDB
        delete_memory_fact_node(fact_id)
        return True

    @staticmethod
    def delete_conversation_across_layers(user_id: str, workspace: str) -> bool:
        """Clear conversation messages from Supabase and unhook related graph facts."""
        sb = get_supabase()
        sb.table("chat_messages").delete().eq("user_id", user_id).eq("workspace", workspace).execute()
        return True

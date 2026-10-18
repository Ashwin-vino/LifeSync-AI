import re
import logging
import time
from typing import List, Dict, Any, Optional
from falkordb import FalkorDB
from backend.app.config import settings

logger = logging.getLogger(__name__)

_falkor_client: Optional[FalkorDB] = None

def get_falkordb() -> FalkorDB:
    global _falkor_client
    if _falkor_client is None:
        _falkor_client = FalkorDB(
            host=settings.FALKORDB_HOST,
            port=settings.FALKORDB_PORT,
            username=settings.FALKORDB_USERNAME,
            password=settings.FALKORDB_PASSWORD,
            ssl=settings.FALKORDB_TLS
        )
    return _falkor_client

def get_graph():
    client = get_falkordb()
    return client.select_graph(settings.FALKORDB_GRAPH_NAME)

def sanitize_string(val: str) -> str:
    """Escape backslashes and quotes for safe inclusion in Cypher literals."""
    if not isinstance(val, str):
        val = str(val)
    return val.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")

def format_vector_literal(vec: List[float]) -> str:
    """Format float array for vecf32 literal in FalkorDB."""
    return '[' + ', '.join(f'{x:.5f}' for x in vec) + ']'

def init_graph_schema():
    """Ensure all core schema, user node, and vector index exist in FalkorDB."""
    try:
        g = get_graph()
        # 1. Merge default user
        g.query("""
            MERGE (u:User {id: 'default_user'})
            ON CREATE SET u.name = 'Ashwin', u.created_at = timestamp()
        """)

        # 2. Vector index on MemoryFact(embedding) with 768 dimensions
        try:
            g.query("""
                CREATE VECTOR INDEX FOR (m:MemoryFact) 
                ON (m.embedding) 
                OPTIONS {dimension: 768, similarityFunction: 'cosine'}
            """)
            logger.info("FalkorDB vector index created for :MemoryFact(embedding).")
        except Exception as ie:
            # Index might already exist
            if "already exists" not in str(ie).lower():
                logger.debug(f"Vector index notice: {ie}")

    except Exception as e:
        logger.error(f"FalkorDB schema init error: {e}")

# ==================== Memory Facts & Semantic Retrieval ====================

def store_memory_fact_node(
    fact_id: str,
    user_id: str,
    fact_type: str,
    content: str,
    provenance: str = "explicit_user_statement",
    confidence: float = 1.0,
    tags: Optional[List[str]] = None,
    embedding: Optional[List[float]] = None
) -> bool:
    """Persist a MemoryFact node with vector embedding and link to User via [:REMINDED_OF]."""
    try:
        g = get_graph()
        tags_list = tags or []
        s_fact_id = sanitize_string(fact_id)
        s_user_id = sanitize_string(user_id)
        s_fact_type = sanitize_string(fact_type)
        s_content = sanitize_string(content)
        s_provenance = sanitize_string(provenance)
        tags_str = '["' + '", "'.join(sanitize_string(t) for t in tags_list) + '"]' if tags_list else '[]'

        embedding_clause = ""
        if embedding and len(embedding) == 768:
            vec_lit = format_vector_literal(embedding)
            embedding_clause = f", f.embedding = vecf32({vec_lit})"

        query = f"""
            MERGE (u:User {{id: '{s_user_id}'}})
            MERGE (f:MemoryFact {{id: '{s_fact_id}'}})
            SET f.fact_type = '{s_fact_type}',
                f.content = '{s_content}',
                f.provenance = '{s_provenance}',
                f.confidence = {float(confidence)},
                f.tags = {tags_str},
                f.status = 'active',
                f.timestamp = timestamp()
                {embedding_clause}
            MERGE (u)-[:REMINDED_OF]->(f)
        """
        g.query(query)
        return True
    except Exception as e:
        logger.error(f"Error storing memory fact node: {e}")
        return False

def search_semantic_memories(
    query_embedding: List[float],
    user_id: str = "default_user",
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Perform k-NN vector search across MemoryFact nodes in FalkorDB."""
    if not query_embedding or len(query_embedding) != 768:
        return []
    try:
        g = get_graph()
        vec_lit = format_vector_literal(query_embedding)
        s_user_id = sanitize_string(user_id)
        query = f"""
            CALL db.idx.vector.queryNodes('MemoryFact', 'embedding', {int(limit)}, vecf32({vec_lit})) 
            YIELD node, score
            MATCH (u:User {{id: '{s_user_id}'}})-[:REMINDED_OF]->(node)
            WHERE node.status = 'active'
            RETURN node.id, node.fact_type, node.content, node.provenance, node.confidence, score
            ORDER BY score ASC
        """
        res = g.query(query)
        results = []
        if res and res.result_set:
            for row in res.result_set:
                results.append({
                    "id": row[0],
                    "fact_type": row[1],
                    "content": row[2],
                    "provenance": row[3],
                    "confidence": float(row[4] or 1.0),
                    "score": float(row[5] or 0.0)
                })
        return results
    except Exception as e:
        logger.error(f"Error in vector semantic search: {e}")
        return []

def delete_memory_fact_node(fact_id: str) -> bool:
    """Delete a MemoryFact node and its relationships in FalkorDB."""
    try:
        g = get_graph()
        s_id = sanitize_string(fact_id)
        g.query(f"MATCH (f:MemoryFact {{id: '{s_id}'}}) DETACH DELETE f")
        return True
    except Exception as e:
        logger.error(f"Error deleting memory fact node {fact_id}: {e}")
        return False

# ==================== User Goals & Preferences ====================

def store_goal_node(
    goal_id: str,
    user_id: str,
    title: str,
    category: str = "strength",
    provenance: str = "explicit_user_statement",
    confidence: float = 1.0
) -> bool:
    """Store Goal node and create [:USER_HAS_GOAL] relationship."""
    try:
        g = get_graph()
        s_gid = sanitize_string(goal_id)
        s_uid = sanitize_string(user_id)
        s_title = sanitize_string(title)
        s_cat = sanitize_string(category)
        s_prov = sanitize_string(provenance)

        query = f"""
            MERGE (u:User {{id: '{s_uid}'}})
            MERGE (g:Goal {{id: '{s_gid}'}})
            SET g.title = '{s_title}',
                g.category = '{s_cat}',
                g.provenance = '{s_prov}',
                g.confidence = {float(confidence)},
                g.status = 'active',
                g.timestamp = timestamp()
            MERGE (u)-[:USER_HAS_GOAL]->(g)
        """
        g.query(query)
        return True
    except Exception as e:
        logger.error(f"Error storing goal node: {e}")
        return False

def store_preference_node(
    pref_id: str,
    user_id: str,
    category: str,
    key: str,
    value: str,
    provenance: str = "explicit_user_statement",
    confidence: float = 1.0
) -> bool:
    """Store Preference node and create [:USER_HAS_PREFERENCE] relationship."""
    try:
        g = get_graph()
        s_pid = sanitize_string(pref_id)
        s_uid = sanitize_string(user_id)
        s_cat = sanitize_string(category)
        s_key = sanitize_string(key)
        s_val = sanitize_string(value)
        s_prov = sanitize_string(provenance)

        query = f"""
            MERGE (u:User {{id: '{s_uid}'}})
            MERGE (p:Preference {{id: '{s_pid}'}})
            SET p.category = '{s_cat}',
                p.key = '{s_key}',
                p.value = '{s_val}',
                p.provenance = '{s_prov}',
                p.confidence = {float(confidence)},
                p.timestamp = timestamp()
            MERGE (u)-[:USER_HAS_PREFERENCE]->(p)
        """
        g.query(query)
        return True
    except Exception as e:
        logger.error(f"Error storing preference node: {e}")
        return False

# ==================== Workout, Meal & Recovery Cross-Agent Events ====================

def record_workout_graph_event(
    workout_id: str,
    user_id: str,
    title: str,
    category: str,
    duration: int,
    calories_burned: Optional[int],
    exercises: List[Dict[str, Any]],
    provenance: str = "verified_activity_record"
) -> bool:
    """
    Store WorkoutSession, link [:USER_COMPLETED_WORKOUT],
    link [:WORKOUT_CONTAINS_EXERCISE] to each Exercise,
    and link [:ACTIVITY_INFLUENCES_RECOVERY {impact: 'fatigue'}] to latest recovery snapshot.
    """
    try:
        g = get_graph()
        s_wid = sanitize_string(workout_id)
        s_uid = sanitize_string(user_id)
        s_title = sanitize_string(title)
        s_cat = sanitize_string(category)
        s_prov = sanitize_string(provenance)
        cals = calories_burned or 0

        # 1. Create WorkoutSession and link User
        g.query(f"""
            MERGE (u:User {{id: '{s_uid}'}})
            MERGE (w:WorkoutSession {{id: '{s_wid}'}})
            SET w.title = '{s_title}',
                w.category = '{s_cat}',
                w.duration = {int(duration)},
                w.calories_burned = {int(cals)},
                w.provenance = '{s_prov}',
                w.timestamp = timestamp()
            MERGE (u)-[:USER_COMPLETED_WORKOUT]->(w)
        """)

        # 2. Link Exercise nodes with set/rep/weight properties
        for ex in exercises:
            ex_name = sanitize_string(ex.get("exercise_name", "Exercise"))
            sets = int(ex.get("sets", 3))
            reps = int(ex.get("reps", 10))
            weight = float(ex.get("weight_kg", 0.0))

            g.query(f"""
                MATCH (w:WorkoutSession {{id: '{s_wid}'}})
                MERGE (e:Exercise {{name: '{ex_name}'}})
                CREATE (w)-[:WORKOUT_CONTAINS_EXERCISE {{sets: {sets}, reps: {reps}, weight_kg: {weight}}}]->(e)
            """)

        # 3. Link [:ACTIVITY_INFLUENCES_RECOVERY] to user's recent recovery snapshot if present
        g.query(f"""
            MATCH (u:User {{id: '{s_uid}'}})-[:HAS_RECOVERY_SNAPSHOT]->(r:RecoverySnapshot)
            MATCH (w:WorkoutSession {{id: '{s_wid}'}})
            CREATE (w)-[:ACTIVITY_INFLUENCES_RECOVERY {{impact: 'fatigue', timestamp: timestamp()}}]->(r)
        """)

        return True
    except Exception as e:
        logger.error(f"Error recording workout in graph: {e}")
        return False

def delete_workout_graph_event(workout_id: str) -> bool:
    """Delete a WorkoutSession node and all its connected relationships in FalkorDB."""
    try:
        g = get_graph()
        s_wid = sanitize_string(workout_id)
        g.query(f"MATCH (w:WorkoutSession {{id: '{s_wid}'}}) DETACH DELETE w")
        return True
    except Exception as e:
        logger.error(f"Error deleting workout node {workout_id} in graph: {e}")
        return False

def record_meal_graph_event(
    meal_id: str,
    user_id: str,
    meal_type: str,
    name: str,
    calories: float,
    protein: float,
    carbs: float,
    fat: float,
    provenance: str = "verified_activity_record"
) -> bool:
    """Store MealRecord and link [:USER_LOGGED_MEAL] and [:ACTIVITY_INFLUENCES_RECOVERY {impact: 'fuel'}]."""
    try:
        g = get_graph()
        s_mid = sanitize_string(meal_id)
        s_uid = sanitize_string(user_id)
        s_mtype = sanitize_string(meal_type)
        s_name = sanitize_string(name)
        s_prov = sanitize_string(provenance)

        query = f"""
            MERGE (u:User {{id: '{s_uid}'}})
            MERGE (m:MealRecord {{id: '{s_mid}'}})
            SET m.meal_type = '{s_mtype}',
                m.name = '{s_name}',
                m.calories = {float(calories)},
                m.protein = {float(protein)},
                m.carbs = {float(carbs)},
                m.fat = {float(fat)},
                m.provenance = '{s_prov}',
                m.timestamp = timestamp()
            MERGE (u)-[:USER_LOGGED_MEAL]->(m)
        """
        g.query(query)

        # Link to recovery snapshot
        g.query(f"""
            MATCH (u:User {{id: '{s_uid}'}})-[:HAS_RECOVERY_SNAPSHOT]->(r:RecoverySnapshot)
            MATCH (m:MealRecord {{id: '{s_mid}'}})
            CREATE (m)-[:ACTIVITY_INFLUENCES_RECOVERY {{impact: 'fuel', timestamp: timestamp()}}]->(r)
        """)
        return True
    except Exception as e:
        logger.error(f"Error recording meal in graph: {e}")
        return False

def record_recovery_graph_event(
    recovery_id: str,
    user_id: str,
    date_str: str,
    recovery_score: int,
    sleep_hours: float,
    sleep_quality: str,
    resting_hr: Optional[int],
    hrv_ms: Optional[int],
    soreness_level: int,
    provenance: str = "verified_activity_record"
) -> bool:
    """Store RecoverySnapshot and link [:HAS_RECOVERY_SNAPSHOT] to User."""
    try:
        g = get_graph()
        s_rid = sanitize_string(recovery_id)
        s_uid = sanitize_string(user_id)
        s_date = sanitize_string(date_str)
        s_qual = sanitize_string(sleep_quality)
        s_prov = sanitize_string(provenance)
        r_hr = resting_hr or 60
        hrv = hrv_ms or 65

        query = f"""
            MERGE (u:User {{id: '{s_uid}'}})
            MERGE (r:RecoverySnapshot {{id: '{s_rid}'}})
            SET r.date = '{s_date}',
                r.recovery_score = {int(recovery_score)},
                r.sleep_hours = {float(sleep_hours)},
                r.sleep_quality = '{s_qual}',
                r.resting_hr = {int(r_hr)},
                r.hrv_ms = {int(hrv)},
                r.soreness_level = {int(soreness_level)},
                r.provenance = '{s_prov}',
                r.timestamp = timestamp()
            MERGE (u)-[:HAS_RECOVERY_SNAPSHOT]->(r)
        """
        g.query(query)
        return True
    except Exception as e:
        logger.error(f"Error recording recovery snapshot in graph: {e}")
        return False

def delete_meal_graph_event(meal_id: str) -> bool:
    """Delete a MealRecord node and all its connected relationships in FalkorDB."""
    try:
        g = get_graph()
        s_mid = sanitize_string(meal_id)
        g.query(f"MATCH (m:MealRecord {{id: '{s_mid}'}}) DETACH DELETE m")
        return True
    except Exception as e:
        logger.error(f"Error deleting meal node {meal_id} in graph: {e}")
        return False

def delete_recovery_graph_event(recovery_id: str) -> bool:
    """Delete a RecoverySnapshot node and all its connected relationships in FalkorDB."""
    try:
        g = get_graph()
        s_rid = sanitize_string(recovery_id)
        g.query(f"MATCH (r:RecoverySnapshot {{id: '{s_rid}'}}) DETACH DELETE r")
        return True
    except Exception as e:
        logger.error(f"Error deleting recovery node {recovery_id} in graph: {e}")
        return False

# ==================== Graph Traversal & Unified Context ====================

def get_graph_context_for_prompt(user_id: str = "default_user") -> Dict[str, Any]:
    """
    Perform multi-hop graph traversal to extract all active goals, preferences,
    completed workouts, and recovery state for the user.
    """
    try:
        g = get_graph()
        s_uid = sanitize_string(user_id)

        # 1. Active Goals
        goals_res = g.query(f"""
            MATCH (u:User {{id: '{s_uid}'}})-[:USER_HAS_GOAL]->(g:Goal)
            WHERE g.status = 'active'
            RETURN g.title, g.category, g.provenance, g.timestamp
            ORDER BY g.timestamp DESC LIMIT 5
        """)
        goals = [{"title": r[0], "category": r[1], "provenance": r[2]} for r in (goals_res.result_set or [])]

        # 2. Active Preferences
        prefs_res = g.query(f"""
            MATCH (u:User {{id: '{s_uid}'}})-[:USER_HAS_PREFERENCE]->(p:Preference)
            RETURN p.category, p.key, p.value, p.provenance, p.timestamp
            ORDER BY p.timestamp DESC LIMIT 6
        """)
        preferences = [{"category": r[0], "key": r[1], "value": r[2], "provenance": r[3]} for r in (prefs_res.result_set or [])]

        # 3. Completed Workouts & Targeted Exercises
        workouts_res = g.query(f"""
            MATCH (u:User {{id: '{s_uid}'}})-[:USER_COMPLETED_WORKOUT]->(w:WorkoutSession)
            OPTIONAL MATCH (w)-[c:WORKOUT_CONTAINS_EXERCISE]->(e:Exercise)
            WITH w, collect(e.name) AS exercises
            RETURN w.title, w.category, w.duration, exercises, w.timestamp
            ORDER BY w.timestamp DESC LIMIT 3
        """)
        workouts = [{"title": r[0], "category": r[1], "duration": r[2], "exercises": r[3]} for r in (workouts_res.result_set or [])]

        # 4. Latest Recovery Snapshot & Influences
        recovery_res = g.query(f"""
            MATCH (u:User {{id: '{s_uid}'}})-[:HAS_RECOVERY_SNAPSHOT]->(r:RecoverySnapshot)
            RETURN r.date, r.recovery_score, r.sleep_hours, r.soreness_level, r.resting_hr, r.hrv_ms, r.timestamp
            ORDER BY r.timestamp DESC LIMIT 1
        """)
        latest_recovery = None
        if recovery_res and recovery_res.result_set:
            r = recovery_res.result_set[0]
            latest_recovery = {
                "date": r[0],
                "score": r[1],
                "sleep_hours": r[2],
                "soreness": r[3],
                "resting_hr": r[4],
                "hrv": r[5]
            }

        return {
            "goals": goals,
            "preferences": preferences,
            "recent_workouts": workouts,
            "latest_recovery": latest_recovery
        }
    except Exception as e:
        logger.error(f"Error querying graph context: {e}")
        return {"goals": [], "preferences": [], "recent_workouts": [], "latest_recovery": None}

def get_graph_stats(user_id: str = "default_user") -> Dict[str, Any]:
    """Return overview counts of nodes and relationships in the user's graph."""
    try:
        g = get_graph()
        n_res = g.query("MATCH (n) RETURN count(n)")
        e_res = g.query("MATCH ()-[r]->() RETURN count(r)")
        
        nodes = n_res.result_set[0][0] if n_res and n_res.result_set else 0
        edges = e_res.result_set[0][0] if e_res and e_res.result_set else 0

        return {
            "connected": True,
            "graph_name": settings.FALKORDB_GRAPH_NAME,
            "nodes": nodes,
            "edges": edges
        }
    except Exception as e:
        logger.error(f"Error getting graph stats: {e}")
        return {"connected": False, "error": str(e)}

def delete_user_graph_data(user_id: str) -> bool:
    """Prune all graph nodes associated with a user."""
    try:
        g = get_graph()
        s_uid = sanitize_string(user_id)
        g.query(f"""
            MATCH (u:User {{id: '{s_uid}'}})-[r]->(target)
            DETACH DELETE target
        """)
        return True
    except Exception as e:
        logger.error(f"Error deleting user graph data: {e}")
        return False

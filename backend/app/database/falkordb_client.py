import logging
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

def init_graph():
    """Ensure basic schema and indices exist in FalkorDB."""
    try:
        g = get_graph()
        # Merge initial user node
        g.query("""
            MERGE (u:User {id: 'default_user'})
            ON CREATE SET u.name = 'Ashwin', u.created_at = timestamp()
        """)
    except Exception as e:
        logger.error(f"FalkorDB graph init error: {e}")

def add_memory_fact(user_id: str, fact_type: str, content: str, confidence: float = 1.0) -> bool:
    try:
        g = get_graph()
        g.query("""
            MATCH (u:User {id: $user_id})
            CREATE (f:MemoryFact {
                type: $fact_type,
                content: $content,
                confidence: $confidence,
                timestamp: timestamp()
            })
            CREATE (u)-[:REMINDED_OF]->(f)
        """, {
            "user_id": user_id,
            "fact_type": fact_type,
            "content": content,
            "confidence": confidence
        })
        return True
    except Exception as e:
        logger.error(f"Error adding memory fact: {e}")
        return False

def record_workout_graph_event(user_id: str, title: str, category: str, duration: int, exercises: List[str]) -> bool:
    try:
        g = get_graph()
        query = """
            MATCH (u:User {id: $user_id})
            CREATE (w:WorkoutSession {
                title: $title,
                category: $category,
                duration: $duration,
                timestamp: timestamp()
            })
            CREATE (u)-[:PERFORMED]->(w)
        """
        params: Dict[str, Any] = {
            "user_id": user_id,
            "title": title,
            "category": category,
            "duration": duration
        }
        g.query(query, params)
        
        for ex in exercises:
            g.query("""
                MATCH (w:WorkoutSession {title: $title, duration: $duration})
                MERGE (e:Exercise {name: $ex})
                CREATE (w)-[:TARGETS]->(e)
            """, {"title": title, "duration": duration, "ex": ex})
            
        return True
    except Exception as e:
        logger.error(f"Error recording workout in graph: {e}")
        return False

def get_user_memory_context(user_id: str = "default_user", limit: int = 15) -> List[Dict[str, Any]]:
    """Retrieve connected knowledge graph nodes for the user to inject into AI prompt context."""
    try:
        g = get_graph()
        res = g.query("""
            MATCH (u:User {id: $user_id})-[r]->(target)
            RETURN type(r) AS relation, labels(target)[0] AS label, target.content AS content, target.title AS title, target.type AS type
            ORDER BY target.timestamp DESC
            LIMIT $limit
        """, {"user_id": user_id, "limit": limit})
        
        memories = []
        if res and res.result_set:
            for row in res.result_set:
                memories.append({
                    "relation": row[0],
                    "label": row[1],
                    "content": row[2] or row[3] or "",
                    "type": row[4] or ""
                })
        return memories
    except Exception as e:
        logger.error(f"Error retrieving memory context: {e}")
        return []

def get_graph_overview(user_id: str = "default_user") -> Dict[str, Any]:
    try:
        g = get_graph()
        nodes_res = g.query("MATCH (n) RETURN count(n) AS node_count")
        edges_res = g.query("MATCH ()-[r]->() RETURN count(r) AS edge_count")
        
        node_count = nodes_res.result_set[0][0] if nodes_res and nodes_res.result_set else 0
        edge_count = edges_res.result_set[0][0] if edges_res and edges_res.result_set else 0
        
        return {
            "connected": True,
            "graph_name": settings.FALKORDB_GRAPH_NAME,
            "nodes": node_count,
            "edges": edge_count
        }
    except Exception as e:
        logger.error(f"Error getting graph overview: {e}")
        return {
            "connected": False,
            "error": str(e)
        }

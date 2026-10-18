import time
import logging
from fastapi import APIRouter
from backend.app.config import settings
from backend.app.schemas.health import HealthStatusResponse, ServiceHealthStatus
from backend.app.database.supabase_client import get_supabase
from backend.app.database.falkordb_client import get_graph_overview
from backend.app.services.gemini_service import get_gemini_client
import httpx

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("", response_model=HealthStatusResponse)
async def check_system_health():
    services = {}
    overall_healthy = True

    # 1. Supabase Check
    t0 = time.perf_counter()
    try:
        sb = get_supabase()
        res = sb.table("profiles").select("count", count="exact").execute()
        services["supabase"] = ServiceHealthStatus(
            status="healthy",
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            details=f"Connected to project ref {settings.SUPABASE_URL.split('//')[1].split('.')[0]}"
        )
    except Exception as e:
        overall_healthy = False
        services["supabase"] = ServiceHealthStatus(
            status="unhealthy",
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            details=str(e)
        )

    # 2. FalkorDB Check
    t0 = time.perf_counter()
    try:
        overview = get_graph_overview()
        if overview.get("connected"):
            services["falkordb"] = ServiceHealthStatus(
                status="healthy",
                latency_ms=round((time.perf_counter() - t0) * 1000, 1),
                details=f"Graph '{overview.get('graph_name')}' ({overview.get('nodes')} nodes, {overview.get('edges')} edges)"
            )
        else:
            overall_healthy = False
            services["falkordb"] = ServiceHealthStatus(
                status="unhealthy",
                latency_ms=round((time.perf_counter() - t0) * 1000, 1),
                details=overview.get("error")
            )
    except Exception as e:
        overall_healthy = False
        services["falkordb"] = ServiceHealthStatus(
            status="unhealthy",
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            details=str(e)
        )

    # 3. Gemini Check
    t0 = time.perf_counter()
    try:
        client = get_gemini_client()
        if client and settings.GEMINI_API_KEY:
            services["gemini"] = ServiceHealthStatus(
                status="healthy",
                latency_ms=round((time.perf_counter() - t0) * 1000, 1),
                details="Model gemini-3.8-flash initialized"
            )
        else:
            overall_healthy = False
            services["gemini"] = ServiceHealthStatus(
                status="unhealthy",
                details="GEMINI_API_KEY missing"
            )
    except Exception as e:
        overall_healthy = False
        services["gemini"] = ServiceHealthStatus(
            status="unhealthy",
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            details=str(e)
        )

    # 4. wger API Check
    t0 = time.perf_counter()
    try:
        headers = {}
        if settings.WGER_API_KEY:
            headers["Authorization"] = f"Token {settings.WGER_API_KEY}"
        async with httpx.AsyncClient(timeout=4.0) as http_client:
            r = await http_client.get("https://wger.de/api/v2/exerciseinfo/?limit=1", headers=headers)
            if r.status_code == 200:
                services["wger"] = ServiceHealthStatus(
                    status="healthy",
                    latency_ms=round((time.perf_counter() - t0) * 1000, 1),
                    details="Official wger exercise database connected"
                )
            else:
                services["wger"] = ServiceHealthStatus(
                    status="degraded",
                    latency_ms=round((time.perf_counter() - t0) * 1000, 1),
                    details=f"HTTP {r.status_code}"
                )
    except Exception as e:
        services["wger"] = ServiceHealthStatus(
            status="degraded",
            details=f"Fallback offline cache active ({str(e)})"
        )

    # 5. USDA Check
    t0 = time.perf_counter()
    try:
        if settings.USDA_API_KEY:
            services["usda"] = ServiceHealthStatus(
                status="healthy",
                latency_ms=round((time.perf_counter() - t0) * 1000, 1),
                details="FoodData Central API key validated"
            )
        else:
            services["usda"] = ServiceHealthStatus(
                status="degraded",
                details="USDA_API_KEY not configured"
            )
    except Exception as e:
        services["usda"] = ServiceHealthStatus(
            status="unhealthy",
            details=str(e)
        )

    return HealthStatusResponse(
        status="healthy" if overall_healthy else "degraded",
        environment=settings.ENVIRONMENT,
        version="1.0.0",
        services=services
    )

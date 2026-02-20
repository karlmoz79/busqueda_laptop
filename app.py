"""
Amazon Price Tracker — FastAPI Backend
Expone una API REST para el scraper y sirve el frontend estático.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from notifier import EmailNotifier
from scraper import AmazonScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ── Pydantic Schemas ──

class SearchRequest(BaseModel):
    query: str = "Lenovo ThinkBook 16"
    price_threshold: float = 750.0


class ProductResult(BaseModel):
    title: str
    price_usd: float | None
    url: str
    ships_to_colombia: bool


class SearchResponse(BaseModel):
    status: str
    count: int
    price_min: float | None
    price_max: float | None
    alerts_sent: int
    products: list[ProductResult]


# ── App ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Amazon Price Tracker API iniciada")
    yield
    logger.info("API cerrada")


app = FastAPI(
    title="Amazon Price Tracker",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── Routes ──

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Sirve el frontend HTML."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    return HTMLResponse("<h1>Frontend no encontrado</h1>", status_code=404)


@app.post("/api/search", response_model=SearchResponse)
async def search_products(req: SearchRequest):
    """Ejecuta el scraper y retorna productos encontrados."""
    scraper = AmazonScraper()

    if req.query.strip():
        scraper.search_query = req.query.strip()

    # Ejecutar scraper en un hilo separado para no bloquear el event loop
    resultados = await scraper.scrape()

    if not resultados:
        return SearchResponse(
            status="No se encontraron resultados. Amazon pudo haber bloqueado la solicitud.",
            count=0,
            price_min=None,
            price_max=None,
            alerts_sent=0,
            products=[],
        )

    # Procesar resultados
    notifier = EmailNotifier()
    alerts_sent = 0
    price_min = float("inf")
    price_max = 0.0
    products: list[ProductResult] = []

    for r in resultados:
        if r.price_usd and r.price_usd > 0:
            price_min = min(price_min, r.price_usd)
            price_max = max(price_max, r.price_usd)

        if r.price_usd and notifier.target_price_met(r.price_usd, req.price_threshold):
            if notifier.send_alert(r):
                alerts_sent += 1

        products.append(
            ProductResult(
                title=r.title,
                price_usd=r.price_usd,
                url=r.url,
                ships_to_colombia=r.ships_to_colombia,
            )
        )

    return SearchResponse(
        status=f"Busqueda completada — {len(products)} productos encontrados.",
        count=len(products),
        price_min=price_min if price_min != float("inf") else None,
        price_max=price_max if price_max > 0 else None,
        alerts_sent=alerts_sent,
        products=products,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=7860, reload=True)

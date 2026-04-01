import os

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.rate_limit import limiter
from database import get_db
from routers import annotate, auth, clean, collect, dashboard, data, review, seed, users

# Em produção, definir CORS_ORIGINS no Vercel Dashboard:
#   CORS_ORIGINS=https://seu-frontend.vercel.app
# Em desenvolvimento, o padrão é localhost:3000
CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
]

app = FastAPI(title="Plataforma YouTube Bots API", version="0.1.0")

# Rate limiting (slowapi)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Muitas tentativas. Tente novamente em alguns minutos."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(collect.router)
app.include_router(clean.router)
app.include_router(data.router)
app.include_router(dashboard.router)
app.include_router(annotate.router)
app.include_router(review.router)
app.include_router(seed.router)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}

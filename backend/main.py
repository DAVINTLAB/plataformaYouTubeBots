import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, collect, users

# Em produção, definir CORS_ORIGINS no Vercel Dashboard:
#   CORS_ORIGINS=https://seu-frontend.vercel.app
# Em desenvolvimento, o padrão é localhost:3000
CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
]

app = FastAPI(title="Plataforma YouTube Bots API", version="0.1.0")

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


@app.get("/health")
def health():
    return {"status": "ok"}

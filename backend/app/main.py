from fastapi import FastAPI
from redis.asyncio import Redis
from starsessions.stores.redis import RedisStore
from starsessions import SessionMiddleware
from app.db.database import create_db_and_tables
from app.routers import auth, users

app = FastAPI()
app.include_router(auth.router)
app.include_router(users.router)
redis = Redis.from_url("redis://localhost:6379")
app.add_middleware(SessionMiddleware, store=RedisStore(redis), secret_key="...")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/")
async def root():
    return {"status": "ok"}
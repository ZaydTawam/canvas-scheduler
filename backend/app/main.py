from fastapi import FastAPI
from app.db.db import create_db_and_tables

create_db_and_tables()
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok"}
from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select
from app.db.database import engine
from app.db.models import User

def get_session():
    with Session(engine) as session:
        yield session # using a yeild so function doesn't terminate here before with block finishes and session closes

def get_current_user(request: Request, session: Session = Depends(get_session)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

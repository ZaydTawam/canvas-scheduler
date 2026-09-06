import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
from sqlmodel import Session, select
from app.dependencies import get_current_user, get_session
from app.db.database import engine
from app.db.models import User

load_dotenv()
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar.events",
]

router = APIRouter(prefix="/auth")

def create_flow(): # create google login url
    return Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8000/auth/callback"],
            }
        },
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/auth/callback",
    )

@router.get("/login")
def login():
    flow = create_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
    )
    return RedirectResponse(auth_url) # return response to the frontend to redirect to google log in url

@router.get("/callback")
def callback(code: str, request: Request): 
    flow = create_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials

    google_user_info = id_token.verify_oauth2_token(
        creds.id_token,
        google_requests.Request(),
        CLIENT_ID,
    )
    google_id, email, name, refresh_token = google_user_info["sub"], google_user_info["email"], google_user_info.get("name"), creds.refresh_token

    with Session(engine) as session:
        user = session.exec(select(User).where(User.google_id == google_id)).first()
        if user is None:
            user = User(
                google_id=google_id,
                refresh_token=refresh_token,
                name =name,
                email=email,
            )
            session.add(user)
        else:
            user.sqlmodel_update({
                "google_id": google_id,
                "name": name,
                "email": email
            })
        session.commit()

    request.session["user_id"] = user.id

@router.get("/me", status_code=204)
def status(user: User = Depends(get_current_user)):
    return

@router.post("/logout")
def logout(request: Request):
    request.session.clear()

@router.delete("/me")
def delete_user(request: Request, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    session.delete(user)
    session.commit()
    request.session.clear()
from sqlmodel import Session, select
from app.agent.runner import run_agent_loop
from app.canvas.sync import sync_user
from app.db.database import engine
from app.db.models import User

def run_scheduler_for_user(user: User):
  with Session(engine) as session:
    change_log = sync_user(session, user)
    if change_log:
      run_agent_loop(user, change_log)
      return True
    return False

def run_scheduler_for_all_users():
  with Session(engine) as session:
    users = session.exec(select(User)).all()

    for user in users:
      if user.canvas_token is None:
        continue
      change_log = sync_user(session, user)
      if change_log:
        run_agent_loop(user, change_log)

if __name__ == "__main__":
  run_scheduler_for_all_users()
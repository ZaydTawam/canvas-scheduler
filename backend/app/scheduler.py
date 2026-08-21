from sqlmodel import Session, select
from app.agent.runner import run_agent_loop
from app.canvas.sync import sync_user
from app.db.database import engine
from app.db.models import User

def run():
  with Session(engine) as session:
    users = session.exec(select(User)).all()

    for user in users:
      change_log = sync_user(session, user)
      if change_log:
        run_agent_loop(user, change_log)
        print(change_log)

if __name__ == "__main__":
  run()
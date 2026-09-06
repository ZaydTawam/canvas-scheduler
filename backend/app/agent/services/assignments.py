from sqlmodel import Session, select
from app.db.database import engine
from app.db.models import Assignment

class AssignmentNotFoundError(Exception):
    pass

def get_assignment_details(assignment_id):
    if not isinstance(assignment_id, int):
        raise TypeError("assignment_id must be an integer")
    with Session(engine) as session:
        assignment = session.get(Assignment, assignment_id)
        if assignment is None:
            raise AssignmentNotFoundError(f"No assignment exists with {assignment_id} id")
        due_date, estimated_minutes, grade_impact = assignment.due_at, assignment.estimated_minutes, assignment.grade_impact
    return due_date, estimated_minutes, grade_impact 
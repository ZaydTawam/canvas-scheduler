from canvasapi import Canvas
import hashlib
from sqlmodel import Session, select
from app.canvas.fetcher import get_active_courses, get_course_assignment_groups, get_course_assignments
from app.canvas.utils.helpers import estimate_minutes, format_change_log
from app.db.models import User, Course, AssignmentGroup, Assignment

# minimum change in grade impact (percentage points of final grade, and fraction of previous value) worth reporting
IMPACT_ABSOLUTE_THRESHOLD = 1.0
IMPACT_RELATIVE_THRESHOLD = 0.25

def sync_user(session: Session, user: User):
  change_log = ""
  canvas = Canvas(user.canvas_url, user.canvas_token)
  courses = get_active_courses(canvas)
  course_ids = {course["id"] for course in courses}

  courses_to_deactivate = session.exec(
    select(Course)
    .where(Course.id.not_in(course_ids))
    .where(Course.user_id == user.id)
  ).all()
  
  for course in courses_to_deactivate:
    course.active = False

  for course in courses:
    db_course = session.get(Course, course["id"])
    if db_course is None:
      session.add(Course(**course, user_id=user.id))
    else:
      db_course.sqlmodel_update(course)

    assignment_groups = get_course_assignment_groups(canvas, course["id"])
    sync_assignment_groups(session, course, assignment_groups)
    
    assignments = get_course_assignments(canvas, course["id"])
    new_assignment_ids, changed_assignments = sync_assignments(session, course, assignments)

    new_assignments = [session.get(Assignment, assignment_id) for assignment_id in new_assignment_ids]
    change_log += format_change_log(course["name"], new_assignments, changed_assignments)
    
    session.commit()
  
  return change_log

def sync_assignment_groups(session: Session, course, assignment_groups):
  for assignment_group in assignment_groups:
    db_assignment_group = session.get(AssignmentGroup, assignment_group["id"])
    if db_assignment_group is None:
      session.add(AssignmentGroup(**assignment_group, course_id=course["id"]))
    else:
      db_assignment_group.sqlmodel_update(assignment_group)
  
def sync_assignments(session, course, assignments):
  new_assignment_ids = []
  changed_assignments = {}

  assignment_ids = {assignment["id"] for assignment in assignments}
  assignments_to_deactivate = session.exec(
    select(Assignment)
    .where(Assignment.id.not_in(assignment_ids))
    .where(Assignment.course_id == course["id"])
  ).all()
  for assignment in assignments_to_deactivate:
    assignment.active = False
  
  total_points_by_group = {}
  for assignment in assignments:
    total_points_by_group[assignment["group_id"]] = total_points_by_group.get(assignment["group_id"], 0) + assignment["points_possible"]

  for assignment in assignments:
    group_weight = session.get(AssignmentGroup, assignment["group_id"]).weight
    group_total_points = total_points_by_group[assignment["group_id"]]
    
    assignment["grade_impact"] = group_weight * (assignment["points_possible"]/group_total_points) if group_total_points else 0
    assignment["description_hash"] = hashlib.md5((assignment["description"] or "").encode()).hexdigest()

    db_assignment = session.get(Assignment, assignment["id"])
    if db_assignment is None:
      session.add(Assignment(
        **assignment,
        course_id=course["id"],
        estimated_minutes=estimate_minutes(assignment["name"], assignment["description"], assignment["id"]),
      ))
      new_assignment_ids.append(assignment["id"])

    else:
      changes = {}

      if assignment["due_at"] != db_assignment.due_at:
        changes["due_at"] = {"before": db_assignment.due_at, "after": assignment["due_at"]}
      
      if assignment["grade_impact"] != db_assignment.grade_impact:
        impact_change = abs(assignment["grade_impact"] - db_assignment.grade_impact)
        if impact_change >= IMPACT_ABSOLUTE_THRESHOLD and impact_change >= IMPACT_RELATIVE_THRESHOLD * db_assignment.grade_impact:
          changes["grade_impact"] = {"before": db_assignment.grade_impact, "after": assignment["grade_impact"]}

      if assignment["description_hash"] != db_assignment.description_hash:
        assignment["estimated_minutes"] = estimate_minutes(assignment["name"], assignment["description"], assignment["id"])
        if assignment["estimated_minutes"] != db_assignment.estimated_minutes:
          changes["estimated_minutes"] = {"before": db_assignment.estimated_minutes, "after": assignment["estimated_minutes"]}

      if assignment["submission_status"] != "unsubmitted" and db_assignment.submission_status == "unsubmitted":
        changes["submission_status"] = {"before": db_assignment.submission_status, "after": assignment["submission_status"]}

      if changes and db_assignment.submission_status == "unsubmitted": # changes to already submitted assignments don't get reported
        changed_assignments[assignment["id"]] = {"name": db_assignment.name, "changes": changes}

      db_assignment.sqlmodel_update(assignment)

  return new_assignment_ids, changed_assignments

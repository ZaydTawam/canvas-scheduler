from canvasapi import Canvas
from datetime import datetime, timezone
from markdownify import markdownify

def get_all_courses(canvas: Canvas):
  canvas_user = canvas.get_current_user()
  courses = canvas_user.get_courses(
    enrollment_state="active",
    include=["total_scores"]
  )

  return [
    {
      "id": course.id,
      "name": course.name,
      "current_grade": course.enrollments[0]["computed_current_score"],
    } 
    for course in courses
  ]

def get_course_assignment_groups(canvas: Canvas, course_id: int):
  course = canvas.get_course(course_id)
  assignment_groups = course.get_assignment_groups()

  return [
    {
      "id": assignment_group.id,
      "name": assignment_group.name,
      "group_weight": assignment_group.group_weight,
    }
    for assignment_group in assignment_groups 
  ]

def get_course_assignments(canvas: Canvas, course_id: int):
  course = canvas.get_course(course_id)
  assignments = course.get_assignments()

  return [
    {
      "id": assignment.id,
      "group_id": assignment.assignment_group_id,
      "name": assignment.name,
      "description": markdownify(assignment.description or "This assignment has no description."), # assignment.description is HTML string
      "due_at": datetime.fromisoformat(assignment.due_at).astimezone(timezone.utc) if assignment.due_at else None,
      "points_possible": assignment.points_possible,
      "submission_status": assignment.get_submission('self').workflow_state,
    }
    for assignment in assignments 
  ]

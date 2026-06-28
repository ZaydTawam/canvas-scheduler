from sqlmodel import CheckConstraint, Field, Relationship, SQLModel
from datetime import datetime

class User(SQLModel, table=True):
  __tablename__ = "users"

  id: int | None = Field(default=None, primary_key=True)
  google_id: str = Field(unique=True)
  refresh_token: str
  canvas_token: str
  name: str
  email: str = Field(unique=True)
  max_block_size: int
  availability_blocks: list["AvailabilityBlock"] = Relationship()

class AvailabilityBlock(SQLModel, table=True):
  __tablename__ = "availability_blocks"
  __table_args__ = (
    CheckConstraint("day_of_week >= 0 AND day_of_week <= 6"),
    CheckConstraint("start_time >= 0 AND start_time <= 1440"),
    CheckConstraint("end_time >= 0 AND end_time <= 1440"),
    CheckConstraint("end_time > start_time")
  )

  id: int | None = Field(default=None, primary_key=True)
  user_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
  day_of_week: int
  # start_time and end_time are minutes since midnight (0-1440)
  start_time: int
  end_time: int

class Course(SQLModel, table=True):
  __tablename__ = "courses"

  id: int | None = Field(default=None, primary_key=True)
  user_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
  name: str
  current_grade: float | None = None
  active: bool
  assignment_groups: list["AssignmentGroup"] = Relationship()
  assignments: list["Assignment"] = Relationship()

class AssignmentGroup(SQLModel, table=True):
  __tablename__ = "assignment_groups"

  id: int | None = Field(default=None, primary_key=True)
  course_id: int = Field(foreign_key="courses.id", ondelete="CASCADE")
  name: str
  group_weight: float
  assignments: list["Assignment"] = Relationship()

class Assignment(SQLModel, table=True):
  __tablename__ = "assignments"

  id: int | None = Field(default=None, primary_key=True)
  course_id: int = Field(foreign_key="courses.id", ondelete="CASCADE")
  group_id: int = Field(foreign_key="assignment_groups.id", ondelete="CASCADE")
  group: AssignmentGroup = Relationship()
  title: str
  description: str
  due_at: datetime | None = None
  type: str
  points_possible: float
  submission_status: str
  estimated_time: int # minutes
  grade_impact: float
  active: bool

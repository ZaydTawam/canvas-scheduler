
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from app.dependencies import get_current_user, get_session
from app.db.models import AvailabilityBlock, Course, User
from app.scheduler import run_scheduler_for_user

router = APIRouter(prefix="/users")

class UserSettingsUpdate(BaseModel):
    canvas_token: str | None = None
    canvas_url: str | None = None
    timezone: str | None = None
    max_block_minutes: int | None = None

class AvailabilityBlockInput(BaseModel):
    day_of_week: int
    start_time: int
    end_time: int

class CourseUpdate(BaseModel):
    course_id: int
    active: bool


def _normalize_availability_blocks(blocks: list[AvailabilityBlockInput]):
    blocks_by_days = [[] for _ in range(7)]
    for block in blocks:
        if block.start_time >= block.end_time:
            raise ValueError("end_time must be after start_time")
        if not 0 <= block.day_of_week <=  6:
            raise ValueError("day_of_week must be between 0 and 6")
        blocks_by_days[block.day_of_week].append(block)

    merged_blocks = []
    for day_of_week, blocks in enumerate(blocks_by_days):
        blocks.sort(key=lambda block: block.start_time)
        for block in blocks:
            if merged_blocks and merged_blocks[-1].day_of_week == day_of_week and merged_blocks[-1].end_time >= block.start_time:
                merged_blocks[-1] = AvailabilityBlockInput(
                    day_of_week=day_of_week,
                    start_time=merged_blocks[-1].start_time,
                    end_time=max(merged_blocks[-1].end_time, block.end_time),
                )
            else:
                merged_blocks.append(block)
    return merged_blocks

@router.get("/me")
def get_settings(user: User = Depends(get_current_user)):
    return user.model_dump(include={"name", "email", "canvas_token", "canvas_url", "timezone", "max_block_minutes"})

@router.patch("/me")
def update_settings(update: UserSettingsUpdate, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    updates = update.model_dump(exclude_unset=True)
    user.sqlmodel_update(updates)
    session.commit()
    session.refresh(user)
    return user.model_dump(include={"canvas_token", "canvas_url", "timezone", "max_block_minutes"})

@router.get("/me/availability-blocks")
def get_availability_blocks(user: User = Depends(get_current_user)):
    return [
        block.model_dump(exclude={"id", "user_id"})
        for block in user.availability_blocks
    ]

@router.put("/me/availability-blocks")
def set_availability_blocks(blocks: list[AvailabilityBlockInput], user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        blocks = _normalize_availability_blocks(blocks)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    existing_blocks = user.availability_blocks
    for block in existing_blocks:
        session.delete(block)

    new_blocks = [
        AvailabilityBlock(user_id=user.id, **block.model_dump())
        for block in blocks
    ]
    session.add_all(new_blocks)

    session.commit()

    for block in new_blocks:
        session.refresh(block)

    return [
        block.model_dump(exclude={"id", "user_id"})
        for block in new_blocks
    ]

@router.get("/me/courses")
def get_all_courses(user: User = Depends(get_current_user)):
    return [course.model_dump(include={"id", "name", "active"}) for course in user.courses] 

@router.patch("/me/course")
def update_course(update: CourseUpdate, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    course_id, active = update.course_id, update.active
    course = session.exec(select(Course).where(Course.user_id == user.id, Course.id == course_id)).first()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    course.active = active
    session.commit()
    session.refresh(course)

    return course.model_dump(include={"id", "name", "active"})

@router.post("/me/schedule")
def schedule(user: User = Depends(get_current_user)):
    scheduled = run_scheduler_for_user(user)
    if scheduled:
        return {"message": "Scheduler ran and updated your calendar."}
    return {"message": "There were no meaningful changes to schedule."}

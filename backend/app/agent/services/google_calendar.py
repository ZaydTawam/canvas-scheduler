import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlmodel import Session, select
from app.db.database import engine
from app.db.models import AvailabilityBlock, User

load_dotenv()
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")


class OutsideAvailabilityError(Exception):
    pass

class CalendarApiError(Exception):
    pass

class CalendarEventNotFoundError(Exception):
    pass


def get_calendar_service(user: User):
    creds = Credentials(
        token=None, # access token
        refresh_token=user.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/calendar.events"],
    )
    return build("calendar", "v3", credentials=creds)


def _assert_within_availability(user: User, start: datetime, end: datetime):
    if end <= start:
        raise ValueError("end_time must be after start_time")

    if start.date() != end.date():
        raise OutsideAvailabilityError("Block cannot span multiple days")

    day_of_week = start.weekday()

    # converting to min since midnight to match Availability Block
    start_min = (start.hour * 60) + start.minute 
    end_min = (end.hour * 60) + end.minute
    
    availability_blocks = user.availability_blocks

    fits = False
    for block in availability_blocks:
        if block.day_of_week != day_of_week:
            continue

        if block.start_time <= start_min and block.end_time >= end_min:
            fits = True
            break

    if not fits:
        raise OutsideAvailabilityError("Requested block falls outside the user's availability")


def create_assignment_block(user: User, title: str, start_time: str, end_time: str, assignment_id: int):
    start = datetime.fromisoformat(start_time)
    end = datetime.fromisoformat(end_time)

    _assert_within_availability(user, start, end)

    service = get_calendar_service(user)
    event = {
        "summary": title,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
        "extendedProperties": {
            "private": {
                "assignment_id": assignment_id,
                "source": "canvas-scheduler",
            },
        },
    }
    try:
        created = service.events().insert(calendarId="primary", body=event).execute()
    except HttpError as e:
        raise CalendarApiError(f"Failed to create calendar event: {e}") from e

    return created["id"]


def get_assignment_blocks(user: User, assignment_id: int):
    service = get_calendar_service(user)
    try:
        response = service.events().list(
            calendarId="primary",
            privateExtendedProperty=f"assignment_id={assignment_id}",
            singleEvents=True,
        ).execute()
    except HttpError as e:
        raise CalendarApiError(f"Failed to fetch calendar events: {e}") from e

    events = response.get("items", [])
    blocks = []
    total_minutes = 0
    for event in events:
        start = datetime.fromisoformat(event["start"]["dateTime"])
        end = datetime.fromisoformat(event["end"]["dateTime"])
        total_minutes += (end - start).total_seconds() / 60
        blocks.append({
            "calendar_event_id": event["id"],
            "title": event.get("summary"),
            "start_time": event["start"]["dateTime"],
            "end_time": event["end"]["dateTime"],
        })

    return blocks, total_minutes


def _list_events(service, start_time: str, end_time: str, canvas_scheduler_only: bool = False):
    kwargs = {
        "calendarId": "primary",
        "timeMin": start_time,
        "timeMax": end_time,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if canvas_scheduler_only:
        kwargs["privateExtendedProperty"] = "source=canvas-scheduler"

    try:
        response = service.events().list(**kwargs).execute()
    except HttpError as e:
        raise CalendarApiError(f"Failed to fetch calendar events: {e}") from e

    return response.get("items", [])


def get_scheduled_blocks(user: User, start_time: str, end_time: str):
    service = get_calendar_service(user)
    events = _list_events(service, start_time, end_time, canvas_scheduler_only=True)

    blocks = []
    for event in events:
        if "dateTime" not in event["start"]:
            continue
        blocks.append({
            "calendar_event_id": event["id"],
            "title": event.get("summary"),
            "start_time": event["start"]["dateTime"],
            "end_time": event["end"]["dateTime"],
        })

    return blocks


def get_calendar_availability(user: User, start_time: str, end_time: str):
    range_start = datetime.fromisoformat(start_time)
    range_end = datetime.fromisoformat(end_time)
    if range_end <= range_start:
        raise ValueError("end_time must be after start_time")

    availability_blocks = user.availability_blocks

    service = get_calendar_service(user)
    busy_events = _list_events(service, start_time, end_time)
    busy_intervals = []
    for event in busy_events:
        if "dateTime" not in event["start"]:
            continue
        busy_intervals.append((
            datetime.fromisoformat(event["start"]["dateTime"]),
            datetime.fromisoformat(event["end"]["dateTime"]),
        ))

    free_blocks = []
    day_start = datetime(range_start.year, range_start.month, range_start.day, tzinfo=range_start.tzinfo)
    while day_start.date() <= range_end.date():
        day_of_week = day_start.weekday()
        for block in availability_blocks:
            if block.day_of_week != day_of_week:
                continue

            block_start = max(day_start + timedelta(minutes=block.start_time), range_start)
            block_end = min(day_start + timedelta(minutes=block.end_time), range_end)
            if block_end <= block_start:
                continue

            free_blocks.extend(_subtract_busy_intervals(block_start, block_end, busy_intervals))

        day_start += timedelta(days=1)

    return [
        {"start_time": start.isoformat(), "end_time": end.isoformat()}
        for start, end in free_blocks
    ]


def _subtract_busy_intervals(start: datetime, end: datetime, busy_intervals: list[tuple[datetime, datetime]]):
    free = [(start, end)]
    for busy_start, busy_end in busy_intervals:
        next_free = []
        for free_start, free_end in free:
            if busy_end <= free_start or busy_start >= free_end:
                next_free.append((free_start, free_end))
                continue
            if busy_start > free_start:
                next_free.append((free_start, busy_start))
            if busy_end < free_end:
                next_free.append((busy_end, free_end))
        free = next_free
    return free


def move_calendar_block(user: User, calendar_event_id: str, start_time: str, end_time: str):
    start = datetime.fromisoformat(start_time)
    end = datetime.fromisoformat(end_time)

    if end <= start:
        raise ValueError("end_time must be after start_time")
    _assert_within_availability(user, start, end)

    service = get_calendar_service(user)
    try:
        event = service.events().get(calendarId="primary", eventId=calendar_event_id).execute()
    except HttpError as e:
        if e.resp.status == 404:
            raise CalendarEventNotFoundError(f"No calendar event with id {calendar_event_id}") from e
        raise CalendarApiError(f"Failed to fetch calendar event: {e}") from e

    if event.get("extendedProperties", {}).get("private", {}).get("source") != "canvas-scheduler":
        raise CalendarEventNotFoundError(f"No canvas-scheduler block with id {calendar_event_id}")

    event["start"]["dateTime"] = start_time
    event["end"]["dateTime"] = end_time

    try:
        updated = service.events().update(calendarId="primary", eventId=calendar_event_id, body=event).execute()
    except HttpError as e:
        raise CalendarApiError(f"Failed to update calendar event: {e}") from e

    return updated["id"]


def delete_calendar_block(user: User, calendar_event_id: str):
    service = get_calendar_service(user)
    try:
        event = service.events().get(calendarId="primary", eventId=calendar_event_id).execute()
    except HttpError as e:
        if e.resp.status == 404:
            raise CalendarEventNotFoundError(f"No calendar event with id {calendar_event_id}") from e
        raise CalendarApiError(f"Failed to fetch calendar event: {e}") from e

    if event.get("extendedProperties", {}).get("private", {}).get("source") != "canvas-scheduler":
        raise CalendarEventNotFoundError(f"No canvas-scheduler block with id {calendar_event_id}")

    try:
        service.events().delete(calendarId="primary", eventId=calendar_event_id).execute()
    except HttpError as e:
        raise CalendarApiError(f"Failed to delete calendar event: {e}") from e
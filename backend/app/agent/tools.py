tools = [
  {
    "name": "get_calendar_availability",
    "description": "Get all available free blocks in the user's calendar within the provided start_time and end_time.",
    "input_schema": {
      "type": "object",
      "properties": {
        "start_time": {
          "type": "string",
          "format": "date-time",
          "description": "Block start time in RFC 3339 format with UTC offset, e.g. '2026-08-13T09:00:00-07:00'."
        },
        "end_time": {
          "type": "string",
          "format": "date-time",
          "description": "Block end time in RFC 3339 format with UTC offset, e.g. '2026-08-13T09:00:00-07:00'."
        },
      },
      "required": ["start_time", "end_time"],
    },
  },
  {
    "name": "get_scheduled_blocks",
    "description": (
      "Get all scheduled assignment blocks in the user's calendar within the provided start_time and end_time. "
      "This does not include other user-created blocks. "
      "Do not assume intervals not returned are empty in the calendar and can be scheduled, use get_calendar_availability tool to get free blocks."
    ),
    "input_schema": {
      "type": "object",
      "properties": {
        "start_time": {
          "type": "string",
          "format": "date-time",
          "description": "Block start time in RFC 3339 format with UTC offset, e.g. '2026-08-13T09:00:00-07:00'."
        },
        "end_time": {
          "type": "string",
          "format": "date-time",
          "description": "Block end time in RFC 3339 format with UTC offset, e.g. '2026-08-13T09:00:00-07:00'."
        },
      },
      "required": ["start_time", "end_time"],
    },
  },
  {
    "name": "get_assignment_blocks",
    "description": "Get all scheduled blocks for a specific assignment in the user's calendar as well as total time scheduled for that assignment.",
    "input_schema": {
      "type": "object",
      "properties": {
        "assignment_id": {
          "type": "int",
          "description": "Identifies which assignment this block is for. This is not a scheduled block's ID or a calendar event ID."
        },
      },
      "required": ["assignment_id"],
    },
  },
  {
    "name": "get_assignment_details",
    "description": "Get due date, estimated_minutes, and grade_impact for a specific assignment.",
    "input_schema": {
      "type": "object",
      "properties": {
        "assignment_id": {
          "type": "int",
          "description": "Identifies which assignment to lookup. This is not a scheduled block's ID or a calendar event ID."
        },
      },
      "required": ["assignment_id"],
    },
  },
  {
    "name": "create_assignment_block",
    "description": "Create a work block in the user's calendar for a specific Canvas assignment. Returns the newly created calendar event ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "assignment_id": {
          "type": "int",
          "description": "Identifies which assignment this block is for. This is not a calendar event ID."
        },
        "title": {
          "type": "string",
          "description": "The name of the assignment being scheduled."
        },
        "start_time": {
          "type": "string",
          "format": "date-time",
          "description": "Block start time in RFC 3339 format with UTC offset, e.g. '2026-08-13T09:00:00-07:00'."
        },
        "end_time": {
          "type": "string",
          "format": "date-time",
          "description": "Block end time in RFC 3339 format with UTC offset, e.g. '2026-08-13T09:00:00-07:00'."
        },
      },
      "required": ["assignment_id", "title", "start_time", "end_time"],
    },
  },
  {
    "name": "move_calendar_block",
    "description": "Change the start_time and end_time of an existing calendar block if the time slot is available. Does not change any other properties of the calendar block.",
    "input_schema": {
      "type": "object",
      "properties": {
        "calendar_event_id": {
          "type": "string",
          "description": "Identifies which block should be moved. This is not a an assignment ID."
        },
        "start_time": {
          "type": "string",
          "format": "date-time",
          "description": "The new start time in RFC 3339 format with UTC offset, e.g. '2026-08-13T09:00:00-07:00'."
        },
        "end_time": {
          "type": "string",
          "format": "date-time",
          "description": "The new end time in RFC 3339 format with UTC offset, e.g. '2026-08-13T09:00:00-07:00'."
        },
      },
      "required": ["calendar_event_id", "start_time", "end_time"],
    },
  },
  {
    "name": "delete_calendar_block",
    "description": "Permanently delete a calendar block. This cannot be undone.",
    "input_schema": {
      "type": "object",
      "properties": {
        "calendar_event_id": {
          "type": "string",
          "description": "Identifies which block should be deleted. This is not a an assignment ID."
        },
      },
      "required": ["calendar_event_id"],
    },
  },
  {
  "name": "surface_alert",
  "description": "Send the user an alert in the event of a calendar conflict or unscheduleable assignment.",
  "input_schema": {
      "type": "object",
      "properties": {
        "message": {
          "type": "string",
          "description": "The text to be included in the alert detailing the issue."
        },
      },
      "required": ["message"],
    },
  },
]


def run_tool(name, tool_input):
  if name == "get_calendar_availability":
    return
  if name == "get_scheduled_blocks":
    return
  if name == "get_assignment_blocks":
    return
  if name == "get_assignment_details":
    return
  if name == "create_assignment_block":
    return
  if name == "move_calendar_block":
    return 
  if name == "delete_calendar_block":
    return
  if name == "surface_alert":
    return
  
  raise ValueError(f"Unknown tool: {name}")

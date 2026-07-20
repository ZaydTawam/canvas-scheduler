import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Literal
from anthropic import Anthropic
from app.canvas.utils.prompts import ESTIMATE_HOURS_SYSTEM_PROMPT

load_dotenv()
ANTHROPIC_API_KEY=os.environ.get("ANTHROPIC_API_KEY")
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

class TimeEstimate(BaseModel):
  estimated_minutes: int
  confidence: Literal["high", "medium", "low"]
  reasoning: str

def estimate_minutes(name: str, description: str, assignment_id: int):
  content = f"Assignment Name: {name}\nAssignment Description: {description}"

  response = anthropic_client.messages.parse(
    model="claude-haiku-4-5",
    max_tokens=1024,
    system=ESTIMATE_HOURS_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": content}],
    output_format=TimeEstimate,
  )

  result = response.parsed_output

  print(
    f"""[assignment_id={assignment_id}]
    '{name}' -> {result.estimated_minutes}min
    confidence={result.confidence}, reasoning='{result.reasoning}' """
  )

  return result.estimated_minutes

def format_change_log(course_name, new_assignments, changed_assignments):
  if not new_assignments and not changed_assignments:
    return ""

  lines = [f"\n{course_name} Updates:"]

  if new_assignments:
    lines.append("New Assignments:")
    for assignment in new_assignments:
      due = assignment.due_at or "no due date"
      lines.append(
        f"  - {assignment.name} id:{assignment.id} (due {due}) ~{assignment.estimated_minutes} min, grade impact: {assignment.grade_impact:.2f}"
      )

  if changed_assignments:
    lines.append("Changed Assignments:")
    for assignment_id, entry in changed_assignments.items():
      lines.append(f"  - {entry['name']} id:{assignment_id}:")
      for field, value in entry["changes"].items():
        lines.append(f"      {field}: {value['before']} -> {value['after']}")

  return "\n".join(lines)
import os
from anthropic import Anthropic
from dotenv import load_dotenv
import json
from app.agent.prompts import build_system_prompt, format_availability_windows
from app.agent.tools import tools, run_tool
from app.db.models import User

load_dotenv()
ANTHROPIC_API_KEY=os.environ.get("ANTHROPIC_API_KEY")
client = Anthropic(api_key=ANTHROPIC_API_KEY)

def run_agent_loop(user: User, change_log):
  messages = [
    {
      "role": "user",
      "content": change_log,
    }
  ]

  SYSTEM_PROMPT = build_system_prompt(user.max_block_minutes, format_availability_windows(user.availability_blocks))

  response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=4000,
    system=SYSTEM_PROMPT,
    tools=tools,
    thinking={"type": "enabled", "budget_tokens": 1024},
    messages=messages
  )

  while response.stop_reason == "tool_use":
    tool_results = []
    for block in response.content:
      if block.type == "tool_use":
        print(f"\nUsed {block.name} tool")
        print(f"Input: {block.input}")
        try: 
          result = run_tool(block.name, block.input)
          print(f"Output: {result}")
          tool_results.append(
            {
              "type": "tool_result",
              "tool_use_id": block.id,
              "content": json.dumps(result, default=str),
            }
          )
        except Exception as e:
          print(f"Error: {e}")
          tool_results.append(
            {
              "type": "tool_result",
              "tool_use_id": block.id,
              "content": str(e),
              "is_error": True,
            }
          )

      elif block.type == "thinking":
        print(f"\nThinking: {block.thinking}")
      elif block.type == "text":
        print(block.text)

    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": tool_results})

    response = client.messages.create(
      model="claude-haiku-4-5",
      max_tokens=4000,
      system=SYSTEM_PROMPT,
      tools=tools,
      thinking={"type": "enabled", "budget_tokens": 1024},
      messages=messages
    )    

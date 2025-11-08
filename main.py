import asyncio
import os
import re
from typing import Optional

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query
from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp

# Load environment variables from .env file
load_dotenv()

# Initialize Slack app with WebSocket mode
app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))


def convert_markdown_to_slack(text: str) -> str:
    """Convert standard markdown formatting to Slack-compatible formatting"""
    # Convert **bold** to *bold* (Slack uses single asterisks for bold)
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)

    # Convert ### headings to bold text with line breaks
    text = re.sub(r"^### (.*?)$", r"*\1*", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.*?)$", r"*\1*", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.*?)$", r"*\1*", text, flags=re.MULTILINE)

    # Convert - list items to • (bullet points)
    text = re.sub(r"^- (.*?)$", r"• \1", text, flags=re.MULTILINE)

    # Preserve code blocks (triple backticks work in Slack)
    # No changes needed for ```code``` blocks

    return text


async def fetch_thread_messages(channel: str, thread_ts: str) -> list[dict]:
    """Fetch the entire Slack thread for additional LLM context"""
    messages: list[dict] = []
    cursor = None

    while True:
        response = await app.client.conversations_replies(
            channel=channel,
            ts=thread_ts,
            cursor=cursor,
            limit=200,
        )
        messages.extend(response.get("messages", []))

        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    return messages


def format_thread_messages(messages: list[dict]) -> str:
    """Create a readable transcript from Slack thread messages"""
    formatted = []
    for msg in messages:
        # Skip Slack events without visible text content
        text = msg.get("text", "").strip()
        if not text:
            continue

        if msg.get("subtype") == "bot_message":
            user_label = msg.get("username") or "bot"
        else:
            user_label = msg.get("user") or msg.get("bot_id") or "unknown"

        formatted.append(f"{user_label}: {text}")

    final = "\n".join(formatted)
    print(f"Formatted thread messages:\n{final}")
    return final


async def process_with_claude(prompt: str, thread_context: Optional[str] = None) -> str:
    """Process message with Claude agent and return response"""
    if thread_context:
        composed_prompt = (
            f"Thread transcript:\n{thread_context}\n\n"
            f"{prompt}"
        )
    else:
        composed_prompt = prompt

    print(
        "Processing with Claude: "
        f"{'[thread context included]' if thread_context else composed_prompt}"
    )

    response_text = ""
    async for message in query(
        prompt=composed_prompt,
        options=ClaudeAgentOptions(
            allowed_tools=[],
            system_prompt="""
You are Myla, a professional facilitator.
You work in Slack as a bot. Be concise.
Your purpose is to **help human teammates reach clear, collaborative decisions** during technical and product discussions.
You don’t just summarize — you **mediate**, **clarify**, and **guide** conversations toward constructive outcomes backed by real data.

You are:
- **Empathetic but assertive** — you understand emotions but stay focused on outcomes.
- **Fact-driven** — you consult data before speaking.
- **Concise** — you use few, thoughtful messages rather than long essays.
- **Collaborative** — you unite participants instead of taking sides.
- **Goal-oriented** — you always steer discussions toward actionable next steps.


## Core Objectives

### 1. Understand the Conversation
- Identify the **main topic or decision** under discussion.
- Detect each participant’s **stance, motivation, and concern**.
- Recognize when the conversation is **stuck, looping, or emotionally tense**.

### 2. Gather & Synthesize Knowledge
Use the available subagents to gather relevant data.
Your final message should integrate their findings *as if you were informed by them*, not quoting raw text — be natural, contextual, and human-readable.
Your role is more like an orchestrator so try to use the subagents when possible.


## 3. Mediate Constructively
- Acknowledge each side’s perspective fairly.
- Frame disagreements as shared goals expressed differently.
- Use calm, respectful tone to **de-escalate tension**.
- Identify where participants actually agree and highlight that common ground.
- When conflict persists, reframe around **project goals and user outcomes**.

---

## 4. Guide Toward Resolution
- Propose a **specific, realistic path forward** that balances technical and product considerations.
- Encourage a **shared decision** by summarizing facts and tradeoffs.
- Explicitly call for light confirmation (e.g. “Sound good to everyone?”).
- If agreement is reached, log a **Decision Note** in concise, professional format.

---

## Behavior Guidelines

- **Tone:** Calm, respectful, confident — never passive-aggressive or dismissive.
- **Length:** 1–3 short paragraphs max, or a mix of one paragraph + bullet list.
- **Empathy:** Use light emotional intelligence markers:
  “I hear both sides,” “Let’s align on what we all want,” “These are all valid points.”
- **Evidence:** Reference facts clearly but conversationally (e.g., “According to the sprint doc, this is marked high priority…”).
- **Transparency:** Never fabricate data; if something is unknown, acknowledge that.
- **Frequency:** Intervene **only when needed** — when conflict arises, or when participants repeat without progress.
- **Autonomy:** You coordinate, not command. Present balanced recommendations, not ultimatums.

---

## Output Format (for Slack or Chat)

When posting in **summary mode**:

```
@parleybot
**Topic:** <summarized decision or question>
**Key Perspectives:**
- <person A>: <their stance>
- <person B>: <their stance>

**Relevant Facts:**
- <key fact from Code or Product Manager Agent>
- <key fact from code/docs>

**Recommendation:**
<neutral, balanced proposal>

✅ <optional closing line like “Sound good to everyone?”>
```

When posting in **mediation mode** (conversation still active):

> “Hey team 👋 — sounds like we’re circling around two main issues: stability vs. sprint capacity.
> Here’s what the facts say — the bug is a P0, and the refactor is scoped as high priority.
> We can balance both by doing the hooks-only refactor this sprint and Redux next sprint.
> That gets us stability without derailing delivery. Sound fair?”
""".strip(),
            model="claude-haiku-4-5-20251001",
            cwd=os.path.join(os.getcwd(), "project"),
            setting_sources=["project"],
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    response_text += block.text

    return response_text or "I don't have a response for that."


@app.message(".*")
async def handle_message(message, say):
    """Handle incoming Slack messages"""
    try:
        user_message = message["text"]
        user_id = message["user"]
        channel_id = message.get("channel")
        thread_ts = message.get("thread_ts")

        print(f"Received message from {user_id}: {user_message}")

        thread_context = None
        if channel_id and thread_ts:
            thread_messages = await fetch_thread_messages(channel_id, thread_ts)
            thread_context = format_thread_messages(thread_messages)

        # Process message with Claude
        claude_response = await process_with_claude(
            user_message, thread_context=thread_context
        )

        # Convert markdown formatting to Slack format
        formatted_response = convert_markdown_to_slack(claude_response)

        # Send response back to Slack as a threaded reply
        reply_thread_ts = thread_ts or message["ts"]
        await say(text=formatted_response, thread_ts=reply_thread_ts)

    except Exception as e:
        print(f"Error handling message: {e}")
        await say("Sorry, I encountered an error processing your message.")


@app.event("app_mention")
async def handle_app_mention(event, say):
    """Handle when the bot is mentioned"""
    try:
        user_message = event["text"]
        user_id = event["user"]
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts")

        print(f"Bot mentioned by {user_id}: {user_message}")

        # Remove the bot mention from the message
        # This assumes the bot mention is at the beginning
        clean_message = user_message.split(">", 1)[-1].strip()

        thread_context = None
        if channel_id and thread_ts:
            print(f"Fetching thread messages for context in channel {channel_id}, thread {thread_ts}")
            thread_messages = await fetch_thread_messages(channel_id, thread_ts)
            print(f"Fetched thread messages:\n{thread_messages}")
            thread_context = format_thread_messages(thread_messages)
            print(f"Thread context:\n{thread_context}")

        # Process message with Claude
        claude_response = await process_with_claude(
            clean_message, thread_context=thread_context
        )

        # Convert markdown formatting to Slack format
        formatted_response = convert_markdown_to_slack(claude_response)
        print(f"Claude response: {formatted_response}")

        # Send response back to Slack as a threaded reply
        reply_thread_ts = thread_ts or event["ts"]
        # await say(text=formatted_response, thread_ts=reply_thread_ts)

    except Exception as e:
        print(f"Error handling app mention: {e}")
        # await say("Sorry, I encountered an error processing your mention.")


async def start_slack_bot():
    """Start the Slack bot with WebSocket connection"""
    # For testing purposes
    # response = await process_with_claude("What's our current sprint status?")
    # print(f"Claude response: {response}")
    handler = AsyncSocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    await handler.start_async()


def main():
    print("Starting Myla Slack Bot...")

    # Check for required environment variables
    if not os.environ.get("SLACK_BOT_TOKEN"):
        print("Error: SLACK_BOT_TOKEN environment variable is required")
        return

    if not os.environ.get("SLACK_APP_TOKEN"):
        print("Error: SLACK_APP_TOKEN environment variable is required")
        return

    print("Connecting to Slack via WebSocket...")
    asyncio.run(start_slack_bot())


if __name__ == "__main__":
    main()

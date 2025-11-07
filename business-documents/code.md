# Quick Hackathon Solution - Slack Facilitator Bot (1 Day Build)

## **Core Strategy: Minimal Viable Facilitator**

For a 1-day hackathon, focus on **one killer demo flow**:

1. Bot gets mentioned in a Slack thread
2. Reads the entire thread context
3. Extracts key facts/decisions/questions
4. Posts structured response

---

## **Tech Stack (Fastest Path)**

```
- Python 3.9+
- Slack Bolt for Python (official Slack framework)
- OpenAI API (GPT-4 or Claude via Anthropic API)
- No database needed for MVP
- Deploy: Ngrok (local tunnel) or Railway/Render (quick deploy)
```

---

## **Architecture (Simplest Possible)**

```
Slack Event (app_mention)
    ↓
Bot triggered (@bot_name)
    ↓
Fetch thread messages via Slack API
    ↓
Send to LLM with prompt template
    ↓
Parse LLM response
    ↓
Post structured facts back to thread
```

---

## **Implementation Plan**

### **Step 1: Slack App Setup (15 min)**

1. Go to https://api.slack.com/apps
2. Create New App → "From scratch"
3. Enable these features:
   - **Event Subscriptions**: `app_mention`
   - **Bot Token Scopes**:
     - `app_mentions:read`
     - `channels:history`
     - `chat:write`
     - `users:read`
4. Install app to workspace
5. Copy **Bot User OAuth Token** and **Signing Secret**

---

### **Step 2: Core Python Code**

```python
# requirements.txt
slack-bolt==1.18.0
openai==1.12.0
python-dotenv==1.0.0

# --- main.py ---
import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import openai
from dotenv import load_dotenv

load_dotenv()

# Initialize Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])
openai.api_key = os.environ["OPENAI_API_KEY"]


def fetch_thread_messages(client, channel, thread_ts):
    """Fetch all messages in a thread"""
    result = client.conversations_replies(
        channel=channel,
        ts=thread_ts,
        inclusive=True
    )

    messages = []
    for msg in result["messages"]:
        user_id = msg.get("user", "Unknown")
        # Get user name
        try:
            user_info = client.users_info(user=user_id)
            user_name = user_info["user"]["real_name"]
        except:
            user_name = user_id

        messages.append({
            "user": user_name,
            "text": msg.get("text", ""),
            "ts": msg["ts"]
        })

    return messages


def analyze_thread_with_llm(messages):
    """Send thread to LLM for analysis"""

    # Build conversation context
    conversation = "\n\n".join([
        f"**{msg['user']}**: {msg['text']}"
        for msg in messages
    ])

    prompt = f"""You are a neutral facilitator bot analyzing a Slack thread.

Your task:
1. Extract KEY FACTS mentioned in the discussion
2. Identify DECISIONS made (if any)
3. List OPEN QUESTIONS that remain unanswered
4. Note any CONTRADICTIONS or disagreements

Thread conversation:
{conversation}

Respond in this format:

📊 **FACTS EXTRACTED**
• [Fact 1]
• [Fact 2]

✅ **DECISIONS MADE**
• [Decision 1]

❓ **OPEN QUESTIONS**
• [Question 1]

⚠️ **CONTRADICTIONS/GAPS**
• [Gap 1]

Keep it concise and actionable."""

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a professional facilitator."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=800
    )

    return response.choices[0].message.content


@app.event("app_mention")
def handle_mention(event, client, say):
    """Triggered when bot is mentioned"""

    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])

    # Show typing indicator
    say("🤖 Analyzing thread...", thread_ts=thread_ts)

    try:
        # Fetch thread messages
        messages = fetch_thread_messages(client, channel, thread_ts)

        # Analyze with LLM
        analysis = analyze_thread_with_llm(messages)

        # Post results
        say(
            text=analysis,
            thread_ts=thread_ts,
            unfurl_links=False,
            unfurl_media=False
        )

    except Exception as e:
        say(f"❌ Error: {str(e)}", thread_ts=thread_ts)


if __name__ == "__main__":
    # Socket mode for easy local development
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
```

---

### **Step 3: Environment Variables**

```bash
# .env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token  # Enable Socket Mode in Slack App settings
OPENAI_API_KEY=sk-your-openai-key
```

---

### **Step 4: Run Locally (5 min)**

```bash
pip install -r requirements.txt
python main.py
```

---

## **Demo Flow for Judges**

1. **Create a messy Slack thread** with:
   - Technical debate about architecture
   - 5-6 messages with conflicting opinions
   - Some facts, some questions

2. **Mention the bot**: `@facilitator analyze this`

3. **Bot responds** with structured breakdown:
   - Facts extracted
   - Decisions made
   - Open questions
   - Contradictions

---

## **Enhancements (If Time Allows)**

### **30-Min Add-ons:**

1. **Tag relevant people**:

```python
# Add to prompt
"Also identify WHO should answer each open question based on context."
```

2. **Sentiment detection**:

```python
"Rate the tone: 🟢 Collaborative | 🟡 Tense | 🔴 Conflicting"
```

3. **Export to Notion** (via Notion API):

```python
import requests

def create_notion_page(content):
    notion_token = os.environ["NOTION_TOKEN"]
    # POST to Notion API...
```

---

## **Alternative: Claude Instead of OpenAI**

```python
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def analyze_thread_with_llm(messages):
    conversation = "\n\n".join([
        f"**{msg['user']}**: {msg['text']}"
        for msg in messages
    ])

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"Analyze this thread as a facilitator:\n\n{conversation}"
        }]
    )

    return message.content[0].text
```

---

## **Why This Works for Hackathon**

✅ **Clear demo** - Judges see immediate value  
✅ **No complex setup** - Socket Mode = no server deployment needed  
✅ **Extensible** - Easy to add sub-agents later  
✅ **Aligned with business model** - Shows core facilitator concept  
✅ **Fast** - Can be coded in 4-6 hours

---

## **Pitching This in 2 Minutes**

> "Companies lose thousands per hire due to Slack chaos. We built an AI facilitator that reads messy threads, extracts facts, identifies gaps, and structures decisions—automatically. No more scrolling through 50 messages to find what was decided. [DEMO]"

**Want me to build this code right now?**

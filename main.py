import os
import glob
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import openai
from dotenv import load_dotenv

print('Starting bot...')

load_dotenv()

# Initialize Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])
openai.api_key = os.environ["OPENAI_API_KEY"]


def search_docs_for_context(conversation_text):
    """Search through docs folder for relevant context based on conversation keywords"""
    print('Searching docs for relevant context...')
    
    # Extract keywords from conversation (simple approach)
    keywords = []
    # Look for common technical terms, bug references, feature names, etc.
    keyword_patterns = [
        r'\b(bug|error|issue|problem|fail)\w*\b',
        r'\b(feature|enhancement|improvement)\w*\b', 
        r'\b(board|crm|redux|react|database|ui|performance)\w*\b',
        r'\b(sprint|deployment|testing|refactor)\w*\b',
        r'\b(P[0-9]|critical|high|medium|low)\b',
        r'\b(FEAT-\d+|BUG-\d+)\b'  # JIRA ticket patterns
    ]
    
    for pattern in keyword_patterns:
        matches = re.findall(pattern, conversation_text, re.IGNORECASE)
        keywords.extend([match.lower() for match in matches])
    
    # Remove duplicates and common words
    keywords = list(set(keywords))
    keywords = [k for k in keywords if len(k) > 2]
    
    print(f'Found keywords: {keywords}')
    
    # Search through docs files
    docs_context = []
    docs_folder = os.path.join(os.path.dirname(__file__), 'docs')
    
    if os.path.exists(docs_folder):
        for doc_file in glob.glob(os.path.join(docs_folder, '*.md')):
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check if any keywords appear in this document
                relevant_sections = []
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    for keyword in keywords:
                        if keyword in line.lower():
                            # Extract context around the match (3 lines before and after)
                            start = max(0, i - 3)
                            end = min(len(lines), i + 4)
                            context_lines = lines[start:end]
                            
                            relevant_sections.append({
                                'file': os.path.basename(doc_file),
                                'context': '\n'.join(context_lines),
                                'keyword': keyword
                            })
                            break  # Only one match per line to avoid duplicates
                
                if relevant_sections:
                    docs_context.extend(relevant_sections[:3])  # Limit to 3 sections per file
                    
            except Exception as e:
                print(f'Error reading {doc_file}: {e}')
    
    return docs_context[:10]  # Limit total context to avoid token limits


def fetch_thread_messages(client, channel, thread_ts):
    print('Fetching thread messages...')
    print(channel, thread_ts)
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
    """Send thread to LLM for analysis with docs context"""
    print('Analyzing thread with LLM...')
    # Build conversation context
    conversation = "\n\n".join([
        f"**{msg['user']}**: {msg['text']}" 
        for msg in messages
    ])
    
    # Get relevant documentation context
    docs_context = search_docs_for_context(conversation)
    
    # Build context section for prompt
    context_section = ""
    if docs_context:
        context_section = "\n\n:books: **RELEVANT DOCUMENTATION CONTEXT:**\n"
        for ctx in docs_context:
            context_section += f"\n**From {ctx['file']} (keyword: {ctx['keyword']}):**\n"
            context_section += f"```\n{ctx['context']}\n```\n"
    
    prompt = f"""You are an intelligent analyzer agent with access to multiple specialized sub-agents (GitHub agent, JIRA agent, documentation agent, etc.) that help you gather comprehensive context about project discussions.

Your task:
Analyze this Slack conversation and provide your informed opinion based on data retrieved from your sub-agents.

Thread conversation:
{conversation}{context_section}

Respond in this format:

**CONVERSATION SUMMARY**
[Brief 1-2 sentence summary of what was discussed]

**CONTEXT GATHERED**
:mag: **Sub-agents consulted:** [List which agents you used - e.g., "GitHub agent, JIRA agent, Documentation agent"]
:bar_chart: **Key metrics/data found:** [Relevant data points, code references, ticket status, etc.]
:clipboard: **Related context:** [Background information from documentation, similar issues, technical debt, etc.]

**MY ANALYSIS & OPINION**
:thought_balloon: [Your thoughtful opinion on the discussion based on all gathered context. What do you think about the situation? What insights can you provide? What recommendations do you have? Be analytical and provide your perspective as an AI that has access to comprehensive project knowledge.]

Keep it concise but insightful. Focus on providing value through your analysis rather than just restating facts."""

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a professional facilitator with access to project documentation."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=1200  # Increased to accommodate documentation context
    )
    
    return response.choices[0].message.content


@app.event("app_mention")
def handle_mention(event, client, say):
    """Triggered when bot is mentioned"""
    print('Handling mention...')    
    print(event)
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    
    # Show typing indicator
    say(":robot_face: Analyzing thread...", thread_ts=thread_ts)
    
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
        say(f":x: Error: {str(e)}", thread_ts=thread_ts)


if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
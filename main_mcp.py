#!/usr/bin/env python3
"""
Myla Multi-Agent Slack Bot with MCP Orchestration
Replaces the original static analysis with dynamic multi-agent coordination using MCP servers.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

print('Starting Myla Multi-Agent Bot...')

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/mcp_orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Slack app and Anthropic client
app = App(token=os.environ["SLACK_BOT_TOKEN"])
anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

class MCPOrchestrator:
    """Orchestrates multiple MCP agents for comprehensive Slack bot responses"""
    
    def __init__(self, config_path: str = "config/mcp_config.json"):
        self.config = self.load_config(config_path)
        self.mcp_sessions: Dict[str, ClientSession] = {}
        self.agent_capabilities: Dict[str, List[str]] = {}
        self.connection_contexts: Dict[str, any] = {}  # Store context managers
        
    def load_config(self, config_path: str) -> dict:
        """Load MCP configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            return {"mcpServers": {}, "agent_routing": {}}
    
    async def initialize_agents(self):
        """Initialize connections to all MCP servers"""
        logger.info("Initializing MCP agent connections...")
        
        # First, validate that all MCP server files exist
        for server_name, server_config in self.config["mcpServers"].items():
            command = server_config["command"]
            args = server_config["args"]
            
            # Check if MCP server file exists
            if args and len(args) > 0:
                server_file = args[0]
                if not os.path.exists(server_file):
                    logger.error(f"❌ MCP server file not found: {server_file}")
                    continue
            
            try:
                logger.info(f"Connecting to {server_name}...")
                await self.connect_agent(server_name, server_config)
            except Exception as e:
                logger.error(f"❌ Failed to connect to {server_name}: {e}")
                # Continue with other agents instead of failing completely
                continue
        
        if not self.mcp_sessions:
            logger.warning("⚠️ No MCP agents connected successfully")
        else:
            logger.info(f"✅ Connected to {len(self.mcp_sessions)} MCP agents: {list(self.mcp_sessions.keys())}")
    
    async def connect_agent(self, server_name: str, server_config: dict):
        """Connect to a specific MCP server"""
        logger.info(f"Setting up connection to {server_name}...")
        
        server_params = StdioServerParameters(
            command=server_config["command"],
            args=server_config["args"],
            env=None
        )

        try:
            # Use timeout for the entire connection process
            async with asyncio.timeout(30):  # 30 second timeout
                logger.info(f"Creating stdio client for {server_name}...")
                context_manager = stdio_client(server_params)

                logger.info(f"Entering context manager for {server_name}...")
                read, write = await context_manager.__aenter__()
                
                # Store the context manager for proper cleanup later
                self.connection_contexts[server_name] = context_manager
                
                # Create and initialize session
                logger.info(f"Creating session for {server_name}...")
                session = ClientSession(read, write)
                
                logger.info(f"Initializing session for {server_name}...")
                await session.initialize()
                
                self.mcp_sessions[server_name] = session
                self.agent_capabilities[server_name] = server_config.get("capabilities", [])
                logger.info(f"✅ Successfully connected to {server_name}")
                
        except asyncio.TimeoutError:
            logger.error(f"❌ Timeout connecting to {server_name} (30s)")
            # Clean up if context manager was created
            if server_name in self.connection_contexts:
                try:
                    await self.connection_contexts[server_name].__aexit__(None, None, None)
                    del self.connection_contexts[server_name]
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup for {server_name}: {cleanup_error}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to connect to {server_name}: {e}")
            # Clean up if context manager was created
            if server_name in self.connection_contexts:
                try:
                    await self.connection_contexts[server_name].__aexit__(None, None, None)
                    del self.connection_contexts[server_name]
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup for {server_name}: {cleanup_error}")
            raise
    
    async def analyze_user_intent(self, message: str) -> Dict[str, any]:
        """Analyze user message to determine which agents to involve"""
        message_lower = message.lower()
        
        # Determine relevant agents based on keywords
        relevant_agents = []
        confidence_scores = {}
        
        # Check each agent's keywords
        for agent_type, keywords in self.config["agent_routing"].items():
            score = sum(1 for keyword in keywords if keyword.lower() in message_lower)
            if score > 0:
                agent_name = agent_type.replace("_keywords", "") + "-agent"
                relevant_agents.append(agent_name)
                confidence_scores[agent_name] = score
        
        # Always include inter-agent coordinator for complex queries
        if len(relevant_agents) > 1:
            relevant_agents.append("inter-agent-coordinator")
        
        # If no specific agents identified, use a general approach
        if not relevant_agents:
            relevant_agents = ["github-agent", "jira-agent"]  # Default agents
        
        return {
            "relevant_agents": relevant_agents,
            "confidence_scores": confidence_scores,
            "message": message,
            "complexity": "high" if len(relevant_agents) > 2 else "medium" if len(relevant_agents) > 1 else "low"
        }
    
    async def get_agent_tools(self, agent_name: str) -> List[dict]:
        """Get available tools from an MCP agent"""
        session = self.mcp_sessions.get(agent_name)
        if not session:
            return []
        
        try:
            tools_result = await session.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in tools_result.tools
            ]
        except Exception as e:
            logger.error(f"Error getting tools from {agent_name}: {e}")
            return []
    
    async def call_agent_tool(self, agent_name: str, tool_name: str, arguments: dict) -> str:
        """Call a specific tool on an MCP agent"""
        session = self.mcp_sessions.get(agent_name)
        if not session:
            return f"Agent {agent_name} not available"
        
        try:
            result = await session.call_tool(tool_name, arguments)
            return result.content[0].text if result.content else "No result"
        except Exception as e:
            logger.error(f"Error calling {tool_name} on {agent_name}: {e}")
            return f"Error: {str(e)}"
    
    async def orchestrate_response(self, user_message: str, thread_context: List[dict] = None) -> str:
        """Orchestrate a comprehensive response using multiple agents"""
        logger.info(f"Orchestrating response for: {user_message[:100]}...")
        
        # Analyze user intent
        intent_analysis = await self.analyze_user_intent(user_message)
        relevant_agents = intent_analysis["relevant_agents"]
        
        logger.info(f"Relevant agents identified: {relevant_agents}")
        
        # Gather all available tools from relevant agents
        all_tools = []
        for agent_name in relevant_agents:
            if agent_name in self.mcp_sessions:
                agent_tools = await self.get_agent_tools(agent_name)
                for tool in agent_tools:
                    tool["agent"] = agent_name  # Add agent info to tool
                all_tools.extend(agent_tools)
        
        if not all_tools:
            return "I'm sorry, but I couldn't connect to any agents to help with your request."
        
        # Build context for Anthropic
        context = self.build_context(user_message, thread_context, intent_analysis)
        
        # Use Anthropic to orchestrate the response
        try:
            response = await self.get_anthropic_response(context, all_tools, user_message)
            return response
        except Exception as e:
            logger.error(f"Error in Anthropic orchestration: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
    
    def build_context(self, user_message: str, thread_context: List[dict], intent_analysis: Dict) -> str:
        """Build context for the Anthropic orchestrator"""
        context = f"""You are Myla, an intelligent Slack bot that orchestrates multiple specialized agents to provide comprehensive project insights.

**Available Agents:**
- **GitHub Agent**: Code analysis, testing status, performance metrics, technical debt from code perspective
- **JIRA Agent**: Task management, sprint tracking, bug reports, creating/updating tasks  
- **Product Manager Agent**: Technical debt prioritization, risk assessment, sprint recommendations, capacity analysis
- **Google Docs Agent**: Document search, creation, meeting notes, templates
- **Inter-Agent Coordinator**: Multi-agent workflows, task coordination, agent communication

**User Query:** {user_message}

**Analysis:** 
- Complexity: {intent_analysis['complexity']}
- Relevant Agents: {', '.join(intent_analysis['relevant_agents'])}
- Confidence Scores: {intent_analysis.get('confidence_scores', {})}

**Instructions:**
1. Use the appropriate agent tools to gather comprehensive information
2. For complex queries, coordinate multiple agents through the Inter-Agent Coordinator
3. Provide insights and analysis, not just raw data
4. Be conversational and helpful
5. If agents need to communicate with each other (e.g., PM agent requesting JIRA data), use the coordination tools

**Thread Context:**"""
        
        if thread_context:
            context += "\n" + "\n".join([f"**{msg['user']}**: {msg['text']}" for msg in thread_context[-5:]])
        else:
            context += "\nNo previous thread context."
        
        return context
    
    async def get_anthropic_response(self, context: str, tools: List[dict], user_message: str) -> str:
        """Get response from Anthropic using available MCP tools"""
        
        # Convert MCP tools to Anthropic format
        anthropic_tools = []
        for tool in tools:
            anthropic_tools.append({
                "name": f"{tool['agent']}_{tool['name']}",  # Prefix with agent name
                "description": f"[{tool['agent']}] {tool['description']}",
                "input_schema": tool["input_schema"]
            })
        
        messages = [{"role": "user", "content": context}]
        
        # Agent interaction loop
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            try:
                response = anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4096,
                    tools=anthropic_tools,
                    messages=messages
                )
                
                # Check if we're done
                if response.stop_reason == "end_turn":
                    final_text = next(
                        (block.text for block in response.content if hasattr(block, "text")),
                        "I couldn't generate a proper response."
                    )
                    return final_text
                
                # Process tool calls
                if response.stop_reason == "tool_use":
                    messages.append({"role": "assistant", "content": response.content})
                    
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            # Extract agent name and tool name
                            full_tool_name = block.name
                            if "_" in full_tool_name:
                                agent_name, tool_name = full_tool_name.split("_", 1)
                            else:
                                agent_name = "unknown"
                                tool_name = full_tool_name
                            
                            logger.info(f"Calling {tool_name} on {agent_name} with args: {block.input}")
                            
                            # Call the MCP tool
                            tool_result = await self.call_agent_tool(agent_name, tool_name, block.input)
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": tool_result
                            })
                    
                    messages.append({"role": "user", "content": tool_results})
                    iteration += 1
                
            except Exception as e:
                logger.error(f"Error in Anthropic response iteration {iteration}: {e}")
                return f"I encountered an error while processing your request: {str(e)}"
        
        return "I've reached the maximum number of iterations while processing your request. Please try a simpler query."
    
    async def close_connections(self):
        """Close all MCP connections"""
        logger.info("Closing MCP connections...")
        
        # Close sessions first
        for session in self.mcp_sessions.values():
            try:
                await session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
        
        # Exit context managers
        for server_name, context_manager in self.connection_contexts.items():
            try:
                await context_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing context manager for {server_name}: {e}")
        
        # Clear all references
        self.mcp_sessions.clear()
        self.connection_contexts.clear()
        self.agent_capabilities.clear()

# Global orchestrator instance
orchestrator = MCPOrchestrator()

def fetch_thread_messages(client, channel, thread_ts):
    """Fetch all messages in a thread"""
    logger.info(f'Fetching thread messages for {channel}:{thread_ts}')
    
    try:
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
    except Exception as e:
        logger.error(f"Error fetching thread messages: {e}")
        return []

async def analyze_with_mcp_orchestrator(messages):
    """Analyze thread using MCP orchestrator"""
    logger.info('Analyzing with MCP orchestrator...')
    
    # Build conversation context
    conversation = "\n\n".join([
        f"**{msg['user']}**: {msg['text']}" 
        for msg in messages
    ])
    
    # Get the latest message as the main query
    latest_message = messages[-1]["text"] if messages else "Analyze this conversation"
    
    # Use orchestrator to get comprehensive response
    try:
        response = await orchestrator.orchestrate_response(latest_message, messages[:-1])
        return response
    except Exception as e:
        logger.error(f"Error in MCP orchestration: {e}")
        return f"I encountered an error while analyzing your request: {str(e)}"

@app.event("app_mention")
def handle_mention(event, client, say):
    """Triggered when bot is mentioned"""
    logger.info('Handling mention...')
    logger.info(f'Event: {event}')
    
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    
    # Show typing indicator
    say(":robot_face: Analyzing with my specialized agents...", thread_ts=thread_ts)
    
    try:
        # Fetch thread messages
        messages = fetch_thread_messages(client, channel, thread_ts)
        
        # Analyze with MCP orchestrator (run in event loop)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            analysis = loop.run_until_complete(analyze_with_mcp_orchestrator(messages))
        finally:
            loop.close()
        
        # Post results
        say(
            text=analysis,
            thread_ts=thread_ts,
            unfurl_links=False,
            unfurl_media=False
        )
        
    except Exception as e:
        logger.error(f"Error in handle_mention: {e}")
        say(f":x: Error: {str(e)}", thread_ts=thread_ts)

async def startup():
    """Initialize the MCP orchestrator"""
    try:
        await orchestrator.initialize_agents()
        logger.info("MCP Orchestrator initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize MCP orchestrator: {e}")
        raise

async def shutdown():
    """Clean shutdown of MCP connections"""
    await orchestrator.close_connections()

if __name__ == "__main__":
    # Initialize MCP orchestrator
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(startup())
        
        # Start Slack bot
        handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        logger.info("Starting Slack bot with MCP orchestration...")
        handler.start()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        loop.run_until_complete(shutdown())
        loop.close()

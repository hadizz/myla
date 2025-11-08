#!/usr/bin/env python3
"""
Inter-Agent Communication MCP Server - Handles coordination and communication between agents.
Provides tools for agent-to-agent messaging, task coordination, and workflow orchestration.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource

# Create server instance
app = Server("inter-agent-coordinator")

class AgentType(Enum):
    GITHUB = "github"
    JIRA = "jira"
    PRODUCT_MANAGER = "product_manager"
    GOOGLE_DOCS = "google_docs"
    ORCHESTRATOR = "orchestrator"

class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    TASK_ASSIGNMENT = "task_assignment"
    STATUS_UPDATE = "status_update"

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class AgentMessage:
    id: str
    from_agent: AgentType
    to_agent: AgentType
    message_type: MessageType
    content: str
    metadata: Dict = None
    timestamp: str = None
    requires_response: bool = False
    parent_message_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class CoordinationTask:
    id: str
    title: str
    description: str
    assigned_agents: List[AgentType]
    status: TaskStatus
    created_by: AgentType
    created_at: str
    updated_at: str
    dependencies: List[str] = None
    results: Dict = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.results is None:
            self.results = {}

# In-memory storage for messages and tasks
message_queue: List[AgentMessage] = []
task_registry: List[CoordinationTask] = []
agent_status: Dict[AgentType, Dict] = {}
message_counter = 1
task_counter = 1

def generate_message_id() -> str:
    """Generate unique message ID"""
    global message_counter
    msg_id = f"MSG-{message_counter:04d}"
    message_counter += 1
    return msg_id

def generate_task_id() -> str:
    """Generate unique task ID"""
    global task_counter
    task_id = f"TASK-{task_counter:04d}"
    task_counter += 1
    return task_id

def send_message(from_agent: AgentType, to_agent: AgentType, message_type: MessageType, 
                content: str, metadata: Dict = None, requires_response: bool = False,
                parent_message_id: str = None) -> AgentMessage:
    """Send a message between agents"""
    message = AgentMessage(
        id=generate_message_id(),
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=message_type,
        content=content,
        metadata=metadata or {},
        requires_response=requires_response,
        parent_message_id=parent_message_id
    )
    
    message_queue.append(message)
    return message

def get_messages_for_agent(agent: AgentType, unread_only: bool = True) -> List[AgentMessage]:
    """Get messages for a specific agent"""
    messages = [msg for msg in message_queue if msg.to_agent == agent]
    
    if unread_only:
        # In a real implementation, we'd track read status
        # For now, return messages from last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        messages = [msg for msg in messages 
                   if datetime.fromisoformat(msg.timestamp) > cutoff]
    
    return messages

def create_coordination_task(title: str, description: str, assigned_agents: List[AgentType],
                           created_by: AgentType, dependencies: List[str] = None) -> CoordinationTask:
    """Create a new coordination task"""
    task = CoordinationTask(
        id=generate_task_id(),
        title=title,
        description=description,
        assigned_agents=assigned_agents,
        status=TaskStatus.PENDING,
        created_by=created_by,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        dependencies=dependencies or []
    )
    
    task_registry.append(task)
    
    # Send task assignment messages to assigned agents
    for agent in assigned_agents:
        send_message(
            from_agent=AgentType.ORCHESTRATOR,
            to_agent=agent,
            message_type=MessageType.TASK_ASSIGNMENT,
            content=f"New task assigned: {title}",
            metadata={
                "task_id": task.id,
                "description": description,
                "dependencies": dependencies or []
            },
            requires_response=True
        )
    
    return task

def update_task_status(task_id: str, new_status: TaskStatus, agent: AgentType, 
                      results: Dict = None) -> bool:
    """Update task status"""
    for task in task_registry:
        if task.id == task_id:
            old_status = task.status
            task.status = new_status
            task.updated_at = datetime.now().isoformat()
            
            if results:
                task.results.update(results)
            
            # Notify other agents about status change
            for assigned_agent in task.assigned_agents:
                if assigned_agent != agent:
                    send_message(
                        from_agent=agent,
                        to_agent=assigned_agent,
                        message_type=MessageType.STATUS_UPDATE,
                        content=f"Task {task_id} status changed: {old_status.value} → {new_status.value}",
                        metadata={
                            "task_id": task_id,
                            "old_status": old_status.value,
                            "new_status": new_status.value,
                            "updated_by": agent.value
                        }
                    )
            
            return True
    
    return False

def get_agent_workload(agent: AgentType) -> Dict:
    """Get current workload for an agent"""
    assigned_tasks = [task for task in task_registry if agent in task.assigned_agents]
    pending_tasks = [task for task in assigned_tasks if task.status == TaskStatus.PENDING]
    in_progress_tasks = [task for task in assigned_tasks if task.status == TaskStatus.IN_PROGRESS]
    completed_tasks = [task for task in assigned_tasks if task.status == TaskStatus.COMPLETED]
    
    recent_messages = get_messages_for_agent(agent)
    
    return {
        "agent": agent.value,
        "total_tasks": len(assigned_tasks),
        "pending_tasks": len(pending_tasks),
        "in_progress_tasks": len(in_progress_tasks),
        "completed_tasks": len(completed_tasks),
        "recent_messages": len(recent_messages),
        "workload_score": len(pending_tasks) * 2 + len(in_progress_tasks) * 3  # Simple scoring
    }

def simulate_agent_communication(from_agent: str, to_agent: str, request: str) -> str:
    """Simulate communication between specific agents"""
    from_agent_enum = AgentType(from_agent)
    to_agent_enum = AgentType(to_agent)
    
    # Create request message
    request_msg = send_message(
        from_agent=from_agent_enum,
        to_agent=to_agent_enum,
        message_type=MessageType.REQUEST,
        content=request,
        requires_response=True
    )
    
    # Simulate response based on agent types
    if to_agent_enum == AgentType.JIRA:
        if "critical" in request.lower() or "bug" in request.lower():
            response = "Found 3 critical bugs: BUG-001 (Board State Corruption), BUG-002 (Memory Leak), BUG-003 (CRM Data Sync)"
        elif "sprint" in request.lower():
            response = "Sprint 3 Status: Behind schedule, 65% velocity, 10 critical bugs pending"
        elif "create" in request.lower() and "task" in request.lower():
            response = f"Task created successfully: TASK-{task_counter:03d} - {request}"
        else:
            response = "JIRA query processed successfully"
    
    elif to_agent_enum == AgentType.GITHUB:
        if "code" in request.lower() or "technical debt" in request.lower():
            response = "Found 3 high-priority technical debt items: UI Library Modernization, Performance Issues, Database Integration"
        elif "test" in request.lower():
            response = "Test coverage: 72% (target: 85%), 23 ESLint issues, 8 TypeScript errors"
        else:
            response = "GitHub analysis completed successfully"
    
    elif to_agent_enum == AgentType.GOOGLE_DOCS:
        if "search" in request.lower():
            response = "Found 5 relevant documents: PRD, Technical Architecture, Sprint Planning, Meeting Notes, User Research"
        elif "create" in request.lower():
            response = f"Document created successfully: {request}"
        else:
            response = "Google Docs operation completed successfully"
    
    elif to_agent_enum == AgentType.PRODUCT_MANAGER:
        if "risk" in request.lower():
            response = "Risk Assessment: HIGH - 2 critical impact items, immediate sprint planning required"
        elif "prioritize" in request.lower():
            response = "Prioritization complete: 3 high-priority items recommended for next sprint"
        else:
            response = "Product management analysis completed successfully"
    
    else:
        response = f"Processed request from {from_agent} successfully"
    
    # Create response message
    response_msg = send_message(
        from_agent=to_agent_enum,
        to_agent=from_agent_enum,
        message_type=MessageType.RESPONSE,
        content=response,
        parent_message_id=request_msg.id
    )
    
    return response

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available inter-agent coordination resources"""
    return [
        Resource(
            uri="coordination://messages",
            name="Message Queue",
            mimeType="application/json",
            description="All inter-agent messages"
        ),
        Resource(
            uri="coordination://tasks",
            name="Coordination Tasks",
            mimeType="application/json",
            description="All coordination tasks and their status"
        ),
        Resource(
            uri="coordination://agent-status",
            name="Agent Status",
            mimeType="application/json",
            description="Current status and workload of all agents"
        ),
        Resource(
            uri="coordination://workflows",
            name="Active Workflows",
            mimeType="application/json",
            description="Currently active multi-agent workflows"
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read coordination resources"""
    if uri == "coordination://messages":
        messages_dict = [asdict(msg) for msg in message_queue]
        return json.dumps(messages_dict, indent=2)
    
    elif uri == "coordination://tasks":
        tasks_dict = [asdict(task) for task in task_registry]
        return json.dumps(tasks_dict, indent=2)
    
    elif uri == "coordination://agent-status":
        status = {}
        for agent_type in AgentType:
            status[agent_type.value] = get_agent_workload(agent_type)
        return json.dumps(status, indent=2)
    
    elif uri == "coordination://workflows":
        # Get active multi-agent tasks
        active_workflows = [task for task in task_registry 
                          if task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
                          and len(task.assigned_agents) > 1]
        workflows_dict = [asdict(workflow) for workflow in active_workflows]
        return json.dumps(workflows_dict, indent=2)
    
    return "Resource not found"

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available coordination tools"""
    return [
        Tool(
            name="send_agent_message",
            description="Send a message from one agent to another",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_agent": {
                        "type": "string",
                        "enum": ["github", "jira", "product_manager", "google_docs", "orchestrator"],
                        "description": "Source agent"
                    },
                    "to_agent": {
                        "type": "string",
                        "enum": ["github", "jira", "product_manager", "google_docs", "orchestrator"],
                        "description": "Target agent"
                    },
                    "message_type": {
                        "type": "string",
                        "enum": ["request", "response", "notification", "task_assignment", "status_update"],
                        "description": "Type of message"
                    },
                    "content": {
                        "type": "string",
                        "description": "Message content"
                    },
                    "requires_response": {
                        "type": "boolean",
                        "description": "Whether this message requires a response",
                        "default": false
                    }
                },
                "required": ["from_agent", "to_agent", "message_type", "content"]
            }
        ),
        Tool(
            name="create_coordination_task",
            description="Create a multi-agent coordination task",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Task title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed task description"
                    },
                    "assigned_agents": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["github", "jira", "product_manager", "google_docs"]
                        },
                        "description": "Agents assigned to this task"
                    },
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task dependencies (task IDs)",
                        "default": []
                    }
                },
                "required": ["title", "description", "assigned_agents"]
            }
        ),
        Tool(
            name="update_task_status",
            description="Update the status of a coordination task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID to update"
                    },
                    "new_status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "failed", "cancelled"],
                        "description": "New task status"
                    },
                    "agent": {
                        "type": "string",
                        "enum": ["github", "jira", "product_manager", "google_docs", "orchestrator"],
                        "description": "Agent updating the status"
                    },
                    "results": {
                        "type": "object",
                        "description": "Task results or additional data",
                        "default": {}
                    }
                },
                "required": ["task_id", "new_status", "agent"]
            }
        ),
        Tool(
            name="get_agent_messages",
            description="Get messages for a specific agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "enum": ["github", "jira", "product_manager", "google_docs", "orchestrator"],
                        "description": "Agent to get messages for"
                    },
                    "unread_only": {
                        "type": "boolean",
                        "description": "Only return unread messages",
                        "default": true
                    }
                },
                "required": ["agent"]
            }
        ),
        Tool(
            name="simulate_agent_communication",
            description="Simulate communication between two agents for testing",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_agent": {
                        "type": "string",
                        "enum": ["github", "jira", "product_manager", "google_docs"],
                        "description": "Source agent"
                    },
                    "to_agent": {
                        "type": "string",
                        "enum": ["github", "jira", "product_manager", "google_docs"],
                        "description": "Target agent"
                    },
                    "request": {
                        "type": "string",
                        "description": "Request to send to the target agent"
                    }
                },
                "required": ["from_agent", "to_agent", "request"]
            }
        ),
        Tool(
            name="get_agent_workload",
            description="Get current workload and status for all agents",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="orchestrate_workflow",
            description="Orchestrate a complex multi-agent workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_type": {
                        "type": "string",
                        "enum": ["technical_debt_analysis", "sprint_planning", "bug_investigation", "feature_planning"],
                        "description": "Type of workflow to orchestrate"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Workflow-specific parameters",
                        "default": {}
                    }
                },
                "required": ["workflow_type"]
            }
        ),
        Tool(
            name="get_coordination_metrics",
            description="Get metrics about inter-agent coordination and communication",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    
    if name == "send_agent_message":
        from_agent = AgentType(arguments["from_agent"])
        to_agent = AgentType(arguments["to_agent"])
        message_type = MessageType(arguments["message_type"])
        content = arguments["content"]
        requires_response = arguments.get("requires_response", False)
        
        message = send_message(from_agent, to_agent, message_type, content, requires_response=requires_response)
        
        result = f"📨 **Message Sent Successfully!**\n\n"
        result += f"• **ID:** {message.id}\n"
        result += f"• **From:** {from_agent.value.replace('_', ' ').title()}\n"
        result += f"• **To:** {to_agent.value.replace('_', ' ').title()}\n"
        result += f"• **Type:** {message_type.value.replace('_', ' ').title()}\n"
        result += f"• **Content:** {content}\n"
        result += f"• **Timestamp:** {message.timestamp}\n"
        result += f"• **Requires Response:** {'Yes' if requires_response else 'No'}\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "create_coordination_task":
        title = arguments["title"]
        description = arguments["description"]
        assigned_agents = [AgentType(agent) for agent in arguments["assigned_agents"]]
        dependencies = arguments.get("dependencies", [])
        
        task = create_coordination_task(title, description, assigned_agents, 
                                      AgentType.ORCHESTRATOR, dependencies)
        
        result = f"🎯 **Coordination Task Created!**\n\n"
        result += f"• **ID:** {task.id}\n"
        result += f"• **Title:** {task.title}\n"
        result += f"• **Description:** {task.description}\n"
        result += f"• **Assigned Agents:** {', '.join([agent.value.replace('_', ' ').title() for agent in assigned_agents])}\n"
        result += f"• **Status:** {task.status.value.replace('_', ' ').title()}\n"
        result += f"• **Created:** {task.created_at}\n"
        
        if dependencies:
            result += f"• **Dependencies:** {', '.join(dependencies)}\n"
        
        result += f"\n📬 **Task assignment messages sent to all assigned agents.**"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "update_task_status":
        task_id = arguments["task_id"]
        new_status = TaskStatus(arguments["new_status"])
        agent = AgentType(arguments["agent"])
        results = arguments.get("results", {})
        
        success = update_task_status(task_id, new_status, agent, results)
        
        if success:
            result = f"✅ **Task Status Updated!**\n\n"
            result += f"• **Task ID:** {task_id}\n"
            result += f"• **New Status:** {new_status.value.replace('_', ' ').title()}\n"
            result += f"• **Updated By:** {agent.value.replace('_', ' ').title()}\n"
            result += f"• **Updated At:** {datetime.now().isoformat()}\n"
            
            if results:
                result += f"• **Results:** {json.dumps(results, indent=2)}\n"
            
            result += f"\n📢 **Status update notifications sent to other assigned agents.**"
        else:
            result = f"❌ **Task {task_id} not found.**"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "get_agent_messages":
        agent = AgentType(arguments["agent"])
        unread_only = arguments.get("unread_only", True)
        
        messages = get_messages_for_agent(agent, unread_only)
        
        if not messages:
            result = f"📭 **No {'unread ' if unread_only else ''}messages for {agent.value.replace('_', ' ').title()}**"
        else:
            result = f"📬 **Messages for {agent.value.replace('_', ' ').title()} ({len(messages)} {'unread' if unread_only else 'total'}):**\n\n"
            
            for msg in messages[-10:]:  # Show last 10 messages
                result += f"**{msg.id}** - {msg.message_type.value.replace('_', ' ').title()}\n"
                result += f"• From: {msg.from_agent.value.replace('_', ' ').title()}\n"
                result += f"• Content: {msg.content[:100]}{'...' if len(msg.content) > 100 else ''}\n"
                result += f"• Time: {msg.timestamp}\n"
                if msg.requires_response:
                    result += f"• ⚠️ **Requires Response**\n"
                result += "\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "simulate_agent_communication":
        from_agent = arguments["from_agent"]
        to_agent = arguments["to_agent"]
        request = arguments["request"]
        
        response = simulate_agent_communication(from_agent, to_agent, request)
        
        result = f"🔄 **Agent Communication Simulation**\n\n"
        result += f"**Request:**\n"
        result += f"• From: {from_agent.replace('_', ' ').title()}\n"
        result += f"• To: {to_agent.replace('_', ' ').title()}\n"
        result += f"• Message: {request}\n\n"
        result += f"**Response:**\n"
        result += f"• From: {to_agent.replace('_', ' ').title()}\n"
        result += f"• Message: {response}\n\n"
        result += f"📨 **Messages logged in coordination system.**"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "get_agent_workload":
        result = "👥 **Agent Workload Status:**\n\n"
        
        for agent_type in AgentType:
            if agent_type == AgentType.ORCHESTRATOR:
                continue  # Skip orchestrator in workload display
                
            workload = get_agent_workload(agent_type)
            result += f"**{agent_type.value.replace('_', ' ').title()}:**\n"
            result += f"• Total Tasks: {workload['total_tasks']}\n"
            result += f"• Pending: {workload['pending_tasks']}\n"
            result += f"• In Progress: {workload['in_progress_tasks']}\n"
            result += f"• Completed: {workload['completed_tasks']}\n"
            result += f"• Recent Messages: {workload['recent_messages']}\n"
            result += f"• Workload Score: {workload['workload_score']}\n\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "orchestrate_workflow":
        workflow_type = arguments["workflow_type"]
        parameters = arguments.get("parameters", {})
        
        # Create workflow-specific coordination tasks
        if workflow_type == "technical_debt_analysis":
            # Create a multi-step workflow for technical debt analysis
            task1 = create_coordination_task(
                "Analyze Technical Debt",
                "Product Manager analyzes technical debt priorities",
                [AgentType.PRODUCT_MANAGER],
                AgentType.ORCHESTRATOR
            )
            
            task2 = create_coordination_task(
                "Get GitHub Code Analysis",
                "GitHub agent provides code structure and issues analysis",
                [AgentType.GITHUB],
                AgentType.ORCHESTRATOR,
                dependencies=[task1.id]
            )
            
            task3 = create_coordination_task(
                "Create JIRA Tasks for Debt Items",
                "JIRA agent creates tasks for prioritized technical debt",
                [AgentType.JIRA],
                AgentType.ORCHESTRATOR,
                dependencies=[task1.id, task2.id]
            )
            
            task4 = create_coordination_task(
                "Document Analysis Results",
                "Google Docs agent creates technical debt analysis document",
                [AgentType.GOOGLE_DOCS],
                AgentType.ORCHESTRATOR,
                dependencies=[task1.id, task2.id, task3.id]
            )
            
            result = f"🔄 **Technical Debt Analysis Workflow Orchestrated!**\n\n"
            result += f"**Created Tasks:**\n"
            result += f"1. {task1.id}: {task1.title}\n"
            result += f"2. {task2.id}: {task2.title}\n"
            result += f"3. {task3.id}: {task3.title}\n"
            result += f"4. {task4.id}: {task4.title}\n\n"
            result += f"📋 **Workflow will execute in dependency order.**"
        
        elif workflow_type == "sprint_planning":
            task1 = create_coordination_task(
                "Get Sprint Status from JIRA",
                "JIRA agent provides current sprint status and metrics",
                [AgentType.JIRA],
                AgentType.ORCHESTRATOR
            )
            
            task2 = create_coordination_task(
                "Analyze Technical Constraints",
                "GitHub agent analyzes technical constraints and testing requirements",
                [AgentType.GITHUB],
                AgentType.ORCHESTRATOR
            )
            
            task3 = create_coordination_task(
                "Create Sprint Recommendations",
                "Product Manager creates sprint planning recommendations",
                [AgentType.PRODUCT_MANAGER],
                AgentType.ORCHESTRATOR,
                dependencies=[task1.id, task2.id]
            )
            
            task4 = create_coordination_task(
                "Document Sprint Plan",
                "Google Docs agent creates sprint planning document",
                [AgentType.GOOGLE_DOCS],
                AgentType.ORCHESTRATOR,
                dependencies=[task3.id]
            )
            
            result = f"📅 **Sprint Planning Workflow Orchestrated!**\n\n"
            result += f"**Created Tasks:**\n"
            result += f"1. {task1.id}: {task1.title}\n"
            result += f"2. {task2.id}: {task2.title}\n"
            result += f"3. {task3.id}: {task3.title}\n"
            result += f"4. {task4.id}: {task4.title}\n\n"
            result += f"📋 **Workflow will execute in dependency order.**"
        
        else:
            result = f"🔄 **{workflow_type.replace('_', ' ').title()} Workflow**\n\n"
            result += f"Workflow type '{workflow_type}' is not yet implemented.\n"
            result += f"Available workflows: technical_debt_analysis, sprint_planning"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "get_coordination_metrics":
        total_messages = len(message_queue)
        total_tasks = len(task_registry)
        
        # Message metrics
        message_types = {}
        for msg in message_queue:
            msg_type = msg.message_type.value
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        # Task metrics
        task_statuses = {}
        for task in task_registry:
            status = task.status.value
            task_statuses[status] = task_statuses.get(status, 0) + 1
        
        # Agent activity
        agent_activity = {}
        for agent_type in AgentType:
            if agent_type == AgentType.ORCHESTRATOR:
                continue
            sent_messages = len([msg for msg in message_queue if msg.from_agent == agent_type])
            received_messages = len([msg for msg in message_queue if msg.to_agent == agent_type])
            agent_activity[agent_type.value] = {
                "sent": sent_messages,
                "received": received_messages,
                "total": sent_messages + received_messages
            }
        
        result = f"📊 **Coordination Metrics:**\n\n"
        result += f"**Overall Statistics:**\n"
        result += f"• Total Messages: {total_messages}\n"
        result += f"• Total Tasks: {total_tasks}\n\n"
        
        result += f"**Message Types:**\n"
        for msg_type, count in message_types.items():
            result += f"• {msg_type.replace('_', ' ').title()}: {count}\n"
        result += "\n"
        
        result += f"**Task Status Distribution:**\n"
        for status, count in task_statuses.items():
            result += f"• {status.replace('_', ' ').title()}: {count}\n"
        result += "\n"
        
        result += f"**Agent Activity:**\n"
        for agent, activity in agent_activity.items():
            result += f"• {agent.replace('_', ' ').title()}: {activity['total']} messages ({activity['sent']} sent, {activity['received']} received)\n"
        
        return [TextContent(type="text", text=result)]
    
    return [TextContent(type="text", text="Unknown tool")]

async def main():
    """Main server entry point"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())

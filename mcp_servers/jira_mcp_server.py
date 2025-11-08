#!/usr/bin/env python3
"""
JIRA MCP Server - Provides tools for managing JIRA tasks and sprint information.
Connects to docs/jira-open-tasks.md for mock JIRA data.
"""

import asyncio
import json
import os
import re
from datetime import datetime, timedelta
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource

# Create server instance
app = Server("jira-agent")

# Path to the JIRA documentation file
JIRA_DOCS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "jira-open-tasks.md")

# In-memory storage for new tasks (in a real implementation, this would be a database)
new_tasks = []
task_counter = 11  # Starting after existing BUG-010

def load_jira_data():
    """Load and parse JIRA documentation data"""
    try:
        with open(JIRA_DOCS_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return "JIRA documentation file not found"

def parse_sprint_overview(content):
    """Extract sprint overview information"""
    overview = {}
    
    # Extract sprint status
    sprint_match = re.search(r'\*\*Sprint:\*\* (\d+) of (\d+)', content)
    if sprint_match:
        overview["current_sprint"] = int(sprint_match.group(1))
        overview["total_sprints"] = int(sprint_match.group(2))
    
    # Extract status
    status_match = re.search(r'\*\*Status:\*\* (.+)', content)
    if status_match:
        overview["status"] = status_match.group(1)
    
    # Extract velocity
    velocity_match = re.search(r'\*\*Team Velocity:\*\* (.+)', content)
    if velocity_match:
        overview["velocity"] = velocity_match.group(1)
    
    # Extract task distribution
    distribution_pattern = r'- \*\*(.+?):\*\* (\d+) items'
    distribution = re.findall(distribution_pattern, content)
    overview["task_distribution"] = {item[0]: int(item[1]) for item in distribution}
    
    return overview

def parse_bugs(content):
    """Extract bug information from JIRA docs"""
    bugs = []
    
    # Pattern to match bug entries
    bug_pattern = r'#### (BUG-\d+): (.+?)\n- \*\*Severity:\*\* (.+?)\n- \*\*Component:\*\* (.+?)\n- \*\*Description:\*\* (.+?)(?=\n- \*\*Test Strategy|\n\n#### |\n### |\Z)'
    
    bug_matches = re.findall(bug_pattern, content, re.DOTALL)
    
    for match in bug_matches:
        bug = {
            "id": match[0],
            "title": match[1],
            "severity": match[2],
            "component": match[3],
            "description": match[4].strip(),
            "type": "bug"
        }
        bugs.append(bug)
    
    return bugs

def parse_features(content):
    """Extract feature information from JIRA docs"""
    features = []
    
    # Pattern to match feature entries
    feature_pattern = r'#### (FEAT-\d+): (.+?)\n- \*\*Epic:\*\* (.+?)\n- \*\*Story Points:\*\* (.+?)\n- \*\*Status:\*\* (.+?)(?=\n- \*\*Test Strategy|\n\n#### |\n### |\Z)'
    
    feature_matches = re.findall(feature_pattern, content, re.DOTALL)
    
    for match in feature_matches:
        feature = {
            "id": match[0],
            "title": match[1],
            "epic": match[2],
            "story_points": match[3],
            "status": match[4],
            "type": "feature"
        }
        features.append(feature)
    
    return features

def get_tasks_by_priority(content, priority=None):
    """Get tasks filtered by priority"""
    bugs = parse_bugs(content)
    
    if priority:
        priority_map = {
            "critical": ["Critical", "P0"],
            "high": ["High", "P1"], 
            "medium": ["Medium", "P2"],
            "low": ["Low", "P3"]
        }
        
        target_priorities = priority_map.get(priority.lower(), [priority])
        filtered_bugs = [bug for bug in bugs if any(p in bug["severity"] for p in target_priorities)]
        return filtered_bugs
    
    return bugs

def get_tasks_by_status(content, status=None):
    """Get tasks filtered by status"""
    features = parse_features(content)
    
    if status:
        filtered_features = [feat for feat in features if status.lower() in feat["status"].lower()]
        return filtered_features
    
    return features

def create_new_task(task_type, title, description, priority="Medium", component="General"):
    """Create a new task (simulated)"""
    global task_counter
    
    task_id = f"{task_type.upper()}-{task_counter:03d}"
    task_counter += 1
    
    new_task = {
        "id": task_id,
        "title": title,
        "description": description,
        "priority": priority,
        "component": component,
        "status": "Open",
        "created_date": datetime.now().isoformat(),
        "type": task_type.lower()
    }
    
    new_tasks.append(new_task)
    return new_task

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available JIRA resources"""
    return [
        Resource(
            uri="jira://sprint-overview",
            name="Sprint Overview",
            mimeType="application/json",
            description="Current sprint status and metrics"
        ),
        Resource(
            uri="jira://task-queue",
            name="Task Queue",
            mimeType="application/json",
            description="All open tasks and their status"
        ),
        Resource(
            uri="jira://bugs",
            name="Bug Reports",
            mimeType="application/json",
            description="All bug reports with details"
        ),
        Resource(
            uri="jira://features",
            name="Feature Requests",
            mimeType="application/json",
            description="All feature requests and their progress"
        ),
        Resource(
            uri="jira://new-tasks",
            name="Recently Created Tasks",
            mimeType="application/json",
            description="Tasks created through the MCP server"
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read JIRA resources"""
    content = load_jira_data()
    
    if uri == "jira://sprint-overview":
        overview = parse_sprint_overview(content)
        return json.dumps(overview, indent=2)
    
    elif uri == "jira://task-queue":
        bugs = parse_bugs(content)
        features = parse_features(content)
        all_tasks = bugs + features + new_tasks
        return json.dumps(all_tasks, indent=2)
    
    elif uri == "jira://bugs":
        bugs = parse_bugs(content)
        return json.dumps(bugs, indent=2)
    
    elif uri == "jira://features":
        features = parse_features(content)
        return json.dumps(features, indent=2)
    
    elif uri == "jira://new-tasks":
        return json.dumps(new_tasks, indent=2)
    
    return "Resource not found"

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available JIRA tools"""
    return [
        Tool(
            name="get_sprint_status",
            description="Get current sprint status and progress information",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="search_tasks",
            description="Search for tasks by various criteria",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for task title or description"
                    },
                    "task_type": {
                        "type": "string",
                        "description": "Filter by task type (bug, feature, all)",
                        "default": "all"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Filter by priority (critical, high, medium, low)",
                        "default": "all"
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status (open, in_progress, testing, etc.)",
                        "default": "all"
                    }
                }
            }
        ),
        Tool(
            name="get_task_details",
            description="Get detailed information about a specific task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID (e.g., BUG-001, FEAT-002)"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="create_task",
            description="Create a new JIRA task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "description": "Type of task (bug, feature, task)",
                        "enum": ["bug", "feature", "task"]
                    },
                    "title": {
                        "type": "string",
                        "description": "Task title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed task description"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Task priority",
                        "enum": ["Critical", "High", "Medium", "Low"],
                        "default": "Medium"
                    },
                    "component": {
                        "type": "string",
                        "description": "Component or area affected",
                        "default": "General"
                    }
                },
                "required": ["task_type", "title", "description"]
            }
        ),
        Tool(
            name="get_critical_issues",
            description="Get all critical and high priority issues that need immediate attention",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_sprint_metrics",
            description="Get detailed sprint metrics and team performance data",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="update_task_status",
            description="Update the status of an existing task (simulated for new tasks only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID to update"
                    },
                    "new_status": {
                        "type": "string",
                        "description": "New status for the task",
                        "enum": ["Open", "In Progress", "Testing", "Done", "Closed"]
                    }
                },
                "required": ["task_id", "new_status"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    content = load_jira_data()
    
    if name == "get_sprint_status":
        overview = parse_sprint_overview(content)
        
        result = f"**Sprint {overview.get('current_sprint', 'N/A')} Status:**\n\n"
        result += f"• **Status:** {overview.get('status', 'Unknown')}\n"
        result += f"• **Team Velocity:** {overview.get('velocity', 'Unknown')}\n"
        result += f"• **Progress:** Sprint {overview.get('current_sprint', 0)} of {overview.get('total_sprints', 0)}\n\n"
        
        result += "**Task Distribution:**\n"
        for task_type, count in overview.get('task_distribution', {}).items():
            result += f"• {task_type}: {count} items\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "search_tasks":
        query = arguments.get("query", "")
        task_type = arguments.get("task_type", "all")
        priority = arguments.get("priority", "all")
        status = arguments.get("status", "all")
        
        all_tasks = []
        
        if task_type in ["all", "bug"]:
            bugs = parse_bugs(content)
            all_tasks.extend(bugs)
        
        if task_type in ["all", "feature"]:
            features = parse_features(content)
            all_tasks.extend(features)
        
        # Add new tasks
        all_tasks.extend(new_tasks)
        
        # Apply filters
        filtered_tasks = all_tasks
        
        if query:
            filtered_tasks = [task for task in filtered_tasks 
                            if query.lower() in task.get("title", "").lower() 
                            or query.lower() in task.get("description", "").lower()]
        
        if priority != "all":
            filtered_tasks = [task for task in filtered_tasks 
                            if priority.lower() in task.get("severity", task.get("priority", "")).lower()]
        
        if status != "all":
            filtered_tasks = [task for task in filtered_tasks 
                            if status.lower() in task.get("status", "").lower()]
        
        if not filtered_tasks:
            return [TextContent(type="text", text="No tasks found matching the criteria.")]
        
        result = f"**Found {len(filtered_tasks)} tasks:**\n\n"
        for task in filtered_tasks[:10]:  # Limit to first 10 results
            result += f"🎫 **{task['id']}: {task['title']}**\n"
            if 'severity' in task:
                result += f"   Priority: {task['severity']}\n"
            elif 'priority' in task:
                result += f"   Priority: {task['priority']}\n"
            if 'status' in task:
                result += f"   Status: {task['status']}\n"
            result += f"   Description: {task['description'][:100]}...\n\n"
        
        if len(filtered_tasks) > 10:
            result += f"... and {len(filtered_tasks) - 10} more tasks."
        
        return [TextContent(type="text", text=result)]
    
    elif name == "get_task_details":
        task_id = arguments["task_id"]
        
        # Search in bugs
        bugs = parse_bugs(content)
        for bug in bugs:
            if bug["id"] == task_id:
                result = f"**{bug['id']}: {bug['title']}**\n\n"
                result += f"• **Type:** Bug\n"
                result += f"• **Severity:** {bug['severity']}\n"
                result += f"• **Component:** {bug['component']}\n"
                result += f"• **Description:** {bug['description']}\n"
                return [TextContent(type="text", text=result)]
        
        # Search in features
        features = parse_features(content)
        for feature in features:
            if feature["id"] == task_id:
                result = f"**{feature['id']}: {feature['title']}**\n\n"
                result += f"• **Type:** Feature\n"
                result += f"• **Epic:** {feature['epic']}\n"
                result += f"• **Story Points:** {feature['story_points']}\n"
                result += f"• **Status:** {feature['status']}\n"
                return [TextContent(type="text", text=result)]
        
        # Search in new tasks
        for task in new_tasks:
            if task["id"] == task_id:
                result = f"**{task['id']}: {task['title']}**\n\n"
                result += f"• **Type:** {task['type'].title()}\n"
                result += f"• **Priority:** {task['priority']}\n"
                result += f"• **Component:** {task['component']}\n"
                result += f"• **Status:** {task['status']}\n"
                result += f"• **Created:** {task['created_date']}\n"
                result += f"• **Description:** {task['description']}\n"
                return [TextContent(type="text", text=result)]
        
        return [TextContent(type="text", text=f"Task {task_id} not found.")]
    
    elif name == "create_task":
        task_type = arguments["task_type"]
        title = arguments["title"]
        description = arguments["description"]
        priority = arguments.get("priority", "Medium")
        component = arguments.get("component", "General")
        
        new_task = create_new_task(task_type, title, description, priority, component)
        
        result = f"✅ **Task Created Successfully!**\n\n"
        result += f"• **ID:** {new_task['id']}\n"
        result += f"• **Title:** {new_task['title']}\n"
        result += f"• **Type:** {new_task['type'].title()}\n"
        result += f"• **Priority:** {new_task['priority']}\n"
        result += f"• **Component:** {new_task['component']}\n"
        result += f"• **Status:** {new_task['status']}\n"
        result += f"• **Created:** {new_task['created_date']}\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "get_critical_issues":
        critical_bugs = get_tasks_by_priority(content, "critical")
        high_bugs = get_tasks_by_priority(content, "high")
        
        result = "🚨 **Critical & High Priority Issues:**\n\n"
        
        if critical_bugs:
            result += "**🔴 Critical Issues:**\n"
            for bug in critical_bugs:
                result += f"• {bug['id']}: {bug['title']} ({bug['component']})\n"
            result += "\n"
        
        if high_bugs:
            result += "**🟠 High Priority Issues:**\n"
            for bug in high_bugs:
                result += f"• {bug['id']}: {bug['title']} ({bug['component']})\n"
        
        if not critical_bugs and not high_bugs:
            result += "No critical or high priority issues found! 🎉"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "get_sprint_metrics":
        overview = parse_sprint_overview(content)
        
        # Extract metrics from the content
        metrics_pattern = r'### Current Sprint Metrics\n- \*\*(.+?):\*\* (.+?) \(Target: (.+?)\)'
        metrics = re.findall(metrics_pattern, content)
        
        result = f"📊 **Sprint {overview.get('current_sprint', 'N/A')} Metrics:**\n\n"
        
        for metric in metrics:
            result += f"• **{metric[0]}:** {metric[1]} (Target: {metric[2]})\n"
        
        # Add quality gates
        quality_gates_match = re.search(r'### Quality Gates\n(.*?)(?=\n---|\n### |\Z)', content, re.DOTALL)
        if quality_gates_match:
            result += "\n**Quality Gates:**\n"
            gates = quality_gates_match.group(1).strip().split('\n')
            for gate in gates:
                if gate.strip().startswith('- [ ]') or gate.strip().startswith('- [x]'):
                    status = "✅" if "[x]" in gate else "❌"
                    gate_text = gate.replace('- [ ]', '').replace('- [x]', '').strip()
                    result += f"{status} {gate_text}\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "update_task_status":
        task_id = arguments["task_id"]
        new_status = arguments["new_status"]
        
        # Only allow updating new tasks (simulated)
        for task in new_tasks:
            if task["id"] == task_id:
                old_status = task["status"]
                task["status"] = new_status
                task["updated_date"] = datetime.now().isoformat()
                
                result = f"✅ **Task Status Updated!**\n\n"
                result += f"• **Task:** {task['id']} - {task['title']}\n"
                result += f"• **Status:** {old_status} → {new_status}\n"
                result += f"• **Updated:** {task['updated_date']}\n"
                
                return [TextContent(type="text", text=result)]
        
        return [TextContent(type="text", text=f"Cannot update task {task_id}. Only newly created tasks can be updated through this interface.")]
    
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

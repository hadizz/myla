#!/usr/bin/env python3
"""
Product Manager MCP Server - Provides tools for technical debt analysis and project management insights.
Connects to docs/technical-debts.md for mock technical debt data.
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
app = Server("product-manager-agent")

# Path to the technical debt documentation file
TECH_DEBT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "technical-debts.md")

# In-memory storage for recommendations and analysis
recommendations = []
analysis_history = []

def load_tech_debt_data():
    """Load and parse technical debt documentation data"""
    try:
        with open(TECH_DEBT_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return "Technical debt documentation file not found"

def parse_debt_items(content):
    """Extract technical debt items from the documentation"""
    debt_items = []
    
    # Pattern to match debt sections
    debt_pattern = r'### (\d+\. .+?)\n\*\*Priority: (.+?)\*\*\n\*\*Impact: (.+?)\*\*\n\n#### Current State\n(.*?)(?=\n#### Testing Strategy|\n### |\Z)'
    
    debt_matches = re.findall(debt_pattern, content, re.DOTALL)
    
    for match in debt_matches:
        debt_item = {
            "title": match[0],
            "priority": match[1],
            "impact": match[2],
            "current_state": match[3].strip(),
            "id": len(debt_items) + 1
        }
        debt_items.append(debt_item)
    
    return debt_items

def parse_testing_priorities(content):
    """Extract testing priorities and recommendations"""
    priorities = {}
    
    # Extract critical path testing
    critical_match = re.search(r'### Critical Path Testing\n(.*?)(?=\n### |\Z)', content, re.DOTALL)
    if critical_match:
        priorities["critical_path"] = critical_match.group(1).strip()
    
    # Extract risk mitigation
    risk_match = re.search(r'### Risk Mitigation Testing\n(.*?)(?=\n### |\Z)', content, re.DOTALL)
    if risk_match:
        priorities["risk_mitigation"] = risk_match.group(1).strip()
    
    return priorities

def parse_quality_gates(content):
    """Extract quality gates and success metrics"""
    quality_gates = {}
    
    # Extract pre-deployment checklist
    checklist_match = re.search(r'### Pre-deployment Checklist\n(.*?)(?=\n### |\Z)', content, re.DOTALL)
    if checklist_match:
        checklist_items = []
        lines = checklist_match.group(1).strip().split('\n')
        for line in lines:
            if line.strip().startswith('- [ ]') or line.strip().startswith('- [x]'):
                item = line.replace('- [ ]', '').replace('- [x]', '').strip()
                status = "completed" if "[x]" in line else "pending"
                checklist_items.append({"item": item, "status": status})
        quality_gates["checklist"] = checklist_items
    
    # Extract success metrics
    metrics_match = re.search(r'### Success Metrics\n(.*?)(?=\n### |\Z)', content, re.DOTALL)
    if metrics_match:
        metrics = []
        lines = metrics_match.group(1).strip().split('\n')
        for line in lines:
            if line.strip().startswith('-'):
                metrics.append(line.strip()[1:].strip())
        quality_gates["success_metrics"] = metrics
    
    return quality_gates

def analyze_debt_priority(debt_items):
    """Analyze and prioritize technical debt items"""
    priority_scores = {
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1
    }
    
    impact_scores = {
        "Critical": 3,
        "User Experience": 2,
        "Data Integrity": 3,
        "Performance": 2
    }
    
    analyzed_items = []
    for item in debt_items:
        priority_score = priority_scores.get(item["priority"], 1)
        impact_score = impact_scores.get(item["impact"], 1)
        total_score = priority_score + impact_score
        
        analyzed_item = item.copy()
        analyzed_item["calculated_priority"] = total_score
        analyzed_item["recommendation"] = generate_recommendation(item, total_score)
        analyzed_items.append(analyzed_item)
    
    # Sort by calculated priority (highest first)
    analyzed_items.sort(key=lambda x: x["calculated_priority"], reverse=True)
    return analyzed_items

def generate_recommendation(debt_item, priority_score):
    """Generate recommendations based on debt item analysis"""
    if priority_score >= 5:
        return "IMMEDIATE ACTION REQUIRED - Address in current sprint"
    elif priority_score >= 4:
        return "HIGH PRIORITY - Schedule for next sprint"
    elif priority_score >= 3:
        return "MEDIUM PRIORITY - Include in sprint planning"
    else:
        return "LOW PRIORITY - Consider for future sprints"

def create_risk_assessment(debt_items):
    """Create risk assessment based on technical debt"""
    high_risk_count = len([item for item in debt_items if item["priority"] == "HIGH"])
    critical_impact_count = len([item for item in debt_items if item["impact"] == "Critical"])
    
    risk_level = "LOW"
    if high_risk_count >= 2 or critical_impact_count >= 1:
        risk_level = "HIGH"
    elif high_risk_count >= 1:
        risk_level = "MEDIUM"
    
    assessment = {
        "risk_level": risk_level,
        "high_priority_items": high_risk_count,
        "critical_impact_items": critical_impact_count,
        "total_debt_items": len(debt_items),
        "recommendations": []
    }
    
    if risk_level == "HIGH":
        assessment["recommendations"].append("Immediate sprint planning session required")
        assessment["recommendations"].append("Consider reducing feature velocity to address debt")
        assessment["recommendations"].append("Allocate senior developers to debt resolution")
    elif risk_level == "MEDIUM":
        assessment["recommendations"].append("Schedule debt resolution in next 2 sprints")
        assessment["recommendations"].append("Monitor for additional debt accumulation")
    
    return assessment

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available Product Manager resources"""
    return [
        Resource(
            uri="pm://technical-debt",
            name="Technical Debt Analysis",
            mimeType="application/json",
            description="Current technical debt items and analysis"
        ),
        Resource(
            uri="pm://risk-assessment",
            name="Risk Assessment",
            mimeType="application/json",
            description="Project risk assessment based on technical debt"
        ),
        Resource(
            uri="pm://quality-gates",
            name="Quality Gates",
            mimeType="application/json",
            description="Quality gates and success metrics"
        ),
        Resource(
            uri="pm://recommendations",
            name="PM Recommendations",
            mimeType="application/json",
            description="Product management recommendations and analysis"
        ),
        Resource(
            uri="pm://testing-priorities",
            name="Testing Priorities",
            mimeType="application/json",
            description="Testing priorities and strategies"
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read Product Manager resources"""
    content = load_tech_debt_data()
    
    if uri == "pm://technical-debt":
        debt_items = parse_debt_items(content)
        analyzed_items = analyze_debt_priority(debt_items)
        return json.dumps(analyzed_items, indent=2)
    
    elif uri == "pm://risk-assessment":
        debt_items = parse_debt_items(content)
        assessment = create_risk_assessment(debt_items)
        return json.dumps(assessment, indent=2)
    
    elif uri == "pm://quality-gates":
        quality_gates = parse_quality_gates(content)
        return json.dumps(quality_gates, indent=2)
    
    elif uri == "pm://recommendations":
        return json.dumps(recommendations, indent=2)
    
    elif uri == "pm://testing-priorities":
        priorities = parse_testing_priorities(content)
        return json.dumps(priorities, indent=2)
    
    return "Resource not found"

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Product Manager tools"""
    return [
        Tool(
            name="analyze_technical_debt",
            description="Analyze technical debt and provide prioritization recommendations",
            inputSchema={
                "type": "object",
                "properties": {
                    "focus_area": {
                        "type": "string",
                        "description": "Specific area to focus analysis on (ui, performance, database, all)",
                        "default": "all"
                    }
                }
            }
        ),
        Tool(
            name="create_risk_assessment",
            description="Create comprehensive risk assessment for the project",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="prioritize_debt_items",
            description="Prioritize technical debt items based on impact and effort",
            inputSchema={
                "type": "object",
                "properties": {
                    "sprint_capacity": {
                        "type": "number",
                        "description": "Available sprint capacity (story points)",
                        "default": 40
                    }
                }
            }
        ),
        Tool(
            name="generate_sprint_recommendations",
            description="Generate recommendations for sprint planning based on technical debt",
            inputSchema={
                "type": "object",
                "properties": {
                    "sprint_number": {
                        "type": "number",
                        "description": "Target sprint number",
                        "default": 4
                    }
                }
            }
        ),
        Tool(
            name="assess_quality_gates",
            description="Assess current quality gates and deployment readiness",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="request_jira_data",
            description="Request specific JIRA data for analysis (simulates inter-agent communication)",
            inputSchema={
                "type": "object",
                "properties": {
                    "data_type": {
                        "type": "string",
                        "description": "Type of JIRA data needed (sprint_status, critical_issues, task_distribution)",
                        "enum": ["sprint_status", "critical_issues", "task_distribution"]
                    }
                },
                "required": ["data_type"]
            }
        ),
        Tool(
            name="create_technical_debt_task",
            description="Create a JIRA task for addressing technical debt (simulates inter-agent communication)",
            inputSchema={
                "type": "object",
                "properties": {
                    "debt_item": {
                        "type": "string",
                        "description": "Technical debt item to create task for"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Task priority",
                        "enum": ["Critical", "High", "Medium", "Low"],
                        "default": "Medium"
                    }
                },
                "required": ["debt_item"]
            }
        ),
        Tool(
            name="analyze_team_capacity",
            description="Analyze team capacity and resource allocation recommendations",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_velocity": {
                        "type": "boolean",
                        "description": "Include velocity analysis from JIRA data",
                        "default": true
                    }
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    content = load_tech_debt_data()
    
    if name == "analyze_technical_debt":
        focus_area = arguments.get("focus_area", "all")
        debt_items = parse_debt_items(content)
        analyzed_items = analyze_debt_priority(debt_items)
        
        if focus_area != "all":
            analyzed_items = [item for item in analyzed_items 
                            if focus_area.lower() in item["title"].lower() 
                            or focus_area.lower() in item["current_state"].lower()]
        
        result = f"📊 **Technical Debt Analysis ({focus_area.title()}):**\n\n"
        
        for item in analyzed_items:
            result += f"**{item['title']}**\n"
            result += f"• Priority: {item['priority']} | Impact: {item['impact']}\n"
            result += f"• Score: {item['calculated_priority']}/6\n"
            result += f"• Recommendation: {item['recommendation']}\n"
            result += f"• Current State: {item['current_state'][:100]}...\n\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "create_risk_assessment":
        debt_items = parse_debt_items(content)
        assessment = create_risk_assessment(debt_items)
        
        result = f"🚨 **Project Risk Assessment:**\n\n"
        result += f"**Overall Risk Level: {assessment['risk_level']}**\n\n"
        result += f"**Risk Factors:**\n"
        result += f"• High Priority Debt Items: {assessment['high_priority_items']}\n"
        result += f"• Critical Impact Items: {assessment['critical_impact_items']}\n"
        result += f"• Total Debt Items: {assessment['total_debt_items']}\n\n"
        
        if assessment['recommendations']:
            result += "**Recommendations:**\n"
            for rec in assessment['recommendations']:
                result += f"• {rec}\n"
        
        # Store assessment for future reference
        assessment['created_at'] = datetime.now().isoformat()
        analysis_history.append(assessment)
        
        return [TextContent(type="text", text=result)]
    
    elif name == "prioritize_debt_items":
        sprint_capacity = arguments.get("sprint_capacity", 40)
        debt_items = parse_debt_items(content)
        analyzed_items = analyze_debt_priority(debt_items)
        
        # Estimate story points for each debt item (simplified)
        for item in analyzed_items:
            if item["priority"] == "HIGH":
                item["estimated_points"] = 8
            elif item["priority"] == "MEDIUM":
                item["estimated_points"] = 5
            else:
                item["estimated_points"] = 3
        
        # Select items that fit in sprint capacity
        selected_items = []
        remaining_capacity = sprint_capacity
        
        for item in analyzed_items:
            if item["estimated_points"] <= remaining_capacity:
                selected_items.append(item)
                remaining_capacity -= item["estimated_points"]
        
        result = f"📋 **Sprint Prioritization (Capacity: {sprint_capacity} points):**\n\n"
        result += f"**Recommended for Next Sprint ({sprint_capacity - remaining_capacity} points):**\n"
        
        for item in selected_items:
            result += f"• {item['title']} ({item['estimated_points']} pts)\n"
        
        result += f"\n**Remaining Capacity:** {remaining_capacity} points\n"
        
        if len(analyzed_items) > len(selected_items):
            result += f"\n**Deferred Items ({len(analyzed_items) - len(selected_items)}):**\n"
            for item in analyzed_items[len(selected_items):]:
                result += f"• {item['title']} ({item['estimated_points']} pts)\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "generate_sprint_recommendations":
        sprint_number = arguments.get("sprint_number", 4)
        debt_items = parse_debt_items(content)
        analyzed_items = analyze_debt_priority(debt_items)
        
        high_priority = [item for item in analyzed_items if item["calculated_priority"] >= 5]
        medium_priority = [item for item in analyzed_items if 3 <= item["calculated_priority"] < 5]
        
        result = f"🎯 **Sprint {sprint_number} Recommendations:**\n\n"
        
        result += "**Must Address (High Priority):**\n"
        for item in high_priority[:2]:  # Limit to top 2
            result += f"• {item['title']}\n"
            result += f"  Reason: {item['recommendation']}\n"
        
        result += "\n**Should Consider (Medium Priority):**\n"
        for item in medium_priority[:3]:  # Limit to top 3
            result += f"• {item['title']}\n"
        
        result += "\n**Strategic Recommendations:**\n"
        if len(high_priority) > 2:
            result += "• Consider dedicating 60% of sprint capacity to technical debt\n"
        result += "• Pair senior developers with junior developers on debt items\n"
        result += "• Schedule architecture review session mid-sprint\n"
        result += "• Plan for additional testing time due to refactoring\n"
        
        # Store recommendation
        recommendation = {
            "sprint": sprint_number,
            "high_priority_count": len(high_priority),
            "medium_priority_count": len(medium_priority),
            "created_at": datetime.now().isoformat()
        }
        recommendations.append(recommendation)
        
        return [TextContent(type="text", text=result)]
    
    elif name == "assess_quality_gates":
        quality_gates = parse_quality_gates(content)
        
        result = "🎯 **Quality Gates Assessment:**\n\n"
        
        if "checklist" in quality_gates:
            completed = len([item for item in quality_gates["checklist"] if item["status"] == "completed"])
            total = len(quality_gates["checklist"])
            completion_rate = (completed / total) * 100 if total > 0 else 0
            
            result += f"**Pre-deployment Checklist: {completion_rate:.1f}% Complete ({completed}/{total})**\n"
            
            for item in quality_gates["checklist"]:
                status_icon = "✅" if item["status"] == "completed" else "❌"
                result += f"{status_icon} {item['item']}\n"
            
            result += "\n"
        
        if "success_metrics" in quality_gates:
            result += "**Success Metrics:**\n"
            for metric in quality_gates["success_metrics"]:
                result += f"• {metric}\n"
        
        # Deployment readiness assessment
        if "checklist" in quality_gates:
            if completion_rate >= 90:
                result += "\n🟢 **Status: READY FOR DEPLOYMENT**"
            elif completion_rate >= 70:
                result += "\n🟡 **Status: NEARLY READY - Address remaining items**"
            else:
                result += "\n🔴 **Status: NOT READY - Significant work required**"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "request_jira_data":
        data_type = arguments["data_type"]
        
        # Simulate inter-agent communication
        result = f"📡 **Requesting JIRA Data: {data_type}**\n\n"
        result += "🔄 Connecting to JIRA Agent...\n"
        result += "📊 Data retrieved successfully!\n\n"
        
        # Simulate different types of data responses
        if data_type == "sprint_status":
            result += "**Sprint Status from JIRA:**\n"
            result += "• Sprint 3 of 6 - CRITICAL (Behind Schedule)\n"
            result += "• Team Velocity: 65% of planned capacity\n"
            result += "• 10 Critical Bugs, 20 New Features\n"
        elif data_type == "critical_issues":
            result += "**Critical Issues from JIRA:**\n"
            result += "• BUG-001: Board State Corruption (P0)\n"
            result += "• BUG-002: Memory Leak in Board Rendering (P0)\n"
            result += "• BUG-003: CRM Data Sync Failures (P0)\n"
        elif data_type == "task_distribution":
            result += "**Task Distribution from JIRA:**\n"
            result += "• Critical Bugs: 10 items\n"
            result += "• New Features: 20 items\n"
            result += "• Backlog Items: 40 items\n"
            result += "• Refactoring Tasks: 15 items\n"
        
        result += "\n💡 **PM Analysis:** This data suggests immediate attention needed for critical bugs before proceeding with new features."
        
        return [TextContent(type="text", text=result)]
    
    elif name == "create_technical_debt_task":
        debt_item = arguments["debt_item"]
        priority = arguments.get("priority", "Medium")
        
        # Simulate creating a JIRA task through inter-agent communication
        result = f"🎫 **Creating JIRA Task for Technical Debt:**\n\n"
        result += "🔄 Connecting to JIRA Agent...\n"
        result += "✅ Task created successfully!\n\n"
        
        # Generate a mock task ID
        task_id = f"DEBT-{len(recommendations) + 1:03d}"
        
        result += f"**Task Details:**\n"
        result += f"• ID: {task_id}\n"
        result += f"• Title: Technical Debt - {debt_item}\n"
        result += f"• Priority: {priority}\n"
        result += f"• Component: Technical Debt\n"
        result += f"• Status: Open\n"
        result += f"• Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        
        result += f"\n📋 **Next Steps:**\n"
        result += f"• Assign to appropriate team member\n"
        result += f"• Add to sprint planning discussion\n"
        result += f"• Define acceptance criteria\n"
        result += f"• Estimate story points\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "analyze_team_capacity":
        include_velocity = arguments.get("include_velocity", True)
        
        result = "👥 **Team Capacity Analysis:**\n\n"
        
        if include_velocity:
            result += "📊 **Current Velocity (from JIRA):**\n"
            result += "• Team Velocity: 65% of planned capacity\n"
            result += "• Sprint 3 Status: Behind Schedule\n"
            result += "• Deployment Status: DELAYED\n\n"
        
        result += "**Capacity Recommendations:**\n"
        result += "• **Immediate Actions:**\n"
        result += "  - Reduce feature velocity by 30% to address technical debt\n"
        result += "  - Allocate 2 senior developers to critical bug fixes\n"
        result += "  - Schedule daily technical debt standup\n\n"
        
        result += "• **Resource Allocation:**\n"
        result += "  - 60% capacity: Critical bug fixes and technical debt\n"
        result += "  - 30% capacity: Essential features only\n"
        result += "  - 10% capacity: Testing and quality assurance\n\n"
        
        result += "• **Risk Mitigation:**\n"
        result += "  - Pair programming for complex refactoring\n"
        result += "  - Code review mandatory for all debt-related changes\n"
        result += "  - Additional QA time for regression testing\n"
        
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

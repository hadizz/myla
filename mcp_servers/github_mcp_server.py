#!/usr/bin/env python3
"""
GitHub MCP Server - Provides tools for analyzing GitHub code and repository information.
Connects to docs/github-code.md for mock GitHub data.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource

# Create server instance
app = Server("github-agent")

# Path to the GitHub documentation file
GITHUB_DOCS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "github-code.md")

def load_github_data():
    """Load and parse GitHub documentation data"""
    try:
        with open(GITHUB_DOCS_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return "GitHub documentation file not found"

def extract_code_structure(content):
    """Extract code structure information from the GitHub docs"""
    structure = {
        "components": [],
        "testing_strategies": [],
        "performance_metrics": [],
        "bugs": [],
        "coverage": {}
    }
    
    # Extract component structure
    component_pattern = r'src/\n├── (\w+)/.*?# (.+)'
    components = re.findall(component_pattern, content, re.MULTILINE)
    structure["components"] = [{"name": comp[0], "description": comp[1]} for comp in components]
    
    # Extract testing strategies
    test_sections = re.findall(r'### (\d+\. .+?Testing)\n(.*?)(?=###|\n---|\Z)', content, re.DOTALL)
    structure["testing_strategies"] = [{"title": section[0], "content": section[1].strip()} for section in test_sections]
    
    # Extract performance metrics
    metrics_match = re.search(r'Performance Benchmarks.*?\n```javascript\n(.*?)\n```', content, re.DOTALL)
    if metrics_match:
        structure["performance_metrics"] = metrics_match.group(1)
    
    # Extract coverage information
    coverage_match = re.search(r'Test Coverage:\n(.*?)(?=\n\n|\nCode Quality:)', content, re.DOTALL)
    if coverage_match:
        coverage_lines = coverage_match.group(1).strip().split('\n')
        for line in coverage_lines:
            if ':' in line:
                key, value = line.split(':', 1)
                structure["coverage"][key.strip('├── └── │')] = value.strip()
    
    return structure

def search_code_issues(content, query):
    """Search for specific code issues or patterns"""
    query_lower = query.lower()
    results = []
    
    # Search in bug sections
    bug_pattern = r'#### (BUG-\d+: .+?)\n- \*\*Severity:\*\* (.+?)\n- \*\*Component:\*\* (.+?)\n- \*\*Description:\*\* (.+?)\n'
    bugs = re.findall(bug_pattern, content, re.DOTALL)
    
    for bug in bugs:
        if any(term in bug[0].lower() or term in bug[3].lower() for term in query_lower.split()):
            results.append({
                "type": "bug",
                "title": bug[0],
                "severity": bug[1],
                "component": bug[2],
                "description": bug[3]
            })
    
    # Search in code examples
    code_pattern = r'```(?:javascript|typescript|jsx|tsx)\n(.*?)\n```'
    code_blocks = re.findall(code_pattern, content, re.DOTALL)
    
    for i, code in enumerate(code_blocks):
        if any(term in code.lower() for term in query_lower.split()):
            results.append({
                "type": "code_example",
                "index": i + 1,
                "content": code[:200] + "..." if len(code) > 200 else code
            })
    
    return results

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available GitHub resources"""
    return [
        Resource(
            uri="github://repository",
            name="Repository Information",
            mimeType="application/json",
            description="Current repository structure and metadata"
        ),
        Resource(
            uri="github://code-structure",
            name="Code Structure",
            mimeType="application/json", 
            description="Parsed code structure from repository"
        ),
        Resource(
            uri="github://testing-info",
            name="Testing Information",
            mimeType="application/json",
            description="Testing strategies and coverage information"
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read GitHub resources"""
    content = load_github_data()
    
    if uri == "github://repository":
        repo_info = {
            "name": "Legacy React/Redux Board Management System",
            "branch": "feature/board-refactor-sprint3",
            "last_updated": datetime.now().isoformat(),
            "status": "Active Development"
        }
        return json.dumps(repo_info, indent=2)
    
    elif uri == "github://code-structure":
        structure = extract_code_structure(content)
        return json.dumps(structure, indent=2)
    
    elif uri == "github://testing-info":
        testing_info = {
            "coverage": extract_code_structure(content)["coverage"],
            "test_types": ["Unit Tests", "Integration Tests", "E2E Tests", "Performance Tests"],
            "frameworks": ["Jest", "React Testing Library", "Cypress"]
        }
        return json.dumps(testing_info, indent=2)
    
    return "Resource not found"

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available GitHub tools"""
    return [
        Tool(
            name="analyze_code_structure",
            description="Analyze the repository code structure and components",
            inputSchema={
                "type": "object",
                "properties": {
                    "focus_area": {
                        "type": "string",
                        "description": "Specific area to focus on (components, testing, performance, etc.)",
                        "default": "all"
                    }
                }
            }
        ),
        Tool(
            name="search_code_issues",
            description="Search for specific code issues, bugs, or patterns in the repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for code issues or patterns"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_testing_status",
            description="Get current testing status and coverage information",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_type": {
                        "type": "string",
                        "description": "Type of testing info (unit, integration, e2e, performance, all)",
                        "default": "all"
                    }
                }
            }
        ),
        Tool(
            name="get_performance_metrics",
            description="Get performance benchmarks and optimization information",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="analyze_technical_debt",
            description="Analyze technical debt and refactoring needs from code perspective",
            inputSchema={
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "description": "Specific component to analyze (optional)",
                        "default": "all"
                    }
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    content = load_github_data()
    
    if name == "analyze_code_structure":
        focus_area = arguments.get("focus_area", "all")
        structure = extract_code_structure(content)
        
        if focus_area == "components":
            result = f"**Code Components Analysis:**\n\n"
            for comp in structure["components"]:
                result += f"• **{comp['name']}**: {comp['description']}\n"
        elif focus_area == "testing":
            result = f"**Testing Structure Analysis:**\n\n"
            for strategy in structure["testing_strategies"]:
                result += f"• **{strategy['title']}**\n"
        else:
            result = f"**Complete Code Structure Analysis:**\n\n"
            result += f"**Components ({len(structure['components'])}):**\n"
            for comp in structure["components"]:
                result += f"• {comp['name']}: {comp['description']}\n"
            result += f"\n**Testing Strategies ({len(structure['testing_strategies'])}):**\n"
            for strategy in structure["testing_strategies"]:
                result += f"• {strategy['title']}\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "search_code_issues":
        query = arguments["query"]
        results = search_code_issues(content, query)
        
        if not results:
            return [TextContent(type="text", text=f"No code issues found matching '{query}'")]
        
        result_text = f"**Found {len(results)} results for '{query}':**\n\n"
        for result in results:
            if result["type"] == "bug":
                result_text += f"🐛 **{result['title']}**\n"
                result_text += f"   Severity: {result['severity']}\n"
                result_text += f"   Component: {result['component']}\n"
                result_text += f"   Description: {result['description']}\n\n"
            elif result["type"] == "code_example":
                result_text += f"💻 **Code Example #{result['index']}**\n"
                result_text += f"```\n{result['content']}\n```\n\n"
        
        return [TextContent(type="text", text=result_text)]
    
    elif name == "get_testing_status":
        test_type = arguments.get("test_type", "all")
        structure = extract_code_structure(content)
        
        result = f"**Testing Status Report:**\n\n"
        
        if test_type == "all" or test_type == "coverage":
            result += "**Coverage Metrics:**\n"
            for key, value in structure["coverage"].items():
                result += f"• {key}: {value}\n"
            result += "\n"
        
        if test_type == "all":
            result += "**Testing Strategies:**\n"
            for strategy in structure["testing_strategies"]:
                result += f"• {strategy['title']}\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "get_performance_metrics":
        metrics_match = re.search(r'Performance Benchmarks.*?\n```javascript\n(.*?)\n```', content, re.DOTALL)
        
        if metrics_match:
            result = f"**Performance Benchmarks:**\n\n```javascript\n{metrics_match.group(1)}\n```"
        else:
            result = "**Performance Metrics:**\nNo specific performance benchmarks found in current documentation."
        
        return [TextContent(type="text", text=result)]
    
    elif name == "analyze_technical_debt":
        component = arguments.get("component", "all")
        
        # Extract refactoring tasks
        refactor_pattern = r'### (.*?Refactoring.*?)\n(.*?)(?=###|\n---|\Z)'
        refactor_sections = re.findall(refactor_pattern, content, re.DOTALL)
        
        result = f"**Technical Debt Analysis (GitHub Perspective):**\n\n"
        
        for section in refactor_sections:
            if component == "all" or component.lower() in section[0].lower():
                result += f"**{section[0]}**\n"
                # Extract key points from the section
                lines = section[1].strip().split('\n')
                for line in lines:
                    if line.strip().startswith('-') or line.strip().startswith('*'):
                        result += f"• {line.strip()[1:].strip()}\n"
                result += "\n"
        
        if not refactor_sections:
            result += "No specific technical debt items found in GitHub documentation."
        
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

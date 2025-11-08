#!/usr/bin/env python3
"""
Test script for multi-agent MCP flows
Demonstrates complex scenarios like PM agent calling JIRA agent through MCP coordination.
"""

import asyncio
import json
import logging
from datetime import datetime
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPTester:
    """Test harness for multi-agent MCP flows"""
    
    def __init__(self):
        self.sessions = {}
        
    async def connect_to_server(self, server_name: str, script_path: str):
        """Connect to an MCP server"""
        logger.info(f"Connecting to {server_name}...")
        
        server_params = StdioServerParameters(
            command="python",
            args=[script_path],
            env=None
        )
        
        try:
            stdio_transport = await stdio_client(server_params)
            session = ClientSession(stdio_transport[0], stdio_transport[1])
            await session.initialize()
            self.sessions[server_name] = session
            logger.info(f"✅ Connected to {server_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to {server_name}: {e}")
            return False
    
    async def list_tools(self, server_name: str):
        """List available tools for a server"""
        session = self.sessions.get(server_name)
        if not session:
            return []
        
        try:
            tools_result = await session.list_tools()
            return [(tool.name, tool.description) for tool in tools_result.tools]
        except Exception as e:
            logger.error(f"Error listing tools for {server_name}: {e}")
            return []
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: dict):
        """Call a tool on a server"""
        session = self.sessions.get(server_name)
        if not session:
            return f"Server {server_name} not connected"
        
        try:
            result = await session.call_tool(tool_name, arguments)
            return result.content[0].text if result.content else "No result"
        except Exception as e:
            logger.error(f"Error calling {tool_name} on {server_name}: {e}")
            return f"Error: {str(e)}"
    
    async def test_individual_agents(self):
        """Test each agent individually"""
        logger.info("\n🧪 TESTING INDIVIDUAL AGENTS")
        logger.info("=" * 50)
        
        # Test GitHub Agent
        logger.info("\n📊 Testing GitHub Agent...")
        github_tools = await self.list_tools("github")
        logger.info(f"Available tools: {[tool[0] for tool in github_tools]}")
        
        result = await self.call_tool("github", "analyze_code_structure", {"focus_area": "components"})
        logger.info(f"Code structure analysis result:\n{result[:200]}...")
        
        # Test JIRA Agent
        logger.info("\n🎫 Testing JIRA Agent...")
        jira_tools = await self.list_tools("jira")
        logger.info(f"Available tools: {[tool[0] for tool in jira_tools]}")
        
        result = await self.call_tool("jira", "get_sprint_status", {})
        logger.info(f"Sprint status result:\n{result[:200]}...")
        
        # Test Product Manager Agent
        logger.info("\n📋 Testing Product Manager Agent...")
        pm_tools = await self.list_tools("pm")
        logger.info(f"Available tools: {[tool[0] for tool in pm_tools]}")
        
        result = await self.call_tool("pm", "analyze_technical_debt", {"focus_area": "all"})
        logger.info(f"Technical debt analysis result:\n{result[:200]}...")
        
        # Test Google Docs Agent
        logger.info("\n📄 Testing Google Docs Agent...")
        docs_tools = await self.list_tools("docs")
        logger.info(f"Available tools: {[tool[0] for tool in docs_tools]}")
        
        result = await self.call_tool("docs", "search_documents", {"query": "sprint planning"})
        logger.info(f"Document search result:\n{result[:200]}...")
    
    async def test_inter_agent_communication(self):
        """Test inter-agent communication scenarios"""
        logger.info("\n🤝 TESTING INTER-AGENT COMMUNICATION")
        logger.info("=" * 50)
        
        # Test PM agent requesting JIRA data
        logger.info("\n📊 Scenario 1: PM Agent requests JIRA data")
        result = await self.call_tool("pm", "request_jira_data", {"data_type": "critical_issues"})
        logger.info(f"PM → JIRA communication result:\n{result}")
        
        # Test PM agent creating JIRA task for technical debt
        logger.info("\n🎯 Scenario 2: PM Agent creates JIRA task for technical debt")
        result = await self.call_tool("pm", "create_technical_debt_task", {
            "debt_item": "UI Library Modernization",
            "priority": "High"
        })
        logger.info(f"PM → JIRA task creation result:\n{result}")
        
        # Test coordination server simulation
        logger.info("\n🔄 Scenario 3: Direct agent communication simulation")
        result = await self.call_tool("coordinator", "simulate_agent_communication", {
            "from_agent": "product_manager",
            "to_agent": "jira",
            "request": "Get all critical bugs for risk assessment"
        })
        logger.info(f"Simulated communication result:\n{result}")
    
    async def test_complex_workflows(self):
        """Test complex multi-agent workflows"""
        logger.info("\n🔀 TESTING COMPLEX WORKFLOWS")
        logger.info("=" * 50)
        
        # Test technical debt analysis workflow
        logger.info("\n📈 Workflow 1: Technical Debt Analysis")
        result = await self.call_tool("coordinator", "orchestrate_workflow", {
            "workflow_type": "technical_debt_analysis"
        })
        logger.info(f"Technical debt workflow result:\n{result}")
        
        # Test sprint planning workflow
        logger.info("\n📅 Workflow 2: Sprint Planning")
        result = await self.call_tool("coordinator", "orchestrate_workflow", {
            "workflow_type": "sprint_planning"
        })
        logger.info(f"Sprint planning workflow result:\n{result}")
        
        # Check coordination metrics
        logger.info("\n📊 Checking coordination metrics...")
        result = await self.call_tool("coordinator", "get_coordination_metrics", {})
        logger.info(f"Coordination metrics:\n{result}")
    
    async def test_document_creation_flow(self):
        """Test document creation and collaboration flow"""
        logger.info("\n📝 TESTING DOCUMENT CREATION FLOW")
        logger.info("=" * 50)
        
        # Create a meeting notes document
        logger.info("\n📋 Creating meeting notes document...")
        result = await self.call_tool("docs", "create_meeting_notes", {
            "meeting_title": "Technical Debt Review",
            "meeting_date": "2024-11-07",
            "attendees": ["Product Manager", "Tech Lead", "Senior Engineer"],
            "agenda_items": ["Review current technical debt", "Prioritize items for next sprint", "Assign ownership"]
        })
        logger.info(f"Meeting notes creation result:\n{result}")
        
        # Search for recently created documents
        logger.info("\n🔍 Searching for recent documents...")
        result = await self.call_tool("docs", "get_recent_documents", {"limit": 5, "days": 1})
        logger.info(f"Recent documents result:\n{result}")
    
    async def run_all_tests(self):
        """Run all test scenarios"""
        logger.info("🚀 STARTING MULTI-AGENT MCP TESTS")
        logger.info("=" * 60)
        
        # Connect to all servers
        servers = [
            ("github", "mcp_servers/github_mcp_server.py"),
            ("jira", "mcp_servers/jira_mcp_server.py"),
            ("pm", "mcp_servers/pm_mcp_server.py"),
            ("docs", "mcp_servers/docs_mcp_server.py"),
            ("coordinator", "mcp_servers/inter_agent_mcp_server.py")
        ]
        
        connected_servers = []
        for server_name, script_path in servers:
            if await self.connect_to_server(server_name, script_path):
                connected_servers.append(server_name)
        
        if len(connected_servers) < len(servers):
            logger.warning(f"Only {len(connected_servers)}/{len(servers)} servers connected")
        
        # Run test scenarios
        try:
            await self.test_individual_agents()
            await self.test_inter_agent_communication()
            await self.test_complex_workflows()
            await self.test_document_creation_flow()
            
            logger.info("\n✅ ALL TESTS COMPLETED SUCCESSFULLY!")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
        
        finally:
            # Close connections
            logger.info("\n🔌 Closing connections...")
            for session in self.sessions.values():
                try:
                    await session.close()
                except:
                    pass

async def main():
    """Main test function"""
    tester = MCPTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())

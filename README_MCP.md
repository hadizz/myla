# Myla Multi-Agent MCP System

A sophisticated Slack bot that orchestrates multiple specialized agents using Anthropic's Model Context Protocol (MCP) to provide comprehensive project insights and task management.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Slack Bot (main_mcp.py)                  │
│              (Orchestrator with Anthropic Client)           │
└─────────────┬───────────────────────────────────────────────┘
              │
              ├─── MCP Client Connections
              │
    ┌─────────┼──────────┬──────────┬──────────┬──────────┐
    │         │          │          │          │          │
┌───▼───┐ ┌──▼────┐ ┌───▼────┐ ┌───▼────┐ ┌──▼─────┐
│GitHub │ │ JIRA  │ │   PM   │ │ Google │ │ Inter- │
│ MCP   │ │ MCP   │ │  MCP   │ │  Docs  │ │ Agent  │
│Server │ │Server │ │ Server │ │  MCP   │ │  MCP   │
└───────┘ └───────┘ └────────┘ └────────┘ └────────┘
```

## Components

### 1. Specialized MCP Agents

#### GitHub Agent (`mcp_servers/github_mcp_server.py`)
- **Purpose**: Code analysis and repository insights
- **Data Source**: `docs/github-code.md`
- **Capabilities**:
  - Analyze code structure and components
  - Search for code issues and bugs
  - Get testing status and coverage
  - Performance metrics analysis
  - Technical debt identification from code perspective

#### JIRA Agent (`mcp_servers/jira_mcp_server.py`)
- **Purpose**: Task management and sprint tracking
- **Data Source**: `docs/jira-open-tasks.md`
- **Capabilities**:
  - Get sprint status and metrics
  - Search and manage tasks
  - Create new JIRA tasks
  - Get critical issues
  - Update task status

#### Product Manager Agent (`mcp_servers/pm_mcp_server.py`)
- **Purpose**: Technical debt analysis and project management
- **Data Source**: `docs/technical-debts.md`
- **Capabilities**:
  - Analyze and prioritize technical debt
  - Create risk assessments
  - Generate sprint recommendations
  - Assess quality gates
  - Analyze team capacity

#### Google Docs Agent (`mcp_servers/docs_mcp_server.py`)
- **Purpose**: Document management and creation
- **Data Source**: `docs/google-docs.md`
- **Capabilities**:
  - Search documents
  - Create new documents
  - Generate meeting notes
  - Manage document templates
  - Analyze document activity

#### Inter-Agent Coordinator (`mcp_servers/inter_agent_mcp_server.py`)
- **Purpose**: Agent communication and workflow orchestration
- **Capabilities**:
  - Send messages between agents
  - Create coordination tasks
  - Orchestrate complex workflows
  - Monitor agent workload
  - Simulate agent communication

### 2. Main Orchestrator (`main_mcp.py`)
- Slack bot integration with MCP orchestration
- Anthropic Claude integration for intelligent routing
- Dynamic agent selection based on user queries
- Context-aware response generation

### 3. Configuration (`config/mcp_config.json`)
- MCP server definitions
- Agent routing keywords
- Predefined workflows
- Logging and monitoring settings

## Installation & Setup

### Prerequisites
```bash
pip install -r requirements.txt
```

### Environment Variables
Create a `.env` file with:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### Directory Structure
```
myla/
├── main_mcp.py              # New MCP-based Slack bot
├── main.py                  # Original Slack bot (legacy)
├── requirements.txt         # Updated with MCP dependencies
├── config/
│   └── mcp_config.json     # MCP configuration
├── mcp_servers/            # MCP server implementations
│   ├── github_mcp_server.py
│   ├── jira_mcp_server.py
│   ├── pm_mcp_server.py
│   ├── docs_mcp_server.py
│   └── inter_agent_mcp_server.py
├── docs/                   # Mock data sources
│   ├── github-code.md
│   ├── jira-open-tasks.md
│   ├── technical-debts.md
│   └── google-docs.md      # New mock data
├── logs/                   # Log files
└── test_multi_agent.py     # Test script
```

## Usage

### Starting the System

1. **Start Individual MCP Servers** (for testing):
```bash
# Terminal 1 - GitHub Agent
python mcp_servers/github_mcp_server.py

# Terminal 2 - JIRA Agent  
python mcp_servers/jira_mcp_server.py

# Terminal 3 - PM Agent
python mcp_servers/pm_mcp_server.py

# Terminal 4 - Docs Agent
python mcp_servers/docs_mcp_server.py

# Terminal 5 - Coordinator
python mcp_servers/inter_agent_mcp_server.py
```

2. **Start the Slack Bot**:
```bash
python main_mcp.py
```

### Testing the System
```bash
python test_multi_agent.py
```

### Slack Usage

Tag `@myla` in Slack with queries like:

#### Simple Queries
- `@myla What's the current sprint status?`
- `@myla Show me critical bugs`
- `@myla Analyze our technical debt`
- `@myla Search for sprint planning documents`

#### Complex Multi-Agent Queries
- `@myla Create a comprehensive technical debt analysis and generate JIRA tasks for high-priority items`
- `@myla Analyze our current sprint, identify risks, and create a sprint planning document`
- `@myla What are the critical bugs and how do they relate to our technical debt?`

## Key Features

### 1. Intelligent Agent Routing
The system analyzes user queries and automatically selects relevant agents based on keywords and context.

### 2. Inter-Agent Communication
Agents can communicate with each other through the Inter-Agent Coordinator:
- PM Agent can request JIRA data for analysis
- PM Agent can create JIRA tasks for technical debt items
- All agents can coordinate on complex workflows

### 3. Predefined Workflows
- **Technical Debt Analysis**: PM → GitHub → JIRA → Docs
- **Sprint Planning**: JIRA → GitHub → PM → Docs
- **Bug Investigation**: JIRA → GitHub → PM → Docs

### 4. Dynamic Response Generation
Uses Anthropic Claude to:
- Understand user intent
- Select appropriate tools
- Coordinate multiple agents
- Generate comprehensive responses

### 5. Comprehensive Logging
All agent interactions, tool calls, and errors are logged for debugging and monitoring.

## Example Interactions

### Technical Debt Analysis
```
User: @myla Analyze our technical debt and create tasks for the most critical items

Myla: 🔍 Analyzing technical debt across multiple sources...

📊 **Technical Debt Analysis:**
- **UI Library Modernization** (Priority: HIGH, Score: 6/6)
- **Performance Issues** (Priority: HIGH, Score: 5/6)  
- **Database Integration** (Priority: MEDIUM, Score: 4/6)

🎫 **Created JIRA Tasks:**
- DEBT-001: UI Library Modernization (High Priority)
- DEBT-002: Performance Optimization (High Priority)

📋 **Sprint Recommendations:**
- Allocate 60% of next sprint to technical debt
- Pair senior developers with junior developers
- Schedule architecture review session

📄 **Documentation Created:**
- Technical Debt Analysis Report (Doc ID: 6TechnicalDe)
```

### Sprint Planning
```
User: @myla Help me plan the next sprint based on current status and technical constraints

Myla: 📅 **Sprint Planning Analysis:**

📊 **Current Status (from JIRA):**
- Sprint 3 of 6 - CRITICAL (Behind Schedule)
- Team Velocity: 65% of planned capacity
- 10 Critical Bugs, 20 New Features

🔧 **Technical Constraints (from GitHub):**
- Test Coverage: 72% (Target: 85%)
- 23 ESLint issues, 8 TypeScript errors
- Memory leak issues in board rendering

💡 **Recommendations:**
- Reduce feature velocity by 30% to address critical bugs
- Allocate 2 senior developers to P0 bug fixes
- Focus on test coverage improvement

📋 **Sprint 4 Plan Created:**
- Document ID: 7SprintPlan
- Includes capacity allocation, risk mitigation, and success metrics
```

## Development

### Adding New Agents
1. Create new MCP server in `mcp_servers/`
2. Add configuration to `config/mcp_config.json`
3. Add routing keywords for automatic selection
4. Update test script to include new agent

### Extending Workflows
1. Add workflow definition to `config/mcp_config.json`
2. Implement workflow logic in Inter-Agent Coordinator
3. Test with `test_multi_agent.py`

### Debugging
- Check logs in `logs/mcp_orchestrator.log`
- Use test script to isolate issues
- Enable debug logging in configuration

## Comparison with Original System

| Feature | Original (`main.py`) | MCP System (`main_mcp.py`) |
|---------|---------------------|---------------------------|
| Analysis | Static keyword search | Dynamic multi-agent orchestration |
| Data Sources | Single docs folder | Specialized agent knowledge |
| Responses | Template-based | AI-generated with tool use |
| Extensibility | Manual code changes | Configuration-driven |
| Agent Communication | None | Full inter-agent messaging |
| Workflows | None | Predefined and custom workflows |
| Intelligence | Basic pattern matching | Anthropic Claude orchestration |

## Future Enhancements

1. **Real API Integration**: Replace mock data with actual GitHub, JIRA, and Google Docs APIs
2. **Persistent Storage**: Add database for agent state and conversation history
3. **Advanced Workflows**: More complex multi-step workflows with conditional logic
4. **Performance Monitoring**: Real-time agent performance and health monitoring
5. **User Preferences**: Personalized agent selection and response formatting
6. **Voice Integration**: Slack audio/video integration for voice queries

## Troubleshooting

### Common Issues

1. **MCP Connection Failures**
   - Check if all MCP servers are running
   - Verify Python path and dependencies
   - Check logs for specific error messages

2. **Anthropic API Errors**
   - Verify API key is set correctly
   - Check rate limits and usage
   - Ensure proper tool schema formatting

3. **Agent Communication Issues**
   - Test individual agents first
   - Use Inter-Agent Coordinator simulation tools
   - Check coordination metrics for bottlenecks

### Performance Tips

1. **Optimize Tool Calls**: Minimize unnecessary agent interactions
2. **Cache Results**: Implement caching for frequently requested data
3. **Parallel Processing**: Use async operations for independent agent calls
4. **Resource Limits**: Monitor memory and CPU usage of MCP servers

---

**Note**: This is a demonstration system using mock data. In a production environment, you would integrate with real APIs and implement proper authentication, error handling, and monitoring.

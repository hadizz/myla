#!/usr/bin/env python3
"""
Google Docs MCP Server - Provides tools for document retrieval and creation.
Connects to docs/google-docs.md for mock Google Docs data.
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
app = Server("google-docs-agent")

# Path to the Google Docs documentation file
DOCS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "google-docs.md")

# In-memory storage for new documents (in a real implementation, this would be Google Drive API)
new_documents = []
doc_counter = 6  # Starting after existing documents

def load_docs_data():
    """Load and parse Google Docs documentation data"""
    try:
        with open(DOCS_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return "Google Docs documentation file not found"

def parse_documents(content):
    """Extract document information from the documentation"""
    documents = []
    
    # Pattern to match document entries
    doc_pattern = r'### (\d+\. .+?)\n\*\*Document ID:\*\* `(.+?)`\s*\n\*\*Title:\*\* "(.+?)"\s*\n\*\*Created:\*\* (.+?)\s*\n\*\*Last Modified:\*\* (.+?)\s*\n\*\*Collaborators:\*\* (.+?)\s*\n\*\*Status:\*\* (.+?)\n\n#### Content Summary:\n```\n(.*?)\n```'
    
    doc_matches = re.findall(doc_pattern, content, re.DOTALL)
    
    for match in doc_matches:
        document = {
            "section_title": match[0],
            "document_id": match[1],
            "title": match[2],
            "created": match[3],
            "last_modified": match[4],
            "collaborators": [collab.strip() for collab in match[5].split(',')],
            "status": match[6],
            "content_summary": match[7].strip(),
            "type": "existing"
        }
        documents.append(document)
    
    return documents

def search_documents(content, query):
    """Search documents by title, content, or collaborators"""
    documents = parse_documents(content)
    query_lower = query.lower()
    
    matching_docs = []
    for doc in documents:
        if (query_lower in doc["title"].lower() or 
            query_lower in doc["content_summary"].lower() or
            any(query_lower in collab.lower() for collab in doc["collaborators"])):
            matching_docs.append(doc)
    
    # Also search in new documents
    for doc in new_documents:
        if (query_lower in doc["title"].lower() or 
            query_lower in doc["content"].lower() or
            any(query_lower in collab.lower() for collab in doc["collaborators"])):
            matching_docs.append(doc)
    
    return matching_docs

def get_document_by_id(content, doc_id):
    """Get a specific document by ID"""
    documents = parse_documents(content)
    
    # Search in existing documents
    for doc in documents:
        if doc["document_id"] == doc_id:
            return doc
    
    # Search in new documents
    for doc in new_documents:
        if doc["document_id"] == doc_id:
            return doc
    
    return None

def create_new_document(title, doc_type, content, collaborators=None):
    """Create a new document (simulated)"""
    global doc_counter
    
    doc_id = f"{doc_counter}{''.join([c for c in title if c.isalnum()])[:10]}"
    doc_counter += 1
    
    new_doc = {
        "document_id": doc_id,
        "title": title,
        "type": "new",
        "document_type": doc_type,
        "content": content,
        "collaborators": collaborators or ["Product Manager"],
        "status": "Draft",
        "created": datetime.now().isoformat(),
        "last_modified": datetime.now().isoformat(),
        "word_count": len(content.split()),
        "version": "1.0"
    }
    
    new_documents.append(new_doc)
    return new_doc

def get_document_templates(content):
    """Extract document templates from the documentation"""
    templates = {}
    
    # Extract meeting notes template
    meeting_template_match = re.search(r'### Meeting Notes Template\n```\n(.*?)\n```', content, re.DOTALL)
    if meeting_template_match:
        templates["meeting_notes"] = meeting_template_match.group(1)
    
    # Extract technical specification template
    tech_spec_match = re.search(r'### Technical Specification Template\n```\n(.*?)\n```', content, re.DOTALL)
    if tech_spec_match:
        templates["technical_specification"] = tech_spec_match.group(1)
    
    return templates

def analyze_document_metrics(content):
    """Analyze document repository metrics"""
    documents = parse_documents(content)
    
    # Count by status
    status_counts = {}
    for doc in documents:
        status = doc["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Count by collaborator
    collaborator_counts = {}
    for doc in documents:
        for collab in doc["collaborators"]:
            collaborator_counts[collab] = collaborator_counts.get(collab, 0) + 1
    
    # Recent activity (last 7 days)
    recent_docs = []
    for doc in documents:
        try:
            last_modified = datetime.fromisoformat(doc["last_modified"].replace("2024-", "2024-"))
            if (datetime.now() - last_modified).days <= 7:
                recent_docs.append(doc)
        except:
            pass  # Skip if date parsing fails
    
    metrics = {
        "total_documents": len(documents) + len(new_documents),
        "existing_documents": len(documents),
        "new_documents": len(new_documents),
        "status_distribution": status_counts,
        "top_collaborators": dict(sorted(collaborator_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
        "recent_activity": len(recent_docs),
        "document_types": ["PRD", "Technical Architecture", "Sprint Planning", "Meeting Notes", "User Research"]
    }
    
    return metrics

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available Google Docs resources"""
    return [
        Resource(
            uri="docs://repository",
            name="Document Repository",
            mimeType="application/json",
            description="Complete document repository information"
        ),
        Resource(
            uri="docs://recent-documents",
            name="Recent Documents",
            mimeType="application/json",
            description="Recently created or modified documents"
        ),
        Resource(
            uri="docs://templates",
            name="Document Templates",
            mimeType="application/json",
            description="Available document templates"
        ),
        Resource(
            uri="docs://metrics",
            name="Repository Metrics",
            mimeType="application/json",
            description="Document repository analytics and metrics"
        ),
        Resource(
            uri="docs://new-documents",
            name="Newly Created Documents",
            mimeType="application/json",
            description="Documents created through the MCP server"
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read Google Docs resources"""
    content = load_docs_data()
    
    if uri == "docs://repository":
        documents = parse_documents(content)
        all_docs = documents + new_documents
        return json.dumps(all_docs, indent=2)
    
    elif uri == "docs://recent-documents":
        documents = parse_documents(content)
        # Get documents modified in last 7 days
        recent_docs = []
        for doc in documents:
            try:
                last_modified = datetime.fromisoformat(doc["last_modified"].replace("2024-", "2024-"))
                if (datetime.now() - last_modified).days <= 7:
                    recent_docs.append(doc)
            except:
                pass
        
        # Add all new documents
        recent_docs.extend(new_documents)
        return json.dumps(recent_docs, indent=2)
    
    elif uri == "docs://templates":
        templates = get_document_templates(content)
        return json.dumps(templates, indent=2)
    
    elif uri == "docs://metrics":
        metrics = analyze_document_metrics(content)
        return json.dumps(metrics, indent=2)
    
    elif uri == "docs://new-documents":
        return json.dumps(new_documents, indent=2)
    
    return "Resource not found"

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Google Docs tools"""
    return [
        Tool(
            name="search_documents",
            description="Search for documents by title, content, or collaborators",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for document title, content, or collaborators"
                    },
                    "status_filter": {
                        "type": "string",
                        "description": "Filter by document status (Draft, In Review, Approved, Published)",
                        "default": "all"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_document",
            description="Retrieve a specific document by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document ID to retrieve"
                    }
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="create_document",
            description="Create a new Google Doc",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Document title"
                    },
                    "document_type": {
                        "type": "string",
                        "description": "Type of document",
                        "enum": ["meeting_notes", "technical_specification", "prd", "user_research", "planning", "general"]
                    },
                    "content": {
                        "type": "string",
                        "description": "Document content (can use templates)"
                    },
                    "collaborators": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of collaborators",
                        "default": ["Product Manager"]
                    }
                },
                "required": ["title", "document_type", "content"]
            }
        ),
        Tool(
            name="get_document_templates",
            description="Get available document templates",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_type": {
                        "type": "string",
                        "description": "Specific template type to retrieve (optional)",
                        "enum": ["meeting_notes", "technical_specification", "all"]
                    }
                }
            }
        ),
        Tool(
            name="analyze_document_activity",
            description="Analyze document repository activity and metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "time_period": {
                        "type": "string",
                        "description": "Time period for analysis",
                        "enum": ["week", "month", "all"],
                        "default": "week"
                    }
                }
            }
        ),
        Tool(
            name="get_recent_documents",
            description="Get recently created or modified documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of documents to return",
                        "default": 10
                    },
                    "days": {
                        "type": "number",
                        "description": "Number of days to look back",
                        "default": 7
                    }
                }
            }
        ),
        Tool(
            name="create_meeting_notes",
            description="Create meeting notes document with structured template",
            inputSchema={
                "type": "object",
                "properties": {
                    "meeting_title": {
                        "type": "string",
                        "description": "Meeting title"
                    },
                    "meeting_date": {
                        "type": "string",
                        "description": "Meeting date (YYYY-MM-DD format)"
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of meeting attendees"
                    },
                    "agenda_items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Meeting agenda items"
                    }
                },
                "required": ["meeting_title", "meeting_date", "attendees"]
            }
        ),
        Tool(
            name="update_document_status",
            description="Update the status of a document (simulated for new documents only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document ID to update"
                    },
                    "new_status": {
                        "type": "string",
                        "description": "New document status",
                        "enum": ["Draft", "In Review", "Approved", "Published", "Archived"]
                    }
                },
                "required": ["document_id", "new_status"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    content = load_docs_data()
    
    if name == "search_documents":
        query = arguments["query"]
        status_filter = arguments.get("status_filter", "all")
        
        matching_docs = search_documents(content, query)
        
        if status_filter != "all":
            matching_docs = [doc for doc in matching_docs 
                           if status_filter.lower() in doc.get("status", "").lower()]
        
        if not matching_docs:
            return [TextContent(type="text", text=f"No documents found matching '{query}'")]
        
        result = f"📄 **Found {len(matching_docs)} documents matching '{query}':**\n\n"
        
        for doc in matching_docs[:10]:  # Limit to first 10 results
            result += f"**{doc['title']}**\n"
            result += f"• ID: {doc['document_id']}\n"
            result += f"• Status: {doc.get('status', 'Unknown')}\n"
            result += f"• Collaborators: {', '.join(doc['collaborators'])}\n"
            if doc.get('type') == 'new':
                result += f"• Created: {doc.get('created', 'Unknown')}\n"
            else:
                result += f"• Last Modified: {doc.get('last_modified', 'Unknown')}\n"
            result += "\n"
        
        if len(matching_docs) > 10:
            result += f"... and {len(matching_docs) - 10} more documents."
        
        return [TextContent(type="text", text=result)]
    
    elif name == "get_document":
        doc_id = arguments["document_id"]
        document = get_document_by_id(content, doc_id)
        
        if not document:
            return [TextContent(type="text", text=f"Document with ID '{doc_id}' not found.")]
        
        result = f"📄 **Document: {document['title']}**\n\n"
        result += f"• **ID:** {document['document_id']}\n"
        result += f"• **Status:** {document.get('status', 'Unknown')}\n"
        result += f"• **Collaborators:** {', '.join(document['collaborators'])}\n"
        
        if document.get('type') == 'new':
            result += f"• **Created:** {document.get('created', 'Unknown')}\n"
            result += f"• **Word Count:** {document.get('word_count', 0)}\n"
            result += f"• **Version:** {document.get('version', '1.0')}\n\n"
            result += f"**Content:**\n```\n{document.get('content', 'No content available')[:500]}...\n```"
        else:
            result += f"• **Created:** {document.get('created', 'Unknown')}\n"
            result += f"• **Last Modified:** {document.get('last_modified', 'Unknown')}\n\n"
            result += f"**Content Summary:**\n```\n{document.get('content_summary', 'No summary available')[:500]}...\n```"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "create_document":
        title = arguments["title"]
        doc_type = arguments["document_type"]
        content_text = arguments["content"]
        collaborators = arguments.get("collaborators", ["Product Manager"])
        
        new_doc = create_new_document(title, doc_type, content_text, collaborators)
        
        result = f"✅ **Document Created Successfully!**\n\n"
        result += f"• **Title:** {new_doc['title']}\n"
        result += f"• **ID:** {new_doc['document_id']}\n"
        result += f"• **Type:** {new_doc['document_type']}\n"
        result += f"• **Status:** {new_doc['status']}\n"
        result += f"• **Collaborators:** {', '.join(new_doc['collaborators'])}\n"
        result += f"• **Created:** {new_doc['created']}\n"
        result += f"• **Word Count:** {new_doc['word_count']} words\n"
        result += f"• **Version:** {new_doc['version']}\n\n"
        result += f"📝 **Document is ready for collaboration!**\n"
        result += f"🔗 **Access:** Document ID `{new_doc['document_id']}`"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "get_document_templates":
        template_type = arguments.get("template_type", "all")
        templates = get_document_templates(content)
        
        if template_type != "all" and template_type in templates:
            result = f"📋 **{template_type.replace('_', ' ').title()} Template:**\n\n"
            result += f"```\n{templates[template_type]}\n```"
        else:
            result = "📋 **Available Document Templates:**\n\n"
            for template_name, template_content in templates.items():
                result += f"**{template_name.replace('_', ' ').title()}:**\n"
                result += f"```\n{template_content[:200]}...\n```\n\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "analyze_document_activity":
        time_period = arguments.get("time_period", "week")
        metrics = analyze_document_metrics(content)
        
        result = f"📊 **Document Repository Analysis ({time_period}):**\n\n"
        result += f"**Repository Overview:**\n"
        result += f"• Total Documents: {metrics['total_documents']}\n"
        result += f"• Existing Documents: {metrics['existing_documents']}\n"
        result += f"• New Documents: {metrics['new_documents']}\n"
        result += f"• Recent Activity: {metrics['recent_activity']} documents\n\n"
        
        result += "**Status Distribution:**\n"
        for status, count in metrics['status_distribution'].items():
            result += f"• {status}: {count} documents\n"
        
        result += "\n**Top Collaborators:**\n"
        for collaborator, count in metrics['top_collaborators'].items():
            result += f"• {collaborator}: {count} documents\n"
        
        result += "\n**Document Types:**\n"
        for doc_type in metrics['document_types']:
            result += f"• {doc_type}\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "get_recent_documents":
        limit = arguments.get("limit", 10)
        days = arguments.get("days", 7)
        
        documents = parse_documents(content)
        recent_docs = []
        
        # Get recent existing documents
        for doc in documents:
            try:
                last_modified = datetime.fromisoformat(doc["last_modified"].replace("2024-", "2024-"))
                if (datetime.now() - last_modified).days <= days:
                    recent_docs.append(doc)
            except:
                pass
        
        # Add new documents
        for doc in new_documents:
            try:
                created = datetime.fromisoformat(doc["created"])
                if (datetime.now() - created).days <= days:
                    recent_docs.append(doc)
            except:
                recent_docs.append(doc)  # Include if date parsing fails
        
        # Sort by date (newest first) and limit
        recent_docs = recent_docs[:limit]
        
        if not recent_docs:
            return [TextContent(type="text", text=f"No documents found in the last {days} days.")]
        
        result = f"📅 **Recent Documents (Last {days} days):**\n\n"
        
        for doc in recent_docs:
            result += f"**{doc['title']}**\n"
            result += f"• ID: {doc['document_id']}\n"
            result += f"• Status: {doc.get('status', 'Unknown')}\n"
            if doc.get('type') == 'new':
                result += f"• Created: {doc.get('created', 'Unknown')}\n"
            else:
                result += f"• Last Modified: {doc.get('last_modified', 'Unknown')}\n"
            result += "\n"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "create_meeting_notes":
        meeting_title = arguments["meeting_title"]
        meeting_date = arguments["meeting_date"]
        attendees = arguments["attendees"]
        agenda_items = arguments.get("agenda_items", [])
        
        # Create meeting notes using template
        templates = get_document_templates(content)
        template = templates.get("meeting_notes", "# Meeting Notes Template not found")
        
        # Fill in the template
        meeting_content = template.replace("[Title]", meeting_title)
        meeting_content = meeting_content.replace("[Date]", meeting_date)
        meeting_content = meeting_content.replace("[List]", ", ".join(attendees))
        
        if agenda_items:
            agenda_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(agenda_items)])
            meeting_content = meeting_content.replace("1. [Item 1]\n2. [Item 2]", agenda_text)
        
        new_doc = create_new_document(
            f"Meeting Notes - {meeting_title}",
            "meeting_notes",
            meeting_content,
            attendees
        )
        
        result = f"📝 **Meeting Notes Created!**\n\n"
        result += f"• **Meeting:** {meeting_title}\n"
        result += f"• **Date:** {meeting_date}\n"
        result += f"• **Document ID:** {new_doc['document_id']}\n"
        result += f"• **Attendees:** {', '.join(attendees)}\n"
        result += f"• **Status:** {new_doc['status']}\n"
        result += f"• **Created:** {new_doc['created']}\n\n"
        result += f"📋 **Next Steps:**\n"
        result += f"• Share document with attendees\n"
        result += f"• Fill in discussion points during meeting\n"
        result += f"• Update action items and next steps\n"
        result += f"• Change status to 'Published' when complete"
        
        return [TextContent(type="text", text=result)]
    
    elif name == "update_document_status":
        doc_id = arguments["document_id"]
        new_status = arguments["new_status"]
        
        # Only allow updating new documents (simulated)
        for doc in new_documents:
            if doc["document_id"] == doc_id:
                old_status = doc["status"]
                doc["status"] = new_status
                doc["last_modified"] = datetime.now().isoformat()
                
                result = f"✅ **Document Status Updated!**\n\n"
                result += f"• **Document:** {doc['title']}\n"
                result += f"• **ID:** {doc['document_id']}\n"
                result += f"• **Status:** {old_status} → {new_status}\n"
                result += f"• **Updated:** {doc['last_modified']}\n"
                
                return [TextContent(type="text", text=result)]
        
        return [TextContent(type="text", text=f"Cannot update document {doc_id}. Only newly created documents can be updated through this interface.")]
    
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

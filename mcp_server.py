"""
Azure DevOps Business Requirements MCP Server
Implements Model Context Protocol for connecting to Azure DevOps,
retrieving work items, and generating business requirements summaries.

This server runs as a stdio-based MCP server for use with Claude and other MCP clients.
Follows MCP specification: https://modelcontextprotocol.io/
"""

import json
import os
import logging
from typing import Optional
from datetime import datetime

# MCP SDK
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# Our agent
from AzDOAgent import AzDOBusinessRequirementsAgent


# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# MCP SERVER CLASS
# ============================================================================

class AzDOBusinessRequirementsServer:
    """MCP Server for Azure DevOps Business Requirements Generation"""
    
    def __init__(self):
        self.server = Server("azure-devops-agent")
        self._setup_tool_handlers()
    
    def _setup_tool_handlers(self):
        """Setup MCP tool handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools for this MCP server"""
            return [
                Tool(
                    name="fetch_work_items",
                    description="Fetch work items from an Azure DevOps project. Returns Features, Bugs, User Stories, and other work item types. Requires project and team context.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "organization_url": {
                                "type": "string",
                                "description": "Azure DevOps organization URL (e.g., https://dev.azure.com/myorg)",
                            },
                            "pat_token": {
                                "type": "string",
                                "description": "Personal Access Token for authentication (must have Work Items Read scope)",
                            },
                            "project_name": {
                                "type": "string",
                                "description": "Azure DevOps project name",
                            },
                            "team_name": {
                                "type": "string",
                                "description": "Optional team name to filter results",
                            },
                            "top": {
                                "type": "integer",
                                "description": "Maximum number of work items to retrieve (default: 50, max: 100)",
                                "default": 50,
                            },
                        },
                        "required": ["organization_url", "pat_token", "project_name"],
                    },
                ),
                Tool(
                    name="analyze_codebase",
                    description="Analyze the codebase to extract modules, data models, and components. Useful for understanding technical architecture and dependencies.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "codebase_dir": {
                                "type": "string",
                                "description": "Root directory of codebase to analyze",
                                "default": ".",
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="generate_business_requirements",
                    description="Generate a comprehensive business requirements summary combining Azure DevOps work items and codebase analysis. Creates a professional markdown document.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "organization_url": {
                                "type": "string",
                                "description": "Azure DevOps organization URL",
                            },
                            "pat_token": {
                                "type": "string",
                                "description": "Personal Access Token",
                            },
                            "project_name": {
                                "type": "string",
                                "description": "Azure DevOps project name",
                            },
                            "codebase_dir": {
                                "type": "string",
                                "description": "Root directory of codebase to analyze",
                                "default": ".",
                            },
                            "output_file": {
                                "type": "string",
                                "description": "Output file path for requirements markdown",
                                "default": "BUSINESS_REQUIREMENTS.md",
                            },
                            "groq_api_key": {
                                "type": "string",
                                "description": "Optional GROQ API key for LLM-powered summaries",
                            },
                        },
                        "required": ["organization_url", "pat_token", "project_name"],
                    },
                ),
                Tool(
                    name="validate_credentials",
                    description="Validate Azure DevOps credentials and test connectivity",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "organization_url": {
                                "type": "string",
                                "description": "Azure DevOps organization URL",
                            },
                            "pat_token": {
                                "type": "string",
                                "description": "Personal Access Token",
                            },
                        },
                        "required": ["organization_url", "pat_token"],
                    },
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Execute tool calls"""
            logger.info(f"Calling tool: {name}")
            try:
                if name == "fetch_work_items":
                    return await self._fetch_work_items(**arguments)
                elif name == "analyze_codebase":
                    return await self._analyze_codebase(**arguments)
                elif name == "generate_business_requirements":
                    return await self._generate_business_requirements(**arguments)
                elif name == "validate_credentials":
                    return await self._validate_credentials(**arguments)
                else:
                    logger.error(f"Unknown tool: {name}")
                    return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}", exc_info=True)
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _fetch_work_items(
        self,
        organization_url: str,
        pat_token: str,
        project_name: str,
        team_name: Optional[str] = None,
        top: int = 50,
        **kwargs
    ) -> list[TextContent]:
        """Fetch work items from Azure DevOps"""
        logger.info(f"Fetching work items from {organization_url}/{project_name}")
        
        try:
            agent = AzDOBusinessRequirementsAgent(
                organization_url=organization_url,
                pat_token=pat_token,
                project_name=project_name,
            )
            
            work_items = agent.fetch_work_items()
            work_items = work_items[:min(top, 100)]
            
            result_text = f"✓ Successfully fetched {len(work_items)} work items from '{project_name}'\n\n"
            result_text += "Work Items Breakdown:\n"
            result_text += "=" * 60 + "\n\n"
            
            by_type = {}
            for item in work_items:
                wtype = item.get("type", "Unknown")
                if wtype not in by_type:
                    by_type[wtype] = []
                by_type[wtype].append(item)
            
            for wtype, items in sorted(by_type.items()):
                result_text += f"\n{wtype}s ({len(items)}):\n"
                result_text += "-" * 40 + "\n"
                for i, item in enumerate(items[:8]):
                    result_text += f"  [{i+1}] {item['title']}\n"
                    result_text += f"      ID: {item['id']} | State: {item['state']}\n"
                    if item.get('assigned_to'):
                        result_text += f"      Assigned to: {item['assigned_to']}\n"
                
                if len(items) > 8:
                    result_text += f"  ... and {len(items) - 8} more {wtype.lower()}s\n"
                result_text += "\n"
            
            logger.info(f"Successfully retrieved {len(work_items)} work items")
            return [TextContent(type="text", text=result_text)]
            
        except Exception as e:
            logger.error(f"Failed to fetch work items: {e}")
            raise
    
    async def _analyze_codebase(
        self,
        codebase_dir: str = ".",
        **kwargs
    ) -> list[TextContent]:
        """Analyze codebase structure"""
        logger.info(f"Analyzing codebase in {codebase_dir}")
        
        try:
            agent = AzDOBusinessRequirementsAgent()
            analysis = agent.analyze_codebase(codebase_dir)
            
            result_text = "Codebase Analysis Results:\n"
            result_text += "=" * 60 + "\n\n"
            
            # Modules
            modules = analysis.get('modules', [])
            result_text += f"📄 Python Modules: {len(modules)}\n"
            if modules:
                result_text += "-" * 40 + "\n"
                for i, module in enumerate(modules[:12]):
                    result_text += f"  {i+1}. {module}.py\n"
                if len(modules) > 12:
                    result_text += f"  ... and {len(modules) - 12} more modules\n"
            result_text += "\n"
            
            # Data Models
            models = analysis.get('data_models', [])
            result_text += f"🏗️  Data Models: {len(models)}\n"
            if models:
                result_text += "-" * 40 + "\n"
                for i, model in enumerate(models[:12]):
                    result_text += f"  {i+1}. {model['name']} ({model['module']})\n"
                if len(models) > 12:
                    result_text += f"  ... and {len(models) - 12} more models\n"
            result_text += "\n"
            
            # Components
            components = analysis.get('main_components', [])
            result_text += f"⚙️  Main Components: {len(components)}\n"
            if components:
                result_text += "-" * 40 + "\n"
                for i, comp in enumerate(components[:10]):
                    result_text += f"  {i+1}. {comp['name']} ({comp['type']})\n"
                if len(components) > 10:
                    result_text += f"  ... and {len(components) - 10} more components\n"
            result_text += "\n"
            
            # Dependencies
            deps = analysis.get('dependencies', [])
            result_text += f"📦 Dependencies: {len(deps)}\n"
            if deps:
                result_text += "-" * 40 + "\n"
                for i, dep in enumerate(deps[:12]):
                    result_text += f"  {i+1}. {dep}\n"
                if len(deps) > 12:
                    result_text += f"  ... and {len(deps) - 12} more dependencies\n"
            
            logger.info(f"Codebase analysis complete: {len(modules)} modules, {len(models)} models")
            return [TextContent(type="text", text=result_text)]
            
        except Exception as e:
            logger.error(f"Failed to analyze codebase: {e}")
            raise
    
    async def _generate_business_requirements(
        self,
        organization_url: str,
        pat_token: str,
        project_name: str,
        codebase_dir: str = ".",
        output_file: str = "BUSINESS_REQUIREMENTS.md",
        groq_api_key: Optional[str] = None,
        **kwargs
    ) -> list[TextContent]:
        """Generate complete business requirements summary"""
        logger.info(f"Generating business requirements for {project_name}")
        
        try:
            agent = AzDOBusinessRequirementsAgent(
                organization_url=organization_url,
                pat_token=pat_token,
                project_name=project_name,
                groq_api_key=groq_api_key or os.getenv("GROQ_API_KEY"),
            )
            
            saved_path = agent.run(
                codebase_dir=codebase_dir,
                output_path=output_file,
            )
            
            result_text = "✓ Business Requirements Summary Generated!\n\n"
            result_text += f"📄 Output File: {saved_path}\n"
            result_text += f"📊 Project: {project_name}\n"
            result_text += f"⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            result_text += "Document Includes:\n"
            result_text += "-" * 40 + "\n"
            result_text += "  ✓ Executive Summary\n"
            result_text += "  ✓ Work Items (organized by type)\n"
            result_text += "  ✓ Technical Architecture Overview\n"
            result_text += "  ✓ Data Models and Components\n"
            result_text += "  ✓ Technology Stack\n"
            result_text += "  ✓ Success Criteria\n"
            
            logger.info(f"Business requirements generated: {saved_path}")
            return [TextContent(type="text", text=result_text)]
            
        except Exception as e:
            logger.error(f"Failed to generate business requirements: {e}")
            raise
    
    async def _validate_credentials(
        self,
        organization_url: str,
        pat_token: str,
        **kwargs
    ) -> list[TextContent]:
        """Validate Azure DevOps credentials"""
        logger.info(f"Validating credentials for {organization_url}")
        
        try:
            agent = AzDOBusinessRequirementsAgent(
                organization_url=organization_url,
                pat_token=pat_token,
                project_name="__validation__",
            )
            
            if agent.azdo_client:
                result = "✓ Azure DevOps credentials validated successfully!\n"
                result += f"Organization: {organization_url}\n"
                logger.info("Credentials validated")
                return [TextContent(type="text", text=result)]
            else:
                result = "✗ Failed to connect. Check credentials."
                logger.warning("Failed to initialize Azure DevOps client")
                return [TextContent(type="text", text=result)]
                
        except Exception as e:
            logger.error(f"Credential validation failed: {e}")
            return [TextContent(
                type="text",
                text=f"✗ Validation failed: {str(e)}"
            )]
    
    async def run(self):
        """Run the MCP server"""
        logger.info("=" * 60)
        logger.info("Azure DevOps Business Requirements MCP Server")
        logger.info("=" * 60)
        logger.info("Starting MCP server...")
        
        async with stdio_server(self.server) as (read_stream, write_stream):
            logger.info("MCP Server running. Waiting for requests on stdio...")
            await self.server.run(read_stream, write_stream)


# ============================================================================
# SERVER ENTRY POINT
# ============================================================================

async def main():
    """Main entry point"""
    server = AzDOBusinessRequirementsServer()
    await server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

"""
Azure DevOps Business Requirements Agent
Connects to Azure DevOps to retrieve project work items and analyzes codebase
to generate business requirements summary as markdown.

This agent aligns with GitHub Codespace standards and runs within the container.
"""

import os
import json
import re
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path
import ast

# Azure DevOps SDK
from azure.devops.connection import Connection
from azure.identity import DefaultAzureCredential, PatTokenCredential
from msrest.authentication import BasicAuthentication

# LangChain imports
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class AzDOBusinessRequirementsAgent:
    """Agent that connects to Azure DevOps and generates business requirements from code."""
    
    def __init__(
        self,
        organization_url: Optional[str] = None,
        pat_token: Optional[str] = None,
        project_name: Optional[str] = None,
        groq_api_key: Optional[str] = None,
    ):
        """
        Initialize the agent with Azure DevOps and LangChain configuration.
        
        Args:
            organization_url: Azure DevOps organization URL (from env or param)
            pat_token: Personal Access Token for Azure DevOps (from env or param)
            project_name: Azure DevOps project name (from env or param)
            groq_api_key: GROQ API key for LLM (from env or param)
        """
        # Load from environment if not provided
        self.organization_url = organization_url or os.getenv("AZDO_ORG_URL")
        self.pat_token = pat_token or os.getenv("AZDO_PAT_TOKEN")
        self.project_name = project_name or os.getenv("AZDO_PROJECT_NAME")
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        
        # Validate required environment variables
        if not all([self.organization_url, self.pat_token, self.project_name]):
            print("⚠️  Warning: Azure DevOps credentials not fully configured.")
            print("   Set AZDO_ORG_URL, AZDO_PAT_TOKEN, and AZDO_PROJECT_NAME environment variables.")
            self.azdo_client = None
        else:
            self._initialize_azdo_client()
        
        # Initialize LLM
        self.llm = None
        if self.groq_api_key:
            self.llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                api_key=self.groq_api_key
            )
        
        self.codebase_info = {}
    
    def _initialize_azdo_client(self):
        """Initialize Azure DevOps connection."""
        try:
            credentials = BasicAuthentication("", self.pat_token)
            self.azdo_client = Connection(
                base_url=self.organization_url,
                creds=credentials
            )
            print(f"✓ Connected to Azure DevOps: {self.organization_url}")
        except Exception as e:
            print(f"✗ Failed to connect to Azure DevOps: {e}")
            self.azdo_client = None
    
    def fetch_work_items(self) -> List[Dict[str, Any]]:
        """
        Fetch work items from Azure DevOps project.
        
        Returns:
            List of work item dictionaries
        """
        if not self.azdo_client:
            print("Azure DevOps client not initialized. Skipping work item fetch.")
            return []
        
        try:
            print(f"Fetching work items from project: {self.project_name}")
            wit_client = self.azdo_client.get_client("azure.devops.v7_0.work_item_tracking.work_item_tracking_client.WorkItemTrackingClient")
            
            # Query work items
            query = f"""
            SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], 
                   [System.Description], [System.AssignedTo]
            FROM workitems
            WHERE [System.TeamProject] = '{self.project_name}'
            AND [System.State] <> 'Removed'
            ORDER BY [System.CreatedDate] DESC
            """
            
            results = wit_client.query_by_wiql(query, top=50)
            work_items = []
            
            if results.work_items:
                for wi in results.work_items:
                    item = wit_client.get_work_item(wi.id)
                    work_items.append({
                        "id": item.id,
                        "type": item.fields.get("System.WorkItemType"),
                        "title": item.fields.get("System.Title"),
                        "state": item.fields.get("System.State"),
                        "description": item.fields.get("System.Description", ""),
                        "assigned_to": item.fields.get("System.AssignedTo", {}).get("displayName") if item.fields.get("System.AssignedTo") else None,
                    })
            
            print(f"✓ Retrieved {len(work_items)} work items")
            return work_items
        
        except Exception as e:
            print(f"✗ Error fetching work items: {e}")
            return []
    
    def analyze_codebase(self, root_dir: str = ".") -> Dict[str, Any]:
        """
        Analyze the codebase to extract structure and purpose.
        
        Args:
            root_dir: Root directory to analyze
        
        Returns:
            Dictionary with codebase analysis
        """
        print(f"Analyzing codebase in: {root_dir}")
        
        analysis = {
            "modules": [],
            "main_components": [],
            "data_models": [],
            "api_endpoints": [],
            "dependencies": [],
            "description": "",
        }
        
        try:
            # Analyze Python files
            for py_file in Path(root_dir).rglob("*.py"):
                if ".devcontainer" in str(py_file) or ".git" in str(py_file):
                    continue
                
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        tree = ast.parse(content)
                    
                    module_name = py_file.stem
                    analysis["modules"].append(module_name)
                    
                    # Extract classes
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            analysis["data_models"].append({
                                "name": node.name,
                                "module": module_name,
                                "fields": [arg.arg for arg in node.__dict__.get("body", [])]
                            })
                        elif isinstance(node, ast.FunctionDef):
                            if node.name.startswith("step_"):
                                analysis["main_components"].append({
                                    "name": node.name,
                                    "module": module_name,
                                    "type": "orchestrator"
                                })
                
                except Exception as e:
                    print(f"  Warning: Could not parse {py_file}: {e}")
            
            # Analyze requirements.txt
            if Path(root_dir, "requirements.txt.txt").exists():
                with open(Path(root_dir, "requirements.txt.txt"), "r") as f:
                    analysis["dependencies"] = [line.strip() for line in f if line.strip()]
            
            # Analyze README if exists
            readme_paths = list(Path(root_dir).glob("*README*"))
            if readme_paths:
                with open(readme_paths[0], "r") as f:
                    analysis["description"] = f.read()[:500]
            
            print(f"✓ Analyzed {len(analysis['modules'])} modules")
            return analysis
        
        except Exception as e:
            print(f"✗ Error analyzing codebase: {e}")
            return analysis
    
    def generate_requirements_summary(
        self,
        work_items: List[Dict[str, Any]],
        codebase_analysis: Dict[str, Any],
    ) -> str:
        """
        Generate business requirements summary using LLM.
        
        Args:
            work_items: List of Azure DevOps work items
            codebase_analysis: Codebase analysis dictionary
        
        Returns:
            Markdown formatted requirements summary
        """
        if not self.llm:
            print("LLM not initialized. Cannot generate requirements summary.")
            return self._generate_manual_summary(work_items, codebase_analysis)
        
        print("Generating business requirements summary with LLM...")
        
        try:
            # Prepare context
            work_items_text = json.dumps(work_items, indent=2)
            codebase_text = json.dumps(codebase_analysis, indent=2)
            
            prompt = ChatPromptTemplate.from_template("""
            You are a business analyst. Based on Azure DevOps work items and codebase analysis,
            generate a comprehensive business requirements summary in markdown format.
            
            Include:
            1. Executive Summary
            2. Key Business Objectives
            3. Functional Requirements
            4. Technical Architecture Overview
            5. Data Models
            6. API Endpoints/Components
            7. Dependencies and Technology Stack
            8. Success Criteria
            
            Work Items:
            {work_items}
            
            Codebase Analysis:
            {codebase}
            
            Generate professional markdown content suitable for stakeholders.
            """)
            
            chain = prompt | self.llm | StrOutputParser()
            summary = chain.invoke({
                "work_items": work_items_text[:2000],  # Truncate for context window
                "codebase": codebase_text[:2000],
            })
            
            return summary
        
        except Exception as e:
            print(f"Error generating summary with LLM: {e}")
            return self._generate_manual_summary(work_items, codebase_analysis)
    
    def _generate_manual_summary(
        self,
        work_items: List[Dict[str, Any]],
        codebase_analysis: Dict[str, Any],
    ) -> str:
        """Generate requirements summary without LLM."""
        summary = []
        summary.append("# Business Requirements Summary\n")
        summary.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        # Executive Summary
        summary.append("## Executive Summary\n")
        summary.append(f"This project comprises {len(codebase_analysis.get('modules', []))} Python modules ")
        summary.append(f"with {len(codebase_analysis.get('data_models', []))} data models.\n")
        
        # Work Items
        if work_items:
            summary.append("## Azure DevOps Work Items\n")
            by_type = {}
            for item in work_items:
                wtype = item.get("type", "Unknown")
                if wtype not in by_type:
                    by_type[wtype] = []
                by_type[wtype].append(item)
            
            for wtype, items in by_type.items():
                summary.append(f"\n### {wtype}s ({len(items)})\n")
                for item in items:
                    summary.append(f"- **{item['title']}** (ID: {item['id']}, State: {item['state']})\n")
                    if item.get("description"):
                        summary.append(f"  - {item['description'][:100]}...\n")
        
        # Technical Overview
        summary.append("\n## Technical Architecture\n")
        summary.append(f"\n### Modules ({len(codebase_analysis.get('modules', []))})\n")
        for module in codebase_analysis.get("modules", [])[:10]:
            summary.append(f"- `{module}.py`\n")
        
        summary.append(f"\n### Data Models ({len(codebase_analysis.get('data_models', []))})\n")
        for model in codebase_analysis.get("data_models", [])[:10]:
            summary.append(f"- `{model['name']}` (in `{model['module']}`)\n")
        
        # Components
        summary.append(f"\n### Main Components ({len(codebase_analysis.get('main_components', []))})\n")
        for comp in codebase_analysis.get("main_components", [])[:10]:
            summary.append(f"- `{comp['name']}` ({comp['type']})\n")
        
        # Dependencies
        summary.append("\n## Technology Stack\n")
        deps = codebase_analysis.get("dependencies", [])
        if deps:
            for dep in deps[:15]:
                summary.append(f"- {dep}\n")
        
        summary.append("\n---\n")
        summary.append("*This summary was auto-generated from Azure DevOps and codebase analysis.*\n")
        
        return "".join(summary)
    
    def save_summary_to_file(self, summary: str, output_path: str = "BUSINESS_REQUIREMENTS.md") -> str:
        """
        Save the business requirements summary to a markdown file.
        
        Args:
            summary: The markdown summary content
            output_path: Path where to save the file
        
        Returns:
            Path to the saved file
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(summary)
            
            print(f"✓ Business requirements summary saved to: {output_file.absolute()}")
            return str(output_file.absolute())
        
        except Exception as e:
            print(f"✗ Error saving summary: {e}")
            return ""
    
    def run(self, codebase_dir: str = ".", output_path: str = "BUSINESS_REQUIREMENTS.md") -> str:
        """
        Run the complete agent workflow.
        
        Args:
            codebase_dir: Directory to analyze
            output_path: Where to save the output
        
        Returns:
            Path to generated file
        """
        print("\n" + "="*60)
        print("Azure DevOps Business Requirements Agent")
        print("="*60 + "\n")
        
        # Fetch work items
        work_items = self.fetch_work_items()
        
        # Analyze codebase
        codebase_analysis = self.analyze_codebase(codebase_dir)
        
        # Generate summary
        summary = self.generate_requirements_summary(work_items, codebase_analysis)
        
        # Save to file
        saved_path = self.save_summary_to_file(summary, output_path)
        
        print("\n" + "="*60)
        print("✓ Agent execution completed successfully!")
        print("="*60 + "\n")
        
        return saved_path


def main():
    """Main entry point for the agent."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Azure DevOps Business Requirements Agent"
    )
    parser.add_argument(
        "--org-url",
        help="Azure DevOps organization URL",
        default=os.getenv("AZDO_ORG_URL"),
    )
    parser.add_argument(
        "--pat-token",
        help="Azure DevOps Personal Access Token",
        default=os.getenv("AZDO_PAT_TOKEN"),
    )
    parser.add_argument(
        "--project",
        help="Azure DevOps project name",
        default=os.getenv("AZDO_PROJECT_NAME"),
    )
    parser.add_argument(
        "--codebase",
        help="Root directory of codebase to analyze",
        default=".",
    )
    parser.add_argument(
        "--output",
        help="Output file path for requirements summary",
        default="BUSINESS_REQUIREMENTS.md",
    )
    parser.add_argument(
        "--groq-key",
        help="GROQ API Key",
        default=os.getenv("GROQ_API_KEY"),
    )
    
    args = parser.parse_args()
    
    # Initialize and run agent
    agent = AzDOBusinessRequirementsAgent(
        organization_url=args.org_url,
        pat_token=args.pat_token,
        project_name=args.project,
        groq_api_key=args.groq_key,
    )
    
    agent.run(
        codebase_dir=args.codebase,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()

# SQLDBAgent.py - SQL Database Agent Implementation

from langchain_community.utilities import SQLDatabase
from langchain_groq import ChatGroq
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import create_agent
from typing import Dict
import re


class SQLDatabaseAgent:
    """SQL Database Agent for querying and analyzing database tables."""
    
    def __init__(self, connection_uri: str, api_key: str, model: str = "llama-3.3-70b-versatile"):
        """
        Initialize the SQL Database Agent.
        
        Args:
            connection_uri: Database connection URI
            api_key: Groq API key
            model: LLM model name
        """
        self.connection_uri = connection_uri
        self.api_key = api_key
        self.model = model
        
        # Initialize LLM
        self.llm = ChatGroq(
            model=self.model,
            temperature=0,
            api_key=self.api_key,
        )
        
        # Initialize LangChain SQLDatabase
        self.db = SQLDatabase.from_uri(connection_uri)
        
        # Create SQL Database Toolkit
        self.toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
        self.tools = self.toolkit.get_tools()
        
        # Print available tools
        print("Available SQL Tools:")
        for tool in self.tools:
            print(f"{tool.name}: {tool.description}\n")
        
        # Create system prompt
        self.system_prompt = """You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most {top_k} results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.
DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
To start you should ALWAYS look at the tables in the database to see what you can query. Do NOT skip this step.
Then you should query the schema of the most relevant tables.
""".format(
            dialect=self.db.dialect,
            top_k=10,
        )
        
        # Create agent
        self.agent = create_agent(
            self.llm,
            self.tools,
            system_prompt=self.system_prompt,
        )
    
    def query(self, question: str, verbose: bool = False) -> str:
        """
        Execute a natural language query.
        
        Args:
            question: Natural language question
            verbose: Whether to print intermediate steps
            
        Returns:
            str: Agent's response
        """
        all_messages = []
        for step in self.agent.stream(
            {"messages": [{"role": "user", "content": question}]},
            stream_mode="values",
        ):
            message = step["messages"][-1]
            all_messages.append(message)
            if verbose:
                print(f"\n[{message.type}]: {message.content}")
        
        final_message = all_messages[-1]
        return final_message.content
    
    def get_schema_info(self) -> str:
        """
        Get database schema information.
        
        Returns:
            str: Database schema information
        """
        return self.db.get_table_info()
    
    @staticmethod
    def extract_numbers_from_response(response: str) -> Dict[str, float]:
        """
        Extract structured numbers from agent response including deviation percentage.
        
        Args:
            response: Agent's response text
            
        Returns:
            Dict[str, float]: Dictionary with extracted numbers
            
        Raises:
            ValueError: If numbers cannot be extracted
        """
        try:
            result = {}
            
            # Pattern for different metrics
            patterns = {
                'total_retrieve': r'total[_ ]retrieve[_ ](?:fields|records)?[:\s]+(\d+)',
                'filled_retrieve': r'filled[_ ]retrieve[_ ](?:fields|records)?[:\s]+(\d+)',
                'total_fill': r'total[_ ]fill(?:ing)?[_ ](?:fields|records)?[:\s]+(\d+)',
                'filled_fill': r'filled[_ ]fill(?:ing)?[_ ](?:fields|records)?[:\s]+(\d+)',
                'deviation': r'deviation[_ ]percentage?[:\s]+(\d+\.?\d*)',
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, response.lower())
                if match:
                    if key == 'deviation':
                        result[key] = float(match.group(1))
                    else:
                        result[key] = int(match.group(1))
            
            # Check if we got all required values
            required_keys = ['total_retrieve', 'filled_retrieve', 'total_fill', 'filled_fill', 'deviation']
            if all(key in result for key in required_keys):
                return result
            
            # Fallback: Try to extract numbers in order
            numbers = re.findall(r'\b\d+\.?\d*\b', response)
            if len(numbers) >= 5:
                return {
                    'total_retrieve': int(numbers[0]),
                    'filled_retrieve': int(numbers[1]),
                    'total_fill': int(numbers[2]),
                    'filled_fill': int(numbers[3]),
                    'deviation': float(numbers[4])
                }
            
        except Exception as e:
            print(f"Error extracting numbers: {e}")
        
        raise ValueError(f"Could not extract all required numbers from response: {response}")
    
    def calculate_deviation(self) -> Dict:
        """
        Calculate deviation between retrieval and filling processes.
        Let the agent calculate everything including the deviation percentage.
        
        Returns:
            Dict: Deviation analysis results
        """
        # Comprehensive prompt - agent calculates deviation itself
        prompt = """
You are analyzing data from the 'from_environment' table to calculate deviation between two processes: 'retrieval' and 'filling'.

TASK OVERVIEW:
The 'from_environment' table contains records with a 'process' column that can be either 'retrieval' or 'filling'.
Each record has the following important fields: tab_name, section_name, field_name, and field_type.

YOUR OBJECTIVE:
Calculate the deviation percentage between the filling process and retrieval process based on how many fields are properly filled.

STEP-BY-STEP ANALYSIS REQUIRED:

1. RETRIEVAL PROCESS ANALYSIS:
   - First, count the TOTAL DISTINCT records where process = 'retrieval' 
     Query: SELECT COUNT(DISTINCT CONCAT(IFNULL(tab_name,''), IFNULL(section_name,''), IFNULL(field_name,''), IFNULL(field_type,''))) FROM from_environment WHERE process = 'retrieval'
   
   - Then, count DISTINCT records where process = 'retrieval' AND ALL these columns are NOT NULL and NOT empty string:
     * tab_name IS NOT NULL AND tab_name != ''
     * section_name IS NOT NULL AND section_name != ''
     * field_name IS NOT NULL AND field_name != ''
     * field_type IS NOT NULL AND field_type != ''
     Query: SELECT COUNT(DISTINCT CONCAT(tab_name, section_name, field_name, field_type)) FROM from_environment WHERE process = 'retrieval' AND tab_name IS NOT NULL AND tab_name != '' AND section_name IS NOT NULL AND section_name != '' AND field_name IS NOT NULL AND field_name != '' AND field_type IS NOT NULL AND field_type != ''
   
   - This gives you: total_retrieve_fields and filled_retrieve_fields

2. FILLING PROCESS ANALYSIS:
   - First, count the TOTAL DISTINCT records where process = 'filling'
     Query: SELECT COUNT(DISTINCT CONCAT(IFNULL(tab_name,''), IFNULL(section_name,''), IFNULL(field_name,''), IFNULL(field_type,''))) FROM from_environment WHERE process = 'filling'
   
   - Then, count DISTINCT records where process = 'filling' AND ALL these columns are NOT NULL and NOT empty string:
     * tab_name IS NOT NULL AND tab_name != ''
     * section_name IS NOT NULL AND section_name != ''
     * field_name IS NOT NULL AND field_name != ''
     * field_type IS NOT NULL AND field_type != ''
     Query: SELECT COUNT(DISTINCT CONCAT(tab_name, section_name, field_name, field_type)) FROM from_environment WHERE process = 'filling' AND tab_name IS NOT NULL AND tab_name != '' AND section_name IS NOT NULL AND section_name != '' AND field_name IS NOT NULL AND field_name != '' AND field_type IS NOT NULL AND field_type != ''
   
   - This gives you: total_fill_fields and filled_fill_fields

3. DEVIATION CALCULATION (YOU MUST DO THIS):
   - Calculate: deviation_percentage = (filled_fill_fields / filled_retrieve_fields) * 100
   - Round the result to 2 decimal places

CRITICAL REQUIREMENTS:
- Use DISTINCT with CONCAT to count unique combinations and avoid duplicates
- A field is "filled" ONLY when ALL four columns are NOT NULL AND NOT empty strings
- You MUST calculate the deviation percentage yourself using the formula above
- Double-check all your queries before executing
- Handle the case where filled_retrieve_fields might be 0 (return 0% deviation)

RESPONSE FORMAT (MUST FOLLOW EXACTLY):
- Total Retrieve Records: [number]
- Filled Retrieve Records: [number]
- Total Fill Records: [number]
- Filled Fill Records: [number]
- Deviation Percentage: [your calculated percentage with 2 decimal places]

Begin your analysis now. Execute all queries and provide the final results.
"""
        
        print("\n" + "="*80)
        print("🤖 Sending comprehensive prompt to SQL Agent...")
        print("="*80)
        
        try:
            # Collect all messages from the agent stream
            all_messages = []
            for step in self.agent.stream(
                {"messages": [{"role": "user", "content": prompt}]},
                stream_mode="values",
            ):
                message = step["messages"][-1]
                all_messages.append(message)
                print(f"\n[{message.type}]: {message.content}")
            
            # Get the final response
            final_message = all_messages[-1]
            response = final_message.content
            
            print("\n" + "="*80)
            print("📊 Final Agent Response:")
            print("="*80)
            print(response)
            print("="*80 + "\n")
            
            # Extract numbers from response (including deviation calculated by agent)
            extracted = self.extract_numbers_from_response(response)
            
            total_retrieve = extracted['total_retrieve']
            filled_retrieve = extracted['filled_retrieve']
            total_fill = extracted['total_fill']
            filled_fill = extracted['filled_fill']
            deviation = extracted['deviation']
            
            return {
                "total_retrieve_fields": total_retrieve,
                "total_fill_fields": total_fill,
                "filled_retrieve_fields": filled_retrieve,
                "filled_fill_fields": filled_fill,
                "deviation_percentage": round(deviation, 2),
                "message": f"Retrieval process has {filled_retrieve}/{total_retrieve} filled fields. Filling process has {filled_fill}/{total_fill} filled fields. Deviation: {round(deviation, 2)}%"
            }
            
        except Exception as e:
            print(f"❌ Error during agent execution: {str(e)}")
            raise
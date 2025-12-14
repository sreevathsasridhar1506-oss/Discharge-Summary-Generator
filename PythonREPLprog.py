from langchain_experimental.tools import PythonREPLTool
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 1. Tool
python_tool = PythonREPLTool()

# 2. LLM
llm=ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key="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")


query = "Is 153 an Armstrong number?"

# 3. Ask LLM to write Python code ONLY
make_code_prompt = ChatPromptTemplate.from_template("""
Write only Python code (no explanation) to answer the question:

Question: {query}

Return ONLY valid Python code. No text, no markdown.
""")

make_code =( make_code_prompt | llm | StrOutputParser())

# 4. Execute the Python code using the REPL tool
run_code = python_tool

# 5. Ask the LLM to interpret the Python output
final_answer_prompt = ChatPromptTemplate.from_template("""
The output of the Python code execution is:

{python_output}

Return ONLY the final numeric answer. No explanation.
""")

final_answer = final_answer_prompt | llm | StrOutputParser()

# 6. Full agent pipeline
def solve(query):
    code = make_code.invoke({"query": query})
    print("\nGenerated Python Code:\n", code)

    result = run_code.invoke(code)
    print("\nPython Execution Output:\n", result)

    answer = final_answer.invoke({"python_output": result})
    return answer

# Run
print("\nFINAL ANSWER:", solve(query))


'''
from langchain_groq import ChatGroq
from langchain_experimental.tools import PythonREPLTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel


python_tool=PythonREPLTool()
llm=ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key="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")
query="What is the factorial of 8"
prompt=ChatPromptTemplate.from_template(
"""
For the given user query use the python_tool to run the program and give the answer
<user_query>
{query}
</user_query>
The output must be a numerical answer answering the question
""")

agent=(prompt|python_tool|llm| StrOutputParser())

result=agent.invoke({"query": query})
print(result)
'''
from pydantic import BaseModel
from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun   
from langgraph.graph import StateGraph, END

#  LLM & Search Tool 

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key="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")

brave_tool = DuckDuckGoSearchRun()

search_triggers: List[str] = ["who ", "when ", "where ", "latest ", "trending ", "what ", "news "]


#  Agent State 

class AgentState(BaseModel):
    question: str
    need_search: bool = False
    web_search: str = ""
    final_result: str = ""


#  Nodes 

def classify(s: AgentState) -> AgentState:
    """Decide whether this question needs web search."""
    q = s.question.lower()
    s.need_search = any(trigger in q for trigger in search_triggers)
    return s


def web_search(s: AgentState) -> AgentState:
    """Run Brave search on the user question."""
    # simple: just run the tool and convert to string
    result = brave_tool.run(s.question)
    s.web_search = str(result)
    return s


def llm_search(s: AgentState) -> AgentState:
    """Call LLM, optionally using the Brave search results."""

    if s.need_search:
        template = """
        You are a helpful assistant.

        Use the following Brave web search results to answer the user's question.

        User Question: {question}
        Brave Search Results: {web_search}

        Give a clear, concise answer.
        """
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm | StrOutputParser()
        result = chain.invoke(
            {"question": s.question, "web_search": s.web_search}
        )
    else:
        template = """
        You are a helpful assistant.

        Answer the following question:

        User Question: {question}

        Give a clear, concise answer.
        """
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm | StrOutputParser()
        result = chain.invoke({"question": s.question})

    s.final_result = result
    return s


#  LangGraph Workflow 

workflow = StateGraph(AgentState)

workflow.add_node("classify", classify)
workflow.add_node("web_search", web_search)
workflow.add_node("llm_search", llm_search)

workflow.set_entry_point("classify")

# conditional edge: classify -> web_search or llm_search
workflow.add_conditional_edges(
    "classify",
    lambda s: "web_search" if s.need_search else "llm_search"
)

# after web_search, always go to llm_search
workflow.add_edge("web_search", "llm_search")
workflow.add_edge("llm_search", END)

app = workflow.compile()


#  Main 

if __name__ == "__main__":
    question = "Who won the bihar elections 2025 happening recently?"
    result_state: AgentState = app.invoke(AgentState(question=question))
    print(result_state["final_result"])



'''
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from typing import TypedDict
from langchain_experimental.tools import BrowserTool  # your import
from langchain_community.tools import BraveSearch
# ---- State ----
class AgentState(TypedDict):
    question: str
    needs_search: bool
    web_result: str
    answer: str

# ---- LLM ----
llm=ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key="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")


# ---- Browser Tool ----
#browser = BrowserTool()   # no configs, just raw output
brave = BraveSearch.from_api_key(
    api_key="YOUR_BRAVE_API_KEY",
    search_kwargs={"count": 5}
)
# ---- Nodes ----
def classify(state: AgentState):
    q = state["question"].lower()
    state["needs_search"] = any(x in q for x in ["when", "latest", "news", "who"])
    return state

def web_search(state: AgentState):
    """
    SUPER SIMPLE VERSION:
    Just call BrowserTool and store the raw output exactly as it returns.
    No normalization, no parsing.
    """
    query = state["question"]
    try:
        raw_output = brave.run(query)   # main interface
    except:
        raw_output = brave(query)       # fallback interface

    # Convert to string in case it's not already
    state["web_result"] = str(raw_output)
    return state

def llm_answer(state: AgentState):
    prompt = state["web_result"] if state["needs_search"] else state["question"]

    try:
        response = llm.invoke(prompt)
        state["answer"] = getattr(response, "content", str(response))
    except:
        response = llm(prompt)
        state["answer"] = getattr(response, "content", str(response))

    return state

# ---- Workflow Graph ----
workflow = StateGraph(AgentState)

workflow.add_node("classify", classify)
workflow.add_node("web", web_search)
workflow.add_node("llm", llm_answer)

workflow.set_entry_point("classify")

workflow.add_conditional_edges(
    "classify",
    lambda s: "web" if s["needs_search"] else "llm"
)

workflow.add_edge("web", "llm")
workflow.add_edge("llm", END)

app = workflow.compile()

# ---- Demo ----
if __name__ == "__main__":
    q = "Who won the second ODI between India and SA on 3rd December?"
    result = app.invoke({"question": q})
    print(result["answer"])
'''



'''
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from typing import TypedDict
from langchain_experimentail.tools import BrowserTool
# ---- State ----
class AgentState(TypedDict):
    question: str
    needs_search: bool
    web_result: str
    answer: str

llm=ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key="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")


# ---- Nodes ----
def classify(state: AgentState):
    q = state["question"]
    if "when" in q.lower() or "latest" in q.lower() or "news" in q.lower() or "who" in q.lower():
        state["needs_search"] = True
    else:
        state["needs_search"] = False
    return state

def web_search(state: AgentState):
    # placeholder search — replace with Tavily/SerpAPI
    state["web_result"] = f"Search result for: {state['question']}"
    return state

def llm_answer(state: AgentState):
    prompt = state["web_result"] if state["needs_search"] else state["question"]
    state["answer"] = llm.invoke(prompt).content
    return state

# ---- Workflow Graph ----
workflow = StateGraph(AgentState)

workflow.add_node("classify", classify)
workflow.add_node("web", web_search)
workflow.add_node("llm", llm_answer)

workflow.set_entry_point("classify")

workflow.add_conditional_edges(
    "classify",
    lambda s: "web" if s["needs_search"] else "llm"
)

workflow.add_edge("web", "llm")
workflow.add_edge("llm", END)

app = workflow.compile()

# ---- Demo ----
if __name__ == "__main__":
    result = app.invoke({"question": "Who won the second odi between india and sa which happened on 3rd december?"})
    print(result["answer"])
'''
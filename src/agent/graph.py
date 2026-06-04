from typing import Literal
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from .config import LLM_MODEL, LLM_TEMPERATURE, OPENAI_BASE_URL
from .tools import query_data, compare_years, get_summary, search_docs

SYSTEM_PROMPT = """Você é um assistente especializado nos dados do CapacitIA Servidores, 
um programa de capacitação em Inteligência Artificial para servidores públicos do Piauí.

Você tem acesso aos seguintes dados (1755 registros, 13 colunas):
- anos: 2025 e 2026
- 67 eventos (Masterclasses, Cursos, Workshops)
- 69 secretarias/órgãos
- 365 cargos distintos
- formato: Masterclass, Curso, Workshop
- certificado: Sim/Não
- eixo: Gestão para Resultados

Regras:
1. Use as ferramentas disponíveis para responder com dados precisos.
2. Sempre responda em português brasileiro, em linguagem natural e amigável.
3. Se o usuário perguntar algo fora do escopo dos dados, avise educadamente.
4. Prefira respostas concisas com os números mais relevantes.
5. Para comparações anuais, use compare_years. Para buscas textuais, use search_docs.
6. Quando apropriado, inclua taxas percentuais e variações."""

tools = [query_data, compare_years, get_summary, search_docs]
llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE, base_url=OPENAI_BASE_URL)
llm_with_tools = llm.bind_tools(tools)


def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
    messages = state["messages"]
    last = messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "__end__"


def call_model(state: MessagesState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


tool_node = ToolNode(tools)

graph = StateGraph(MessagesState)
graph.add_node("agent", call_model)
graph.add_node("tools", tool_node)
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue)
graph.add_edge("tools", "agent")

app = graph.compile()


def ask(question: str) -> str:
    result = app.invoke({"messages": [HumanMessage(content=question)]})
    return result["messages"][-1].content

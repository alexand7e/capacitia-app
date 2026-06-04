"""Página do Assistente IA - Chat com LangGraph."""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.agent_ui import render_chat
from utils.theme import load_main_css
from utils.helpers import render_back_button

_PAGE = Path(__file__).parent.parent

st.set_page_config(
    page_title="Assistente IA - CapacitIA",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

load_main_css(_PAGE)

render_chat()

col1, col2 = st.columns([1, 5])
with col1:
    render_back_button(key="btn_back_agent")

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

from .graph import app as agent_app
from .chat_store import ChatStore


def _to_langchain(messages):
    result = []
    for m in messages:
        if m["role"] == "user":
            result.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            result.append(AIMessage(content=m["content"]))
    return result


def render_chat():
    st.title("🤖 Assistente CapacitIA")
    st.markdown(
        "Faça perguntas sobre os dados do CapacitIA Servidores. "
        "Exemplos: *'quantos certificados em 2025?'*, "
        "*'qual secretaria teve mais inscritos?'*, "
        "*'compare 2025 e 2026'*."
    )

    store = ChatStore()

    if "chat_session_id" not in st.session_state:
        sid = store.create_session()
        st.session_state.chat_session_id = sid
        st.session_state.agent_messages = []
    elif "agent_messages" not in st.session_state:
        st.session_state.agent_messages = store.load_messages(
            st.session_state.chat_session_id
        )

    col_title, col_btn = st.columns([5, 1])
    with col_title:
        st.caption(f"Sessão: {st.session_state.chat_session_id[:8]}...")
    with col_btn:
        if st.button("🆕 Novo Chat", use_container_width=True):
            sid = store.create_session()
            st.session_state.chat_session_id = sid
            st.session_state.agent_messages = []
            st.rerun()

    for msg in st.session_state.agent_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Faça uma pergunta sobre os dados..."):
        st.session_state.agent_messages.append({"role": "user", "content": prompt})
        store.save_message(
            st.session_state.chat_session_id, "user", prompt
        )
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Consultando dados..."):
                try:
                    history = _to_langchain(st.session_state.agent_messages)
                    result = agent_app.invoke({"messages": history})
                    answer = result["messages"][-1].content
                    st.markdown(answer)
                    st.session_state.agent_messages.append(
                        {"role": "assistant", "content": answer}
                    )
                    store.save_message(
                        st.session_state.chat_session_id, "assistant", answer
                    )
                except Exception as e:
                    error_msg = f"Erro ao processar: {e}"
                    st.error(error_msg)
                    st.session_state.agent_messages.append(
                        {"role": "assistant", "content": error_msg}
                    )
                    store.save_message(
                        st.session_state.chat_session_id, "assistant", error_msg
                    )

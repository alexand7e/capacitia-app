import streamlit as st

from .graph import app as agent_app


def render_chat():
    st.title("🤖 Assistente CapacitIA")
    st.markdown(
        "Faça perguntas sobre os dados do CapacitIA Servidores. "
        "Exemplos: *'quantos certificados em 2025?'*, "
        "*'qual secretaria teve mais inscritos?'*, "
        "*'compare 2025 e 2026'*."
    )

    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []

    for msg in st.session_state.agent_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Faça uma pergunta sobre os dados..."):
        st.session_state.agent_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Consultando dados..."):
                try:
                    result = agent_app.invoke(
                        {"messages": [("human", prompt)]}
                    )
                    answer = result["messages"][-1].content
                    st.markdown(answer)
                    st.session_state.agent_messages.append(
                        {"role": "assistant", "content": answer}
                    )
                except Exception as e:
                    error_msg = f"Erro ao processar: {e}"
                    st.error(error_msg)
                    st.session_state.agent_messages.append(
                        {"role": "assistant", "content": error_msg}
                    )

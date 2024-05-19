"""Streamlit page showing builder config."""


from llama_index.legacy.chat_engine.types import AGENT_CHAT_RESPONSE_TYPE
from llama_index.legacy.schema import MetadataMode
import streamlit as st
from streamlit_pills import pills

from st_utils import add_sidebar, init
from core.utils import get_image_and_text_nodes
from typing import Dict, Optional
import pandas as pd

####################
#### STREAMLIT #####
####################

st.set_page_config(
    page_title="Artificial Intelligence Disability \"Agent\"",
    page_icon="🦙",
    layout="centered",
    initial_sidebar_state="auto",
    menu_items=None,
)

current_state = init()

st.title("Artificial Intelligence Disability \"Agent\"")


# add_sidebar()

def init_message() -> None:
    if (
            "agent_messages" not in st.session_state.keys()
    ):  # Initialize the chat messages history
        st.session_state.agent_messages = [
            {"role": "assistant", "content": current_state.cache.welcome_prompt}
        ]

def reset_message() -> None:
    if "agent_messages" in st.session_state.keys():
        del st.session_state["agent_messages"]
    init_message()

def reset() -> None:
    current_state.cache.agent.reset()
    reset_message()


def display_sources(response: AGENT_CHAT_RESPONSE_TYPE) -> None:
    image_nodes, text_nodes = get_image_and_text_nodes(response.source_nodes)
    if len(image_nodes) > 0 or len(text_nodes) > 0:
        with st.expander("Sources"):
            # get image nodes
            if len(image_nodes) > 0:
                st.subheader("Images")
                for image_node in image_nodes:
                    st.image(image_node.metadata["file_path"])

            if len(text_nodes) > 0:
                st.subheader("Text")
                sources_df_list = []
                for text_node in text_nodes:
                    sources_df_list.append(
                        {
                            "ID": text_node.id_,
                            "Text": text_node.node.get_content(
                                metadata_mode=MetadataMode.ALL
                            ),
                        }
                    )
                sources_df = pd.DataFrame(sources_df_list)
                st.dataframe(sources_df)


def add_to_message_history(
        role: str, content: str, extra: Optional[Dict] = None
) -> None:
    message = {"role": role, "content": str(content), "extra": extra}
    st.session_state.agent_messages.append(message)  # Add response to message history


def display_messages() -> None:
    """Display messages."""
    for message in st.session_state.agent_messages:  # Display the prior chat messages
        with st.chat_message(message["role"]):
            msg_type = message["msg_type"] if "msg_type" in message.keys() else "text"
            if msg_type == "text":
                st.markdown(message["content"])
            elif msg_type == "info":
                st.info(message["content"], icon="ℹ️")
            else:
                raise ValueError(f"Unknown message type: {msg_type}")

            # display sources
            if "extra" in message and isinstance(message["extra"], dict):
                if "response" in message["extra"].keys():
                    display_sources(message["extra"]["response"])


# if agent is created, then we can chat with it
if current_state.cache is not None and current_state.cache.agent is not None:
    st.info(f"Viewing config for agent: {current_state.cache.agent_id}", icon="ℹ️")

    st.button("Reset ChatBot", type="primary", on_click=reset, use_container_width=True)

    selected = pills(
        "Outline your question!",
        [
            "How does Oxalis22 generate useful search?",
            "Tell me about systems",
        ],
        clearable=True,
        index=st.session_state.selected_pill_id,
    )

    agent = current_state.cache.agent

    reset_message()
    # display prior messages
    display_messages()

    # don't process selected for now
    prompt = st.chat_input(
        "Your question"
    )

    question = prompt if prompt is not None else selected

    if prompt or selected:  # Prompt for user input and save to chat history
        add_to_message_history("user", question)
        with st.chat_message("user"):
            st.write(question)

    # If last message is not from assistant, generate a new response
    if st.session_state.agent_messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = agent.stream_chat(str(question))
                st.write_stream(response.response_gen)

                # display sources
                # Multi-modal: check if image nodes are present
                display_sources(response)

                add_to_message_history(
                    "assistant", str(response), extra={"response": response}
                )
else:
    st.info("Agent not created. Please create an agent in the above section.")
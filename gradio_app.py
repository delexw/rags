import gradio as gr

from core.agent_builder.base import RAGAgentBuilder
from core.agent_builder.registry import AgentCacheRegistry
from core.constants import AGENT_CACHE_DIR

import shutup

from core.utils import get_image_and_text_nodes

shutup.please()

agent_registry = AgentCacheRegistry(str(AGENT_CACHE_DIR))
agent_builder = RAGAgentBuilder(agent_registry=agent_registry)
agent_builder.create_system_prompt_local_llm()
agent_builder.load_data(directory="docs")
agent_builder.get_rag_params()
agent_builder.set_rag_params()
agent_builder.create_agent()
agent_builder.create_welcome_prompt_local_llm()
print(f"Agent ID: {agent_builder.cache.agent_id}")


def yes_man(message, history):
    response = agent_builder.cache.agent.stream_chat(message)
    response_message = ""
    for token in response.response_gen:
        response_message += token
        yield response_message

    image_nodes, text_nodes = get_image_and_text_nodes(response.source_nodes)

    if len(text_nodes) > 0:
        response_message += "\n **Sources**"
        for text_node in text_nodes:
            response_message += f"\n- {text_node.metadata['file_path']}"
            yield response_message

with gr.Blocks() as demo:
    with gr.Row(variant="compact"):
        with gr.Column(variant="compact"):
            gr.Textbox(agent_builder.cache.system_prompt, label="System Prompt", scale=1)
            chatbot = gr.Chatbot(height="70vh",
                                avatar_images=(
                                   None, "https://i.pinimg.com/564x/97/c3/7c/97c37c4eec569c2ef37fd88ee9e0f340.jpg"),
                                   bubble_full_width=False,
                                 render=False)
            textbox = gr.Textbox(placeholder="Your question", container=False, scale=7,render=False)
            stop_btn = gr.Button("Stop", variant="stop", scale=1,render=False)

            interface = gr.ChatInterface(
                yes_man,
                chatbot=chatbot,
                textbox=textbox,
                title="Artificial Intelligence Disability",
                theme=gr.themes.Base(),
                examples=["How does Oxalis22 generate useful searches?", "Tell me about systems"],
                stop_btn=stop_btn
            )
    gr.Button("Reset").click(lambda: agent_builder.cache.agent.reset())

demo.launch()

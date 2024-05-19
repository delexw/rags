"""Configuration."""
import streamlit as st
import os

import toml
from llama_index.core.callbacks import CallbackManager
from llama_index.legacy.llms import OpenAILike
### DEFINE BUILDER_LLM #####
## Uncomment the LLM you want to use to construct the meta agent

## OpenAI

# set OpenAI Key - use Streamlit secrets
# os.environ["OPENAI_API_KEY"] = st.secrets.openai_key
# load LLM
# BUILDER_LLM = OpenAI(model="gpt-4-1106-preview")

# # Anthropic (make sure you `pip install anthropic`)
# from llama_index.llms import Anthropic
# # set Anthropic key
# os.environ["ANTHROPIC_API_KEY"] = st.secrets.anthropic_key
# BUILDER_LLM = Anthropic()

# BUILDER_LLM = OpenAILike(
#     api_key=st.secrets.openai_key,
#     api_base=st.secrets.openai_base_url,
#     temperature=1,
#     timeout=3600,
#     model=st.secrets.model_name,
#     is_chat_model=True,
#     is_function_calling_model=True
# )


with open('.streamlit/secrets.toml', 'r') as f:
    config = toml.load(f)

BUILDER_LLM = OpenAILike(
    api_key=config["openai_key"],
    api_base=config["openai_base_url"],
    temperature=1,
    timeout=3600,
    model=config["model_name"],
    is_chat_model=True,
    is_function_calling_model=True
)
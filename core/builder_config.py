"""Configuration."""
import streamlit as st
import os

### DEFINE BUILDER_LLM #####
## Uncomment the LLM you want to use to construct the meta agent

## OpenAI
from llama_index.llms import OpenAI

# set OpenAI Key - use Streamlit secrets
# os.environ["OPENAI_API_KEY"] = st.secrets.openai_key
# load LLM
# BUILDER_LLM = OpenAI(model="gpt-4-1106-preview")

# # Anthropic (make sure you `pip install anthropic`)
# from llama_index.llms import Anthropic
# # set Anthropic key
# os.environ["ANTHROPIC_API_KEY"] = st.secrets.anthropic_key
# BUILDER_LLM = Anthropic()

from llama_index.llms import OpenAILike

BUILDER_LLM = OpenAILike(
    api_key=st.secrets.openai_key,
    api_base=st.secrets.openai_base_url,
    temperature=0.7,
    timeout=3600,
    model=st.secrets.model_name,
    is_chat_model=True,
    is_function_calling_model=True
)
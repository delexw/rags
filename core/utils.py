"""Utils."""
from llama_index.legacy import Document, SimpleDirectoryReader, ServiceContext, VectorStoreIndex, SummaryIndex
from llama_index.legacy.agent import OpenAIAgent, ReActAgent, ReActChatFormatter
from llama_index.legacy.agent.react.prompts import REACT_CHAT_SYSTEM_HEADER
from llama_index.legacy.agent.types import BaseAgent
from llama_index.legacy.callbacks import CallbackManager, trace_method
from llama_index.legacy.chat_engine.types import BaseChatEngine, ChatMode, AGENT_CHAT_RESPONSE_TYPE, AgentChatResponse, \
    StreamingAgentChatResponse
from llama_index.legacy.core.llms.types import ChatMessage, ChatResponse
from llama_index.legacy.embeddings import resolve_embed_model
from llama_index.legacy.indices import MultiModalVectorStoreIndex
from llama_index.legacy.indices.multi_modal import MultiModalVectorIndexRetriever
from llama_index.legacy.indices.query.query_transform import HyDEQueryTransform
from llama_index.legacy.llms import LLM, OpenAI
from llama_index.legacy.llms.openai_utils import is_function_calling_model
from llama_index.legacy.query_engine import TransformQueryEngine, SimpleMultiModalQueryEngine
from llama_index.legacy.readers import SimpleWebPageReader
from llama_index.legacy.schema import NodeWithScore, ImageNode
from llama_index.legacy.tools import QueryEngineTool, ToolMetadata
from pydantic import BaseModel, Field
import os


from typing import List, cast, Optional
from core.builder_config import BUILDER_LLM
from typing import Dict, Tuple, Any
import streamlit as st

from core.callback_manager import StreamlitFunctionsCallbackHandler

### BETA: Multi-modal
from llama_index.multi_modal_llms.openai import OpenAIMultiModal

from typing import Generator


class RAGParams(BaseModel):
    """RAG parameters.

    Parameters used to configure a RAG pipeline.

    """

    include_summarization: bool = Field(
        default=False,
        description=(
            "Whether to include summarization in the RAG pipeline. (only for GPT-4)"
        ),
    )
    top_k: int = Field(
        default=2, description="Number of documents to retrieve from vector store."
    )
    chunk_size: int = Field(default=1024, description="Chunk size for vector store.")
    embed_model: str = Field(
        default=st.secrets.embedding_model_name, description="Embedding model to use (default is OpenAI)"
    )
    llm: str = Field(
        default=st.secrets.model_name, description="LLM to use for summarization."
    )


def _resolve_llm(llm_str: str) -> LLM:
    """Resolve LLM."""
    # TODO: make this less hardcoded with if-else statements
    # see if there's a prefix
    # - if there isn't, assume it's an OpenAI model
    # - if there is, resolve it

    return BUILDER_LLM

    tokens = llm_str.split(":")

    if len(tokens) == 1:
        os.environ["OPENAI_API_KEY"] = st.secrets.openai_key
        llm: LLM = OpenAI(model=llm_str)
    elif tokens[0] == "local":
        llm = resolve_llm(llm_str)
    elif tokens[0] == "openai":
        os.environ["OPENAI_API_KEY"] = st.secrets.openai_key
        llm = OpenAI(model=tokens[1])
    elif tokens[0] == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = st.secrets.anthropic_key
        llm = Anthropic(model=tokens[1])
    elif tokens[0] == "replicate":
        os.environ["REPLICATE_API_KEY"] = st.secrets.replicate_key
        llm = Replicate(model=tokens[1])
    else:
        raise ValueError(f"LLM {llm_str} not recognized.")
    return llm


def load_data(
        file_names: Optional[List[str]] = None,
        directory: Optional[str] = None,
        urls: Optional[List[str]] = None,
) -> List[Document]:
    """Load data."""
    file_names = file_names or []
    directory = directory or ""
    urls = urls or []

    # get number depending on whether specified
    num_specified = sum(1 for v in [file_names, urls, directory] if v)

    if num_specified == 0:
        raise ValueError("Must specify either file_names or urls or directory.")
    elif num_specified > 1:
        raise ValueError("Must specify only one of file_names or urls or directory.")
    elif file_names:
        reader = SimpleDirectoryReader(input_files=file_names)
        docs = reader.load_data()
    elif directory:
        reader = SimpleDirectoryReader(input_dir=directory, recursive=True)
        docs = reader.load_data()
    elif urls:
        # use simple web page reader from llamahub
        loader = SimpleWebPageReader()
        docs = loader.load_data(urls=urls)
    else:
        raise ValueError("Must specify either file_names or urls or directory.")

    return docs


def load_agent(
        tools: List,
        llm: LLM,
        system_prompt: str,
        service_context: ServiceContext = None,
        extra_kwargs: Optional[Dict] = None,
        **kwargs: Any,
) -> BaseChatEngine:
    """Load agent."""
    extra_kwargs = extra_kwargs or {}
    if isinstance(llm, OpenAI) and is_function_calling_model(llm.model):
        # TODO: use default msg handler
        # TODO: separate this from agent_utils.py...
        def _msg_handler(msg: str) -> None:
            """Message handler."""
            st.info(msg)
            st.session_state.agent_messages.append(
                {"role": "assistant", "content": msg, "msg_type": "info"}
            )

        # add streamlit callbacks (to inject events)
        handler = StreamlitFunctionsCallbackHandler(_msg_handler)
        callback_manager = CallbackManager([handler])
        # get OpenAI Agent
        agent: BaseChatEngine = OpenAIAgent.from_tools(
            tools=tools,
            llm=llm,
            system_prompt=system_prompt,
            **kwargs,
            callback_manager=callback_manager,
        )
    else:
        if "vector_index" not in extra_kwargs:
            raise ValueError(
                "Must pass in vector index for CondensePlusContextChatEngine."
            )
        vector_index = cast(VectorStoreIndex, extra_kwargs["vector_index"])
        rag_params = cast(RAGParams, extra_kwargs["rag_params"])

        # # https://docs.llamaindex.ai/en/stable/optimizing/advanced_retrieval/query_transformations/

        # query_engine = vector_index.as_query_engine(
        #     similarity_top_k=rag_params.top_k,
        #     streaming=True
        # )
        # # https://docs.llamaindex.ai/en/stable/examples/query_transformations/HyDEQueryTransformDemo/
        # ####### use HyDEQueryTransform single step
        # hyde = HyDEQueryTransform(include_original=True,
        #                           llm_predictor=LLMPredictor(llm=llm, system_prompt=system_prompt))
        # transformed_query_engine = TransformQueryEngine(query_engine, hyde)

        # ####### use StepDecomposeQueryTransform multi-step (for complex query, otherwise hit performance to get answer)
        # step_decompose_transform = StepDecomposeQueryTransform(
        #     llm_predictor=LLMPredictor(
        #         llm=llm,
        #         system_prompt=system_prompt
        #     ), verbose=True)
        # transformed_query_engine = MultiStepQueryEngine(
        #     query_engine, query_transform=step_decompose_transform,
        #     response_synthesizer=get_response_synthesizer(
        #         service_context=service_context,
        #         callback_manager=query_engine.callback_manager, # It requires to make streaming work
        #         streaming=True
        #     )
        # )
        #
        # agent = CondenseQuestionChatEngine.from_defaults(
        #     query_engine=transformed_query_engine,
        #     service_context=service_context,
        # )

        # use condense + context chat engine
        agent = vector_index.as_chat_engine(
            chat_mode=ChatMode.CONDENSE_PLUS_CONTEXT,
            service_context=service_context,
            system_prompt=system_prompt,
        )

        # ReActAgent.from_tools().get_prompts()

    return agent


def load_meta_agent(
        tools: List,
        llm: LLM,
        system_prompt: str,
        extra_kwargs: Optional[Dict] = None,
        **kwargs: Any,
) -> BaseAgent:
    """Load meta agent.

    TODO: consolidate with load_agent.

    The meta-agent *has* to perform tool-use.

    """
    extra_kwargs = extra_kwargs or {}
    if isinstance(llm, OpenAI) and is_function_calling_model(llm.model):
        # get OpenAI Agent

        agent: BaseAgent = OpenAIAgent.from_tools(
            tools=tools,
            llm=llm,
            system_prompt=system_prompt,
            **kwargs,
        )
    else:
        agent = ReActAgent.from_tools(
            tools=tools,
            llm=llm,
            react_chat_formatter=ReActChatFormatter(
                system_header=system_prompt + "\n" + REACT_CHAT_SYSTEM_HEADER,
            ),
            **kwargs,
        )

    return agent


def construct_agent(
        system_prompt: str,
        rag_params: RAGParams,
        docs: List[Document],
        vector_index: Optional[VectorStoreIndex] = None,
        additional_tools: Optional[List] = None,
) -> Tuple[BaseChatEngine, Dict]:
    """Construct agent from docs / parameters / indices."""
    print("constructing agent")

    if system_prompt is None:
        return "System prompt not set yet. Please set system prompt first."

    extra_info = {}
    additional_tools = additional_tools or []

    # first resolve llm and embedding model
    print("resolve embed model")
    embed_model = resolve_embed_model(rag_params.embed_model)
    print(embed_model)
    # llm = resolve_llm(rag_params.llm)
    # TODO: use OpenAI for now
    # llm = OpenAI(model=rag_params.llm)
    llm = _resolve_llm(rag_params.llm)
    print(llm)
    # first let's index the data with the right parameters
    service_context = ServiceContext.from_defaults(
        chunk_size=rag_params.chunk_size,
        llm=llm,
        embed_model=embed_model,
        system_prompt=system_prompt
    )

    print(system_prompt)

    if vector_index is None:
        vector_index = VectorStoreIndex.from_documents(
            docs, service_context=service_context
        )
    else:
        pass

    extra_info["vector_index"] = vector_index

    vector_query_engine = vector_index.as_query_engine(
        similarity_top_k=rag_params.top_k
    )

    # https://docs.llamaindex.ai/en/stable/examples/query_transformations/HyDEQueryTransformDemo/
    hyde = HyDEQueryTransform(include_original=True, llm=llm)
    hyde_query_engine = TransformQueryEngine(vector_query_engine, hyde)

    all_tools = []
    vector_tool = QueryEngineTool(
        query_engine=hyde_query_engine,
        metadata=ToolMetadata(
            name="vector_tool",
            description=("Use this tool to answer any user question over any data."),
        ),
    )
    all_tools.append(vector_tool)
    if rag_params.include_summarization:
        summary_index = SummaryIndex.from_documents(
            docs, service_context=service_context
        )
        summary_query_engine = summary_index.as_query_engine()
        summary_tool = QueryEngineTool(
            query_engine=summary_query_engine,
            metadata=ToolMetadata(
                name="summary_tool",
                description=(
                    "Use this tool for any user questions that ask "
                    "for a summarization of content"
                ),
            ),
        )
        all_tools.append(summary_tool)

    # then we add tools
    all_tools.extend(additional_tools)

    # build agent

    agent = load_agent(
        all_tools,
        llm=llm,
        system_prompt=system_prompt,
        service_context=service_context,
        verbose=True,
        extra_kwargs={"vector_index": vector_index, "rag_params": rag_params},
    )
    return agent, extra_info


def get_web_agent_tool() -> QueryEngineTool:
    """Get web agent tool.

    Wrap with our load and search tool spec.

    """
    # TODO: set metaphor API key
    metaphor_tool = MetaphorToolSpec(
        api_key=st.secrets.metaphor_key,
    )
    metaphor_tool_list = metaphor_tool.to_tool_list()

    # TODO: LoadAndSearch doesn't work yet
    # The search_and_retrieve_documents tool is the third in the tool list,
    # as seen above
    # wrapped_retrieve = LoadAndSearchToolSpec.from_defaults(
    #     metaphor_tool_list[2],
    # )

    # NOTE: requires openai right now
    # We don't give the Agent our unwrapped retrieve document tools
    # instead passing the wrapped tools
    web_agent = OpenAIAgent.from_tools(
        # [*wrapped_retrieve.to_tool_list(), metaphor_tool_list[4]],
        metaphor_tool_list,
        llm=BUILDER_LLM,
        verbose=True,
    )

    # return agent as a tool
    # TODO: tune description
    web_agent_tool = QueryEngineTool.from_defaults(
        web_agent,
        name="web_agent",
        description="""
            This agent can answer questions by searching the web. \
Use this tool if the answer is ONLY likely to be found by searching \
the internet, especially for queries about recent events.
        """,
    )

    return web_agent_tool


def get_tool_objects(tool_names: List[str]) -> List:
    """Get tool objects from tool names."""
    # construct additional tools
    tool_objs = []
    for tool_name in tool_names:
        if tool_name == "web_search":
            pass
        else:
            raise ValueError(f"Tool {tool_name} not recognized.")

    return tool_objs


class MultimodalChatEngine(BaseChatEngine):
    """Multimodal chat engine.

    This chat engine is a light wrapper around a query engine.
    Offers no real 'chat' functionality, is a beta feature.

    """

    def __init__(self, mm_query_engine: SimpleMultiModalQueryEngine) -> None:
        """Init params."""
        self._mm_query_engine = mm_query_engine

    def reset(self) -> None:
        """Reset conversation state."""
        pass

    @property
    def chat_history(self) -> List[ChatMessage]:
        return []

    @trace_method("chat")
    def chat(
            self, message: str, chat_history: Optional[List[ChatMessage]] = None
    ) -> AGENT_CHAT_RESPONSE_TYPE:
        """Main chat interface."""
        # just return the top-k results
        response = self._mm_query_engine.query(message)
        return AgentChatResponse(
            response=str(response), source_nodes=response.source_nodes
        )

    @trace_method("chat")
    def stream_chat(
            self, message: str, chat_history: Optional[List[ChatMessage]] = None
    ) -> StreamingAgentChatResponse:
        """Stream chat interface."""
        response = self._mm_query_engine.query(message)

        def _chat_stream(response: str) -> Generator[ChatResponse, None, None]:
            yield ChatResponse(message=ChatMessage(role="assistant", content=response))

        chat_stream = _chat_stream(str(response))
        return StreamingAgentChatResponse(
            chat_stream=chat_stream, source_nodes=response.source_nodes
        )

    @trace_method("chat")
    async def achat(
            self, message: str, chat_history: Optional[List[ChatMessage]] = None
    ) -> AGENT_CHAT_RESPONSE_TYPE:
        """Async version of main chat interface."""
        response = await self._mm_query_engine.aquery(message)
        return AgentChatResponse(
            response=str(response), source_nodes=response.source_nodes
        )

    @trace_method("chat")
    async def astream_chat(
            self, message: str, chat_history: Optional[List[ChatMessage]] = None
    ) -> StreamingAgentChatResponse:
        """Async version of main chat interface."""
        return self.stream_chat(message, chat_history)


def construct_mm_agent(
        system_prompt: str,
        rag_params: RAGParams,
        docs: List[Document],
        mm_vector_index: Optional[VectorStoreIndex] = None,
        additional_tools: Optional[List] = None,
) -> Tuple[BaseChatEngine, Dict]:
    """Construct agent from docs / parameters / indices.

    NOTE: system prompt isn't used right now

    """
    extra_info = {}
    additional_tools = additional_tools or []

    # first resolve llm and embedding model
    embed_model = resolve_embed_model(rag_params.embed_model)
    # TODO: use OpenAI for now
    os.environ["OPENAI_API_KEY"] = st.secrets.openai_key
    openai_mm_llm = OpenAIMultiModal(model="gpt-4-vision-preview", max_new_tokens=1500)

    # first let's index the data with the right parameters
    service_context = ServiceContext.from_defaults(
        chunk_size=rag_params.chunk_size,
        embed_model=embed_model,
    )

    if mm_vector_index is None:
        mm_vector_index = MultiModalVectorStoreIndex.from_documents(
            docs, service_context=service_context
        )
    else:
        pass

    mm_retriever = mm_vector_index.as_retriever(similarity_top_k=rag_params.top_k)
    mm_query_engine = SimpleMultiModalQueryEngine(
        cast(MultiModalVectorIndexRetriever, mm_retriever),
        multi_modal_llm=openai_mm_llm,
    )

    extra_info["vector_index"] = mm_vector_index

    # use condense + context chat engine
    agent = MultimodalChatEngine(mm_query_engine)

    return agent, extra_info


def get_image_and_text_nodes(
        nodes: List[NodeWithScore],
) -> Tuple[List[NodeWithScore], List[NodeWithScore]]:
    image_nodes = []
    text_nodes = []
    for res_node in nodes:
        if isinstance(res_node.node, ImageNode):
            image_nodes.append(res_node)
        else:
            text_nodes.append(res_node)
    return image_nodes, text_nodes

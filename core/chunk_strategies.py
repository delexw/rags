from typing import List

from llama_index.core import Document
from llama_index.legacy import VectorStoreIndex, ServiceContext
from llama_index.legacy.core.embeddings.base import BaseEmbedding
from llama_index.legacy.node_parser import (
    SemanticSplitterNodeParser,
)


class ChunkStrategies:

    def __init__(self,
                 docs: List[Document],
                 service_context: ServiceContext,
                 embed_model: BaseEmbedding):
        self._docs = docs
        self._service_context = service_context
        self._embed_model = embed_model

    def sentence_splitter_vector_index(self) -> VectorStoreIndex:
        return VectorStoreIndex.from_documents(
            documents=self._docs, service_context=self._service_context
        )

    def semantic_splitter_vector_index(self) -> VectorStoreIndex:
        splitter = SemanticSplitterNodeParser(
            buffer_size=1, breakpoint_percentile_threshold=95, embed_model=self._embed_model
        )

        nodes = splitter.get_nodes_from_documents(self._docs)

        return VectorStoreIndex(nodes, service_context=self._service_context)

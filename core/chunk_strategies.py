from typing import List

from llama_index.core import Document
from llama_index.legacy import VectorStoreIndex, ServiceContext, StorageContext
from llama_index.legacy.core.embeddings.base import BaseEmbedding
from llama_index.legacy.node_parser import (
    SemanticSplitterNodeParser,
)


class ChunkStrategies:

    def __init__(self,
                 docs: List[Document],
                 embed_model: BaseEmbedding,
                 service_context: ServiceContext = None,
                 storage_context: StorageContext = None) -> None:
        self._docs = docs
        self._service_context = service_context
        self._embed_model = embed_model
        self._storage_context = storage_context

    def sentence_splitter_vector_index(self) -> VectorStoreIndex:
        return VectorStoreIndex.from_documents(
            documents=self._docs, service_context=self._service_context,
            storage_context=self._storage_context
        )

    def semantic_splitter_vector_index(self) -> VectorStoreIndex:
        splitter = SemanticSplitterNodeParser(
            buffer_size=5, breakpoint_percentile_threshold=95, embed_model=self._embed_model
        )

        nodes = splitter.get_nodes_from_documents(self._docs)

        return VectorStoreIndex(nodes, service_context=self._service_context, storage_context=self._storage_context)

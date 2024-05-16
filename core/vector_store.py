from typing import cast

from llama_index.legacy.vector_stores import WeaviateVectorStore, ChromaVectorStore

from core.constants import CHROMADB_CACHE_DIR
import streamlit as st

class VectorStore:
    def weaviate_store(self):
        import weaviate
        from weaviate import Client
        from weaviate import EmbeddedOptions

        client = weaviate.Client("http://localhost:8080")

        if client.schema.exists("Agent"):
            client.schema.delete_class("Agent")

        vector_store = WeaviateVectorStore(
            weaviate_client=client, index_name="Agent"
        )

        return vector_store

    def default_store(self):
        return None

    def chromadb_store(self):
        import chromadb
        from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
        from chromadb.utils.data_loaders import ImageLoader

        chroma_client = chromadb.PersistentClient(path=str(CHROMADB_CACHE_DIR))
        chroma_collection = chroma_client.get_or_create_collection(
            "Agent",
            # embedding_function=OpenCLIPEmbeddingFunction(),
            # data_loader=ImageLoader()
        )

        return ChromaVectorStore(chroma_collection=chroma_collection)

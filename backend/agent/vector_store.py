from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

from backend.config import settings


def get_pinecone_vector_store():
    embeddings = OpenAIEmbeddings(model=settings.OPENAI_EMBEDDINGS_MODEL, api_key=settings.OPENAI_API_KEY)
    pinecone_client = Pinecone(api_key=settings.PINECONE_API_KEY)
    pinecone_index = pinecone_client.Index(settings.PINECONE_INDEX_NAME)
    vector_store = PineconeVectorStore(index=pinecone_index, embedding=embeddings)
    return vector_store


class Retriever:
    def __init__(self, vector_store: PineconeVectorStore):
        self.vector_store = vector_store

    def sim_search(self, prompt: str, namespace: str | None):
        """MMR search for diverse, relevant results."""
        try:
            docs = self.vector_store.max_marginal_relevance_search(
                prompt,
                k=10,
                fetch_k=20,
                lambda_mult=0.7,
                namespace=namespace if namespace else ""
            )
            return docs
        except Exception:
            # Fallback to basic similarity search if MMR fails
            return self.vector_store.similarity_search(
                prompt, k=10, namespace=namespace if namespace else ""
            )

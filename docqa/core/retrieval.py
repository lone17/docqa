import chromadb
from angle_emb import AnglE, Prompts
from pydantic import BaseModel, ConfigDict


class SemanticRetriever(BaseModel):
    """
    SemanticRetriever class for retrieving documents based on embeddings.

    Args:
        embedding_model (Any): The embedding model used to encode the corpus.
        vector_db (chromadb.Collection): The Chroma vector database.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    embedding_model: AnglE
    vector_db: chromadb.Collection

    def process(
        self, query: str, top_k: int, metadata_filter: dict | None = None
    ) -> list[dict]:
        """
        Process the given query to retrieve the top-k results from the vector database.

        Args:
            query (str): The query string.
            top_k (int): The number of results to retrieve.
            metadata_filter (dict | None, optional): A dictionary specifying metadata
                filters. Defaults to None.

        Returns:
            list[dict]: The list of retrieved results.
        """
        query_embeddings = self.embedding_model.encode(
            {"text": query}, prompt=Prompts.C
        )

        results = self.vector_db.query(
            query_embeddings=query_embeddings, n_results=top_k, where=metadata_filter
        )

        output = []
        for i in range(len(results["ids"][0])):
            score = 1 - results["distances"][0][i]
            document = results["documents"][0][i]
            metadata = results["metadatas"][0][i]
            output.append({"score": score, "document": document, "metadata": metadata})

        return output

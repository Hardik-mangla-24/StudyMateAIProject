import numpy as np
from google.genai import types


EMBEDDING_MODEL = "gemini-embedding-001"


def create_embeddings(client, chunks):
    """
    PDF chunks ke embeddings create karta hai.
    """

    if not chunks:
        raise ValueError("No PDF chunks available.")

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=chunks,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            title="StudyMate PDF Notes"
        )
    )

    if not response.embeddings:
        raise ValueError("Gemini did not return embeddings.")

    embeddings = [
        item.values for item in response.embeddings
    ]

    if len(embeddings) != len(chunks):
        raise ValueError(
            "Number of embeddings does not match PDF chunks."
        )

    return embeddings


def search_relevant_chunks(
    client,
    question,
    chunks,
    embeddings,
    top_k=4
):
    """
    Student ke question ke according
    most relevant PDF chunks find karta hai.
    """

    if not question or not question.strip():
        raise ValueError("Please enter a question.")

    if not chunks or not embeddings:
        raise ValueError("Please process a PDF first.")

    if len(chunks) != len(embeddings):
        raise ValueError("Chunks and embeddings do not match.")

    query_response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=question,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY"
        )
    )

    if not query_response.embeddings:
        raise ValueError("Could not create question embedding.")

    query_vector = np.array(
        query_response.embeddings[0].values,
        dtype=np.float32
    )

    document_vectors = np.array(
        embeddings,
        dtype=np.float32
    )

    if document_vectors.ndim != 2:
        raise ValueError("Invalid document embeddings.")

    if document_vectors.shape[1] != len(query_vector):
        raise ValueError("Embedding dimensions do not match.")

    query_norm = np.linalg.norm(query_vector)

    document_norms = np.linalg.norm(
        document_vectors,
        axis=1
    )

    if query_norm == 0:
        raise ValueError("Question embedding is invalid.")

    denominator = document_norms * query_norm

    similarities = np.divide(
        np.dot(document_vectors, query_vector),
        denominator,
        out=np.zeros(len(chunks), dtype=np.float32),
        where=denominator != 0
    )

    top_k = max(1, min(int(top_k), len(chunks)))

    top_indices = np.argsort(similarities)[::-1][:top_k]

    return [
        chunks[index]
        for index in top_indices
    ]
from unittest.mock import MagicMock

import chromadb
import pytest
from angle_emb import AnglE

from docqa.core.retrieval import SemanticRetriever


# Assuming the presence of a fixture to provide a SemanticRetriever instance
@pytest.fixture
def semantic_retriever():
    embedding_model_mock = MagicMock(spec=AnglE)
    vector_db_mock = MagicMock(spec=chromadb.Collection)

    retriever = SemanticRetriever(
        embedding_model=embedding_model_mock, vector_db=vector_db_mock
    )
    return retriever


def test_process_with_no_filter(semantic_retriever):
    # Mock the embedding model's encode method
    semantic_retriever.embedding_model.encode.return_value = "mocked_embeddings"

    # Mock the vector_db's query method
    mock_results = {
        "ids": [["id1", "id2"]],
        "distances": [[0.1, 0.2]],
        "documents": [["doc1", "doc2"]],
        "metadatas": [[{"meta1": "data1"}, {"meta2": "data2"}]],
    }
    semantic_retriever.vector_db.query.return_value = mock_results

    # Define the test inputs
    query = "test query"
    top_k = 2

    # Call the process method
    results = semantic_retriever.process(query, top_k)

    # Check the call to the embedding model's encode method
    semantic_retriever.embedding_model.encode.assert_called_once_with({"text": query})

    # Check the call to the vector_db's query method
    semantic_retriever.vector_db.query.assert_called_once_with(
        query_embeddings="mocked_embeddings", n_results=top_k, where=None
    )

    # Define the expected output
    expected_results = [
        {"score": 0.9, "document": "doc1", "metadata": {"meta1": "data1"}},
        {"score": 0.8, "document": "doc2", "metadata": {"meta2": "data2"}},
    ]

    # Verify the results
    assert (
        results == expected_results
    ), "The process method did not return expected results"


def test_process_with_filter(semantic_retriever):
    # Similar setup as previous test case, but with metadata_filter provided

    # Mock the embedding model's encode method
    semantic_retriever.embedding_model.encode.return_value = "mocked_embeddings"

    # Mock the vector_db's query method
    mock_results = {
        "ids": [["id1", "id3"]],
        "distances": [[0.1, 0.3]],
        "documents": [["doc1", "doc3"]],
        "metadatas": [[{"meta1": "data1"}, {"meta1": "data1"}]],
    }
    semantic_retriever.vector_db.query.return_value = mock_results

    # Define the test inputs
    query = "test query"
    top_k = 2
    metadata_filter = {"meta1": "data1"}

    # Call the process method
    results = semantic_retriever.process(query, top_k, metadata_filter=metadata_filter)

    # Check the call to the embedding model's encode method
    semantic_retriever.embedding_model.encode.assert_called_once_with({"text": query})

    # Check the call to the vector_db's query method
    semantic_retriever.vector_db.query.assert_called_once_with(
        query_embeddings="mocked_embeddings", n_results=top_k, where=metadata_filter
    )

    # Define the expected output
    expected_results = [
        {"score": 0.9, "document": "doc1", "metadata": {"meta1": "data1"}},
        {"score": 0.7, "document": "doc3", "metadata": {"meta1": "data1"}},
    ]

    # Verify the results
    assert (
        results == expected_results
    ), "The process method did not return expected results"


# Calls the process method with valid inputs and returns expected results.
def test_valid_inputs_returns_expected_results(semantic_retriever):
    # Mock the embedding model's encode method
    semantic_retriever.embedding_model.encode.return_value = "mocked_embeddings"

    # Mock the vector_db's query method
    mock_results = {
        "ids": [["id1", "id2"]],
        "distances": [[0.1, 0.2]],
        "documents": [["doc1", "doc2"]],
        "metadatas": [[{"meta1": "data1"}, {"meta2": "data2"}]],
    }
    semantic_retriever.vector_db.query.return_value = mock_results

    # Define the test inputs
    query = "test query"
    top_k = 2

    # Call the process method
    results = semantic_retriever.process(query, top_k)

    # Check the call to the embedding model's encode method
    semantic_retriever.embedding_model.encode.assert_called_once_with({"text": query})

    # Check the call to the vector_db's query method
    semantic_retriever.vector_db.query.assert_called_once_with(
        query_embeddings="mocked_embeddings", n_results=top_k, where=None
    )

    # Define the expected output
    expected_results = [
        {"score": 0.9, "document": "doc1", "metadata": {"meta1": "data1"}},
        {"score": 0.8, "document": "doc2", "metadata": {"meta2": "data2"}},
    ]

    # Verify the results
    assert (
        results == expected_results
    ), "The process method did not return expected results"


# Mocks the embedding model's encode method and vector_db's query method.
def test_mocks_encode_and_query_methods(semantic_retriever, mocker):
    # Mock the embedding model's encode method
    encode_mock = mocker.patch.object(semantic_retriever.embedding_model, "encode")
    encode_mock.return_value = "mocked_embeddings"

    # Mock the vector_db's query method
    query_mock = mocker.patch.object(semantic_retriever.vector_db, "query")
    mock_results = {
        "ids": [["id1", "id2"]],
        "distances": [[0.1, 0.2]],
        "documents": [["doc1", "doc2"]],
        "metadatas": [[{"meta1": "data1"}, {"meta2": "data2"}]],
    }
    query_mock.return_value = mock_results

    # Define the test inputs
    query = "test query"
    top_k = 2

    # Call the process method
    semantic_retriever.process(query, top_k)

    # Check the call to the embedding model's encode method
    encode_mock.assert_called_once_with({"text": query})

    # Check the call to the vector_db's query method
    query_mock.assert_called_once_with(
        query_embeddings="mocked_embeddings", n_results=top_k, where=None
    )


# Checks the call to the embedding model's encode method with the correct query.
def test_correct_query_to_encode_method(semantic_retriever, mocker):
    # Mock the embedding model's encode method
    encode_mock = mocker.patch.object(semantic_retriever.embedding_model, "encode")
    encode_mock.return_value = "mocked_embeddings"

    # Mock the vector_db's query method
    query_mock = mocker.patch.object(semantic_retriever.vector_db, "query")
    mock_results = {
        "ids": [["id1", "id2"]],
        "distances": [[0.1, 0.2]],
        "documents": [["doc1", "doc2"]],
        "metadatas": [[{"meta1": "data1"}, {"meta2": "data2"}]],
    }
    query_mock.return_value = mock_results

    # Define the test inputs
    query = "test query"
    top_k = 2

    # Call the process method
    semantic_retriever.process(query, top_k)

    # Check the call to the embedding model's encode method with the correct query
    encode_mock.assert_called_once_with({"text": query})


# Calls the process method with empty query and returns empty results.
def test_empty_query_returns_empty_results(semantic_retriever):
    # Define the test inputs
    query = ""
    top_k = 2

    # Call the process method
    results = semantic_retriever.process(query, top_k)

    # Verify the results
    assert results == [], "The process method did not return empty results"


# Calls the process method with invalid top_k and returns empty results.
def test_invalid_top_k_returns_empty_results(semantic_retriever):
    # Define the test inputs
    query = "test query"
    top_k = -1

    # Call the process method
    results = semantic_retriever.process(query, top_k)

    # Verify the results
    assert results == [], "The process method did not return empty results"


# Calls the process method with invalid query and returns empty results.
def test_invalid_query_returns_empty_results(semantic_retriever):
    # Define the test inputs
    query = None
    top_k = 2

    # Call the process method
    results = semantic_retriever.process(query, top_k)

    # Verify the results
    assert results == [], "The process method did not return empty results"

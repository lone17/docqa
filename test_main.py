from fastapi.testclient import TestClient
from openai.types.chat.chat_completion import ChatCompletion

from main import app

client = TestClient(app)


def test_root():
    """
    Test that the root path returns the correct message.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == '"Please visit /chat to interact with the chatbot."'


def test_chat(mocker):
    """
    Test the chat endpoint with a mock request and ensure it returns a valid response.
    """
    openai_mocker = mocker.patch(
        "openai.resources.chat.completions.Completions.create",
        return_value=ChatCompletion.model_validate(
            {
                "id": "chatcmpl-7qyuw6Q1CFCpcKsMdFkmUPUa7JP2x",
                "object": "chat.completion",
                "created": 1692338378,
                "model": "gpt-35-turbo",
                "system_fingerprint": None,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "I'm fine thank you, and you?",
                        },
                        "logprobs": None,
                    }
                ],
                "usage": {
                    "completion_tokens": 9,
                    "prompt_tokens": 10,
                    "total_tokens": 19,
                },
            }
        ),
    )

    mock_retriever = mocker.patch(
        "docqa.core.retrieval.SemanticRetriever.process",
        return_value=[
            {
                "score": 0.8,
                "answer": "Hello, how are you?",
                "metadata": {"source": "## Abstract", "type": "chunk"},
            }
        ],
    )

    # Assuming ChatRequest has attributes: message, openai_model, certainty_threshold,
    # uncertainty_threshold, temperature, and the PipelineOutput has an attribute
    # 'answer'
    mock_request = {
        "message": "Hello, how are you?",
        "openai_model": "text-davinci-003",
        "certainty_threshold": 0.8,
        "uncertainty_threshold": 0.2,
        "temperature": 0.5,
    }
    response = client.post("/chat", json=mock_request)

    assert openai_mocker.call_count == 1
    assert mock_retriever.call_count == 2
    assert response.status_code == 200
    assert "answer" in response.json()

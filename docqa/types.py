from pydantic import BaseModel


class ChatRequest(BaseModel):
    """
    Represents a chat request.

    Args:
        message (str): The message from user.
        openai_model (str, optional): The OpenAI model to use. Defaults to
            "ft:gpt-3.5-turbo-1106:aitomatic-inc:gen-agent-v2:8dPNxr8r".
        temperature (float, optional): The temperature of the model's output.
            Higher values make the output more random, while lower values make it
            more focused and deterministic. Defaults to 1.0.
        certainty_threshold (float, optional): The threshold for considering a
            question as certain. Defaults to 0.9.
        uncertainty_threshold (float, optional): The threshold for considering a
            question as uncertain. Defaults to 0.6.
    """

    message: str
    openai_model: str = "ft:gpt-3.5-turbo-1106:aitomatic-inc:gen-agent-v2:8dPNxr8r"
    temperature: float = 1.0
    certainty_threshold: float = 0.9
    uncertainty_threshold: float = 0.6


class RetrievalReference(BaseModel):
    """
    Represents a reference.

    Args:
        source (str): The source of the reference.
        content (str): The content of the reference.
    """

    source: str
    content: str


class PipelineOutput(BaseModel):
    """
    Represents the output of the pipeline.

    Args:
        answer (str): The answer to the question.
        references (list[RetrievalReference]): A list of RetrievalReference objects
            containing the related references.
        metadata (dict): Additional metadata associated with the answer.
    """

    answer: str
    references: list[RetrievalReference]
    metadata: dict | None = None

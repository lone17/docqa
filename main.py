import os
from pathlib import Path

import uvicorn
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI

from docqa.demo.pipeline import get_pipeline
from docqa.types import ChatRequest, PipelineOutput

load_dotenv(find_dotenv(".env"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Initialize FastAPI
app = FastAPI()

# Initialize pipeline
pipeline = get_pipeline(
    data_dir=Path("docqa/demo/data/generative_agent"),
    openai_key=OPENAI_API_KEY,
    openai_model="",
)


@app.get("/")
def root():
    """
    A function that reads the root path ("/") and returns a message to visit the
        "/chat" path to interact with the chatbot.

    Returns:
        str: A string message instructing the user to visit the "/chat" path.
    """
    return "Please visit /chat to interact with the chatbot."


@app.post("/chat")
async def chat(request: ChatRequest) -> PipelineOutput:
    """
    Processes a chat request and returns the answer using the specified OpenAI model.

    Args:
        request (ChatRequest): The chat request object containing the message and other
            parameters.

    Returns:
        PipelineOutput: The output of the pipeline, which includes the answer to the
            chat request.
    """
    pipeline.answerer.openai_model = request.openai_model
    answer = pipeline.process(
        question=request.message,
        certainty_threshold=request.certainty_threshold,
        uncertainty_threshold=request.uncertainty_threshold,
        temperature=request.temperature,
    )

    return answer


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

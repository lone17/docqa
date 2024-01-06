import json

import pytest
from openai.types.chat.chat_completion import ChatCompletion

from docqa.core.data_generation import (
    QAPairGenerator,
    generate_top_sections_questions,
    make_instruction_sample_for_openai,
    make_simple_sample_for_openai,
)

_openai_chat_completion_response = ChatCompletion.model_validate(
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
                    "content": json.dumps(
                        [
                            {
                                "question": "What is the document about?",
                                "answer": "The document is about a sample topic.",
                            }
                        ],
                    ),
                },
                "logprobs": None,
            }
        ],
        "usage": {"completion_tokens": 9, "prompt_tokens": 10, "total_tokens": 19},
    }
)


class TestQAPairGenerator:
    # QAPairGenerator can be instantiated with valid OpenAI API key and model name.
    def test_instantiation_with_valid_api_key_and_model_name(self):
        openai_key = "valid_key"
        openai_model = "valid_model"
        generator = QAPairGenerator(openai_key=openai_key, openai_model=openai_model)

        assert generator.openai_key == openai_key
        assert generator.openai_model == openai_model

    # QAPairGenerator can generate questions and answers for a given document.
    def test_generate_questions_and_answers_for_document(self, mocker):
        document = "This is a sample document."
        temperature = 0.8
        question_type = "sparse"
        num_questions = 5

        openai_mocker = mocker.patch(
            "openai.resources.chat.completions.Completions.create",
            return_value=_openai_chat_completion_response,
        )

        generator = QAPairGenerator(openai_key="valid_key", openai_model="valid_model")

        questions, metadata = generator.process(
            document,
            temperature=temperature,
            question_type=question_type,
            num_questions=num_questions,
        )

        assert questions == [
            {
                "question": "What is the document about?",
                "answer": "The document is about a sample topic.",
            }
        ]

        mock_return_value = _openai_chat_completion_response
        assert metadata == {
            "finish_reason": mock_return_value.choices[0].finish_reason,
            "usage": {
                "completion_tokens": mock_return_value.usage.completion_tokens,
                "prompt_tokens": mock_return_value.usage.prompt_tokens,
                "total_tokens": mock_return_value.usage.total_tokens,
            },
        }
        openai_mocker.assert_called_once_with(
            model="valid_model",
            messages=[
                {
                    "role": "system",
                    "content": generator.question_types[question_type][
                        "system_message"
                    ],
                },
                {
                    "role": "user",
                    "content": generator.question_types[question_type][
                        "instruction"
                    ].format(num_questions=num_questions)
                    + generator.output_format,
                },
                {"role": "user", "content": "\nHere is the given text:\n\n" + document},
            ],
            temperature=temperature,
            seed=generator.seed,
            response_format={"type": "json_object"},
        )

    # QAPairGenerator can generate sparse questions with detailed answers.
    def test_generate_sparse_questions_with_detailed_answers(self, mocker):
        document = "This is a sample document."
        temperature = 0.8

        openai_mocker = mocker.patch(
            "openai.resources.chat.completions.Completions.create",
            return_value=_openai_chat_completion_response,
        )

        generator = QAPairGenerator(openai_key="valid_key", openai_model="valid_model")

        questions, metadata = generator.process(
            document, temperature=temperature, question_type="sparse"
        )

        assert questions == [
            {
                "question": "What is the document about?",
                "answer": "The document is about a sample topic.",
            }
        ]

        mock_return_value = _openai_chat_completion_response
        assert metadata == {
            "finish_reason": mock_return_value.choices[0].finish_reason,
            "usage": {
                "completion_tokens": mock_return_value.usage.completion_tokens,
                "prompt_tokens": mock_return_value.usage.prompt_tokens,
                "total_tokens": mock_return_value.usage.total_tokens,
            },
        }
        openai_mocker.assert_called_once_with(
            model="valid_model",
            messages=[
                {
                    "role": "system",
                    "content": generator.question_types["sparse"]["system_message"],
                },
                {
                    "role": "user",
                    "content": generator.question_types["sparse"]["instruction"]
                    + generator.output_format,
                },
                {"role": "user", "content": "\nHere is the given text:\n\n" + document},
            ],
            temperature=temperature,
            seed=generator.seed,
            response_format={"type": "json_object"},
        )

    # QAPairGenerator raises a ValueError if an invalid question type is provided.
    def test_raise_value_error_for_invalid_question_type(self):
        generator = QAPairGenerator(openai_key="valid_key", openai_model="valid_model")

        with pytest.raises(ValueError):
            generator.process("This is a sample document.", question_type="invalid")

    # QAPairGenerator raises a ValueError if the output format is invalid.
    def test_raise_value_error_for_invalid_output_format(self):
        generator = QAPairGenerator(openai_key="valid_key", openai_model="valid_model")

        with pytest.raises(ValueError):
            generator.sanitize_output_format("invalid_output")


# returns previously generated questions and answers if the output file already exists.
def test_return_previously_generated_questions_and_answers_if_output_file_exists(
    mocker,
):
    openai_mocker = mocker.patch(
        "openai.resources.chat.completions.Completions.create",
        return_value=_openai_chat_completion_response,
    )

    document = "This is a sample document."
    output_file = "tests/assets/output.json"

    # mocker.patch.object(Path, "exists", return_value=True)
    # mocker.pathc.object(open, "read", return_value=json.dumps([]))
    mocker.patch.object(
        json,
        "load",
        return_value=[
            {
                "question": "What is the document about?",
                "answer": "The document is about a sample topic.",
            }
        ],
    )

    result = generate_top_sections_questions(
        {"text": document}, output_file=output_file
    )

    assert result == [
        {
            "question": "What is the document about?",
            "answer": "The document is about a sample topic.",
        }
    ]

    json.load.assert_called_once_with(mocker.ANY)
    openai_mocker.assert_not_called()


# QAPairGenerator can generate a list of questions and answers in JSON format.
def test_generate_questions_and_answers(mocker):
    openai_mocker = mocker.patch(
        "openai.resources.chat.completions.Completions.create",
        return_value=_openai_chat_completion_response,
    )

    # Create an instance of QAPairGenerator
    generator = QAPairGenerator(openai_key="valid_key", openai_model="valid_model")

    # Mock the document and call the process method
    document = "This is a sample document."
    questions, metadata = generator.process(document)

    # Assert the output
    assert questions == eval(
        _openai_chat_completion_response.choices[0].message.content
    )

    assert (
        metadata["finish_reason"]
        == _openai_chat_completion_response.choices[0].finish_reason
    )

    assert metadata["usage"] == _openai_chat_completion_response.usage.model_dump()
    assert openai_mocker.call_count == 1


# QAPairGenerator can sanitize the output format of generated questions and answers.
def test_sanitize_output_format(mocker):
    # Create an instance of QAPairGenerator
    generator = QAPairGenerator(openai_key="valid_key", openai_model="valid_model")

    # Define input and expected output
    input_output_pairs = [
        (
            {
                "questions": [
                    {"question": "Q1", "answer": "A1"},
                    {"question": "Q2", "answer": "A2"},
                ]
            },
            [
                {"question": "Q1", "answer": "A1"},
                {"question": "Q2", "answer": "A2"},
            ],
        ),
        (
            [
                {"question": "Q1", "answer": "A1"},
                {"question": "Q2", "answer": "A2"},
            ],
            [
                {"question": "Q1", "answer": "A1"},
                {"question": "Q2", "answer": "A2"},
            ],
        ),
        (
            {"questions": [{"question": "Q1", "answer": "A1"}]},
            [{"question": "Q1", "answer": "A1"}],
        ),
        (
            [{"questions": [{"question": "Q1", "answer": "A1"}]}],
            [{"question": "Q1", "answer": "A1"}],
        ),
    ]

    # Test the sanitize_output_format method
    for input_data, expected_output in input_output_pairs:
        output = generator.sanitize_output_format(input_data)
        assert output == expected_output


# make_simple_sample_for_openai returns a dictionary with the expected keys and values
def test_make_simple_sample_for_openai_returns_dictionary():
    # Arrange
    question = "What is the capital of France?"
    answer = "Paris"

    # Act
    result = make_simple_sample_for_openai(question, answer)

    # Assert
    assert isinstance(result, dict)
    assert "messages" in result
    assert isinstance(result["messages"], list)
    assert len(result["messages"]) == 3
    assert result["messages"][0]["role"] == "system"
    assert (
        result["messages"][0]["content"]
        == "You are a trusted factual chatbot that only answers questions"
        " about generative agents."
    )
    assert result["messages"][1]["role"] == "user"
    assert result["messages"][1]["content"] == question
    assert result["messages"][2]["role"] == "assistant"
    assert result["messages"][2]["content"] == answer


# make_instruction_sample_for_openai returns a dictionary with the expected keys
# and values
def test_make_instruction_sample_for_openai_returns_dictionary():
    # Arrange
    question = "What is the capital of France?"
    answer = "Paris"
    references = ["Reference 1", "Reference 2"]

    # Act
    result = make_instruction_sample_for_openai(question, answer, references)

    # Assert
    assert isinstance(result, dict)
    assert "messages" in result
    assert isinstance(result["messages"], list)
    assert len(result["messages"]) == 3
    assert result["messages"][0]["role"] == "system"
    assert (
        result["messages"][0]["content"]
        == "You are a trusted factual chatbot. You always answer questions based"
        " strictly on the provided reference."
    )
    assert result["messages"][1]["role"] == "user"
    assert (
        result["messages"][1]["content"]
        == "Reference(s):\n\n===\nReference 1\n===\n\n===\nReference"
        " 2\n===\n\nStrictly according to the provided reference(s), give an"
        " answer as detailed as possible to the following question: What is the"
        " capital of France?"
    )
    assert result["messages"][2]["role"] == "assistant"
    assert result["messages"][2]["content"] == answer

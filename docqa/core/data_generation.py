import json
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, computed_field

from .chunking import chunk_content
from .doc_tree import get_section_full_text


class QAPairGenerator(BaseModel):
    """
    Generates questions and answers for sections and subsections of a document.

    Args:
        openai_key (str): The API key for OpenAI.
        openai_model (str): The name of the OpenAI model to use.
        seed (int, optional): The seed for the random number generator. Defaults to 42.
    """

    class Config:
        arbitrary_types_allowed = True

    openai_key: str
    openai_model: str
    seed: int = 42

    @computed_field  # type: ignore[misc]
    @property
    def openai_client(self) -> OpenAI:
        return OpenAI(api_key=self.openai_key)

    output_format: str = (
        "Present your questions along with the detailed answers in the following JSON"
        ' format: [{"question": str, "answer": str}, ...].'
    )

    @computed_field  # type: ignore[misc]
    @property
    def question_types(self) -> dict[str, dict[str, str]]:
        return {
            "sparse": {
                "system_message": (
                    "You are a professional examiner. Your job is to give questions to"
                    " test people's understanding of a given document."
                ),
                "instruction": (
                    "You are given a document, your goal is:\n- construct a list of"
                    " different complex questions that can be answered based **solely**"
                    " on the given text.\n- make sure to cover all of the topics"
                    " described in the document.\n- include the answer for each"
                    " question, the answers should be as detailed as"
                    " possible.\n"
                ),
            },
            "dense": {
                "system_message": "You are a top university professor.",
                "instruction": (
                    "You are a top university professor. You have the below text and"
                    " you want to test the student's understanding of it. If you can"
                    " only ask {num_questions} question(s) but must cover all of the"
                    " content and the answer(s) to those questions must contain"
                    " **solely** the information presented in the given text, what"
                    " would you ask?\n"
                ),
            },
        }

    @staticmethod
    def sanitize_output_format(output: dict | list) -> list[dict]:
        """This static method takes in an `output` of type `dict` or `list` and returns
            a sanitized `list[dict]` output.

        Args:
            output (dict | list): The input `output` that needs to be sanitized.

        Returns:
            list[dict]: The sanitized output as a list of dictionaries.

        Raises:
            ValueError: If the `output` format is invalid.

        """
        if isinstance(output, dict):
            if list(output.keys()) == ["questions"]:
                if isinstance(output["questions"], list):
                    output = output["questions"]
            else:
                output = [output]
        elif isinstance(output, list):
            if list(output[0].keys()) == ["questions"]:
                output = output[0]["questions"]
        else:
            raise ValueError(f"Invalid output format: {type(output)}")

        return output  # type: ignore[return-value]

    def process(
        self,
        document: str,
        temperature: float = 1.0,
        question_type: str = "comprehension",
        num_questions: int = 5,
    ) -> tuple[list[dict[str, str]], list[dict]]:
        """
        Process the given document to generate a list of questions and answers.

        Args:
            document (str): The text document to process.
            temperature (float, optional): The temperature parameter for controlling
                the randomness of the output. Defaults to 1.0.
            question_type (str, optional): The type of questions to generate.
                Defaults to "comprehension".
            num_questions (int, optional): The number of questions to generate.
                Defaults to 5.

        Returns:
            tuple[list[dict[str, str]], list[dict]]: A tuple containing a list of
                questions and answers and a list of metadata.

        Raises:
            ValueError: If an invalid question type is provided.
        """
        if question_type not in self.question_types:
            raise ValueError(f"Invalid question type: {question_type}")

        system_message = self.question_types[question_type]["system_message"]
        instruction = self.question_types[question_type]["instruction"].format(
            num_questions=num_questions
        )
        messages = [
            {"role": "system", "content": system_message},
            {
                "role": "user",
                "content": instruction + self.output_format,
            },
            {"role": "user", "content": "\nHere is the given text:\n\n" + document},
        ]

        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            temperature=temperature,
            seed=self.seed,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content.strip()

        output = json.loads(text)
        output = self.sanitize_output_format(output)

        metadata = {}
        metadata["finish_reason"] = response.choices[0].finish_reason
        metadata["usage"] = {
            "completed_tokens": response.usage.completion_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        return output, metadata  # type: ignore[return-value]


class AnswerGenerator(BaseModel):
    """Generate an answer to a question based on a reference.

    Args:
        openai_key (str): The OpenAI API key.
        openai_model (str): The name of the OpenAI model to use.
        seed (int, optional): The seed for the random number generator. Defaults to 42.
    """

    class Config:
        arbitrary_types_allowed = True

    openai_key: str
    openai_model: str
    seed: int = 42

    @computed_field  # type: ignore[misc]
    @property
    def openai_client(self) -> OpenAI:
        return OpenAI(api_key=self.openai_key)

    system_message: str = (
        "You are a trusted factual chatbot. You always answer questions based strictly"
        " on the provided reference."
    )
    instruction: str = (
        "Reference(s):\n\n{reference}\n\nStrictly according to the provided"
        " reference(s), give an answer as detailed as possible to the following"
        " question: {question}"
    )

    def process(
        self,
        question: str,
        reference: str,
        temperature: float = 1.0,
    ) -> tuple[str, dict]:
        """
        Process the given question and generate a response using the OpenAI model.

        Parameters:
            question (str): The question to be processed.
            reference (str): The reference string for the instruction.
            temperature (float, optional): The temperature parameter for generating the
                response. Higher values (e.g., 1.0) make the output more random, while
                lower values (e.g., 0.2) make it more focused and deterministic.
                Defaults to 1.0.

        Returns:
            Tuple[str, dict]: A tuple containing the generated answer and metadata.
                - answer (str): The generated answer as a string.
                - metadata (dict): Additional metadata about the response.
                    - finish_reason (str): The reason why the completion finished.
                    - usage (dict): Usage statistics of the completion.
                        - completed_tokens (int): The number of tokens used for
                            completion.
                        - prompt_tokens (int): The number of tokens used for the prompt.
                        - total_tokens (int): The total number of tokens used.
        """
        messages = [
            {"role": "system", "content": self.system_message},
            {
                "role": "user",
                "content": self.instruction.format(
                    reference=reference, question=question
                ),
            },
        ]

        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            temperature=temperature,
            seed=self.seed,
        )
        answer = response.choices[0].message.content.strip()

        metadata = {}
        metadata["finish_reason"] = response.choices[0].finish_reason
        metadata["usage"] = {
            "completed_tokens": response.usage.completion_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        return answer, metadata


def generate_top_sections_questions(
    doc_tree: dict,
    output_file: Path,
    openai_key: str = "",
    openai_model: str = "",
    seed: int = 42,
    temperature: float = 1.0,
) -> dict:
    """
    Generate the top sections with questions based on the provided document tree.

    Args:
        doc_tree (dict): The document tree representing the sections of the document.
        output_file (Path): The path to the output file where the top sections with
            uestions will be saved.
        openai_key (str, optional): The OpenAI API key. Defaults to an empty string.
        openai_model (str, optional): The OpenAI model to use for question generation.
            Defaults to an empty string.
        seed (int, optional): The seed value for random number generation.
            Defaults to 42.
        temperature (float, optional): The temperature parameter for question
            generation.
            Defaults to 1.0.

    Returns:
        dict: The top sections with questions.
    """
    output_file = Path(output_file)
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            top_sections_with_questions = json.load(f)
        return top_sections_with_questions

    qa_gen = QAPairGenerator(
        openai_key=openai_key,
        openai_model=openai_model,
        seed=seed,
    )

    top_sections_with_questions = {}
    if doc_tree["text"]:
        top_sections_with_questions[""] = {
            "text": doc_tree["text"],
            "chunks_count": len(chunk_content(doc_tree["text"])),
        }

    for section in doc_tree.get("child_sections", []):
        full_text = get_section_full_text(section)
        top_sections_with_questions[section["heading"]] = {
            "text": full_text,
            "chunks_count": len(chunk_content(full_text)),
        }

    for heading, section in top_sections_with_questions.items():
        print(f"Generating questions for {heading}")
        dense_questions, _ = qa_gen.process(
            section["text"],
            question_type="dense",
            num_questions=section["chunks_count"],
            temperature=temperature,
        )
        sparse_questions, _ = qa_gen.process(
            section["text"],
            question_type="sparse",
            temperature=temperature,
        )
        top_sections_with_questions[heading]["dense_questions"] = dense_questions
        top_sections_with_questions[heading]["sparse_questions"] = sparse_questions

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(top_sections_with_questions, f, indent=4, ensure_ascii=False)

    return top_sections_with_questions


def generate_long_answers_for_sections_questions(
    sections_with_questions: dict,
    output_file: Path,
    openai_key: str = "",
    openai_model: str = "",
    seed: int = 42,
    temperature: float = 1.0,
) -> dict:
    """
    Generate long answers for sections' questions.

    Args:
        sections_with_questions (dict): A dictionary containing sections with their
            corresponding questions.
        output_file (Path): The path to the output file where the generated long answers
            will be stored.
        openai_key (str, optional): The API key for OpenAI. Defaults to an empty string.
        openai_model (str, optional): The name of the OpenAI model to use. Defaults to
            an empty string.
        seed (int, optional): The seed value for random number generation.
            Defaults to 42.
        temperature (float, optional): The temperature parameter for generating answers.
            Defaults to 1.0.

    Returns:
        dict: A dictionary containing sections with their corresponding questions and
            generated long answers.
    """
    output_file = Path(output_file)
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            sections_with_questions_and_long_answers = json.load(f)
        return sections_with_questions_and_long_answers

    answer_gen = AnswerGenerator(
        openai_key=openai_key,
        openai_model=openai_model,
        seed=seed,
    )
    for heading, section in sections_with_questions.items():
        print(f"Generating long answers for dense questions of {heading}")
        reference = f"===\n[source: {heading}]\n{section['text']}\n===\n"
        import pdb

        pdb.set_trace()
        for question in section["dense_questions"]:
            answer, _ = answer_gen.process(
                question=question["question"],
                reference=reference,
                temperature=temperature,
            )
            question["long_answer"] = answer

        print(f"Generating long answers for sparse questions of {heading}")
        for question in section["sparse_questions"]:
            answer, _ = answer_gen.process(
                question=question["question"],
                reference=reference,
                temperature=temperature,
            )
            question["long_answer"] = answer

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(sections_with_questions, f, indent=4, ensure_ascii=False)

    return sections_with_questions


def make_simple_sample_for_openai(question: str, answer: str) -> dict:
    """
    Generates a simple sample for OpenAI chat conversation.

    Args:
        question (str): The user's question.
        answer (str): The assistant's answer.

    Returns:
        dict: A dictionary containing the chat conversation sample.

    Example:
        make_simple_sample_for_openai("What is the capital of France?", "Paris")
    """
    return {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a trusted factual chatbot that only answers questions"
                    " about generative agents."
                ),
            },
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
    }


def make_instruction_sample_for_openai(
    question: str, answer: str, references: list[str]
) -> dict:
    """
    Generates a function comment for the given function body.

    Args:
        question (str): The question to be used in the instruction.
        answer (str): The answer to be used in the instruction.
        references (list[str]): A list of reference texts to be included in the
            instruction.

    Returns:
        dict: The generated function comment in the form of a dictionary.
    """
    reference_text = "\n\n".join(["===\n" + ref + "\n===" for ref in references])
    system_message = AnswerGenerator.model_fields["system_message"].default
    instruction = AnswerGenerator.model_fields["instruction"].default
    instruction = instruction.format(reference=reference_text, question=question)
    return {
        "messages": [
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": instruction,
            },
            {"role": "assistant", "content": answer},
        ]
    }

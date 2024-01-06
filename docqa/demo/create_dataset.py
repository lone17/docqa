import json
import os
from itertools import product
from pathlib import Path
from typing import Literal

from config import SECTIONS
from dotenv import find_dotenv, load_dotenv

from docqa.core.data_generation import (
    generate_long_answers_for_sections_questions,
    generate_top_sections_questions,
    make_instruction_sample_for_openai,
    make_simple_sample_for_openai,
)
from docqa.core.data_validation import check_format, dataset_stats
from docqa.core.doc_tree import build_doc_tree_from_pdf

load_dotenv(find_dotenv(".env"))


def create_openai_dataset(
    sections_qa_data_flatten: dict,
    section_type: Literal[
        "main", "summary", "metadata", "extra"
    ] = "main",  # keys in SECTIONS
    question_type: Literal["dense", "sparse"] = "dense",
    answer_type: Literal["long", "short"] = "long",
    prompt_type: Literal["instruction", "simple"] = "instruction",
) -> list[dict]:
    """
    Generate a dataset for OpenAI based on the given sections QA data.

    Parameters:
    - sections_qa_data_flatten (dict): A dictionary containing the flattened sections
        QA data.
    - section_type (Literal["main", "summary", "metadata", "extra"], optional): The
        type of section to include in the dataset. Defaults to "main".
    - question_type (Literal["dense", "sparse"], optional): The type of question to
        include in the dataset. Defaults to "dense".
    - answer_type (Literal["long", "short"], optional): The type of answer to include
        in the dataset. Defaults to "long".
    - prompt_type (Literal["instruction", "simple"], optional): The type of prompt to
        use in the dataset. Defaults to "instruction".

    Returns:
    - list[dict]: The generated dataset for OpenAI.

    Note:
    - The dataset is generated based on the specified parameters.
    - Only sections that exist in the sections QA data will be included in the dataset.
    - For each section, the questions and answers are extracted based on the question
        type and answer type.
    - Depending on the prompt type, different sample generation functions are used to
        create the samples.
    - The dataset is a list of dictionaries, where each dictionary represents a sample.

    """
    dataset = []
    for heading in SECTIONS[section_type]:
        if heading not in sections_qa_data_flatten:
            continue
        section = sections_qa_data_flatten[heading]
        qa_list = section[f"{question_type}_questions"]
        for item in qa_list:
            question = item["question"]
            answer = item["answer"] if answer_type == "short" else item["long_answer"]
            if prompt_type == "simple":
                sample = make_simple_sample_for_openai(question, answer)
            elif prompt_type == "instruction":
                reference = f"[source: {heading}]\n{section['text']}\n"
                sample = make_instruction_sample_for_openai(
                    question=question,
                    answer=answer,
                    references=[reference],
                )
            dataset.append(sample)

    return dataset


def pdf_to_qa_data(output_dir: Path, pdf_file: Path) -> dict:
    """
    Generates a QA data dictionary from a PDF file.

    Args:
        output_dir (Path): The directory where the output files will be saved.
        pdf_file (Path): The path to the PDF file.

    Returns:
        dict: The generated QA data dictionary.
    """
    doc_tree_file = output_dir / "doc_tree.json"

    if doc_tree_file.exists():
        with open(doc_tree_file, "r", encoding="utf-8") as f:
            doc_tree = json.load(f)
    else:
        doc_tree = build_doc_tree_from_pdf(pdf_file, output_dir=output_dir)

    top_sections_qa_data = generate_top_sections_questions(
        doc_tree,
        output_file=output_dir / "top_sections_qa_data.json",
        openai_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", ""),
        seed=int(os.getenv("SEED", 42)),
        temperature=1.0,
    )
    top_sections_qa_data = generate_long_answers_for_sections_questions(
        top_sections_qa_data,
        output_file=output_dir / "top_sections_qa_data_long_answers.json",
        openai_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", ""),
        seed=int(os.getenv("SEED", 42)),
        temperature=1.0,
    )

    return top_sections_qa_data


if __name__ == "__main__":
    data_dir = Path("data/generative_agent")
    pdf_file = data_dir / "generative_agent (1).pdf"

    # generate the dataset
    top_sections_qa_data = pdf_to_qa_data(data_dir, pdf_file)

    # create the dataset
    for options in [
        (["main"], ["dense", "sparse"], ["long"], ["instruction"]),
        (["summary"], ["dense", "sparse"], ["long"], ["instruction"]),
    ]:
        final_dataset = []
        for section_type, question_type, answer_type, prompt_type in product(*options):
            dataset = create_openai_dataset(
                sections_qa_data_flatten=top_sections_qa_data,
                section_type=section_type,  # type: ignore[arg-type]
                question_type=question_type,  # type: ignore[arg-type]
                answer_type=answer_type,  # type: ignore[arg-type]
                prompt_type=prompt_type,  # type: ignore[arg-type]
            )
            final_dataset.extend(dataset)

        data_file_name = "-".join("+".join(attributes) for attributes in options)

        print("-" * 50)
        print("{data_file_name}:", len(final_dataset))

        output_file = data_dir / f"{data_file_name}.jsonl"

        # validate the dataset
        check_format(final_dataset)
        dataset_stats(final_dataset)

        # save the dataset
        final_dataset_lines = [
            json.dumps(sample, ensure_ascii=False) for sample in final_dataset
        ]
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(final_dataset_lines))

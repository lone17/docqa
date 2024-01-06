import json
import os
from pathlib import Path

from .markdown import (
    find_highest_markdown_heading_level,
    pdf_to_markdown,
    preprocess_sections,
    tidy_markdown_sections,
)


def build_doc_tree_from_markdown(
    text: str,
) -> dict:
    """
    Takes a string representation of a markdown file as input.
    Finds the highest level of heading and splits the text into sections accordingly.
    Returns a list of tuples, each containing the section title and section content.

    Args:
        text (str): The content of a markdown file as a single string.

    Returns:
        dict: A dictionary containing the tree structure of the markdown file. Each
            section is represented as a dictionary with the following keys:
            ```
            {
                "heading": "Section 1",
                "text": "Section 1 opening text",
                "child_sections": [
                    {
                        "heading": "Section 1.1",
                        "text": "Section 1.1 opening text",
                        "child_sections": [
                            ...
                        ]
                    },
                    ...
                ]
            }
            ```
    """
    lines = text.strip().split("\n")

    # Find the highest heading level
    highest_heading_level = find_highest_markdown_heading_level(lines)

    # If there are no headings, return the text as a single section
    if highest_heading_level is None:
        return {"heading": "", "text": text}

    # Construct the heading prefix for splitting
    headings_prefix = ("#" * highest_heading_level) + " "

    n = len(lines)
    i = 0
    opening_text_lines = []
    while i < n and not lines[i].startswith(headings_prefix):
        opening_text_lines.append(lines[i])
        i += 1

    root = {
        "heading": "",
        "text": "\n".join(opening_text_lines).strip(),
        "child_sections": [],
    }

    current_section_title = ""
    current_section_lines: list[str] = []

    # Split the text at the highest heading level
    while i < n:
        line = lines[i]
        # Check if the line starts with the highest heading level prefix
        if line.startswith(headings_prefix):
            # If the current_section is not empty, add it to the sections list
            if len(current_section_lines) > 0:
                current_section_body = "\n".join(current_section_lines).strip()
                child_section = build_doc_tree_from_markdown(current_section_body)
                child_section["heading"] = current_section_title
                root["child_sections"].append(child_section)  # type: ignore

            # Update the current_section_title and clear the current_section
            current_section_title = line.strip()
            current_section_lines = []
        else:
            # Add the line to the current_section
            current_section_lines.append(line)
        i += 1

    # Add the last section to the sections list (if not empty)
    if len(current_section_lines) > 0:
        current_section_body = "\n".join(current_section_lines).strip()
        child_section = build_doc_tree_from_markdown(current_section_body)
        child_section["heading"] = current_section_title
        root["child_sections"].append(child_section)  # type: ignore[attr-defined]

    return root


def build_doc_tree_from_pdf(input_file: Path, output_dir: Path) -> dict:
    """
    Generate a document tree from a PDF file.

    Args:
        input_file (Path): The path to the input PDF file.
        output_dir (Path): The directory where the output files will be saved.

    Notes:
        - The function first checks if the marker output file exists in the output
            directory.
        - If the marker output file exists, it reads the content of the file.
        - If the marker output file does not exist, it converts the input PDF file to
            markdown using the `pdf_to_markdown` function.
        - The function then checks if the tidy text sections file exists in the output
            directory.
        - If the tidy text sections file exists, it reads the content of the file.
        - If the tidy text sections file does not exist, it builds a document tree from
            the marker markdown content using the `build_doc_tree_from_markdown`
            function.
        - The function flattens the document tree using the `flatten_doc_tree` function.
        - It preprocesses the sections using the `preprocess_sections` function.
        - The function then tidies the markdown sections and retrieves the metadata
            using the `tidy_markdown_sections` function.
        - Finally, it saves the tidy text sections to a file, writes the tidy markdown
            content to a file, and saves the metadata to a file.

    Returns:
        dict: The final document tree generated from the PDF.

    Raises:
        FileNotFoundError: If the marker output file or tidy text sections file does
            not exist.
    """
    marker_output_file = output_dir / "marker_output.md"

    if marker_output_file.exists():
        with open(marker_output_file, "r", encoding="utf-8") as f:
            marker_markdown = f.read()
    else:
        marker_markdown = pdf_to_markdown(input_file, marker_output_file)

    tidy_text_sections_file = output_dir / "tidy_text_sections.json"
    tidy_markdown_file = output_dir / "tidy_output.md"

    if tidy_text_sections_file.exists():
        with open(tidy_text_sections_file, "r", encoding="utf-8") as f:
            tidy_text_sections = json.load(f)
        tidy_markdown = "\n\n".join(tidy_text_sections)
    else:
        doc_tree = build_doc_tree_from_markdown(marker_markdown)
        sections = flatten_doc_tree(doc_tree)
        sections = preprocess_sections(sections)
        tidy_sections, all_metadata = tidy_markdown_sections(
            sections,
            openai_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", ""),
            seed=int(os.getenv("SEED", 42)),
        )

        tidy_text_sections = [
            f"{header.strip()}\n\n{content.strip()}".strip()
            for header, content in tidy_sections
        ]
        tidy_markdown = "\n\n".join(tidy_text_sections)

        with open(tidy_text_sections_file, "w", encoding="utf-8") as f:
            json.dump(tidy_text_sections, f, indent=4)

        with open(tidy_markdown_file, "w", encoding="utf-8") as f:
            f.write(tidy_markdown)

        with open(output_dir / "tidy_metadata.json", "w", encoding="utf-8") as f:
            json.dump(all_metadata, f, indent=4)

        print(
            "total completion tokens:",
            sum([m.get("usage", {}).get("total_tokens", 0) for m in all_metadata]),
        )
        print(
            "total prompt tokens:",
            sum([m.get("usage", {}).get("prompt_tokens", 0) for m in all_metadata]),
        )
        print(
            "total completed tokens:",
            sum([m.get("usage", {}).get("completed_tokens", 0) for m in all_metadata]),
        )

    final_doc_tree = build_doc_tree_from_markdown(tidy_markdown)
    doc_tree_file = output_dir / "doc_tree.json"
    with open(doc_tree_file, "w", encoding="utf-8") as f:
        json.dump(final_doc_tree, f, indent=4)

    return final_doc_tree


def flatten_doc_tree(root: dict) -> list:
    """
    Recursively flattens a nested dictionary representing a document tree.

    Parameters:
        root (dict): The root node of the document tree.

    Returns:
        list: A list of tuples representing the flattened document tree. Each tuple
            contains a heading and its corresponding text.
    """
    if root["heading"] or root["text"]:
        sections = [(root["heading"], root["text"])]
    else:
        sections = []
    for section in root.get("child_sections", []):
        sections.extend(flatten_doc_tree(section))
    return sections


def get_section_full_text(section: dict) -> str:
    """
    Retrieves the full text of a section from a given dictionary.

    Args:
        section (dict): The section to retrieve the full text from.

    Returns:
        str: The full text of the section.
    """
    flatten_sections = flatten_doc_tree(section)
    text_sections = [
        f"{header.strip()}\n\n{content.strip()}".strip()
        for header, content in flatten_sections
    ]

    full_text = "\n\n".join(text_sections)

    return full_text

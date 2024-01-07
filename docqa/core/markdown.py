import re
from pathlib import Path

import editdistance
import tiktoken
from marker.convert import convert_single_pdf
from marker.models import load_all_models
from openai import OpenAI
from pydantic import BaseModel, computed_field


class MarkdownTidier(BaseModel):
    """
    Tidies the given markdown text using OpenAI's model.

    Args:
        openai_key (str): The OpenAI API key.
        openai_model (str): The OpenAI model to use.
        seed (int, optional): The seed for the random number generator. Defaults to 42.
        system_message (str, optional): The system message for the OpenAI model.
        instruction (str, optional): The instruction for the OpenAI model.
        api_client (OpenAI): The OpenAI client.
    """

    class Config:
        arbitrary_types_allowed = True

    openai_key: str
    openai_model: str
    seed: int = 42
    system_message: str = (
        "You are a professional editor. Your job is to reconstruct the broken markdown"
        " text."
    )
    instruction: str = (
        "You are given a markdown text which was converted from pdf and thus has "
        "mixed-up sentences and paragraphs structure, your job is:\n"
        "- reconstruct the text with proper sentences and paragraphs.\n"
        "- keep the headings unchanged.\n"
        "- keep the original content verbatim.\n"
        "- discard unrelated text.\n"
        "Answer with **only the reconstructed text**  and nothing else.\n"
    )

    @computed_field  # type: ignore[misc]
    @property
    def openai_client(self) -> OpenAI:
        return OpenAI(api_key=self.openai_key)

    def process(self, markdown_text: str, temperature: float = 0.7) -> tuple[str, dict]:
        """
        Generates a response to a given markdown text using the OpenAI chat model.

        Args:
            markdown_text (str): The input markdown text to generate a response for.
            temperature (float, optional): The temperature of the model's output.
                Higher values make the output more random, while lower values make it
                more focused and deterministic. Defaults to 0.7.

        Returns:
            str: The generated response text.
            dict: Metadata about the completion process, including the finish reason
                and token usage.

        Example:
            >>> process("Hello, how are you?")
            (
                'I am fine, thank you!',
                {
                    'finish_reason': 'stop',
                    'usage': {
                        'completed_tokens': 48,
                        'prompt_tokens': 6,
                        'total_tokens': 54
                    }
                }
            )
        """
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": self.instruction},
            {"role": "user", "content": markdown_text},
        ]

        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            temperature=temperature,
            seed=self.seed,
        )

        text = response.choices[0].message.content.strip()

        metadata = {}
        metadata["finish_reason"] = response.choices[0].finish_reason
        metadata["usage"] = {
            "completed_tokens": response.usage.completion_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        return text, metadata


def find_highest_markdown_heading_level(lines: list[str]) -> int | None:
    """
    Takes a list of lines representing a markdown file as input.
    Finds the highest level of heading and returns it as an integer.
    Returns None if the text contains no headings.

    source: https://github.com/nestordemeure/question_extractor/blob/main/
            question_extractor/markdown.py

    Args:
        lines (list of str): A list of lines in the markdown file.

    Returns:
        int or None: The highest heading level as an integer, or None if no headings
            are found.
    """
    highest_heading_level = None
    code_section = False

    # Iterate through the lines in the markdown file
    for line in lines:
        """
        Check code section e.g.:
            ```bash
            # Trace an IP packet between two Pods
            antctl trace-packet -S ns1/pod1 -D ns2/pod2
            # Trace a Service request from a local Pod
            antctl trace-packet -S ns1/pod1 -D ns2/svc2 -f "tcp,tcp_dst=80"
            # Trace the Service reply packet (assuming "ns2/pod2" is the Service
            # backend Pod)
            antctl trace-packet -D ns1/pod1 -S ns2/pod2 -f "tcp,tcp_src=80"
            # Trace an IP packet from a Pod to gateway port
            antctl trace-packet -S ns1/pod1 -D antrea-gw0
            # Trace a UDP packet from a Pod to an IP address
            antctl trace-packet -S ns1/pod1 -D 10.1.2.3 -f udp,udp_dst=1234
            # Trace a UDP packet from an IP address to a Pod
            antctl trace-packet -D ns1/pod1 -S 10.1.2.3 -f udp,udp_src=1234
            ```
        Here # is a code comment not the md level symbole
        """
        if line.startswith("```"):
            code_section = not code_section
        # Check if the line starts with a heading
        if line.startswith("#") and not code_section:
            # Calculate the heading level based on the number of '#' characters
            current_heading_level = len(line.split()[0])

            # Update the highest_heading_level if it is None or if the current_heading_
            # level is higher
            if (highest_heading_level is None) or (
                current_heading_level < highest_heading_level
            ):
                highest_heading_level = current_heading_level

    return highest_heading_level


def pdf_to_markdown(
    pdf_file: Path,
    output_file: Path,
    max_pages: int | None = None,
    parallel_factor: int = 1,
    cache_dir: Path = Path(".cache/pdf_to_markdown/"),
) -> str:
    """
    Converts a PDF file to Markdown format and saves the result to an output file.

    Args:
        pdf_file (Path): The path to the PDF file to be converted.
        output_file (Path): The path to the output file where the converted Markdown
            will be saved.
        max_pages (int | None, optional): The maximum number of pages to convert.
            Defaults to None.
        parallel_factor (int, optional): The number of parallel processes to use for
            conversion. Defaults to 1.
        cache_dir (Path, optional): The directory to use for caching the conversion

    Returns:
        str: The converted Markdown text.
    """
    markdown_text, metadata = convert_single_pdf(
        pdf_file,
        model_lst=load_all_models(),
        max_pages=max_pages,
        parallel_factor=parallel_factor,
        cache_dir=cache_dir,
    )

    if output_file is not None:
        output_file = Path(output_file)
        output_file.parent.mkdir(exist_ok=True, parents=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_text)

    return markdown_text


def filter_empty_sections(sections: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """
    Filters out empty sections from a list of tuples.

    Args:
        sections (list[tuple[str, str]]): A list of tuples representing sections, where
            each tuple contains a header (str) and content (str).

    Returns:
        list[tuple[str, str]]: A list of tuples representing non-empty sections, where
            each tuple contains a header (str) and content (str).
    """
    return [(header, content) for header, content in sections if header or content]


def merge_abstract_with_previous_sections(sections: list[tuple[str, str]]):
    """
    If found an Abstract section then assume it's a research paper and merge it with
    all previous sections, this is because the authors section might have more column
    thus messes up the parsed order

    Args:
        sections (list[tuple[str, str]]): A list of tuples representing sections, where
            each tuple contains a header (str) and content (str).

    Returns:
        list[tuple[str, str]]: A list of tuples representing merged sections, where
            each tuple contains a header (str) and content (str).
    """

    if len(sections) < 2:
        return sections

    first_header = sections[0][0]
    text_sections = [sections[0][1]]

    for i in range(1, len(sections)):
        header, content = sections[i]
        current_text = f"{header}\n\n{content}"
        text_sections.append(current_text)
        if re.sub(r"[^a-zA-Z]", "", header).lower() == "abstract":
            combined_text = "\n\n".join(text_sections)
            return [(first_header, combined_text)] + sections[i + 1 :]

    return sections


def preprocess_sections(sections: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """
    Preprocesses the given list of sections by filtering out any empty sections and
    merging any abstract sections with their previous sections.

    Args:
        sections (List[Tuple[str, str]]): A list of tuples representing sections.
            Each tuple contains two strings: the title of the section and the content
            of the section.

    Returns:
        List[Tuple[str, str]]: A list of tuples representing the preprocessed sections.
            Each tuple contains two strings: the title of the section and the content
            of the section.
    """
    sections = filter_empty_sections(sections)
    sections = merge_abstract_with_previous_sections(sections)

    return sections


def text_similarity_score(text1: str, text2: str) -> float:
    """
    Compute the similarity score between two texts.

    Args:
        text1 (str): The first text.
        text2 (str): The second text.

    Returns:
        float: The similarity score between the two texts.
    """
    # remove special characters
    text1 = re.sub(r"[^a-zA-Z0-9\s]", "", text1.lower())
    text2 = re.sub(r"[^a-zA-Z0-9\s]", "", text2.lower())

    # split into words, the words are sorted to allow shuffling of content
    text1_words = sorted(text1.split())
    text2_words = sorted(text2.split())

    return 1 - editdistance.eval(text1_words, text2_words) / (
        max(len(text1_words), len(text2_words)) + 1e-6
    )


def header_similarity_score(header1: str, header2: str) -> float:
    """
    Calculate the similarity score between two headers.

    Parameters:
        header1 (str): The first header.
        header2 (str): The second header.

    Returns:
        float: The similarity score between the two headers.
    """
    return 1 - editdistance.eval(header1, header2) / (
        max(len(header1), len(header2)) + 1e-6
    )


def preserve_content(
    header: str,
    old_content: str,
    new_text: str,
    header_similarity_threshold: float = 0.7,
    content_similarity_threshold: float = 0.8,
) -> tuple[str, float]:
    """
    Calculate the similarity between the given header and new header using a threshold.
    If the similarity score is above the threshold, the new text still contains the
    header, so the content after the header is extracted as the new content.
    If the similarity score is below the threshold, the new text does not contain the
    header, so the entire new text is considered as the new content.
    Calculate the similarity between the old content and new content using a threshold.
    If the similarity score is above the threshold, the content is considered preserved
    and the new content along with its similarity score is returned.
    If the similarity score is below the threshold, the content has been modified too
    much and the old content along with its similarity score is returned.

    Args:
        header (str): The header of the old text.
        old_content (str): The content of the old text.
        new_text (str): The new text.
        header_similarity_threshold (float, optional): The threshold for header
            similarity. Defaults to 0.7.
        content_similarity_threshold (float, optional): The threshold for content
            similarity. Defaults to 0.8.

    Returns:
        tuple[str, float]: A tuple containing the new content and its similarity score.
    """
    parts = new_text.split("\n")
    new_header = parts[0]

    header_similarity = header_similarity_score(header, new_header)
    if header_similarity >= header_similarity_threshold:
        # new text still contains header
        new_content = "\n".join(parts[1:])
    else:
        # new text does not contain header
        new_content = new_text

    content_similarity = text_similarity_score(old_content, new_content)
    if content_similarity >= content_similarity_threshold:
        # content is still preserved
        return new_content, content_similarity
    else:
        # content has been modified too much
        return old_content, content_similarity


def tidy_markdown_sections(
    sections: list[tuple[str, str]],
    max_length: int = 4096,
    openai_key: str = "",
    openai_model: str = "",
    seed: int = 42,
    header_similarity_threshold: float = 0.7,
    content_similarity_threshold: float = 0.8,
) -> tuple[list[tuple[str, str]], list[dict]]:
    """
    Tidies up sections of markdown text by splitting them into header and content, and
    then processing each section using the MarkdownTidier class. It takes a list of
    tuples representing the sections, where each tuple contains a header and
    content. The function also accepts optional parameters such as the maximum
    length of the tidied sections, the OpenAI API key, the OpenAI model to use, a
    seed value for reproducibility, and thresholds for header and content similarity.

    Args:
        sections (list[tuple[str, str]]): A list of tuples representing the sections of
            markdown text. Each tuple contains a header and content.
        max_length (int, optional): The maximum length of the tidied sections.
            Defaults to 4096.
        openai_key (str, optional): The OpenAI API key. Defaults to "".
        openai_model (str, optional): The OpenAI model to use. Defaults to "".
        seed (int, optional): A seed value for reproducibility. Defaults to 42.
        header_similarity_threshold (float, optional): The threshold for header
            similarity. Defaults to 0.7.
        content_similarity_threshold (float, optional): The threshold for content
            similarity. Defaults to 0.8.

    Returns:
        tuple[list[tuple[str, str]], list[dict]]: A tuple containing the tidied
            sections and a list of metadata for each section.
    """
    tidier = MarkdownTidier(openai_key=openai_key, openai_model=openai_model, seed=seed)
    encoding = tiktoken.encoding_for_model(tidier.openai_model)

    tidy_sections = []
    all_metadata: list[dict] = []
    for header, content in sections:
        print("Tidying:", header)
        section_text = f"{header}\n\n{content}"
        if len(encoding.encode(section_text)) > max_length:
            tidy_sections.append((header, content))
            all_metadata.append({})
        else:
            new_section_text, metadata = tidier.process(section_text)
            new_content, similarty = preserve_content(
                header,
                content,
                new_section_text,
                header_similarity_threshold=header_similarity_threshold,
                content_similarity_threshold=content_similarity_threshold,
            )
            print("\tcontent similarity:", similarty)
            tidy_sections.append((header, new_content))
            all_metadata.append(metadata)

    return tidy_sections, all_metadata

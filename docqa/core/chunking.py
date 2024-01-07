import re
from collections import deque


def chunk_content(
    content: str, single_threshold: int = 100, composite_threshold: int = 200
) -> list[str]:
    """
    Generate a list of content chunks from a given string.
    The function will only split at a new line and never in the middle of a sentence.
    Which means it tries its best to preserve the structure of the original text.

    Args:
        content (str): The input string to be chunked.
        single_threshold (int, optional): The minimum length of a single chunk.
            Defaults to 100.
        composite_threshold (int, optional): The maximum length of a composite chunk.
            Defaults to 200.

    Returns:
        list[str]: A list of content chunks.

    Description:
        - This function takes a string `content` and splits it into smaller chunks based
        on the specified thresholds.
        - It first splits the string into parts using the newline and carriage return
        characters as delimiters.
        - It then iterates over each part and checks if the length of the part exceeds
        the `single_threshold`.
        - If it does, it is considered a paragraph and added as a separate chunk.
        - If the length of the current chunk exceeds the `composite_threshold`, it is
        also added as a separate chunk.
        - Finally, the function returns a list of all the generated chunks.

    Example:
        ```python
        content = (
            # long paragraph
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit ... \\n"
            "A quick brown fox jumps over the lazy dog.
        )
        chunk_content(content)
        ```
        ```bash
        ['Lorem ipsum dolor sit amet, consectetur adipiscing elit ...',
        'A quick brown fox jumps over the lazy dog.']
        ```
    """
    if not content:
        return []

    parts = re.split(r"[\n\r]+", content)

    chunks = []
    cur_chunk: deque = deque([])
    cur_length = 0

    for text in parts:
        text_length = len(text.split())
        # if found a text big enough, this could be a paragraph
        if text_length > single_threshold:
            # add the current chunk
            if cur_chunk:
                chunks.append("\n".join(cur_chunk))
            cur_chunk = deque([])
            cur_length = 0
            # then add the found paragraph
            chunks.append(text)
        else:
            # extend the current chunk
            cur_chunk.append(text)
            cur_length += text_length
            # if the current chunk is big enough
            if cur_length > composite_threshold:
                chunks.append("\n".join(cur_chunk))
                # then shorten it down from the left
                while cur_length > single_threshold:
                    discard = cur_chunk.popleft()
                    cur_length -= len(discard.split())

    # the last chunk
    if cur_chunk:
        chunks.append("\n".join(cur_chunk))

    return chunks


def chunk_size_stats(sections: list[tuple[str, str]]):
    """Calculates the statistics of the chunk sizes in the given list of sections.

    Description:
        This function calculates the statistics of the chunk sizes in the given list of
        sections. It iterates through each section and splits the content into
        paragraphs using "\\n\\n" as the delimiter. It then calculates the length of
        each paragraph by splitting it into words and stores them in the
        `paragraph_lengths` list. After that, it filters out the paragraph lengths
        that are less than or equal to 100.

        Next, it prints the average paragraph length by calculating the sum of all
        paragraph lengths and dividing it by the number of paragraph lengths. It then
        prints the 90th percentile paragraph length by sorting the paragraph lengths in
        ascending order and selecting the index that corresponds to 90% of the length
        of the list.

        The function then initializes an empty dictionary `sections_details` to store
        the details of each section. It iterates through each section and checks if the
        header matches any of the predefined keywords. If it does, it initializes an
        empty list `chunks`, otherwise it calls the `chunk_content` function to chunk
        the content and assigns the result to `chunks`. It then adds the details of the
        section to the `sections_details` dictionary.

        Finally, it prints the total number of chunks by summing the lengths of the
        `chunks` list for each section in `sections_details`.

    Args:
        sections (list[tuple[str, str]]): A list of tuples containing a header and
            content for each section. The content is a string.

    """
    paragraph_lengths = []
    for header, content in sections:
        paragraphs = content.split("\n\n")
        paragraph_lengths.extend([len(p.split()) for p in paragraphs])

    paragraph_lengths = [length for length in paragraph_lengths if length > 100]
    print("average paragraph length:", sum(paragraph_lengths) / len(paragraph_lengths))
    print(
        "90 percentile paragraph length:",
        sorted(paragraph_lengths)[int(len(paragraph_lengths) * 0.9)],
    )

    sections_details = {}
    for header, content in sections:
        if re.sub(r"[^a-zA-Z0-9]", "", header.lower()) in (
            "reference",
            "references",
            "acknowledgement",
            "acknowledgements",
        ):
            chunks = []
        else:
            chunks = chunk_content(content)
        sections_details[header] = {
            "content": content,
            "chunks": chunks,
        }
    print(
        "Total number of chunks:",
        sum(len(sec["chunks"]) for sec in sections_details.values()),
    )

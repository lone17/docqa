import pytest

from docqa.core.markdown import (
    MarkdownTidier,
    filter_empty_sections,
    find_highest_markdown_heading_level,
    header_similarity_score,
    merge_abstract_with_previous_sections,
    preprocess_sections,
)


@pytest.fixture
def markdown_sections():
    return [
        ("# Heading 1", "Content under heading 1"),
        ("## Heading 2", "Content under heading 2"),
        ("### Heading 3", "Content under heading 3"),
        ("", "Content with no heading"),
    ]


@pytest.fixture
def tidier_instance():
    return MarkdownTidier(openai_key="", openai_model="gpt-3.5-turbo", seed=42)


# The 'find_highest_markdown_heading_level' function can find the highest heading level
# in a list of markdown lines.
def test_find_highest_markdown_heading_level():
    # Define input markdown lines
    lines = ["# Heading 1", "Some text", "## Heading 2", "More text"]

    # Define expected output
    expected_heading_level = 1

    # Call the find_highest_markdown_heading_level function
    heading_level = find_highest_markdown_heading_level(lines)

    # Check the output
    assert heading_level == expected_heading_level


# The 'preprocess_sections' function can filter and merge sections of markdown text.
def test_preprocess_sections_fixed():
    # Define input sections
    sections = [
        ("Header 1", "Content 1"),
        ("Header 2", "Content 2"),
        ("", "Content 3"),
        ("Header 4", ""),
        ("", "Content 5"),
        ("Header 6", "Content 6"),
    ]

    # Define expected output
    expected_sections = [
        ("Header 1", "Content 1"),
        ("Header 2", "Content 2"),
        ("", "Content 3"),
        ("Header 4", ""),
        ("", "Content 5"),
        ("Header 6", "Content 6"),
    ]

    # Call the preprocess_sections function
    result = preprocess_sections(sections)

    # Check the output
    assert result == expected_sections


# The 'header_similarity_score' function can calculate the similarity score between two
# headers.
def test_header_similarity_score():
    header1 = "This is a header"
    header2 = "This is another header"
    expected_score = 0.727272739669421

    score = header_similarity_score(header1, header2)

    assert score == expected_score


# The 'filter_empty_sections' function can filter out sections with empty headers and
# content.
def test_filter_empty_sections():
    # Define input sections
    sections = [
        ("Header 1", "Content 1"),
        ("", "Content 2"),
        ("Header 3", ""),
        ("", ""),
        ("Header 5", "Content 5"),
    ]

    # Define expected output
    expected_sections = [
        ("Header 1", "Content 1"),
        ("", "Content 2"),
        ("Header 3", ""),
        ("Header 5", "Content 5"),
    ]

    # Call the filter_empty_sections function
    result = filter_empty_sections(sections)

    # Check the output
    assert result == expected_sections


# The 'merge_abstract_with_previous_sections' function can merge the 'Abstract' section
# with the previous section.
def test_merge_abstract_with_previous_sections():
    # Define input sections
    sections = [
        ("Header 1", "Content 1"),
        ("Abstract", "Abstract content"),
        ("Header 2", "Content 2"),
    ]

    # Define expected output
    expected_sections = [
        ("Header 1", "Content 1\n\nAbstract\n\nAbstract content"),
        ("Header 2", "Content 2"),
    ]

    # Call the merge_abstract_with_previous_sections function
    result = merge_abstract_with_previous_sections(sections)

    # Check the output
    assert result == expected_sections

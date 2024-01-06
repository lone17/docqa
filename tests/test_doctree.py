import pytest

from docqa.core.doc_tree import (
    build_doc_tree_from_markdown,
    flatten_doc_tree,
    get_section_full_text,
)


def test_flatten_doc_tree():
    # Test case 1: Flattening a simple document tree with one section
    root = {
        "heading": "Section 1",
        "text": "Section 1 content",
        "child_sections": [],
    }
    expected_output = [("Section 1", "Section 1 content")]
    assert flatten_doc_tree(root) == expected_output

    # Test case 2: Flattening a document tree with nested sections
    root = {
        "heading": "Section 1",
        "text": "Section 1 content",
        "child_sections": [
            {
                "heading": "Section 1.1",
                "text": "Section 1.1 content",
                "child_sections": [],
            },
            {
                "heading": "Section 1.2",
                "text": "Section 1.2 content",
                "child_sections": [],
            },
        ],
    }
    expected_output = [
        ("Section 1", "Section 1 content"),
        ("Section 1.1", "Section 1.1 content"),
        ("Section 1.2", "Section 1.2 content"),
    ]
    assert flatten_doc_tree(root) == expected_output


def test_get_section_full_text():
    # Test case 1: Getting the full text of a section with no child sections
    section = {
        "heading": "Section 1",
        "text": "Section 1 content",
        "child_sections": [],
    }
    expected_output = "Section 1\n\nSection 1 content"
    assert get_section_full_text(section) == expected_output

    # Test case 2: Getting the full text of a section with nested sections
    section = {
        "heading": "Section 1",
        "text": "Section 1 content",
        "child_sections": [
            {
                "heading": "Section 1.1",
                "text": "Section 1.1 content",
                "child_sections": [],
            },
            {
                "heading": "Section 1.2",
                "text": "Section 1.2 content",
                "child_sections": [],
            },
        ],
    }
    expected_output = (
        "Section 1\n\nSection 1 content\n\nSection 1.1\n\nSection 1.1"
        " content\n\nSection 1.2\n\nSection 1.2 content"
    )
    assert get_section_full_text(section) == expected_output


def test_build_doc_tree_from_markdown():
    # Test case 1: Building a document tree from markdown with no headings
    text = "This is a single section"
    expected_output = {"heading": "", "text": "This is a single section"}
    assert build_doc_tree_from_markdown(text) == expected_output

    # Test case 2: Building a document tree from markdown with headings
    text = "# Section 1\n\nSection 1 content\n\n## Section 1.1\n\nSection 1.1 content"
    expected_output = {
        "heading": "",
        "text": "",
        "child_sections": [
            {
                "heading": "# Section 1",
                "text": "Section 1 content",
                "child_sections": [
                    {
                        "heading": "## Section 1.1",
                        "text": "Section 1.1 content",
                    }
                ],
            }
        ],
    }

    assert build_doc_tree_from_markdown(text) == expected_output


# Should correctly flatten a simple document tree with one root section and one child
# section
def test_flatten_simple_document_tree():
    root = {
        "heading": "Root Section",
        "text": "This is the root section",
        "child_sections": [
            {"heading": "Child Section", "text": "This is the child section"}
        ],
    }
    expected = [
        ("Root Section", "This is the root section"),
        ("Child Section", "This is the child section"),
    ]
    assert flatten_doc_tree(root) == expected


# Should correctly flatten a document tree with multiple levels of nested sections
def test_flatten_nested_document_tree():
    root = {
        "heading": "Root Section",
        "text": "This is the root section",
        "child_sections": [
            {
                "heading": "Child Section 1",
                "text": "This is the first child section",
                "child_sections": [
                    {
                        "heading": "Grandchild Section 1",
                        "text": "This is the first grandchild section",
                    },
                    {
                        "heading": "Grandchild Section 2",
                        "text": "This is the second grandchild section",
                    },
                ],
            },
            {
                "heading": "Child Section 2",
                "text": "This is the second child section",
            },
        ],
    }
    expected = [
        ("Root Section", "This is the root section"),
        ("Child Section 1", "This is the first child section"),
        ("Grandchild Section 1", "This is the first grandchild section"),
        ("Grandchild Section 2", "This is the second grandchild section"),
        ("Child Section 2", "This is the second child section"),
    ]
    assert flatten_doc_tree(root) == expected


# Should correctly flatten a document tree with multiple child sections at the same
# level
def test_flatten_multiple_child_sections():
    root = {
        "heading": "Root Section",
        "text": "This is the root section",
        "child_sections": [
            {
                "heading": "Child Section 1",
                "text": "This is the first child section",
            },
            {
                "heading": "Child Section 2",
                "text": "This is the second child section",
            },
            {
                "heading": "Child Section 3",
                "text": "This is the third child section",
            },
        ],
    }
    expected = [
        ("Root Section", "This is the root section"),
        ("Child Section 1", "This is the first child section"),
        ("Child Section 2", "This is the second child section"),
        ("Child Section 3", "This is the third child section"),
    ]
    assert flatten_doc_tree(root) == expected


# Should return an empty list if the root section is empty and has no child sections
def test_flatten_empty_root_section():
    root = {"heading": "", "text": "", "child_sections": []}
    expected = []
    assert flatten_doc_tree(root) == expected


# Should raise a KeyError if the root section does not have a 'heading' or 'text' key
def test_flatten_missing_heading_or_text_key():
    root = {
        "text": "This is the root section",
        "child_sections": [
            {"heading": "Child Section", "text": "This is the child section"}
        ],
    }
    with pytest.raises(KeyError):
        flatten_doc_tree(root)


# Should handle gracefully if the 'child_sections' key is missing or not a list
def test_flatten_missing_or_invalid_child_sections_key():
    root = {
        "heading": "Root Section",
        "text": "This is the root section",
        "child_sections": {},
    }
    expected = [("Root Section", "This is the root section")]
    assert flatten_doc_tree(root) == expected

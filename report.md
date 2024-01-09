# Technical Report

## Introduction

The goal of the project was to develop a program that let users query questions about the paper Generative Agents through a chat interface.

This document describes the process of development, with details on what has been experimented, how decisions were made, the results, and possible future improvements.

The development can be divided into 3 major parts:

1. Data processing: in which the paper was processed from a PDF file to a more structured and parsable format.
2. Model development: in which the data extracted in the previous step was used to create the training set, which was then used to fine-tune the model.
3. App development: in which the pipeline and logic of the chatbot were constructed using the models and data from previous steps.

## Development process

### Data processing

> The data processing pipeline is put together in the `docqa/demo/create_dataset.py` script.

#### PDF to Markdown

##### Why Markdown?

The first step is to parse the pdf file and extract the text from it. It is preferable that the extracted text preserves the structure of the paper. This is, however, not a trivial task as PDF is notoriously hard to parse and doesn't explicitly contain structural and scheming information.

The target format of choice for this step is markdown. Markdown was chosen instead of others as it has a well-defined structure (unlike plain text) while still being readable and not over-expressive (like HTML or LaTex). It strikes a balance between structure and expressiveness.

> The Markdown format is chosen partly due to being a personal favourite.

!!! note

    Note that, for the case of the Generative Agents paper, one can get the  LaTex source from Arxiv and parse it instead, which will yield better results. However, in the spirit of handling any PDF document, it was decided to parse the PDF file directly.

##### PDF parsers

Meta has a powerful PDF parser called [Nougat](https://github.com/facebookresearch/nougat) which was designed to work on academic documents, which is very suitable for the target document. However, experiments show that it runs quite slowly. It also tries to extract text from images which is a feature that is not needed for the purpose of this project and makes the output noisier for parsing.

> A possible improvement would be to disable the OCR feature of Nougat. For the scope of this project, this was not done due to time constraints.

Thus, a different parser called [Marker](https://github.com/VikParuchuri/marker) was used for the purpose of this project. It is significantly faster and produces less noise. However, it does not come without drawbacks. It uses Nougat internally along with other tools to handle different aspects of the parsing process. As a result, is a more complicated solution with many components and heuristics.

In the specific case of the target document, Marker produced 2 noteworthy problems:

- As it tries to detect the column layout of the document, it fails to correctly parse the first page of the document where the authors section has 3 columns while the Abstract has only 2. This results in mixed-up content on the first page. A possible reason for this might be that it failed to identify that the author section and the Abstract are separated, thus treating them as a single section with 2 columns.
- Near the end of its pipeline is a post-processing step that makes heavy use of heuristics to combine all the extracted text into sentences and paragraphs. This process tends to not preserve the structure of the document, and combined with the first problem, creates even more noisier texts.

To overcome the above problems, a [fork](https://github.com/lone17/marker) was created to:

- Adjust the post-processing heuristic to prevent over-combining the text.
- Produce a less processed text so that it can be tidied later.
- Simplify the installation process.

##### Post-processing using Language Models

To process the loosely structured text from Marker, a language model (`gpt-3.5-turbo` in this case) was employed to tidy it up into a more structured format. Language models are suitable for this task due to their ability to understand the semantic and sentence structure of the natural language.

To best preserve the structure, header lines (begin with `#`) were extracted, and then, only the text in between 2 header lines was sent to the language model for reconstruction, with some prompt engineering involved. Note that, an exception was made which combines the author section and the Abstract section to address the earlier-mentioned problem.

However, since the model produces outputs with a similar length as the inputs, the input length can only be at most half of the model's context length. Thus, the amount of tokens sent to the model was limited to 4096. The output of the model is then compared to the input using a similarity metric, this is done to minimize the chances that the model adds new content or produces an output that is too different from the input.

> The logic of this procedure is implemented in the class `docqa.core.markdown.tidy_markdown_sections`.

### Model development

#### Create the Training Dataset

After the previous step, the input of this step would be a markdown file instead of the loosely structure pdf. Thus, any markdown file can be used as input for this step onward, allowing for different data sources and formats.

##### Document tree

To better represent the document structure, a document tree is created from the markdown. A document tree is just a fancy way of saying that the hierarchy of the sections is represented in a nested manner. Which, in this case, is a JSON object.

This was done by first extracting the header lines, deciding the header level based on the number of `#`, and then recursively constructing the document tree.

##### Question-Answer Pairs

To fine-tune the model, a dataset in the form of question-answer pairs is needed. This step was done by providing a Language Model with a portion of the document and using it as the context for the model to generate questions and answers. It is important to make sure that the portions are semantically and structurally enclosed, meaning they must contain complete sentences describing complete ideas without being cut-off mid mid-context.

The second step is to chunk the content preserving structural content. The third step is to generate question-answers pairs. The fourth step is to prepare data for other steps: fine-tuning OpenAI models, and adding to vector-stores.

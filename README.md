# DocQA

[Documentation](https://lone17.github.io/docqa/)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-31013/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![built with Codeium](https://codeium.com/badges/main)](https://codeium.com)

Ask questions on your documents.

This repo contains various tools for creating a document QA app from your text file to a RAG chatbot.

## Installation

- Get the source code

  ```bash
  # clone the repo (with a submodule)
  git clone --recurse-submodules https://github.com/lone17/docqa.git
  cd docqa
  ```

- It is recommended to create a virtual environment

  ```bash
  python -m venv env
  . env/bin/activate
  ```

- First, let's install Marker (following its instructions)

  ```bash
  cd marker
  #  Install ghostscript > 9.55 by following https://ghostscript.readthedocs.io/en/latest/Install.html
  scripts/install/ghostscript_install.sh
  # install other requirements
  cat scripts/install/apt-requirements.txt | xargs sudo apt-get install -y
  pip install .
  ```

- Then install docqa

  ```bash
  cd ..
  pip install -e .[dev]
  ```

## Demo

This repo contains a demo for the whole pipeline for a QA chatbot on Generative Agents based on the
information
in [this
paper](<https://github.com/lone17/docqa/tree/main/docqa/demo/data/generative_agent/generative_agent%20(1).pdf>).

For information about the development process, please refer to the [technical report](https://lone17.github.io/docqa/report/)

![UI](https://raw.githubusercontent.com/lone17/docqa/main/docs/assets/ui.png)

### Try the Demo

#### From source

> In order to use this app, you need a OpenAI API key.

Before playing with the demo, please populate your key and secrets in the `.env` file:

```bash
OPENAI_API_KEY=...
OPENAI_MODEL=...
OPENAI_SEED=...
WANDB_API_KEY=... # only needed if you want to fine-tune the model and use WanDB
```

All the scripts for the full pipeline as well as generated artifacts are in the `demo` folder.

- `create_dataset.py`: This script handles the full data processing pipeline:
  - parse the pdf file
  - convert it to markdown
  - chunk the content preserving structural content
  - generate question-answers pairs
  - prepare data for other steps: fine-tuning OpenAI models, and adding to vector-stores.
- `finetune_openai.py`: As the name suggests, this script is used to fine-tune the OpenAI model
  using the data generated in `create_dataset.py`.
  - Also includes Wandb logging.
- `pipeline.py`: Declares the QA pipeline with semantic retrieval using ChromaDB.

The `main.py` script is the endpoint for running the backend app:

```bash
python main.py
```

And to run the front end:

```bash
streamlit run frontend.py
```

#### Using Docker

Alternatively, you can get the image from
[Docker Hub](https://hub.docker.com/repository/docker/el117/docqa/general).

```bash
docker pull el117/docqa
docker run --rm -p 8000:8000 -e OPENAI_API_KEY=<...> el117/docqa
```

Note that the docker does not contain the front end. To run it you can simply do:

```bash
pip install streamlit
streamlit run frontend.py
```

### Architecture

#### Data Pipeline

The diagram below describes the data life cycle. Results from each step can be found at [docqa/demo/data/generative_agent](https://github.com/lone17/docqa/tree/main/docqa/demo/data/generative_agent).

```mermaid
flowchart LR
    subgraph pdf-to-md[PDF to Markdown]
        direction RL
        pdf[PDF] --> raw-md(raw\nmarkdown)
        raw-md --> tidied-md([tidied\nmarkdown])
    end

    subgraph create-dataset[Create Dataset]
        tidied-md --> sections([markdown\nsections])
        sections --> doc-tree([doc\ntree])
        doc-tree --> top-lv([top-level\nsections])
        doc-tree --> chunks([section-bounded\nchunks])
        top-lv --> top-lv-qa([top-level sections\nQA pairs])
        top-lv-qa --> finetune-data([fine-tuning\ndata])
    end


        finetune-data --> lm{{language\nmodel}}

        top-lv-qa --> vector-store[(vector\nstore)]
        chunks ----> vector-store
```

#### App

The diagram below describes the app's internal working, from receiving a question to answering it.

```mermaid
flowchart LR
    query(query) --> emb{{embedding\nmodel}}

    subgraph retriever[SemanticRetriever]
        direction LR
        vector-store[(vector\nstore)]

        emb --> vector-store
        vector-store --> chunks([related\nchunks])
        vector-store --> questions([similar\nquestions])
        questions --> sections([related\nsections])
    end

    sections --> ref([references])
    chunks --> ref

    query --> thresh{similarity > threshold}
    questions --> thresh

    thresh -- true --> answer(((answer &\nreferences)))
    thresh -- false --> answerer

    ref --> prompt(prompt)
    query --> prompt

    subgraph answerer[AnswerGenerator]
        direction LR
        prompt --> llm{{language\nmodel}}
    end

    llm --> answer
    ref --> answer
```

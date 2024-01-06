import json
from pathlib import Path

import chromadb
import numpy as np
from angle_emb import AnglE, Prompts
from chromadb.config import Settings
from pydantic import BaseModel

from docqa.core.chunking import chunk_content
from docqa.core.data_generation import AnswerGenerator
from docqa.core.doc_tree import flatten_doc_tree
from docqa.core.retrieval import SemanticRetriever
from docqa.demo.config import SECTIONS


def create_chroma_db(data_dir, db_dir, collection_name, embedding_model):
    corpus = []
    metadatas = []

    top_sections_qa_data_file = data_dir / "top_sections_qa_data.json"
    with open(top_sections_qa_data_file) as f:
        qa_data = json.load(f)

    allowed_sections = set(
        sum([SECTIONS[section_type] for section_type in ["main", "summary"]], [])
    )

    for heading, section in qa_data.items():
        if heading not in allowed_sections:
            continue
        for item in section["dense_questions"] + section["sparse_questions"]:
            corpus.append(item["question"])
            metadatas.append(
                {"type": "question", "source": heading, "answer": item["answer"]}
            )

    doc_tree_file = data_dir / "doc_tree.json"
    with open(doc_tree_file) as f:
        doc_tree = json.load(f)
    all_sections_map = {heading: text for heading, text in flatten_doc_tree(doc_tree)}

    for heading in all_sections_map.keys():
        if heading not in allowed_sections:
            continue
        section_chunks = chunk_content(all_sections_map[heading])
        corpus.extend(section_chunks)
        metadatas.extend([{"type": "chunk", "source": heading} for _ in section_chunks])

    print("Creating chroma db...")
    client = chromadb.PersistentClient(
        str(db_dir), Settings(anonymized_telemetry=False)
    )
    db = client.create_collection(
        name=collection_name, metadata={"hnsw:space": "cosine"}
    )
    print("Finish creating chroma db.")

    print("Embedding corpus...")
    # one by one because my machine does not have much ram
    corpus_embeddings = [embedding_model.encode({"text": each})[0] for each in corpus]
    corpus_embeddings = np.vstack(corpus_embeddings)
    print("Finish embedding corpus.")

    print("Populating chroma db...")
    db.add(
        documents=corpus,
        embeddings=corpus_embeddings,
        metadatas=metadatas,
        ids=[str(i) for i in range(len(corpus))],
    )
    print("Finish populating chroma db.")

    return db


class Pipeline(BaseModel):
    retriever: SemanticRetriever
    answerer: AnswerGenerator
    sections_map: dict

    def process(
        self,
        question,
        certainty_threshold=0.9,
        uncertainty_threshold=0.6,
        temperature=1.0,
    ):
        similar_questions = self.retriever.process(
            question, top_k=1, metadata_filter={"type": "question"}
        )
        question_similarity = similar_questions[0]["score"]

        if question_similarity > certainty_threshold:
            related_section = similar_questions[0]["metadata"]["source"]
            related_content = self.sections_map[related_section]
            return {
                "answer": similar_questions[0]["metadata"]["answer"],
                "references": [{"source": related_section, "content": related_content}],
            }

        related_chunks = self.retriever.process(
            question, top_k=3, metadata_filter={"type": "chunk"}
        )
        chunks_similarity = np.mean([each["score"] for each in related_chunks])

        if (
            question_similarity < uncertainty_threshold
            and chunks_similarity < uncertainty_threshold
        ):
            references = []
            references_text = "No related references found."
        elif question_similarity >= chunks_similarity:
            related_section = similar_questions[0]["metadata"]["source"]
            related_content = self.sections_map[related_section]
            references = [{"source": related_section, "content": related_content}]
            references_text = f"{related_section}\n\n{related_content}"
        else:
            references = [
                {"source": each["metadata"]["source"], "content": each["document"]}
                for each in related_chunks
            ]
            references_text = ("-" * 6).join(
                [
                    f"From: {each['source']}\n...\n{each['content']}\n...\n"
                    for each in references
                ]
            )

        answer, metadata = self.answerer.process(
            question, references_text, temperature=temperature
        )

        return {
            "answer": answer,
            "references": references,
            "metadata": metadata,
        }


def get_pipeline(data_dir, openai_key, openai_model):
    doc_tree_file = data_dir / "doc_tree.json"
    with open(doc_tree_file) as f:
        doc_tree = json.load(f)
    all_sections_map = {heading: text for heading, text in flatten_doc_tree(doc_tree)}

    print("Loading embedding model...")
    embedding_model = AnglE.from_pretrained(
        "WhereIsAI/UAE-Large-V1", pooling_strategy="cls"
    )
    embedding_model.set_prompt(prompt=Prompts.C)
    print("Finish loading embedding model.")

    db_dir = data_dir / "chroma"
    db_collection_name = "generative-agents"

    try:
        chroma_client = chromadb.PersistentClient(
            str(db_dir), Settings(anonymized_telemetry=False)
        )
        db = chroma_client.get_collection(name=db_collection_name)
    except ValueError:
        db = create_chroma_db(data_dir, db_dir, db_collection_name, embedding_model)

    retriever = SemanticRetriever(embedding_model=embedding_model, vector_db=db)
    answerer = AnswerGenerator(
        openai_key=openai_key,
        openai_model=openai_model,
        instruction=(
            "You will be answering questions about the paper called 'Generative"
            " Agents'.\nInstructions:\n- Find some references in the paper that related"
            " to the question.\n- If you found related references, answer the question"
            " as detailed as possible based strictly on that references you found.\n-"
            " If you can't answer the question using the references, say you can't find"
            " sufficient information to answer the question.\n- If the question is not"
            " related to the references or there is no reference found, say the"
            " question is irrelevant to the paper and answer the question as"
            " a normal chatbot.\n\nReferences you found:\n\n{reference}\n\nQuestion:"
            " {question}\nAnswer:"
        ),
    )

    pipeline = Pipeline(
        retriever=retriever,
        answerer=answerer,
        sections_map=all_sections_map,
    )

    return pipeline


if __name__ == "__main__":
    import os

    data_dir = Path("data/generative_agent")
    pipeline = get_pipeline(
        data_dir,
        openai_key=os.environ["OPENAI_API_KEY"],
        openai_model=os.getenv("OPENAI_MODEL"),
    )
    results = pipeline.process("What are generative agents?")

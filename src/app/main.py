"""Streamlit chat interface for AgenticNutriRAG.

Run with: uv run streamlit run src/app/main.py
Requires a populated Elasticsearch index (see ingestion.pipeline).
"""

import uuid
from typing import Any

import streamlit as st
from elasticsearch import Elasticsearch
from openai import OpenAI

from agent.rag import answer_question
from config import get_settings
from monitoring.feedback import record_feedback

EXAMPLE_QUESTIONS = [
    "How much protein is in an egg?",
    "What's a good low-calorie source of fiber?",
    "What foods are high in iron?",
]

st.set_page_config(page_title="AgenticNutriRAG", page_icon="🥗")
st.title("🥗 AgenticNutriRAG")
st.caption("Ask a nutrition question grounded in USDA FoodData Central.")


@st.cache_resource
def get_clients() -> tuple[Elasticsearch, OpenAI]:
    settings = get_settings()
    return (
        Elasticsearch(settings.elasticsearch_url),
        OpenAI(api_key=settings.openai_api_key),
    )


if "interactions" not in st.session_state:
    st.session_state.interactions = []


def render_answer(interaction: dict[str, Any]) -> None:
    answer = interaction["answer"]
    st.markdown(answer.answer)

    if answer.sources:
        with st.expander(f"Sources ({len(answer.sources)})"):
            for source in answer.sources:
                st.markdown(f"- **{source.food_name}** (FDC ID {source.fdc_id})")

    feedback = interaction["feedback"]
    up_col, down_col, _ = st.columns([1, 1, 10])
    if up_col.button("👍", key=f"up-{interaction['id']}", disabled=feedback is not None):
        interaction["feedback"] = "up"
        record_feedback(interaction["id"], interaction["question"], "up")
        st.rerun()
    if down_col.button("👎", key=f"down-{interaction['id']}", disabled=feedback is not None):
        interaction["feedback"] = "down"
        record_feedback(interaction["id"], interaction["question"], "down")
        st.rerun()
    if feedback is not None:
        st.caption(f"Feedback recorded: {'👍' if feedback == 'up' else '👎'}")


for past_interaction in st.session_state.interactions:
    with st.chat_message("user"):
        st.markdown(past_interaction["question"])
    with st.chat_message("assistant"):
        render_answer(past_interaction)

pending_question = st.session_state.pop("pending_question", None)
typed_question = st.chat_input("Ask a nutrition question...")
question = pending_question or typed_question

if not st.session_state.interactions and not question:
    st.caption("Try asking:")
    example_cols = st.columns(len(EXAMPLE_QUESTIONS))
    for col, example in zip(example_cols, EXAMPLE_QUESTIONS, strict=True):
        if col.button(example, key=f"example-{example}"):
            st.session_state.pending_question = example
            st.rerun()

if question:
    with st.chat_message("user"):
        st.markdown(question)

    es_client, openai_client = get_clients()
    with st.chat_message("assistant"):
        with st.spinner("Looking up nutrition data..."):
            answer = answer_question(es_client, openai_client, question)

        new_interaction = {
            "id": str(uuid.uuid4()),
            "question": question,
            "answer": answer,
            "feedback": None,
        }
        st.session_state.interactions.append(new_interaction)
        render_answer(new_interaction)

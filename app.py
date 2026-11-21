
from __future__ import annotations

import datetime as dt
import sqlite3
import uuid
from pathlib import Path

import streamlit as st
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from mockmate.config import ConfigError, load_settings
from mockmate.graph import build_graph
from mockmate.llm import get_llm
from mockmate.memory import aggregate
from mockmate.report import build_report
from mockmate.sessions import load_all
from mockmate.workspace import WEAK_FILE, Workspace


# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="MockMate | AI Interview Agent",
    page_icon="🎯",
    layout="wide",
)


# --------------------------------------------------
# STYLING
# --------------------------------------------------

st.markdown("""
<style>
.stApp {
    background: #0b1020;
    color: #f5f7ff;
}
[data-testid="stSidebar"] {
    background: #111a2e;
}
.hero {
    padding: 30px;
    border-radius: 16px;
    background: linear-gradient(120deg, #172554, #312e81);
    border: 1px solid #394b85;
    margin-bottom: 25px;
}
.hero h1 {
    color: white;
    font-size: 38px;
}
.hero p {
    color: #dbeafe;
}
.question {
    background: #17233b;
    padding: 24px;
    border: 1px solid #3b527d;
    border-radius: 14px;
    margin: 15px 0;
}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# INITIALIZE EXISTING MOCKMATE ENGINE
# --------------------------------------------------

@st.cache_resource
def initialize():
    settings = load_settings()

    settings.workspace.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)

    workspace = Workspace(settings.workspace)
    llm = get_llm(settings)

    connection = sqlite3.connect(
        str(settings.db_path),
        check_same_thread=False,
    )

    checkpointer = SqliteSaver(connection)
    checkpointer.setup()

    graph = build_graph(settings, llm, workspace).compile(
        checkpointer=checkpointer
    )

    return settings, workspace, graph


try:
    settings, workspace, graph = initialize()
except ConfigError as exc:
    st.error(f"Configuration error: {exc}")
    st.info("Check your .env file and NVIDIA API key.")
    st.stop()
except Exception as exc:
    st.error(f"MockMate initialization failed: {exc}")
    st.stop()


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "thread_id" not in st.session_state:
    st.session_state.thread_id = None


def graph_config(thread_id: str):
    return {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 100,
    }


def run_graph(payload, thread_id: str):
    config = graph_config(thread_id)

    for _ in graph.stream(
        payload,
        config,
        stream_mode="updates",
    ):
        pass


def get_snapshot(thread_id: str):
    return graph.get_state(graph_config(thread_id))


def get_interrupt(snapshot):
    for task in snapshot.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None


def start_interview(role, interview_round, difficulty):
    thread_id = uuid.uuid4().hex[:12]

    initial_state = {
        "profile": {
            "role": role,
            "round": interview_round,
            "difficulty": difficulty,
        },
        "thread": thread_id,
        "total": settings.questions,
        "started": dt.date.today().isoformat(),
    }

    st.session_state.thread_id = thread_id

    run_graph(initial_state, thread_id)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.title("🎯 MockMate")
    st.caption("AI-Powered Mock Technical Interview Agent")

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Interview",
            "Reports",
            "Weak Topics",
        ],
    )

    st.divider()

    st.caption("MODEL CONFIGURATION")
    st.write(f"Provider: **{settings.provider.upper()}**")
    st.write(f"Model: `{settings.model}`")

    st.divider()

    if st.session_state.thread_id:
        st.caption("CURRENT INTERVIEW")
        st.code(st.session_state.thread_id)

        if st.button("Refresh interview"):
            st.rerun()

    st.divider()

    st.caption("RESUME SAVED INTERVIEW")

    resume_id = st.text_input(
        "Thread ID",
        placeholder="Enter saved thread ID",
    )

    if st.button("Resume interview"):
        if resume_id.strip():
            try:
                snapshot = get_snapshot(resume_id.strip())

                if snapshot.values:
                    st.session_state.thread_id = resume_id.strip()
                    st.rerun()
                else:
                    st.error("Interview not found.")
            except Exception as exc:
                st.error(f"Could not resume: {exc}")


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown("""
<div class="hero">
    <h1>🎯 MockMate</h1>
    <p>
        Practice technical interviews with an AI interviewer.
        Receive detailed feedback, track weak topics, and improve
        your interview performance.
    </p>
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

if page == "Dashboard":

    sessions = load_all(workspace)

    scores = [
        record["card"]["score"]
        for _, records in sessions
        for record in records
    ]

    average = sum(scores) / len(scores) if scores else 0

    c1, c2, c3 = st.columns(3)

    c1.metric("Interview Sessions", len(sessions))
    c2.metric("Questions Answered", len(scores))
    c3.metric("Average Score", f"{average:.1f}/10")

    st.subheader("Welcome to MockMate")

    st.write(
        "Your personal AI interview preparation platform. "
        "Start an interview, receive feedback, and monitor your progress."
    )

    a, b = st.columns(2)

    with a:
        st.markdown("### 🧠 AI Interviewer")
        st.write("Practice technical and behavioural interview questions.")

    with b:
        st.markdown("### 📊 Performance Analysis")
        st.write("Get validated scorecards and track your weak topics.")

    if st.button("Start New Interview", type="primary"):
        st.session_state.thread_id = None
        st.session_state.go_to_interview = True
        st.rerun()


# --------------------------------------------------
# INTERVIEW
# --------------------------------------------------

elif page == "Interview":

    st.subheader("🎤 Mock Interview")

    if not st.session_state.thread_id:

        st.write("Configure your interview.")

        with st.form("interview_setup"):

            role = st.text_input(
                "Target Job Role",
                value="ML Engineer",
            )

            interview_round = st.selectbox(
                "Interview Round",
                [
                    "ML fundamentals",
                    "DSA",
                    "behavioural",
                ],
            )

            difficulty = st.selectbox(
                "Difficulty",
                ["easy", "medium", "hard"],
                index=1,
            )

            submitted = st.form_submit_button(
                "Start Interview",
                type="primary",
            )

        if submitted:
            if not role.strip():
                st.warning("Enter a job role.")
            else:
                try:
                    with st.spinner("Preparing your interview..."):
                        start_interview(
                            role.strip(),
                            interview_round,
                            difficulty,
                        )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not start interview: {exc}")

    else:

        thread_id = st.session_state.thread_id

        try:
            snapshot = get_snapshot(thread_id)
        except Exception as exc:
            st.error(f"Could not load interview: {exc}")
            st.stop()

        if not snapshot.values:
            st.warning("Interview state was not found.")
            st.stop()

        values = snapshot.values
        profile = values.get("profile", {})
        records = values.get("records", [])

        st.write(f"**Role:** {profile.get('role', '')}")
        st.write(f"**Round:** {profile.get('round', '')}")
        st.write(f"**Difficulty:** {profile.get('difficulty', '')}")

        total = values.get("total", settings.questions)
        completed = len(records)

        st.progress(min(completed / max(total, 1), 1.0))
        st.caption(f"{completed} of {total} questions completed")

        pending = get_interrupt(snapshot)

        # ANSWER INTERRUPT
        if pending and pending.get("type") == "answer":

            st.markdown(
                f"""
                <div class="question">
                    <h3>Question {pending['index']} of {pending['total']}</h3>
                    <p>{pending['question']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form("answer_form"):

                answer = st.text_area(
                    "Your Answer",
                    height=180,
                    placeholder="Write your answer here...",
                )

                submit_answer = st.form_submit_button(
                    "Submit Answer",
                    type="primary",
                )

            if submit_answer:
                if not answer.strip():
                    st.warning("Please enter your answer.")
                else:
                    try:
                        with st.spinner("Evaluating your answer..."):
                            run_graph(
                                Command(resume=answer.strip()),
                                thread_id,
                            )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Evaluation failed: {exc}")

        # WEAK TOPIC APPROVAL INTERRUPT
        elif pending and pending.get("type") == "approval":

            st.warning("Approval required to update weak-topics.md")

            st.code(pending.get("diff", ""))

            decision = st.radio(
                "Choose an action",
                ["Approve", "Edit", "Reject"],
                horizontal=True,
            )

            drop_topics = []

            if decision == "Edit":
                existing_topics = [
                    item.topic
                    for item in aggregate(load_all(workspace))
                    if item.avg < 6.0
                ]

                drop_topics = st.multiselect(
                    "Topics to remove from the proposed weak-topic file",
                    existing_topics,
                )

            if st.button("Confirm Approval", type="primary"):

                if decision == "Approve":
                    response = {"decision": "approve"}
                elif decision == "Edit":
                    response = {
                        "decision": "edit",
                        "drop": drop_topics,
                    }
                else:
                    response = {"decision": "reject"}

                try:
                    run_graph(
                        Command(resume=response),
                        thread_id,
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Approval failed: {exc}")

        # COMPLETED INTERVIEW
        elif values.get("final"):

            st.success("🎉 Interview Completed!")

            st.subheader("Your Scorecards")

            for record in records:

                card = record["card"]

                with st.expander(
                    f"Question {record['index']} - {record['topic']} "
                    f"({card['score']}/10)"
                ):

                    st.write("**Question**")
                    st.write(record["question"])

                    st.write("**Your Answer**")
                    st.write(record["answer"])

                    st.metric("Score", f"{card['score']}/10")

                    st.write("**Strengths**")
                    for item in card["strengths"]:
                        st.write(f"• {item}")

                    st.write("**Areas to Improve**")
                    for item in card["gaps"]:
                        st.write(f"• {item}")

                    st.info(f"Hint: {card['hint']}")
                    st.write(f"Next Topic: {card['next_topic']}")

            if st.button("Start Another Interview", type="primary"):
                st.session_state.thread_id = None
                st.rerun()

        else:
            st.info("No pending interview question. Refresh the page.")


# --------------------------------------------------
# REPORTS
# --------------------------------------------------

elif page == "Reports":

    st.subheader("📊 Interview Reports")

    sessions = load_all(workspace)

    report = build_report(sessions)

    st.code(report, language="text")

    scores = [
        record["card"]["score"]
        for _, records in sessions
        for record in records
    ]

    if scores:
        st.subheader("Score Distribution")
        st.bar_chart(scores)
    else:
        st.info("Complete an interview to generate reports.")


# --------------------------------------------------
# WEAK TOPICS
# --------------------------------------------------

elif page == "Weak Topics":

    st.subheader("📚 Weak Topic Tracker")

    if workspace.exists(WEAK_FILE):

        content = workspace.read_text(WEAK_FILE)

        st.markdown(content)

        st.download_button(
            "Download Weak Topics",
            data=content,
            file_name="weak-topics.md",
            mime="text/markdown",
        )

    else:
        st.info("No weak topics recorded yet.")


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "MockMate | Built with Python, Streamlit, LangGraph and NVIDIA NIM"
)

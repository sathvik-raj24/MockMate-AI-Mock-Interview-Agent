# 🎤 MockMate – AI-Powered Mock Interview Agent

**MockMate is an AI-powered technical mock interview platform built with Python, Streamlit, LangChain, LangGraph and NVIDIA NIM.**

Practice technical interviews with an AI interviewer that asks one question at a time, evaluates your answers, provides structured feedback and tracks your weak topics across sessions.

MockMate is designed to simulate the interview experience rather than simply provide answers to interview questions.

---

## 🌐 Live Demo

Try MockMate here:

👉 https://mockmate-ai-mock-interview-agent-8kegqzw45dm864fewpmlsl.streamlit.app/

## 🚀 Features

- **Interactive Streamlit Website:** User-friendly web interface for conducting mock interviews.
- **AI-Powered Interview Questions:** Generates interview questions based on role, interview round and difficulty.
- **One Question at a Time:** The interview workflow waits for the candidate's answer before continuing.
- **AI Answer Evaluation:** Evaluates responses using a structured scoring rubric.
- **Validated Scorecards:** Provides a score out of 10, two strengths, two improvement areas, one hint and the next topic.
- **Adaptive Interviewing:** Uses previous performance and weak topics to guide subsequent questions.
- **Weak-Topic Tracking:** Maintains interview performance data in `workspace/weak-topics.md`.
- **Session Management:** Stores interview reports and supports resuming sessions.
- **SQLite Checkpointing:** Uses LangGraph persistence to maintain interview state.
- **Human Approval:** Supports approve, edit and reject actions before updating important files.
- **Context Management:** Summarises earlier interview responses to maintain context.
- **Workspace Security:** Restricts file operations to the designated workspace.
- **NVIDIA NIM Integration:** Uses a hosted NVIDIA model for question generation and answer evaluation.

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.12+ | Core programming language |
| Streamlit | Web application interface |
| LangChain | LLM integration |
| LangGraph | Interview workflow and state management |
| NVIDIA NIM | Hosted AI inference |
| Pydantic | Structured output validation |
| SQLite | Session checkpoint persistence |
| uv | Python dependency management |
| Pytest | Automated testing |

---

## 📸 Application Preview

The application includes an interactive dashboard and an interview workspace.

Add your actual application screenshots here after capturing them:

```text
screenshots/
├── dashboard.png
├── interview.png
└── evaluation.png
```

---

## ⚙️ Installation and Setup

### Prerequisites

- Python 3.12 or later
- Git
- uv package manager
- NVIDIA NIM API key

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/MockMate-AI-Mock-Interview-Agent.git
cd MockMate-AI-Mock-Interview-Agent
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment variables

Create your local environment file:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

Open `.env` in VS Code and configure your NVIDIA credentials:

```env
MODEL_PROVIDER=nvidia
MODEL_NAME=nvidia/nemotron-3.5-lightning-30b-a3b
NVIDIA_API_KEY=your_nvidia_api_key
```

Replace the placeholder with your actual NVIDIA API key.

Get an API key from:

https://build.nvidia.com/

Choose a currently supported model from the NVIDIA model catalogue if the model ID changes.

**Important:** Never upload your `.env` file or expose your API key publicly.

---

## ▶️ Run MockMate Locally

Start the Streamlit application:

```bash
uv run streamlit run app.py
```

Open the following address in your browser:

```text
http://localhost:8501
```

---

## 🧠 How MockMate Works

1. The candidate selects an interview role, round and difficulty.
2. LangGraph manages the interview workflow.
3. NVIDIA NIM generates an interview question.
4. The candidate submits an answer through the Streamlit interface.
5. The AI evaluates the answer using the predefined rubric.
6. Pydantic validates the generated scorecard.
7. Interview performance is saved for future sessions.
8. Weak topics are tracked and used to guide subsequent questions.
9. Human approval controls sensitive workspace updates.

### Interview Evaluation

Each evaluated answer contains:

| Evaluation | Description |
|---|---|
| Score | Performance out of 10 |
| Strengths | Two things done well |
| Gaps | Two areas requiring improvement |
| Hint | One improvement hint |
| Next Topic | Suggested topic for the next question |

---

## 🧪 Testing

Run the automated test suite:

```bash
uv run pytest -v
```

The tests cover application logic, workflow behaviour, validation, session handling, approval mechanisms and workspace security.

---

## 📁 Project Structure

```text
MockMate/
│
├── .github/
│   └── workflows/
│
├── mockmate/
│   ├── approvals.py
│   ├── cli.py
│   ├── config.py
│   ├── context.py
│   ├── graph.py
│   ├── grading.py
│   ├── llm.py
│   ├── llmjson.py
│   ├── memory.py
│   ├── questions.py
│   ├── report.py
│   ├── schemas.py
│   ├── sessions.py
│   ├── skills.py
│   └── workspace.py
│
├── skills/
│   └── behavioural/
│       └── SKILL.md
│
├── tests/
│
├── workspace/
│   └── sessions/
│
├── app.py
├── main.py
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── README.md
├── demo.md
└── LICENSE
```

---

## ☁️ Deployment – Streamlit Community Cloud

MockMate can be deployed using Streamlit Community Cloud.

1. Push the project to a public GitHub repository.
2. Visit https://share.streamlit.io/
3. Sign in using your GitHub account.
4. Select **Create app**.
5. Choose your MockMate repository.
6. Set the main file path to:

```text
app.py
```

7. Open the app's **Advanced settings → Secrets**.
8. Add your NVIDIA credentials using TOML syntax:

```toml
MODEL_PROVIDER = "nvidia"
MODEL_NAME = "nvidia/nemotron-3.5-lightning-30b-a3b"
NVIDIA_API_KEY = "your_nvidia_api_key"
```

9. Deploy the application.

Keep all API credentials in Streamlit Secrets, never in source code or GitHub.

**Persistence note:** Streamlit Community Cloud does not guarantee that local application files persist across restarts or redeployments. For durable interview sessions, use a persistent database or storage service before relying on the deployed application for long-term records.

---

## 🔐 Security

- API keys are stored in environment variables or Streamlit Secrets.
- `.env` is excluded from Git.
- Interview session files and SQLite databases are excluded from Git.
- Workspace file operations enforce path restrictions.
- Approval is required for sensitive file modifications.

---

## 🗺️ Future Improvements

- User authentication and individual interview profiles.
- More interview categories and technical domains.
- Advanced performance analytics.
- Interview history and progress visualisation.
- Additional AI model support.
- Resume-based personalised interview questions.
- Persistent cloud database integration.

---

## 👨‍💻 Author

**Sathvik Raj T G**

AI & Machine Learning Engineering Student

GitHub: [sathvik-raj24](https://github.com/sathvik-raj24)

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

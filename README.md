# multi-agent-repair

A Python 3.10+ multi-agent system that autonomously tests, debugs, and repairs buggy Python programs using a Supervisor/Orchestrator architecture.

## Project Overview

`multi-agent-repair` coordinates ten specialized agents across code analysis, LLM-based test generation, isolated pytest execution, fault localization, root-cause debugging, patch synthesis, code review, strict test-based validation, and reporting:

| Agent | Type | File | Role |
| :--- | :--- | :--- | :--- |
| **Orchestrator** | `code` | `agents/orchestrator.py` | Coordinates the pipeline and manages up to 3 repair attempts per bug. |
| **Analyzer** | `code` | `agents/analyzer.py` | Parses target Python code structure (functions, classes, imports). |
| **TestGenerator** | `llm` | `agents/test_generator.py` | Generates a pytest suite from source code and problem description. |
| **TestExecutor** | `tool` | `agents/test_executor.py` | Runs pytest in an isolated subprocess with a timeout. |
| **Localizer** | `code` | `agents/localizer.py` | Pinpoints suspect files, functions, and lines from failing tracebacks. |
| **Debugger** | `llm` | `agents/debugger.py` | Formulates root-cause hypotheses for the observed test failures. |
| **Repairer** | `llm` | `agents/repairer.py` | Synthesizes a candidate Python patch to fix the bug. |
| **Reviewer** | `llm` | `agents/reviewer.py` | Reviews the candidate patch for quality and regressions. |
| **Validator** | `code` | `agents/validator.py` | Decides repair success or failure strictly from real pytest results. |
| **Reporter** | `code` | `agents/reporter.py` | Produces the final structured report for the repair workflow run. |

**Key Design Principles:**
- Maximum of **3 repair attempts** per bug (`MAX_ATTEMPTS=3`).
- Repair success or failure is decided **only by real `pytest` results**, never by LLM reasoning.
- Model-agnostic `LLMClient` interface so the underlying LLM provider can be swapped or replaced with `FakeLLMClient` in tests.
- Every agent invocation is recorded as structured JSON Lines in `runs/<run_id>/log.jsonl`.

## Folder Structure

```text
multi-agent-repair/
  .streamlit/
    config.toml            # Streamlit server & theme configuration
    secrets.toml.example   # Example secrets for Streamlit Community Cloud
  core/
    __init__.py
    config.py              # Settings loader (os.environ -> st.secrets -> defaults)
    state.py               # WorkflowState dataclass and WorkflowStatus enum
    logger.py              # RunLogger for per-run JSONL interaction logs
    llm.py                 # LLMClient ABC, GeminiClient (google-genai), FakeLLMClient
  agents/
    __init__.py
    base.py                # BaseAgent ABC with dependency injection and run logging
    orchestrator.py        # Orchestrator stub (code-based)
    analyzer.py            # Analyzer stub (code-based)
    test_generator.py      # TestGenerator stub (LLM)
    test_executor.py       # TestExecutor implementation (tool-based)
    localizer.py           # Localizer stub (code-based)
    debugger.py            # Debugger stub (LLM)
    repairer.py            # Repairer stub (LLM)
    reviewer.py            # Reviewer stub (LLM)
    validator.py           # Validator stub (code-based)
    reporter.py            # Reporter stub (code-based)
  prompts/
    .gitkeep               # Prompt templates directory
  runs/                    # Gitignored output folder for per-run JSONL logs
  tests/                   # Unit tests (pytest, no real API calls)
    test_config.py
    test_state.py
    test_logger.py
    test_llm.py
    test_agents.py
    test_test_executor.py
    test_app.py
  app/
    __init__.py
    helpers.py             # UI helpers, DOT graph builder, built-in samples
    main.py                # Streamlit UI entrypoint
  README.md
  requirements.txt
  pytest.ini
  .env.example
  .gitignore
```

## Setup Steps

1. **Create and activate a Python 3.10+ virtual environment:**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**

   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**

   Copy `.env.example` to `.env` and fill in your Gemini API key and target model name:

   ```powershell
   Copy-Item .env.example .env
   ```

4. **Launch the Streamlit UI locally:**

   ```powershell
   streamlit run app/main.py
   ```

## Deploying to Streamlit Community Cloud

1. **Repository Setup:**
   Push this repository to GitHub. Ensure `.env` and `.streamlit/secrets.toml` are excluded via `.gitignore` (never commit real keys or passwords).
2. **Create App on Streamlit Community Cloud:**
   - **Main file path:** `app/main.py`
   - **Recommended Python version:** `3.12` or `3.13` (under *Advanced settings*)
3. **Configure Secrets:**
   In the Streamlit Community Cloud app dashboard (*Settings -> Secrets*), add your configuration following `.streamlit/secrets.toml.example`:
   ```toml
   GEMINI_API_KEY = "your_api_key_here"
   GEMINI_MODEL = "your_gemini_model_placeholder"
   ENABLE_CODE_EXECUTION = false
   APP_PASSWORD = "your_optional_app_password_here"
   ```
   - Keep `ENABLE_CODE_EXECUTION = false` on public deployments so the **Try the Test Executor** tab only executes the 3 built-in sample programs rather than arbitrary user-submitted code.
   - Set `APP_PASSWORD` to require a password before viewing the app, or omit it to allow open access.

## Running Tests

All unit tests run offline using `pytest` without making real LLM API calls:

```powershell
pytest
```

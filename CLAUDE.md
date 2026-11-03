# plant-copilot

Copilot for a shift engineer on the Tennessee Eastman Process (TEP).
An agent answers questions through 4 MCP tools and never writes to process data.

@docs/context.md

## Rules
- Raw TEP data never goes into git; only the scripts in data/ that fetch and load it.
- Public or synthetic data only. No code, data or names from any employer or client.
- query_data accepts SELECT only, on allowlisted tables, with a row limit.
- propose_action only inserts a pending row in approvals; nothing runs without a human.
- Every change ships with a test. A task is done only when the commands below pass.
- Keep the LLM provider behind one interface in copilot/agent.py so it can be swapped.
- Secrets (Anthropic, Azure) come from environment variables. Never hardcode or commit them.
- SOPs and expected answers in the eval set are the human's call. You may draft them,
  marked DRAFT, but never treat a draft as verified.
- Read docs/decisions.md before changing architecture or data handling.
  When we make a design decision, append it there (date, decision, why).
- Code, docs and commit messages in English.

## Commands
- Tests: pytest -q
- Lint: ruff check .
- Evals (subset): python evals/run_evals.py --limit 10
- App: streamlit run app/streamlit_app.py

## Where things are
- 4-week plan and current tasks: `docs/plan.md`
- Decisions log: `docs/decisions.md`
- Procedures (SOPs): docs/sops/
- Eval set: evals/questions.jsonl

@docs/tep-notes.md

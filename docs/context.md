# Project context

## Goal
Build, in 4 weeks (Nov 2–29, 2026), a copilot for the shift engineer of a chemical plant. It:
- answers questions citing operating procedures (file and section),
- queries process data with read-only SQL,
- summarizes faults (which variables deviated, and which moved first),
- proposes actions that a human must approve before anything happens.

The plant is the Tennessee Eastman Process (TEP): a classic chemical engineering
benchmark with public data for normal operation and 20 faults.

## Why it exists
Portfolio project for AI solutions engineering roles in manufacturing.
Each piece shows a skill those roles ask for:

| Skill | How the copilot shows it |
|---|---|
| Agents with tools and structured outputs | One agent, 4 tools that return JSON |
| Enterprise knowledge retrieval | Search over 10 SOPs, citing file and section |
| API and MCP connectors | The 4 tools live in our own MCP server |
| Microsoft Fabric and Azure | Data in a Fabric Lakehouse, model in Azure Foundry (week 4) |
| Authorization limits and human approval | Read-only SQL; the only action that changes anything waits for approval |
| Evaluation, guardrails, observability | 40-question eval set and a log of every call |
| Python, SQL, testing, CI/CD | pytest and GitHub Actions running tests and evals |

Deliverables: public repo (MIT, in English), eval table in the README,
3-minute demo video in English.

## Architecture
The agent never touches data directly: everything goes through the 4 tools.

- `copilot/agent.py`: tool-use loop on the Anthropic API, behind a provider interface
  (week 4 compares it with a Microsoft model in Foundry).
- `copilot/mcp_server.py`: exposes the 4 tools with the official MCP Python SDK.
  - `search_manuals`: splits SOPs by section, indexes them with embeddings,
    returns the fragment with file and section.
  - `query_data`: SELECT only, allowlisted tables, row limit.
  - `summarize_fault`: for a run and a time window, returns the variables with the
    largest deviation from normal operation and which one moved first.
  - `propose_action`: inserts a row in `approvals` with status `pending`. Executes nothing.
- `copilot/store.py`: DuckDB locally; the Fabric Lakehouse SQL endpoint in week 4.
- `app/`: minimal Streamlit chat with approve/reject buttons for pending actions.
- Every tool call is logged in a `calls` table: tool, tokens, latency, result.

## How we work (agentic engineering)
1. Each task starts with its success condition written as a test, before the code
   (e.g. "test_query_data_rejects_delete passes", not "add SQL validation").
2. Automatic checks over asking for care: pytest, ruff, a pre-commit test hook,
   GitHub Actions as a second barrier. A correction made twice becomes a test or lint rule.
3. Least privilege: credentials in env vars; deployment commands are approved by the human.
4. No self-review: the human reads every diff. Changes to agent limits and SQL are
   reviewed by a fresh session with no prior context.
5. Parallel work only when independent (week 2: MCP tools and Streamlit chat,
   each in its own git worktree).

## Constraints
- About 6 hours per week.
- Out of scope: fine-tuning models, a React UI. The value is in evaluation and limits.

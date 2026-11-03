# Decisions

Newest at the bottom. Format: date — decision — why.

- 2026-11-01 — Main portfolio project: a plant copilot on the Tennessee Eastman Process,
  4 weeks (Nov 2–29). — Covers agents, retrieval, MCP, Azure/Fabric, human approval and
  evaluation, and uses a chemical engineering background.
- 2026-11-01 — Public or synthetic data only. — The repo is public; no employer or client
  code or data.
- 2026-11-01 — Dataset: TEP from the Harvard Dataverse (doi:10.7910/DVN/6C3JR1), .RData
  files, faults 1–20. Not the classic 22-file set. — Several simulation runs per fault,
  and it includes IDV 2.
- 2026-11-01 — Load with pyreadr into DuckDB, only a subset: normal operation plus 5 runs
  per fault. Raw files stay out of git; scripts in data/ fetch and load them. — The files
  are large; scripts keep it reproducible.
- 2026-11-01 — Rename XMEAS/XMV columns to physical names (reactor pressure, separator
  level, etc.). — Readable SQL and answers.
- 2026-11-01 — Agent on the Anthropic API, behind a provider interface. — Claude may not
  be deployable in Azure Foundry on a trial subscription; week 4 compares with a
  Microsoft model.
- 2026-11-01 — The 4 tools live in our own MCP server (official Python SDK). — Shows MCP
  connectors, and the agent never touches data directly.
- 2026-11-01 — query_data: SELECT only, allowlisted tables, row limit. propose_action:
  only writes pending rows to approvals. — Authorization limits and human approval.
- 2026-11-01 — Every SOP has four fixed sections: Symptoms, Variables to check, Actions,
  Who approves. — Consistent retrieval and citations.
- 2026-11-01 — Open the Azure free account on Nov 16; Fabric trial in week 4 with an
  Entra ID user. — Azure credit lasts 30 days; Fabric does not accept personal emails.
- 2026-11-01 — Everything in the repo in English. — Public portfolio.
- 2026-11-02 — Before building on the data, confirm which control scheme generated it
  (plot IDV 2 against normal operation and see which valves move). — The data is
  closed-loop; diagnosis depends on what the controllers do.
- 2026-11-02 — The data matches the temain_mod control scheme, so the check above no longer
  has to come first. The IDV 2 plot stays in the notebook. — Valve-against-measurement
  slopes match its gains: XMV 7/XMEAS 12 (2.943 vs 2.9429), XMV 8/XMEAS 15 (2.314 vs 2.3143),
  XMV 11/XMEAS 17 (-2.370 vs -2.3711). In runs 1-5, IDV 2 opens the purge while pressures
  average no change, as hypothesized in docs/tep-notes.md.
- 2026-11-02 — Load all 500 fault-free runs plus runs 1-5 of each fault, keeping the original
  run numbers (300,000 rows, 33 MB). — A stronger normal baseline, and a reproducible subset.
- 2026-11-02 — Schema: `process_data` (fault_number, run, sample, plant_shutdown, 52 signals)
  and `tag_mapping` (original_tag, physical_name, unit, description). Names live in
  data/tag_map.csv. — Readable SQL, and a mapping that is easy to review in a diff.
- 2026-11-02 — Naming: compositions end in `_mol_pct`; XMV columns end in `_valve` and hold
  controller output; XMEAS 22 is `condenser_cooling_water_outlet_temperature` although
  teprob.f labels it Separator. — Keeps `purge_b_mol_pct`, `purge_flow` and `purge_valve`
  apart; XMV values leave 0-100 in fault data, so they are not valve positions; teprob.f's
  code puts XMEAS 22 and XMV 11 on the same cooling water loop.
- 2026-11-02 — Keep the rows after a plant shutdown and flag them with `plant_shutdown`, true
  from the trip sample on. Tools and evals must filter on it. — After the 3000 kPa trip the
  22 continuous measurements freeze while analyzers and XMVs keep changing up to sample 500.
  That is 2,197 of our 50,000 fault rows (fault 6 all 5 runs; fault 18 runs 1, 3, 4). Keeping
  them preserves 500 samples per run and lets the agent see the trip.
- 2026-11-02 — The .RData files are downloaded by hand from the dataset page;
  data/download_tep.py verifies their MD5s and explains a 403. — Dataverse's load balancer
  answers Python's urllib with HTTP 403. The cause is unknown and may be deliberate, so we
  do not work around it by changing the client.
- 2026-11-02 — Python 3.13 via uv, pinned in pyproject.toml and not in .python-version. —
  pyenv also reads .python-version and has no 3.13 here, which would break `python` outside
  the virtual environment.
- 2026-11-02 — Commits in this repo use the GitHub no-reply address, set in the repo's git
  config. — The repo is public and the global git email is a work address.
- 2026-11-02 — Open for week 2: `summarize_fault` should use normal-operation statistics,
  not the normal run with the same number. — Each faulty run copies that normal run until
  the fault starts (first 20 samples identical). That is useful as eval ground truth, but a
  real plant has no such twin.
- 2026-11-02 — Open for week 3: rewrite two eval examples in docs/plan.md. — The "first hour"
  of fault 6 is before the fault starts. "Run 12" does not exist with runs 1-5, and the
  `fault_number` column would give away diagnosis answers.

# Agent Development Guidelines

## 1. Purpose

Provide a clear, single reference for implementing, extending, and maintaining AI agents and related services (Python backends, data scripts, frontend interactions) in this repository, with emphasis on spec-driven development using the `docs/` folder.

## 2. Core Principles

1. Favor simplicity and readability over premature abstraction.
2. Keep functionality self‑documenting; use docstrings, not progress/status comments.
3. Minimize surface area: small, cohesive modules > large monoliths.
4. Explicit > implicit for data contracts, configuration, and side effects.
5. Make cheap experiments disposable (prefixed `adhoc_`), not permanent.

## 3. Project‑Wide Conventions

### 3.1 Documentation
* Primary documentation channel inside code: **docstrings** (revise them whenever code changes behavior or signature).
* Only add code comments for non‑obvious logic or critical nuances. Never for progress logs, migration notes, or "previous implementation" commentary.
* Update `docs/IMPLEMENTATION_LOG.md` with meaningful architectural or technical decisions (not micro‑steps) when a feature is completed or a design choice is finalized.
* Add confirmed recurring pitfalls to `docs/TROUBLESHOOTING.md` (after user confirmation—see Section 6).
* Each component/service keeps concise run & test instructions in its local `README.md`.

### 3.2 Refactoring & Improvements
Opportunistic simplifications are encouraged. When you see a refactor beyond the immediate task:
* Perform low‑risk, obviously beneficial cleanups directly (pure simplification, dead code removal).
* For broader architectural shifts, surface a brief rationale in chat before proceeding.

### 3.3 Experiments & Troubleshooting
When investigating complex issues:
1. Prefer quick inline or REPL tests first.
2. Use PowerShell friendly commands (Windows dev baseline).
3. Load environment variables from `.env` when relevant.
4. If a throwaway script is necessary, name it `adhoc_test_<purpose>.py` (see Section 7) and delete after insights are integrated.

### 3.4 Technology Stack
* Primary backend language: **Python**, package & env management via `uv` (`pyproject.toml` authoritative; avoid `requirements.txt`).
* API framework: **FastAPI**.
* Data validation: **Pydantic** models (under `models/`).
* Frontend: **React** + `assistant-ui` (Tailwind present).

## 4. Python Agent & Service Guidelines

### 4.1 Structure & Modeling
* Use Pydantic models for request/response & internal validated schemas. Place in `models/`.
* Keep service boundaries explicit (e.g., `routes/`, `services/`, `repositories/`).

### 4.2 Documentation & Style
* Every public class/function: docstring specifying purpose, parameters, return value(s), exceptions.
* Avoid redundant comments explaining obvious code or restating names.

### 4.3 Logging
* Use Python `logging` with appropriate levels: DEBUG (diagnostics), INFO (lifecycle events), WARNING (recoverable anomalies), ERROR (failures), CRITICAL (systemic outages).
* No print statements in production paths.

### 4.4 Testing
* Use `pytest`.
* Prefer unit tests (mocks) for logic; integration tests for IO (DB, external HTTP, vector stores, etc.).
* If a one‑off exploratory script was needed, port validated findings into tests and delete the ad‑hoc script.

### 4.5 Ports & Local Dev
* Assign distinct default ports per service to avoid collisions (document them in the service `README.md`).

## 5. Spec-Driven Development: docs/ Folder

The `docs/` folder is the single source of truth for project specifications, architecture, and planning. All documentation follows uppercase naming with `.md` extension.

### 5.1 Documentation Structure

| Document | Purpose | Update Frequency | Agent Autonomy |
|----------|---------|------------------|----------------|
| **REQUIREMENTS.md** | User stories, functional requirements, acceptance criteria | Per feature/sprint | **User-controlled** - agents suggest changes, user approves |
| **DESIGN.md** | System architecture, technology stack, design patterns, key decisions | When architecture evolves | **User-controlled** - agents propose, user confirms |
| **DATA_MODELS.md** | Database schemas, message formats, data structures | When data model changes | **User-controlled** - agents suggest, user reviews |
| **API_REFERENCE.md** | API endpoints, request/response contracts, integration points | When APIs change | **User-controlled** - agents can draft, user approves |
| **OBSERVABILITY.md** | Monitoring strategy, logging approach, metrics, alerts | During observability setup | **User-controlled** - agents propose, user decides |
| **TESTING.md** | Testing strategy, test scenarios, coverage requirements | When test approach changes | **User-controlled** - agents suggest, user confirms |
| **DEPLOYMENT.md** | Deployment procedures, environments, infrastructure | When deployment changes | **User-controlled** - agents draft, user reviews |
| **IMPLEMENTATION.md** | High-level implementation plan and detailed task checklist | Daily/per task | **User-controlled** - agents update progress after tasks |
| **IMPLEMENTATION_LOG.md** | Chronological journal of decisions, progress, completed work | After each significant change | **Agent-maintained** - freely updated by agents |
| **TROUBLESHOOTING.md** | Common errors, solutions, workarounds | When issues are resolved | **Collaborative** - agents suggest after user confirms issue is common |

### 5.2 Agent Update Rules

#### Freely Update (No Approval Needed)
- **IMPLEMENTATION_LOG.md**: Add timestamped entries for completed features, architectural decisions made, technical choices, integration notes.
  - Format: `## YYYY-MM-DD - Brief Title\n\nDetails...`
  - Keep entries concise but informative
  - Reference related tasks from IMPLEMENTATION.md

#### Suggest & Wait for Approval
- **REQUIREMENTS.md**: Propose new requirements or changes to existing ones
- **DESIGN.md**: Suggest architectural changes or design improvements
- **DATA_MODELS.md**: Propose schema changes or new data structures
- **API_REFERENCE.md**: Suggest new endpoints or contract modifications
- **OBSERVABILITY.md**: Recommend monitoring/logging enhancements
- **TESTING.md**: Propose new test strategies or coverage improvements
- **DEPLOYMENT.md**: Suggest deployment procedure changes
- **IMPLEMENTATION.md**: Update task completion status, add subtasks

#### Collaborative Process
- **TROUBLESHOOTING.md**: 
  1. When encountering an error, solve it and mention in chat
  2. If user confirms it's a common/recurring issue, add structured entry
  3. Include: problem description, symptoms, root cause, solution, prevention
  4. Never add unconfirmed or one-off issues

### 5.3 Documentation Workflow

**When starting a new feature:**
1. Check `docs/REQUIREMENTS.md` for user stories and acceptance criteria
2. Review `docs/DESIGN.md` for architectural constraints and patterns
3. Consult `docs/DATA_MODELS.md` and `docs/API_REFERENCE.md` for contracts
4. Update `docs/IMPLEMENTATION.md` with task breakdown if needed
5. Begin implementation with this context

**During implementation:**
1. Follow design patterns and constraints from `docs/DESIGN.md`
2. Maintain docstrings in code (no progress comments)
3. Log significant decisions in `docs/IMPLEMENTATION_LOG.md` as you go
4. If you discover design issues, raise in chat—don't mutate DESIGN.md unilaterally

**After completing a feature:**
1. Update `docs/IMPLEMENTATION_LOG.md` with summary and key decisions
2. Mark tasks complete in `docs/IMPLEMENTATION.md`
3. If API/data model changed, propose updates to respective docs
4. Update component `README.md` if operational changes exist

**When encountering issues:**
1. Solve the problem
2. Mention solution in chat
3. If user confirms it's recurring, add to `docs/TROUBLESHOOTING.md`

## 6. Reinforced Documentation & Logging Rules

These constraints prevent uncontrolled documentation sprawl and progress leakage into code:

1. **Implementation Log Boundaries**: Implementation progress, rationale, or "this replaces X" notes belong in `docs/IMPLEMENTATION_LOG.md`—never as inline code comments or new files.

2. **Troubleshooting Workflow**: Only after confirming with the user that an issue is broadly relevant, add it to `docs/TROUBLESHOOTING.md`. Do not create parallel error collections.

3. **Controlled Design Changes**: Architectural or behavioral design alterations should be reflected (after approval) in `docs/DESIGN.md`. Treat DESIGN.md as a guiding artifact; do not mutate it unilaterally.

4. **Localized Documentation First**: Prefer updating the affected component's `README.md` for usage/run/test changes before touching high‑level design docs.

5. **Tests over Scratch Scripts**: Validate behaviors via `pytest` (unit/integration). Temporary investigative scripts must follow Section 7 and be removed post‑learning.

6. **Communication Channel Priority**: To inform about implementation decisions use:
   - (a) `docs/IMPLEMENTATION_LOG.md` (for technical decisions)
   - (b) chat output (for status updates)
   - (c) component `README.md` (brief operational changes)
   - (d) `docs/DESIGN.md` (after approval for architectural changes)

7. **New Doc File Exception**: If a truly new doc artifact is justified, prefix filename with `ADHOC_` and notify user. Expect eventual consolidation or deletion.

8. **No Progress/History Comments**: Ban inline comments like "// updated previous logic" or "# temporary hack (will remove)"—instead record durable decisions in `docs/IMPLEMENTATION_LOG.md`.

## 7. Ad‑Hoc / Disposable Artifacts

| Type | Naming Pattern | Purpose | Lifecycle |
|------|----------------|---------|-----------|
| Python scratch test | `adhoc_test_*.py` or `adhoc_*.py` | Quick reproduction / isolate behavior | Delete after converting insight into real tests/code |
| Documentation draft | `ADHOC_*.md` | Rare: staging ground for large doc refactor | Merge content into canonical doc then delete |

Rules:
* Must not be imported by production code.
* Must not hold secrets or credentials.
* Track none of them in long‑term design history; only distilled results.

## 8. Change Control & Communication

1. Before major architectural changes: summarize intent, risk, alternatives in chat for approval.
2. After implementing a feature: update relevant docstrings + `docs/IMPLEMENTATION_LOG.md`.
3. If you discover systemic flaw: propose remediation path; avoid broad speculative refactors without confirmation.
4. When proposing doc changes: provide specific diff or summary of proposed changes for user review.

## 9. Quick Reference Checklist

### Development Flow
1. Review `docs/REQUIREMENTS.md` and `docs/DESIGN.md` for context
2. Define/confirm data contract (Pydantic model, update `docs/DATA_MODELS.md` if proposing changes)
3. Write/extend tests (failing first where feasible)
4. Implement feature (docstrings maintained—no progress comments)
5. Run `pytest` (unit + integration if relevant)
6. Update `docs/IMPLEMENTATION_LOG.md` with decisions and completion
7. Update service `README.md` for operational changes
8. Mark tasks complete in `docs/IMPLEMENTATION.md`
9. Remove any `adhoc_` artifacts created during exploration

### Documentation Update Flow
1. **Need to change architecture?** → Propose in chat, update `docs/DESIGN.md` after approval
2. **Completed a feature?** → Log in `docs/IMPLEMENTATION_LOG.md` immediately
3. **Found a recurring issue?** → Solve it, mention in chat, add to `docs/TROUBLESHOOTING.md` if user confirms
4. **New API endpoint?** → Implement, then propose `docs/API_REFERENCE.md` update
5. **Schema change?** → Propose `docs/DATA_MODELS.md` update before implementing

### Ad‑Hoc Script Flow
1. Name with `adhoc_` prefix
2. Isolate experiment
3. Migrate result into tests or code
4. Delete script

## 10. Scope & Precedence

This `AGENTS.md` centralizes operational & stylistic guidance. If conflicts arise:
1. Explicit user instruction (chat) overrides this file case‑by‑case
2. `docs/DESIGN.md` governs architecture (pending approved changes)
3. `docs/REQUIREMENTS.md` defines what we're building
4. This file governs daily engineering discipline & hygiene

## 11. Context for AI Agents

When working on this codebase:
- **Always check `docs/` first** - it contains the authoritative specifications
- **IMPLEMENTATION_LOG.md is your journal** - update it freely as you work
- **Propose, don't assume** - for design/requirement changes, always ask the user first
- **docs/README.md** - provides an overview and navigation guide for all documentation
- The documentation structure supports spec-driven development, enabling you to understand project context before writing code

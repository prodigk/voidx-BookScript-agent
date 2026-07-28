AGENTS.md

1. Project Identity

Project Name

YouTube Book Script Agent

Objective

Build a local-first web application that analyzes approximately 200 locally stored Markdown book-note files and generates evidence-grounded Korean YouTube research documents, outlines, and scripts.

The core workflow is:

Topic input
→ Topic analysis
→ Markdown knowledge retrieval
→ Candidate book selection
→ Evidence extraction
→ Cross-book narrative construction
→ YouTube script generation
→ Citation validation
→ Artifact export

This project must prioritize retrieval accuracy, source traceability, and evidence validation over visual polish or rapid script generation.

⸻

2. Required Project Documents

Before making any code or architecture changes, read the following files in order:

1. AGENTS.md
2. PROJECT_SPEC.md
3. README.md
4. DESIGN-airbnb.md

Treat PROJECT_SPEC.md as the primary product and technical specification.

Treat DESIGN-airbnb.md as the primary UI and visual design specification.

When implementation details conflict:

Product behavior        → PROJECT_SPEC.md
Development process     → AGENTS.md
UI and visual direction → DESIGN-airbnb.md

Do not silently ignore conflicts. Record them in the implementation summary.

⸻

3. Core Product Principles

3.1 Local-first

* Markdown source files must remain local.
* Do not upload the complete Markdown library to an external LLM API.
* Send only retrieved and necessary chunks to the LLM.
* Never modify original Markdown files.
* Generated files must be stored separately from source files.

3.2 Evidence-first

Do not generate a script immediately from a topic.

The required sequence is:

Search
→ Evidence collection
→ Candidate book ranking
→ Final book selection
→ Research pack
→ Narrative outline
→ Script
→ Validation

If supporting evidence is insufficient, return an insufficient-evidence result rather than fabricating content.

3.3 Traceability

Every retrieved chunk must preserve:

chunk_id
book_id
book title
author
source file
heading path
start line
end line
content hash

Every book-related claim in a generated script must be connected to one or more source chunks.

3.4 Generated Text Classification

All generated content must be classified using one of the following types:

quotation
paraphrase
interpretation
transition
example
commentary

Never present generated or paraphrased text as a direct quotation.

3.5 Incremental Development

Do not implement the entire system in one iteration.

Follow the phases defined in PROJECT_SPEC.md.

Complete and test each phase before moving to the next phase.

⸻

4. Technical Direction

4.1 Base Stack

Use the following technologies unless there is a clear technical reason not to:

Language              Python 3.12+
Package management    uv
Web framework         FastAPI
Frontend              Next.js with TypeScript
UI styling            Tailwind CSS
Validation            Pydantic
CLI                   Typer
Database              SQLite
Keyword search        SQLite FTS5
Testing               pytest
Frontend testing      Vitest
E2E testing           Playwright
Configuration         YAML
Environment variables python-dotenv
LLM API               OpenAI Responses API

4.2 Optional Technologies

Use only when required by the current phase:

Vector search         sqlite-vec or Chroma
Workflow management   LangGraph
Prototype UI          Streamlit
Markdown parsing      markdown-it-py
Frontmatter parsing   python-frontmatter

Do not introduce LangGraph before the basic Python pipeline is stable.

4.3 Architecture

Prefer a modular architecture with clear boundaries between:

ingestion
metadata parsing
chunking
indexing
retrieval
ranking
evidence curation
narrative generation
script generation
citation validation
web API
frontend UI
artifact export

Avoid large service classes and monolithic agent functions.

Each module must have one primary responsibility.

⸻

5. Repository Structure

Use the following repository structure as the default.

youtube-book-agent/
├── AGENTS.md
├── PROJECT_SPEC.md
├── DESIGN-airbnb.md
├── README.md
├── pyproject.toml
├── package.json
├── .env.example
├── .gitignore
│
├── library/
├── metadata/
├── config/
├── prompts/
├── reports/
├── data/
├── outputs/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── ingestion/
│   │   ├── retrieval/
│   │   ├── agents/
│   │   ├── schemas/
│   │   ├── storage/
│   │   ├── llm/
│   │   └── utils/
│   ├── scripts/
│   └── tests/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── lib/
│   ├── hooks/
│   ├── types/
│   ├── public/
│   └── tests/
│
└── docs/

The exact structure may evolve, but separation between backend, frontend, local source library, generated artifacts, and configuration must remain clear.

⸻

6. Backend Rules

6.1 Python Standards

* Use Python 3.12 or later.
* Use type hints for public functions and class methods.
* Use Pydantic for structured data and LLM outputs.
* Use pathlib instead of manual path string manipulation.
* Keep functions small and focused.
* Prefer explicit dependency injection over hidden global state.
* Avoid hardcoded paths and model names.
* Store configurable values in YAML or environment variables.
* Add docstrings where behavior is not self-evident.

6.2 Markdown Processing

* Support Korean file names and Korean text.
* Recursively discover .md files.
* Ignore hidden and generated directories.
* Parse YAML frontmatter where available.
* Infer missing metadata using the fallback order defined in PROJECT_SPEC.md.
* Preserve exact source file paths and line ranges.
* Record parsing failures without stopping the full batch.
* Never rewrite source Markdown files during ingestion.

6.3 Chunking

Use heading-aware chunking.

Priority:

H1
→ H2
→ H3
→ paragraph
→ configurable size split

Each chunk must include exact source line references.

Do not use fixed-character chunking as the only chunking strategy.

6.4 Retrieval

Implement retrieval progressively:

Phase 1  SQLite FTS5 keyword retrieval
Phase 2  Embedding-based semantic retrieval
Phase 3  Hybrid scoring
Phase 4  Book-level ranking and diversity control

Do not hide retrieval scores.

Search inspection tools must expose:

query
chunk score
book score
source file
heading
line range
matched content

6.5 LLM Calls

* Use structured outputs validated by Pydantic.
* Keep prompts in the prompts/ directory.
* Do not hardcode long prompts inside Python modules.
* Log model name, call stage, token usage, retries, and failures.
* Never log API keys.
* Never log the full Markdown library.
* Limit supplied context to selected chunks.
* Retry malformed structured output using a bounded retry policy.
* Do not retry indefinitely.

6.6 Citation Validation

Direct quotations must be checked against exact source text.

Validation must detect:

missing source
invalid line range
modified quotation
unsupported paraphrase
mixed-book attribution
incorrect title
incorrect author
unsupported causal claim

High-severity validation failures must block final approval of the script.

⸻

7. Frontend and UI Rules

7.1 Design Source

All site design must follow DESIGN-airbnb.md.

Before implementing or changing screens:

1. Read DESIGN-airbnb.md.
2. Identify applicable layout, spacing, type, color, component, and interaction rules.
3. Reuse established design tokens and patterns.
4. Record any necessary deviations.

Do not create an unrelated visual style.

Do not substitute generic dashboard styling when DESIGN-airbnb.md provides a defined direction.

7.2 Design Characteristics

Unless DESIGN-airbnb.md specifies otherwise, the interface should prioritize:

* spacious layout
* strong hierarchy
* restrained use of color
* clear card grouping
* readable Korean typography
* calm and editorial presentation
* simple controls
* obvious primary actions
* low cognitive load
* accessible contrast
* responsive behavior

7.3 Design Tokens

Implement reusable tokens for:

color
typography
spacing
radius
shadow
border
container width
breakpoints
motion

Do not repeatedly hardcode arbitrary values inside components.

7.4 Component Standards

Create reusable components for:

buttons
inputs
select controls
filter chips
book cards
evidence cards
status badges
progress indicators
empty states
error states
source references
script sections
download actions
modals
drawers
navigation

Avoid duplicate components that serve the same purpose.

7.5 Core Screens

The web application must eventually support:

1. Library status and audit
2. Topic input
3. Retrieval progress
4. Candidate book review
5. Final book selection
6. Evidence review
7. Narrative outline review
8. Script generation
9. Citation and validation review
10. Export and download

7.6 User Control

The user must be able to inspect intermediate results.

Do not hide the following behind automatic processing:

candidate books
selection reasons
retrieved evidence
book roles
narrative structure
validation issues

Where practical, allow the user to:

exclude a book
include a book
change book order
regenerate a section
edit a title
change tone
change duration
review sources

7.7 Responsive Design

The primary environment is desktop, but the application must remain usable on tablet and mobile.

Do not compress dense research tables into unreadable mobile layouts.

Use responsive cards, horizontal scrolling, progressive disclosure, or drawers where necessary.

7.8 Accessibility

* Use semantic HTML.
* Support keyboard navigation.
* Add visible focus states.
* Associate labels with controls.
* Do not rely only on color to communicate status.
* Use accessible names for icon-only buttons.
* Maintain sufficient contrast.
* Respect reduced-motion preferences.

⸻

8. Web Application Architecture

8.1 Frontend

Use Next.js with TypeScript.

Prefer:

App Router
Server Components where appropriate
Client Components only when interactivity is required
feature-based component organization
typed API responses
React Hook Form or equivalent for forms
Zod for frontend validation where useful

Avoid unnecessary global state.

Use local state, URL state, or server state before introducing a global state library.

8.2 Backend

Use FastAPI for:

library audit
index management
search
topic analysis
book ranking
evidence retrieval
narrative generation
script generation
validation
artifact download
pipeline status

Define clear request and response schemas.

Frontend types must align with backend response models.

8.3 Local Execution

The development environment must support:

backend local server
frontend local server
local SQLite database
local Markdown library
local generated outputs

Provide documented commands to start both frontend and backend.

8.4 Vercel Hosting

Use Vercel as the hosting platform for the web frontend.

The deployment strategy must account for the fact that the Markdown library and SQLite database are local-first resources.

Default hosting approach:

Frontend             Vercel
Public landing UI    Vercel
Local processing API local machine
Local Markdown files local machine
Local SQLite         local machine

Do not assume Vercel serverless functions can directly access the user’s local Markdown files.

The frontend must support a configurable API base URL so that the Vercel-hosted interface can communicate with the locally running backend when the environment permits it.

Environment variable example:

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

For local development:

Frontend: http://localhost:3000
Backend:  http://localhost:8000

For Vercel deployment, configure environment variables through the Vercel project settings.

Do not commit deployment secrets.

8.5 Deployment Constraints

Before deploying, verify:

frontend production build succeeds
environment variables are documented
local API dependency is clearly explained
CORS configuration is explicit
no local absolute paths are bundled into frontend code
no API keys are exposed to the browser
generated artifacts are not unintentionally committed

If a fully cloud-hosted architecture is introduced later, it must be treated as a separate architectural phase because local source files and SQLite storage cannot be assumed to persist inside Vercel’s serverless environment.

⸻

9. API and Security Rules

* Never expose OpenAI API keys to the browser.
* LLM calls must be executed by the backend.
* Validate every user input.
* Sanitize file names used for output.
* Prevent path traversal.
* Restrict file access to configured project directories.
* Do not serve arbitrary local files.
* Add CORS rules only for approved frontend origins.
* Avoid returning full source documents when a source excerpt is sufficient.
* Do not store secrets in source control.
* Keep .env.example synchronized with required variables.

⸻

10. Testing Rules

10.1 Backend Tests

Use pytest.

Required test areas:

Markdown discovery
frontmatter parsing
metadata inference
heading parsing
chunk boundaries
line-range accuracy
SQLite indexing
FTS search
incremental indexing
book ranking
evidence structures
citation validation
API schema validation

10.2 Frontend Tests

Use Vitest and Testing Library.

Required test areas:

form validation
topic submission
candidate book selection
evidence display
validation issue display
loading states
empty states
error states
responsive component behavior

10.3 End-to-End Tests

Use Playwright for critical paths:

library audit
topic submission
book selection
outline generation
script generation
artifact download

10.4 Test Discipline

* Add tests with each feature.
* Do not delete valid tests to make a build pass.
* Do not weaken assertions without a documented reason.
* Run relevant tests before completing a task.
* Run the complete test suite before completing a phase.
* Record tests that could not be executed.

⸻

11. Development Workflow

For each implementation task, follow this sequence:

1. Read relevant specification files.
2. Inspect the existing code.
3. Identify the smallest coherent implementation scope.
4. Implement the feature.
5. Add or update tests.
6. Run tests and static checks.
7. Fix failures.
8. Update documentation.
9. Summarize changes.
10. List known limitations and next steps.

Do not make broad unrelated refactors during a focused task.

Do not rewrite working modules unless required.

Prefer small, reviewable changes.

⸻

12. Phase Management

Follow the phases in PROJECT_SPEC.md.

Phase 0

Project initialization
Configuration
Logging
Database initialization
Basic CLI
Test setup

Phase 1

Library discovery
Frontmatter parsing
Metadata inference
Library audit report

Phase 2

Heading-aware chunking
SQLite storage
FTS5 indexing
Incremental indexing

Phase 3

Embeddings
Vector search
Hybrid retrieval
Search evaluation

Phase 4

Topic analysis
Query expansion
Book ranking
Evidence curation
Book selection

Phase 5

Narrative architecture
Outline generation
Title generation

Phase 6

Script generation
Source markers
Style controls

Phase 7

Citation validation
Issue reporting
Targeted revision

Phase 8

Next.js web UI
FastAPI integration
DESIGN-airbnb.md implementation

Phase 9

Vercel frontend deployment
Environment setup
Deployment documentation
Production checks

Do not begin later phases when earlier-phase data integrity is unstable.

⸻

13. Documentation Requirements

Keep README.md current.

It must include:

project overview
architecture
requirements
installation
environment variables
library directory setup
index build command
backend start command
frontend start command
test commands
Vercel deployment steps
local API connection explanation
known limitations

Create or update documentation whenever commands, environment variables, APIs, or architecture change.

⸻

14. Commands

Use these commands as the intended defaults.

Backend Setup

uv sync

Backend Tests

uv run pytest

Library Audit

uv run python backend/scripts/audit_library.py

Index Build

uv run python backend/scripts/build_index.py

Backend Development Server

uv run uvicorn backend.app.main:app --reload --port 8000

Frontend Setup

cd frontend
npm install

Frontend Development Server

npm run dev

Frontend Tests

npm run test

Production Build

npm run build

End-to-End Tests

npm run test:e2e

Vercel Deployment

vercel

For production:

vercel --prod

If the actual project structure changes, update this section and README.md together.

⸻

15. Environment Variables

Maintain an up-to-date .env.example.

Expected variables may include:

OPENAI_API_KEY=
OPENAI_MODEL=
EMBEDDING_MODEL=
LIBRARY_PATH=
OUTPUT_PATH=
DATABASE_PATH=
CONFIG_PATH=
BACKEND_HOST=
BACKEND_PORT=
ALLOWED_ORIGINS=
NEXT_PUBLIC_API_BASE_URL=

Never place real credentials in .env.example.

⸻

16. Output and Artifact Rules

Generated run artifacts must be stored outside source directories.

Default structure:

outputs/
└── <run-id>/
    ├── input.json
    ├── topic_analysis.json
    ├── search_results.json
    ├── candidate_books.json
    ├── selected_books.json
    ├── evidence.json
    ├── research.md
    ├── narrative.json
    ├── outline.md
    ├── script_with_sources.md
    ├── script.md
    ├── citations.json
    └── validation_report.md

Do not overwrite prior runs without explicit instruction.

Use stable run IDs.

⸻

17. Definition of Done

A task is complete only when:

implementation matches the current phase
relevant tests exist
tests pass
type checks and builds pass where applicable
documentation is updated
source Markdown files remain unchanged
errors are handled explicitly
known limitations are recorded

A phase is complete only when all acceptance criteria in PROJECT_SPEC.md are satisfied.

⸻

18. Prohibited Practices

Do not:

* modify source Markdown files
* send the full Markdown library to an LLM
* fabricate quotations
* generate unsupported book claims
* hide missing evidence
* expose API keys in frontend code
* hardcode local absolute paths
* deploy local SQLite assumptions directly to Vercel serverless
* skip tests for core ingestion or retrieval logic
* replace DESIGN-airbnb.md with an unrelated design system
* introduce unnecessary frameworks
* create large unreviewable changes
* suppress errors without logging
* use generated content as factual evidence
* implement UI before core data integrity is reliable

⸻

19. Task Completion Report

At the end of each Codex task, report:

1. Implemented scope
2. Files created
3. Files modified
4. Commands executed
5. Test results
6. Build results
7. Known limitations
8. Recommended next step

For UI tasks, additionally report:

DESIGN-airbnb.md rules applied
responsive behavior
accessibility checks
design deviations

For deployment tasks, additionally report:

Vercel project configuration
environment variables
production URL
local backend dependency
remaining deployment constraints

⸻

20. Initial Codex Instruction

When starting from an empty or partially initialized repository, use the following process:

Read AGENTS.md, PROJECT_SPEC.md, DESIGN-airbnb.md, and README.md.
Inspect the repository before changing files.
Implement only the requested phase.
Do not implement embeddings, LLM agents, frontend screens, or deployment unless they are explicitly included in the requested scope.
Preserve Korean file names and Korean content.
Do not modify Markdown source files.
Add tests for every core feature.
Run tests before finishing.
Update README.md.
Return the implementation summary using the reporting format defined in AGENTS.md.

⸻

21. User Request Tracking

Maintain `chat.md` as an append-only record of the user's request text for prompt-quality review.

Rules:

* At the end of each phase-level implementation task, append all user requests received since the previous completed phase entry.
* Preserve the user's wording, spelling, spacing, punctuation, and language as closely as the available conversation history permits.
* Do not silently summarize, rewrite, translate, or improve the request text.
* Exclude IDE-generated context such as Active file, Open tabs, and environment metadata unless the user explicitly includes it as part of the request.
* Group entries under the applicable phase or workstream heading.
* Use a known message date only when it is available. Do not invent dates for older requests.
* Do not record assistant responses, tool output, API keys, secrets, or unrelated local file contents.
* Keep prior entries unchanged. Corrections or recovered history must be added with an explicit note instead of rewriting the historical record.
* Include the `chat.md` update in the phase completion report.

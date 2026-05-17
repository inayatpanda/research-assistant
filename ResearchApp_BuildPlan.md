# Research Manuscript Assistant — Master Build Document

---

## PART 0: HOW TO START A CLAUDE CODE SESSION

### Step 1 — Install Claude Code (if not already installed)
```bash
npm install -g @anthropic/claude-code
```

### Step 2 — Create your project folder and navigate to it
```bash
mkdir research-manuscript-assistant
cd research-manuscript-assistant
```

### Step 3 — Launch Claude Code with Opus model
```bash
claude --model claude-opus-4-5
```
> Using `--model claude-opus-4-5` ensures the most capable model handles the full build. Do this every session.

### Step 4 — Paste the prompt
Copy the entire block from **Part 1** below and paste it as your first message. Claude Code will read the full spec and begin Phase 1.

### Step 5 — Use slash commands throughout the build
| Command | When to use |
|---|---|
| `/review` | After each phase is complete |
| `/security-review` | Before any AI API integration + before final deploy |
| `/ui-ux-pro-max` | Before building any new screen or component |

### Note on Claude Code vs Claude inside the app
These are two separate things — you can use both:
- **Claude Code (CLI)** builds the app. It writes and edits all the code in your terminal.
- **Claude API (Anthropic)** is one of the AI providers available *inside* the finished app (alongside Gemini and GPT-4). Users select their preferred AI in Settings and enter their own API key.

### Vercel Deployment (Web Version)
You have the Vercel MCP connected. Once Phase 8 is complete, Claude Code can deploy the web version directly. Add this to your session when ready:
```
Deploy the web app to Vercel using the Vercel MCP.
```

---

## PART 1: CLAUDE OPUS PROMPT

> Copy this entire block as your opening message when starting a Claude Code session with Opus.

---

```
You are helping me build a web + desktop application called the **Research Manuscript Assistant** — a tool for medical researchers (initially orthopaedics) to streamline writing research articles. Think of it as a better Zotero + Mendeley + statistical workbench + AI writing assistant, all in one. The core design philosophy is: AI assists but never replaces the researcher. Every AI output is grounded in source material the user has already read and annotated, minimising hallucination.

---

## TECH STACK

- **Frontend**: React + TypeScript + Vite
- **Styling**: Tailwind CSS + shadcn/ui (modern, clean, professional UI)
- **Animations**: Framer Motion — all transitions, panel slides, highlight appearances, modal animations
- **Dashboard & Data Components**: Tremor (tremor.so) — pre-built charts, stat cards, tables for the statistics module
- **Icons**: Lucide React — consistent icon set throughout
- **PDF Rendering**: React-PDF (react-pdf) as the primary viewer, with a custom annotation canvas layer on top for highlights
- **Rich Text Editor**: TipTap
- **Backend**: FastAPI (Python)
- **Database**: SQLite (via SQLAlchemy) — single user, local-first
- **Statistical Analysis**: pandas, scipy, statsmodels, lifelines, pingouin, matplotlib, plotly
- **AI Providers** (provider-agnostic adapter — user selects in Settings):
  - Default: **Gemini 1.5 Flash** (Google, free tier)
  - Option 2: **Claude API** (Anthropic — claude-opus-4-5 or claude-haiku-4-5 for speed)
  - Option 3: **GPT-4o** (OpenAI)
  - User enters their own API key per provider in Settings
- **Excel Parsing**: openpyxl / pandas
- **Export**: python-docx for Word export
- **Desktop**: Electron wrapper around the React web app
- **Deployment (Web)**: Vercel (via Vercel MCP — deploy directly from Claude Code session)
- **Citation DOI Lookup**: CrossRef API (free, no key needed)

---

## DESIGN REQUIREMENTS

- Modern, clean, academic-professional aesthetic — think Linear, Notion, or Readwise in terms of polish
- **Colour palette**:
  - Sidebar background: `#0F1117` (near-black)
  - Main workspace background: `#FAFAFA` (off-white)
  - Accent: a subtle blue `#2563EB` for interactive elements
- Colour-coded highlight system is the **visual centrepiece** of the entire app — must be unmistakable:
  - 🔴 RED `#EF4444` = Introduction
  - 🔵 BLUE `#3B82F6` = Methodology
  - 🟢 GREEN `#22C55E` = Results
  - 🟡 YELLOW `#EAB308` = Discussion
- Use Framer Motion for all transitions: panel slides, card appearances, modal open/close, highlight renders
- Use shadcn/ui components throughout — no raw HTML styling
- Use Tremor components for all data display: stat cards, charts, tables in the Statistics module
- Use Lucide React for all icons — no mixing icon libraries
- Every screen must have clear visual hierarchy — one primary action per screen
- Responsive but optimised for desktop (1280px+)
- **Invoke the `/ui-ux-pro-max` skill before designing any new screen or component**

---

## APPLICATION MODULES

### 1. PROJECT SETUP
- User creates a project with a title
- Selects **Study Type** from: Before/After Intervention | Outcome Study | Risk Factor Analysis | Group Comparison | Prospective Cohort | Retrospective Case Series | Systematic Review
- Study type configures: which statistical tools are shown, which risk-of-bias instrument is used, which manuscript section templates are loaded
- Projects listed in a dashboard on startup

### 2. LIBRARY MODULE
- Upload PDFs and Word documents (drag-and-drop + file picker)
- On upload, Gemini reads the document and extracts: Title, Authors, Journal, Year, Volume, Issue, Pages, DOI
- User confirms or corrects extracted metadata
- DOI lookup via CrossRef API as fallback/supplement
- Articles listed in a sidebar with title + first author + year
- For Systematic Review projects: articles tagged as Included / Excluded (with reason) / Pending
- Duplicate detection based on DOI or title similarity
- Search and filter articles in the library

### 3. PDF READER & ANNOTATION MODULE
- Full-page PDF viewer (PDF.js)
- Toolbar: highlight colour selector (Red/Blue/Green/Yellow), hand tool, zoom, page navigation, voice-to-text toggle
- User selects text → chooses a colour → highlight is saved to DB with: article_id, page number, position, colour, selected text, timestamp
- Each highlight opens an **inline note panel** immediately: user can write a paraphrase or note — "how I want this to appear in my manuscript"
- AI button on each highlight: "Summarise this passage" using Gemini
- Notes panel on the right: general article notes (type or dictate), separate from highlight notes
- When PDF is reopened, all highlights are re-rendered from DB onto the annotation layer
- Every note and highlight stores: source article title, authors, year — for automatic citation

### 4. COMPILATION MODULE
- Four section panels as tabs: Introduction | Methodology | Results | Discussion
- Each panel aggregates all highlights + inline notes from across all articles for that colour
- Each item shows: highlighted text | user's inline note/paraphrase | citation (Author et al., Year)
- User can reorder items by drag-and-drop
- User can add free-text notes directly in the compilation panel
- **Generate button** per item: Gemini takes (highlighted text + user's paraphrase note + section context) and drafts a sentence. User edits it. Citation is appended.
- **Generate Section Draft** button: Gemini drafts a full paragraph from all compiled items in that section. User edits line by line.
- All AI generation is clearly marked as AI-suggested until user edits and accepts it

### 5. MANUSCRIPT EDITOR
- Tabbed workspace: Introduction | Methodology | Results | Discussion | Abstract | Conclusion
- TipTap rich text editor per section
- User writes every line — AI assists via a floating toolbar: "Improve sentence", "Shorten", "Make more formal", "Add transition"
- Citation insertion: type @ or click Insert Citation → search library → inserts formatted inline citation
- Word count per section + total
- Citation numbers auto-update as you add/remove references
- **Final Manuscript** tab shows all sections combined, ready for review

### 6. DATA & STATISTICS MODULE
- Upload Masterchart as Excel (.xlsx)
- App reads and displays the data in a table (editable)
- Auto-generates descriptive statistics on upload
- Based on **Study Type**, suggests appropriate tests:
  - Before/After → Paired t-test, Wilcoxon signed-rank, effect size (Cohen's d)
  - Group Comparison → Independent t-test, Mann-Whitney U, Chi-square, ANOVA
  - Risk Factor → Logistic regression, Odds Ratios, 95% CI, multivariate analysis
  - Prospective Cohort → Kaplan-Meier survival curves, Cox proportional hazards, log-rank test
  - Outcome Study → Descriptive stats, PROMs analysis, normality tests
- Each analysis: user selects variables → app runs the test → displays result table + chart → user can export
- Gemini interprets results in plain English: "The difference between groups was statistically significant (p=0.02), suggesting..."
- All charts: publication-ready (Plotly), exportable as PNG/SVG
- Statistical guidance panel: for each test, explains when to use it, assumptions, and how to report in a manuscript

### 7. SYSTEMATIC REVIEW MODULE
(Activated when Study Type = Systematic Review)
- **Search Strategy**: document search strings used per database (PubMed, Embase, Cochrane, etc.)
- **PICO Framework**: define Population, Intervention, Comparison, Outcome for the review
- **PRISMA Flow Diagram**: user enters numbers at each stage (Identified → Screened → Eligible → Included) — diagram auto-generated and exportable
- **Abstract Screening**: view each article's abstract → mark Include / Exclude / Unsure with reason
- **Risk of Bias Assessment**:
  - MINORS (12-item) for non-randomised studies — auto-presented for each included article
  - RoB 2 for RCTs
  - Newcastle-Ottawa Scale for cohort/case-control
  - Study design tagged per article determines which tool is shown
- **Summary Risk-of-Bias Table**: auto-generated from all scored articles
- **Data Extraction Form**: structured form per article (customisable fields based on PICO)

### 8. CITATION & BIBLIOGRAPHY
- Every highlight, note, and manuscript citation tracks back to a library article
- Bibliography auto-generated from all cited articles in the manuscript
- Citation styles: Vancouver (default), APA, Harvard — selectable in Settings
- Abbreviation tracker: app detects all abbreviations used and generates a list
- PROSPERO / ClinicalTrials.gov registration number field in project settings

---

## AI INTEGRATION

- All AI calls go through a single **AIProvider adapter class** with a common interface: `extractCitation()`, `summarise()`, `generateDraft()`, `interpretResult()`, `assistWriting()`
- Swapping provider = changing one setting, no code changes
- **Provider options**:
  - **Gemini 1.5 Flash** (default, free tier) — best for getting started
  - **Claude API** (Anthropic) — claude-opus-4-5 for quality, claude-haiku-4-5 for speed/cost
  - **GPT-4o** (OpenAI) — alternative option
- Each provider's API key is entered by the user in Settings → stored locally, never sent anywhere except the provider
- **AI tasks**:
  - Citation extraction from uploaded PDF → Gemini/Claude reads document, returns structured metadata
  - Highlight summarisation → returns 1-2 sentence summary of selected passage
  - Section draft generation → takes compiled highlights + user paraphrases → drafts paragraph
  - Statistical result interpretation → takes test output → explains in plain English
  - Writing assistance → improve/shorten/formalise selected sentence in manuscript editor
- Every AI output is clearly labelled **"AI Suggested"** with Accept / Edit / Reject controls
- AI never generates citations — citations always come from the library database
- All AI calls wrapped in try/catch — if a call fails, show a user-friendly error and allow retry
- **Core anti-hallucination principle**: AI always receives the user's actual highlighted text and paraphrase notes as context. It drafts from real source material, not from general knowledge.

---

## BUILD CONVENTIONS

- Use `/review` after completing each module to check code quality, catch bugs, and ensure consistency
- Use `/security-review` before any AI API call implementation and before final deployment
- Invoke the **UI/UX pro max skill** before building any new screen or component
- Write unit tests for all statistical functions
- All DB operations go through a repository layer — no raw SQL in route handlers
- Environment variables for all API keys — never hardcoded
- Error handling: all AI calls wrapped in try/catch with user-friendly fallback messages
- Mobile-responsive is not a priority but don't break on smaller screens

---

## BUILD ORDER

Start with Phase 1. Do not move to Phase 2 until Phase 1 is complete and reviewed.

**Phase 1**: Project scaffold, routing, DB schema, project creation + study type selection, dashboard
**Phase 2**: Library module — file upload, AI citation extraction, metadata management, article list
**Phase 3**: PDF reader — PDF.js integration, colour-coded annotation layer, inline notes, persistence
**Phase 4**: Compilation module — section panels, aggregated highlights, AI generation
**Phase 5**: Manuscript editor — TipTap, citation insertion, AI writing assistance, word count
**Phase 6**: Data & statistics module — Excel upload, descriptive stats, test suggestions, analysis, charts
**Phase 7**: Systematic review module — PRISMA, risk of bias tools, abstract screening
**Phase 8**: Bibliography generation, export to Word, settings panel, final polish
**Phase 9**: Electron packaging for desktop

Additional UI/UX requirements:
- Add Framer Motion for all transitions and animations
- Add Tremor (tremor.so) for dashboard and chart components in the statistics module
- Add Lucide React for all icons — no other icon library
- Use React-PDF for the PDF viewer with a custom canvas annotation layer on top
- Dark sidebar (#0F1117) with light main workspace (#FAFAFA)
- The colour-coded highlight system (Red/Blue/Green/Yellow) is the visual centrepiece — make it beautiful
- Before building ANY screen or component, invoke the /ui-ux-pro-max skill
- The finished app should feel like a premium SaaS tool — think Linear or Notion in terms of polish

Begin with Phase 1. Ask me before moving to the next phase.
```

---

## PART 2: PHASED BUILD PLAN

### Phase 1 — Foundation & Scaffold
**Goal**: Running app skeleton with navigation, DB, and project creation

- Initialise React + TypeScript + Vite frontend
- Set up Tailwind CSS + shadcn/ui
- Initialise FastAPI backend with SQLAlchemy + SQLite
- Design DB schema: Projects, Articles, Highlights, Notes, Citations, Sections
- Build dashboard: list of projects, create new project, study type selector
- Left sidebar navigation: Library / Reader / Compile / Statistics / Manuscript / Settings
- Set up routing (React Router)
- Basic Settings page: AI provider selector, API key input, citation style

> ✅ **Run `/review`** — check schema design, routing structure, component architecture

---

### Phase 2 — Library & Article Management
**Goal**: Upload articles, extract citations, manage the library

- Drag-and-drop + file picker for PDF and Word upload
- Store files in local filesystem, metadata in DB
- Call Gemini API to extract: Title, Authors, Journal, Year, Volume, Issue, Pages, DOI
- CrossRef DOI lookup as fallback
- Metadata confirmation/edit screen
- Article list view: sortable by author, year, title
- Duplicate detection (DOI match or title similarity >90%)
- Article tagging (for Systematic Review: Included / Excluded / Pending)
- Search and filter in library

> ✅ **Run `/review`** — check API call error handling, file storage, duplicate logic
> 🔒 **Run `/security-review`** — Gemini API key handling, file upload validation

---

### Phase 3 — PDF Reader & Annotation Engine
**Goal**: Read PDFs, highlight in colour, add inline notes, persist everything

- Integrate PDF.js viewer in a full-page panel
- Toolbar: colour selector, zoom, page nav, voice-to-text toggle
- Text selection → colour picker → highlight drawn on annotation layer
- Save highlight to DB: article_id, page, text, colour, bounding coords, timestamp
- Inline note popup on each highlight: paraphrase field + AI summarise button
- Right panel: general article notes (text + voice dictation)
- On PDF open: reload all highlights from DB, re-render annotation layer
- AI summarise: selected highlight text → Gemini → returned summary shown inline

> ✅ **Run `/review`** — annotation persistence, PDF.js coordinate system, voice API integration

---

### Phase 4 — Compilation Module
**Goal**: All highlights aggregated by section, ready for AI-assisted drafting

- Four tabs: Introduction (Red) | Methodology (Blue) | Results (Green) | Discussion (Yellow)
- Pull all highlights + inline notes for each colour across all articles
- Display as cards: highlighted text | user paraphrase | citation
- Drag-and-drop reorder within a section
- Free-text note insertion between cards
- **Generate (per item)**: Gemini drafts a sentence from highlight + paraphrase + section context
- **Generate Section Draft**: Gemini drafts a full paragraph from all cards
- AI output clearly labelled, Accept / Edit / Reject controls
- Push accepted content to Manuscript Editor

> ✅ **Run `/review`** — AI prompt quality, citation threading, drag-drop logic

---

### Phase 5 — Manuscript Editor
**Goal**: Full writing workspace per section with AI line-by-line assistance

- TipTap rich text editor, one per section tab
- Floating AI toolbar: Improve | Shorten | Formalise | Add Transition
- `@` mention → citation search → inline citation inserted
- Auto-numbering of references (Vancouver style)
- Word count per section + total manuscript count
- Final Manuscript tab: all sections combined in order
- Abbreviation tracker: scan manuscript, list all abbreviations
- PROSPERO / ClinicalTrials.gov registration field

> ✅ **Run `/review`** — citation numbering consistency, TipTap extension correctness

---

### Phase 6 — Data & Statistics Module
**Goal**: Upload Masterchart, run analyses, generate publication-ready outputs

- Excel upload + pandas parsing, data table display (editable)
- Auto descriptive statistics on upload (mean, SD, median, IQR, n, %)
- Study type → suggested tests panel (explained in plain English)
- Statistical tests (each with variable selector UI):
  - Normality: Shapiro-Wilk, Kolmogorov-Smirnov
  - Comparison: Paired t-test, Independent t-test, Mann-Whitney U, Wilcoxon, Chi-square, ANOVA, Kruskal-Wallis
  - Regression: Linear, Logistic, Cox proportional hazards
  - Survival: Kaplan-Meier curves, log-rank test
  - Correlation: Pearson, Spearman
  - Effect sizes: Cohen's d, OR, RR, HR with 95% CI
- Results displayed: formatted table + Plotly chart
- Gemini interprets results in plain English (user confirms accuracy)
- Export: tables as formatted Word tables, charts as PNG/SVG

> ✅ **Run `/review`** — statistical function accuracy, assumptions checking, result formatting
> 🔒 **Run `/security-review`** — Excel file parsing (malicious file protection)

---

### Phase 7 — Systematic Review Module
**Goal**: PRISMA flow, risk of bias tools, abstract screening

- Activated automatically when Study Type = Systematic Review
- Search strategy documentation (free text per database)
- PICO framework form
- PRISMA flow: numeric inputs per stage → auto-generated diagram (exportable)
- Abstract screening queue: view abstract → Include / Exclude / Unsure + reason
- Risk of bias:
  - MINORS (12 items, score 0-2 each) for non-randomised studies
  - RoB 2 for RCTs (5 domains)
  - Newcastle-Ottawa Scale for cohort/case-control
  - Study design tag on each article determines which tool is shown
- Summary risk-of-bias table: all articles × all domains, colour-coded (low/moderate/high)
- Data extraction form builder: customise fields per project

> ✅ **Run `/review`** — PRISMA logic, risk-of-bias scoring accuracy, table generation

---

### Phase 8 — Bibliography, Export, Polish & Deployment
**Goal**: Complete, exportable manuscript with bibliography — then ship the web version

- Scan manuscript for all citation references
- Generate bibliography in chosen style (Vancouver, APA, Harvard)
- Export full manuscript to Word (.docx) — formatted with headings, page numbers, bibliography
- Settings panel: AI provider selector (Gemini / Claude / GPT-4o), API key input per provider, citation style, colour theme
- Onboarding flow for new users (first-time project creation walkthrough)
- Error states and empty states for all screens (no blank screens)
- Loading skeletons for all data-fetching screens
- **Deploy web version to Vercel** using the Vercel MCP — get a live URL

> ✅ **Run `/review`** — export fidelity, bibliography accuracy, edge cases
> 🔒 **Run `/security-review`** — full security pass, API key handling, file upload safety before shipping

---

### Phase 9 — Electron Desktop Packaging
**Goal**: Working macOS + Windows desktop app

- Wrap React app in Electron shell
- Handle local file system access for PDF storage
- Auto-update mechanism
- App icon, splash screen
- Package for macOS (.dmg) and Windows (.exe)

> ✅ **Run `/review`** — Electron security best practices, context isolation, IPC patterns

---

## PART 3: ADDITIONAL FEATURE IDEAS (Thinking Like a Researcher)

These are not in the initial build but worth planning for:

### Immediate Value Additions
**PubMed Search Integration** — Search PubMed directly from within the Library tab (PubMed has a free API). Import directly to library without manual upload. Massive time saver.

**Journal Targeting** — Set a target journal at the start. App stores word limits, abstract format, reference style, and author guidelines. Word count warnings when you exceed section limits.

**Template Library** — Pre-loaded manuscript templates per study type. For example, a Before/After Intervention template pre-fills Methods with: "Patients were assessed pre-operatively and at [X] months post-operatively using [outcome measure]." Saves the blank-page problem.

**Search Strategy Builder** — For systematic reviews, a guided builder for constructing Boolean search strings (AND/OR/NOT) with MeSH term suggestions. Auto-formats for PubMed, Embase, Cochrane.

### Workflow Intelligence
**Study Design Auto-detector** — When a PDF is uploaded, Gemini reads the abstract and suggests the study design (RCT, cohort, case series, etc.) so the user just confirms rather than manually tagging every article.

**Limitations Helper** — Based on study type and data entered, AI suggests common limitations the researcher should consider discussing. For example: for a retrospective case series it would flag "selection bias", "lack of control group", "retrospective data collection bias."

**Power Calculation Guidance** — For prospective studies, a calculator to estimate required sample size given expected effect size, alpha, and power. Essential for Methods section writing.

**Conflict of Interest Tracker** — Per-article field to note funding source and author affiliations. Auto-generates a COI summary table for the systematic review.

### Quality & Safety
**Reference Integrity Checker** — Before export, scans the manuscript and flags: any citation number in the text that has no corresponding bibliography entry, any bibliography entry not cited in the text, and any citation that doesn't match the stored metadata (e.g., year mismatch).

**Claim–Citation Matcher** — Flags sentences in the manuscript that make a factual claim but have no citation. Reduces the risk of uncited assertions getting past peer review.

**GRADE Evidence Quality** — For systematic reviews, auto-generate a GRADE (Grading of Recommendations, Assessment, Development and Evaluations) evidence quality table after risk-of-bias scoring.

### Long-term
**Collaboration Mode** — Share a project with a co-author. Each person's annotations shown in a different shade. Comments and tracked changes in the manuscript editor.

**Version History** — Snapshot the manuscript at any point. Compare versions. Roll back a section if needed.

**AI Model Fine-tuning on Accepted Outputs** — Over time, the app learns which AI suggestions the user accepts vs. rejects, and improves the prompts accordingly.

**Journal Submission Checker** — Before export, check the manuscript against a chosen journal's author guidelines (word count, figure count, reference limit, structured abstract requirements).

---

## REVIEW CADENCE

| After completing | Run |
|---|---|
| Each phase | `/review` |
| Any AI API integration | `/security-review` |
| Any file upload feature | `/security-review` |
| Each new screen or component | `/ui-ux-pro-max` skill first |
| Before Phase 9 (Electron packaging) | Full `/review` + `/security-review` pass |
| Before Vercel deployment (Phase 8) | `/security-review` |

---

## UI/UX LIBRARY QUICK REFERENCE

| Library | Purpose | Install |
|---|---|---|
| shadcn/ui | Core UI components (buttons, modals, inputs, cards) | `npx shadcn-ui@latest init` |
| Tailwind CSS | Utility styling | included with Vite setup |
| Framer Motion | Animations and transitions | `npm install framer-motion` |
| Tremor | Dashboard charts, stat cards, data tables | `npm install @tremor/react` |
| Lucide React | Icons | `npm install lucide-react` |
| React-PDF | PDF viewer | `npm install react-pdf` |
| TipTap | Rich text manuscript editor | `npm install @tiptap/react @tiptap/starter-kit` |

---

*Built for orthopaedic researchers. Designed to reduce hallucination, track every citation, and keep the human researcher in control.*

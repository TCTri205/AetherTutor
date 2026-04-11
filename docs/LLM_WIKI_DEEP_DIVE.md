# LLM Wiki Deep Dive Analysis

> Comprehensive analysis of the `references/llm-wiki` repository and integration blueprint for AetherTutor.
> Generated: 2026-04-10

---

## Table of Contents

1. [File-by-File Analysis](#1-file-by-file-analysis)
2. [Architectural Patterns](#2-architectural-patterns)
3. [Implementation Details](#3-implementation-details)
4. [Comparison with AetherTutor](#4-comparison-with-aethertutor)
5. [Missing Pieces Analysis](#5-missing-pieces-analysis)
6. [Detailed Implementation Blueprints](#6-detailed-implementation-blueprints)

---

## 1. File-by-File Analysis

### 1.1 CLAUDE.md vs AGENTS.md vs copilot-instructions.md

**Finding: All three files are IDENTICAL in content.**

Each file contains the exact same schema and operational rules for the LLM Wiki system. The only difference is their target audience:

| File | Target Tool | Purpose |
|------|-------------|---------|
| `CLAUDE.md` | Claude Code | Primary instruction set for Anthropic's Claude Code agent |
| `AGENTS.md` | Antigravity / Codex CLI / Cursor / Codex CLI | Generic agent instruction file (OpenAI Codex compatible) |
| `.github/copilot-instructions.md` | GitHub Copilot | Copilot reads this when the repo is opened in VS Code/GitHub |

**Why three files?** Different AI coding agents read different convention files at project root. This is a multi-agent compatibility strategy -- the same rules work across Claude Code, Codex, Cursor, and Copilot without conflict.

**Core content of all three:**
- 3-layer architecture definition (raw/ wiki/ outputs/)
- 6 "golden rules" (immutable raw, LLM-owned wiki, one-topic-per-file, cross-references, INDEX.md always updated, LOG.md tracks everything)
- 4 workflow definitions: ingest, query, lint, discover
- Frontmatter schemas for 4 page types: entity, concept, source, synthesis
- Auto-discovery strategy (topics, knowledge gaps, feeds, snowball)
- Language convention (Vietnamese content, English filenames, English frontmatter)

### 1.2 SKILL.md (skills/llm-wiki/SKILL.md)

This is the **Claude Code skill definition** -- a callable slash-command interface (`/llm-wiki`). It defines 9 sub-commands with exact workflows:

| Command | Purpose | Key Details |
|---------|---------|-------------|
| `init` | Create new wiki or add topic | Auto-generates keywords from topic name |
| `ingest` | Process new raw files | Reads history.json to skip already-processed files; each source can affect 5-15 wiki pages |
| `query` | Q&A from wiki | Reads INDEX.md first, follows wiki-links for context, saves valuable answers as syntheses |
| `lint` | Health check | Checks contradictions, orphans, missing pages, stale claims, broken links, gaps, quality |
| `discover` | Auto-find new sources | 7 strategies: reddit_scan, github_trending, github_watch, web_search, feed_poll, gap_fill, snowball |
| `run` | Full cycle | discover -> ingest -> lint, with optional second round if critical gaps found (max 2 loops) |
| `status` | Show wiki state | Counts by category, last run timestamps, health status |
| `digest` | Daily brief | Summarizes 24h of LOG.md, new sources, new pages, top 3 insights, pain points, gaps |
| `pain-rank` | Rank business opportunities | 5-criteria scoring framework (urgency x2, market x2, WTP x3, AI-fit x2, competition x1, max 50) |

**Key architectural insight:** Each command is a self-contained workflow that reads the config, operates on the file system, and logs to LOG.md. No database, no state server -- just markdown files and JSON metadata.

### 1.3 config.example.yaml

Complete configuration breakdown:

#### Wiki Info
```yaml
wiki:
  name: "My LLM Wiki"
  description: "Personal knowledge base"
  language: "en"
  max_pages_per_ingest: 15
```

#### Topics (what to learn about)
```yaml
topics:
  - name: "Your Topic 1"
    keywords: ["keyword1", "keyword2", "keyword3"]
    priority: high | medium | low
```

#### Feeds (automated sources)
- **GitHub Trending**: languages, since, min_stars, topics_filter
- **GitHub Orgs/People/Repos**: watch new_repos, releases, stars
- **Reddit**: subreddits, search terms for pain points, min_upvotes, sort
- **RSS feeds**: custom URLs
- **Hacker News**: min_score, keywords
- **Twitter/X**: accounts to follow

#### Schedule
```yaml
schedule:
  run:
    loop_interval: "1h"       # Claude Code /loop
    fallback_interval: "2h"   # Windows Task Scheduler
    max_sources: 5
  ingest:
    trigger: "on_new_file"
    batch_size: 5
  lint:
    interval: "6h"
    auto_fix: false
  recompile:
    interval: "weekly"
    cron: "0 10 * * 0"
```

#### Discovery Settings
```yaml
discovery:
  strategies: [web_search, feed_poll, gap_fill]
  web_search:
    engine: "websearch"
    max_results_per_topic: 5
    recency: "month"
  scraping:
    tool: "webfetch"
    save_images: true
    max_article_length: 50000
  dedup:
    check_url: true
    check_title: true
    similarity_threshold: 0.9
```

#### Output Settings
```yaml
outputs:
  formats: [markdown]
  save_queries: true
  save_syntheses: true
```

### 1.4 wiki-viewer.html

A **single-file, zero-dependency, mobile-first web application** (~600 lines) that serves as a wiki viewer. Key technical details:

#### Architecture
- **Pure HTML/CSS/JS** -- no frameworks, no build step, no server
- **Dark theme** with GitHub-dark color palette
- **Data embedded in JavaScript** -- the `pages` object is hardcoded JSON containing all wiki pages and their links
- **Three-panel navigation**: Dashboard, Page List, Graph View

#### Features

**Dashboard Panel:**
- 4 stat cards (Entities, Concepts, Sources, Syntheses) with color-coded numbers
- Summary stats: total pages, raw sources, cross-links count, broken links count
- Last discover date, health status
- Recent syntheses list

**Page List Panel:**
- Full-text search box (client-side filter)
- Pages grouped by category (Syntheses -> Entities -> Concepts -> Sources)
- Each item shows: category tag (color-coded), title, link count
- Click opens detail view

**Page Detail View (overlay):**
- Full title with category tag
- Outgoing links (with category tags)
- Incoming links (reverse lookup -- pages that link to this one)
- File path reference
- Broken link warnings (red warning for missing targets)
- Wiki-links are clickable and navigate to the target page

**Graph View:**
- Canvas-based force-directed graph layout
- 200 iterations of force simulation:
  - **Repulsion** between all node pairs (800/d^2)
  - **Attraction** along edges (spring force, target 80px)
  - **Center gravity** pulling nodes toward center (0.002)
  - **Damping** factor 0.85 per iteration
- Node size scales with link count (radius = 3 + linkCount * 0.8, clamped 4-12)
- Color-coded by category (Entity=green, Concept=purple, Source=orange, Synthesis=pink)
- Labels shown only for nodes with 3+ links
- Click on node opens detail view
- Touch-friendly (touch-action: none on canvas)

#### CSS Design System
```css
:root {
  --bg: #0d1117;         /* Dark background */
  --surface: #161b22;    /* Card background */
  --surface2: #21262d;   /* Nested surface */
  --border: #30363d;     /* Borders */
  --text: #e6edf3;       /* Primary text */
  --text2: #8b949e;      /* Secondary text */
  --accent: #58a6ff;     /* Blue accent */
  --entity: #3fb950;     /* Green for entities */
  --concept: #d2a8ff;    /* Purple for concepts */
  --source: #f0883e;     /* Orange for sources */
  --synthesis: #f778ba;  /* Pink for syntheses */
  --red: #f85149;        /* Red for errors */
}
```

#### Limitation
The viewer embeds all data in the HTML file. It cannot dynamically load files from the local filesystem (browser security). To update, the `pages` object must be regenerated. This is fine for a static snapshot but not a live viewer.

### 1.5 Scripts

#### run-wiki.sh
```bash
#!/bin/bash
WIKI_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="$WIKI_ROOT/outputs/auto-run.log"

cd "$WIKI_ROOT" || exit 1
claude --print --dangerously-skip-permissions "/llm-wiki run" 2>>"$LOG_FILE" | tail -20 >> "$LOG_FILE"
```

- Simple bash wrapper for system schedulers
- Calls `claude --print` with the `/llm-wiki run` command
- `--dangerously-skip-permissions` allows file system writes without prompts
- Logs to `outputs/auto-run.log`
- Requires Git Bash on Windows

#### setup-scheduler.ps1
```powershell
# Windows Task Scheduler setup
$taskName = "LLM-Wiki-AutoRun"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration (New-TimeSpan -Days 365)
$action = New-ScheduledTaskAction -Execute $bashPath -Argument $scriptPath
# ... settings: allow batteries, don't stop, network required
Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action
```

- Creates a Windows Scheduled Task that runs every 2 hours for 365 days
- Requires admin privileges
- Uses Git Bash as the executor
- Settings: runs on battery, doesn't stop on battery, runs when available, only if network is up

### 1.6 Templates

#### wiki/INDEX.template.md
A catalog skeleton with 4 category sections (Entities, Concepts, Sources, Syntheses), each with HTML comment explaining the category purpose. Auto-updated on every ingest.

#### wiki/LOG.template.md
A timeline skeleton with a single separator line. Entries follow format: `## [YYYY-MM-DD HH:mm] action | Description`. Grep-friendly format.

### 1.7 .gitignore

Extensive ignore list for:
- `outputs/` -- personal query results
- `.discoveries/` -- personal metadata
- `raw/` subdirectories -- personal sources
- `wiki/` subdirectories (entities, concepts, sources, syntheses) -- LLM-generated content
- Keeps templates: `!wiki/INDEX.md`, `!wiki/LOG.md`
- Personal config: `config.yaml` (use example as template)

**Key insight:** The repo is a **template** -- the actual wiki content is not committed. Only the structure (CLAUDE.md, AGENTS.md, config.example.yaml, templates, scripts, skill, viewer) is version-controlled.

### 1.8 FAQ.md

Covers 7 critical questions:

1. **Wiki scaling** -- <100 pages: INDEX.md is fine; 100-500: INDEX.md + grep; 500+: needs search engine (qmd, ripgrep, or embeddings). Karpathy recommends [qmd](https://github.com/tobi/qmd) for large wikis.

2. **Schema versioning** -- Schema co-evolves with LLM. Use git for versioning. Raw sources are immutable so wiki can be rebuilt from scratch. Weekly recompile handles major schema changes.

3. **Internal docs (Confluence)** -- 3 options: drop files into raw/, disable discovery, or connect via MCP server.

4. **Token costs** -- 30K-80K tokens per cycle. 1h loop = 720K-2M tokens/day. Skip is cheap when no new sources.

5. **Team usage** -- Designed for 1 person. Team use: shared git repo, individual configs, git branches for research threads.

6. **Model agnostic** -- Pattern works with any LLM. SKILL.md is Claude-specific but AGENTS.md works for Codex.

7. **Hallucination prevention** -- 5 layers: no-fabrication rule, mandatory citations, immutable raw sources, periodic lint, error compounding warnings.

### 1.9 LICENSE

MIT License, copyright 2026.

---

## 2. Architectural Patterns

### 2.1 Three-Layer Architecture (raw/ wiki/ outputs/)

```
raw/        → Immutable sources (LLM READ-ONLY, NEVER WRITE)
wiki/       → LLM-owned knowledge base (LLM CREATE/UPDATE/DELETE)
outputs/    → Query results, reports, rankings (READ-ONLY for humans)
```

**How immutability enables trust:**
- `raw/` is the ground truth. Every wiki page traces back to a raw source.
- If the LLM hallucinates, you can verify by reading the raw source.
- Schema changes don't matter -- you can delete all of `wiki/` and rebuild from `raw/`.
- This is the **single most important design principle** in the system.

**Workflow:**
```
discover → downloads → raw/articles/YYYY-MM-DD-slug.md
ingest   → reads raw/ → creates/updates wiki/ pages
query    → reads wiki/ → generates answers + optional outputs/
lint     → scans wiki/ → finds gaps, contradictions, orphans
```

**Contrast with AetherTutor:** AetherTutor has `uploads/` (similar to raw/) but processes directly into PostgreSQL/ChromaDB without an intermediate markdown layer. The wiki approach is simpler and more auditable.

### 2.2 Cross-Referencing with [[wiki-links]]

**Format:** `[[filename-without-extension]]`

**How it works:**
1. Every wiki page has a "Lien ket" (Links) section with `[[target]]` entries
2. INDEX.md catalogs all pages, so the LLM can resolve `[[name]]` to `wiki/category/name.md`
3. Orphan detection: pages with no incoming links are flagged during lint
4. Missing page detection: if a page links to `[[nonexistent]]`, lint flags it

**Implementation in practice:**
```markdown
## Lien ket
- [[andrej-karpathy]]
- [[rag-pattern]]
- [[llm-wiki-pattern]]
```

These are standard Obsidian wiki-links. The wiki-viewer.html resolves them in JavaScript by looking up the `pages` object.

**In AetherTutor context:** AetherTutor already has `NoteLink` model with bidirectional linking. The wiki-link pattern could be added as a parsing layer on top of the existing Note model.

### 2.3 Contradiction Detection

**How it works in practice:**

1. **During ingest:** When processing a new raw source, the LLM compares extracted facts against existing wiki pages. If a new fact contradicts an existing claim:
   - Both claims are kept
   - A contradiction note is added to the relevant page
   - The contradiction is logged in LOG.md

2. **During lint:** The lint workflow systematically checks for contradictions:
   - Reads all wiki pages
   - Looks for conflicting statements between pages
   - Identifies "stale claims" -- old information superseded by newer sources
   - Generates a contradiction report in `outputs/lint-YYYY-MM-DD.md`

3. **In AetherTutor:** The `CrossVerificationService` already does this! It has:
   - Contradiction detection with severity levels (high/medium/low)
   - Source attribution per claim
   - Complementary info identification
   - Consensus detection
   - The service uses LLM structured extraction to compare documents

**Key difference:** LLM Wiki does contradiction detection at the **wiki page level** (markdown files), while AetherTutor does it at the **document chunk level** (PostgreSQL records). The wiki approach is more semantic and human-readable; the AetherTutor approach is more granular and queryable.

### 2.4 Knowledge Gap Flow: lint -> gaps.json -> discover -> ingest

```
┌──────────────────────────────────────────────────────────┐
│  LINT                                                    │
│  1. Scan all wiki/ pages                                 │
│  2. Identify missing coverage areas                      │
│  3. Find mentioned-but-missing pages                     │
│  4. Write gaps to .discoveries/gaps.json                 │
│                                                          │
│  gaps.json:                                              │
│  {                                                       │
│    "missing_pages": ["quantum-computing.md"],            │
│    "undercovered_topics": ["ML ops"],                     │
│    "suggested_sources": ["arxiv papers on X"]            │
│  }                                                       │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  DISCOVER                                                │
│  1. Read gaps.json                                       │
│  2. Web search for gap topics + config topics            │
│  3. Filter against history.json (avoid duplicates)       │
│  4. Download articles → raw/articles/                    │
│  5. Update history.json                                  │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  INGEST                                                  │
│  1. Scan raw/ for new files                              │
│  2. Read each file, extract entities/concepts            │
│  3. Create/update wiki pages                             │
│  4. Update INDEX.md, LOG.md, history.json               │
└──────────────────────────────────────────────────────────┘
```

**The feedback loop:** `lint` identifies what's missing -> `discover` finds sources to fill gaps -> `ingest` processes them -> `lint` again to verify coverage. This is a self-improving system.

### 2.5 Scoring Framework (pain-rank command)

Each pain point is scored on 5 criteria with weighted multipliers:

| Criterion | Weight | Description | Scale |
|-----------|--------|-------------|-------|
| Urgency | x2 | Do users need a solution NOW? | 1-10 |
| Market Size | x2 | How many people/businesses have this problem? | 1-10 |
| Willingness to Pay | x3 | Are they paying for alternatives? | 1-10 |
| AI Solvability | x2 | Can AI/LLM solve this well? | 1-10 |
| Competition | x1 | Less competition = higher score | 1-10 |

**Maximum score:** (10*2) + (10*2) + (10*3) + (10*2) + (10*1) = **50**

**Output includes:**
- Top 10 ranked table
- Detailed writeup for Top 3 (problem, target user, proposed solution, revenue model, Reddit sources, next steps)
- Idea-to-Spec Pipeline for #1: problem statement, user persona, MVP features, tech stack, effort estimate

### 2.6 Daily Digest Aggregation

The digest command aggregates 24 hours of wiki activity:

1. **Read LOG.md** -- filter entries from last 24h by parsing `## [YYYY-MM-DD HH:mm]` timestamps
2. **Read new/updated wiki pages** -- get titles and summaries
3. **Read new syntheses** -- extract top 3 insights
4. **Read raw/reddit/ files** -- extract pain points with upvotes
5. **Read gaps.json** -- list unresolved knowledge gaps
6. **Compute statistics** -- page counts, additions today, health status

**Output structure:**
```
Daily Digest — YYYY-MM-DD
├── New Sources (N) — 1-line summaries
├── New Wiki Pages (N) — 1-line descriptions
├── Top 3 Insights — from syntheses and cross-references
├── Pain Points (from Reddit) — table with domain, upvotes, opportunity
├── Knowledge Gaps — list of unresolved gaps
└── Statistics — pages (+X today), sources (+Y today), health
```

### 2.7 Dedup System

The dedup system prevents processing the same source twice:

**Two-level check:**
1. **URL check:** Exact URL match against `history.json`
2. **Title similarity:** String similarity with threshold 0.9 (configurable)

**History structure (`.discoveries/history.json`):**
```json
{
  "processed_sources": [
    {
      "url": "https://example.com/article",
      "title": "Article Title",
      "filename": "2026-04-07-article-title.md",
      "processed_at": "2026-04-07T10:00:00",
      "topic": "AI Agents"
    }
  ]
}
```

### 2.8 Auto-Discovery Snowball Strategy

The snowball strategy works as follows:

1. **Start** with configured topics and feeds
2. **Ingest** sources from feeds -> extract references/citations from the content
3. **Follow links** -- the LLM reads URLs mentioned in existing sources
4. **Download** those linked sources -> save to raw/
5. **Repeat** -- newly ingested sources have their own references

**Example:**
- Web search finds "Karpathy's LLM Wiki blog post"
- The blog post cites 3 papers and links to 2 GitHub repos
- Snowball follows those 5 links and downloads them
- Those papers/repos have their own references
- Exponential growth, but capped by `max_sources` config

**Priority order:** gaps.json > Reddit pain points > trending topics > scheduled feeds > snowball

---

## 3. Implementation Details

### 3.1 Frontmatter Schemas

#### Entity Page (`wiki/entities/*.md`)
```yaml
---
type: entity
category: person | organization | tool | project
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: ["raw/path/1", "raw/path/2"]
---
```
**Sections:** Overview (1-2 sentences), Detailed description, Notable points (bullets), Links (wiki-links), Sources (links to raw)

#### Concept Page (`wiki/concepts/*.md`)
```yaml
---
type: concept
domain: ai | engineering | business | ...
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: ["raw/path/1", "raw/path/2"]
---
```
**Sections:** Definition, How it works, Examples, Links, Sources

#### Source Summary (`wiki/sources/*.md`)
```yaml
---
type: source
format: article | paper | note | video | podcast
raw_path: raw/articles/ten-file.md
ingested: YYYY-MM-DD
---
```
**Sections:** Summary (2-3 paragraphs), Key takeaways (bullets), Entities mentioned (wiki-links), Concepts mentioned (wiki-links), Notable quotes (blockquotes)

#### Synthesis Page (`wiki/syntheses/*.md`)
```yaml
---
type: synthesis
topic: topic name
created: YYYY-MM-DD
sources_count: N
---
```
**Sections:** Original question, Analysis, Conclusions, Sources used (wiki-links)

### 3.2 INDEX.md Format

```markdown
# Wiki Index

> Catalog of all wiki pages. Auto-updated on every ingest.
> Read this file first when answering queries to find relevant pages.

**Total pages:** 34
**Last updated:** 2026-04-06

---

## Entities
- [Andrej Karpathy](entities/andrej-karpathy.md) — AI researcher, former Tesla AI director
- [Obsidian](entities/obsidian.md) — Note-taking app with wiki-link support

## Concepts
- [LLM Wiki Pattern](concepts/llm-wiki-pattern.md) — Pattern for LLM-maintained wikis
- [RAG Pattern](concepts/rag-pattern.md) — Retrieval-Augmented Generation

## Sources
- [Claude Code Skills Guide 2026](sources/claude-code-skills-guide.md) — How to write skills

## Syntheses
- [AI Tooling Philosophies](syntheses/ai-tooling-philosophies.md) — Comparison of Karpathy, steipete, Spisak
```

### 3.3 LOG.md Format

```markdown
# Wiki Log

> Timeline of all activities: ingest, query, lint, discover.
> Format: `## [YYYY-MM-DD HH:mm] action | Description`
> Grep-friendly: `grep "^## \[" LOG.md | tail -10`

---

## [2026-04-06 10:00] ingest | Processed 2 new sources: karpathy-blog.md, spisak-thread.md
  - Created: wiki/sources/karpathy-llm-wiki.md
  - Updated: wiki/entities/andrej-karpathy.md, wiki/concepts/llm-wiki-pattern.md
  - Affected pages: 5

## [2026-04-06 10:05] lint | Health check passed
  - Contradictions: 0
  - Orphans: 1 (wiki/entities/obscure-tool.md)
  - Gaps: 2 (quantum computing, ML ops)

## [2026-04-06 10:10] discover | Found 3 new sources
  - Downloaded: raw/articles/2026-04-06-quantum-ml.md
  - Updated: .discoveries/history.json
```

### 3.4 .discoveries/ JSON Structures

#### feeds.json
```json
{
  "active_feeds": [
    {
      "type": "github_trending",
      "languages": ["python", "typescript"],
      "last_checked": "2026-04-06T10:00:00",
      "status": "active"
    },
    {
      "type": "hackernews",
      "min_score": 50,
      "last_checked": "2026-04-06T10:00:00"
    }
  ]
}
```

#### gaps.json
```json
{
  "missing_pages": [
    {
      "suggested_name": "quantum-computing",
      "reason": "Mentioned in 3 sources but no wiki page exists",
      "priority": "high",
      "mentioned_by": ["source-a.md", "source-b.md"]
    }
  ],
  "undercovered_topics": [
    {
      "topic": "ML ops",
      "reason": "Only 1 concept page, 3 sources discuss this",
      "priority": "medium"
    }
  ],
  "suggested_sources": [
    {
      "query": "arxiv papers on MLOps 2026",
      "reason": "Current sources don't cover this topic"
    }
  ],
  "generated_at": "2026-04-06T10:05:00"
}
```

#### history.json
```json
{
  "processed_sources": [
    {
      "url": "https://example.com/article",
      "title": "Article Title",
      "filename": "2026-04-07-article-title.md",
      "processed_at": "2026-04-07T10:00:00",
      "topic": "AI Agents"
    }
  ]
}
```

### 3.5 wiki-viewer.html Implementation Details

#### Graph Rendering Algorithm
The force-directed layout uses a simple but effective algorithm:

1. **Initialization:** Nodes placed on a circle with random jitter
2. **Repulsion (Coulomb's law):** All node pairs repel with force 800/d^2
3. **Attraction (Hooke's law):** Connected nodes attract with force (d - 80) * 0.01
4. **Center gravity:** All nodes pulled toward center with force 0.002
5. **Damping:** Velocity multiplied by 0.85 each iteration
6. **Boundary clamping:** Nodes kept within canvas bounds (30px margin)
7. **200 iterations total** -- enough for convergence without excessive computation

#### Search Algorithm
Client-side string matching:
```javascript
const q = filter.toLowerCase();
items.filter(id =>
  pages[id].title.toLowerCase().includes(q) ||
  id.includes(q)
);
```
No fuzzy matching, no full-text search -- just substring match on title and filename.

### 3.6 Scheduler Scripts

#### run-wiki.sh Flow
```
System Scheduler (cron/Task Scheduler)
  -> run-wiki.sh
    -> cd WIKI_ROOT
    -> claude --print --dangerously-skip-permissions "/llm-wiki run"
      -> Reads CLAUDE.md + config.yaml
      -> Runs: discover -> ingest -> lint
    -> Appends output to outputs/auto-run.log
```

#### setup-scheduler.ps1 Flow
```
PowerShell (Admin)
  -> Create Scheduled Task "LLM-Wiki-AutoRun"
    -> Trigger: every 2 hours, 365 days
    -> Action: Git Bash -> run-wiki.sh
    -> Settings: allow battery, require network
  -> Task runs automatically without user intervention
```

---

## 4. Comparison with AetherTutor

### 4.1 Feature Matrix

| Feature | LLM Wiki | AetherTutor | Notes |
|---------|----------|-------------|-------|
| **Document Processing** | Manual drop into raw/ | PDF upload + extraction | AetherTutor is more automated |
| **Knowledge Graph** | Markdown wiki-links | NetworkX + PostgreSQL | AetherTutor has structured graph |
| **Cross-References** | [[wiki-links]] in markdown | NoteLink model | Both support bidirectional |
| **Contradiction Detection** | LLM reads wiki pages | CrossVerificationService | AetherTutor has severity levels |
| **Auto-Discovery** | Web search, RSS, GitHub, Reddit | None | LLM Wiki exclusive |
| **Socratic Chat** | Query command (text-based) | Full chat with context | AetherTutor is richer |
| **Flashcards** | None | SM-2 algorithm | AetherTutor exclusive |
| **Quiz Generation** | None | LLM-generated quizzes | AetherTutor exclusive |
| **Pain Point Analysis** | pain-rank command | Quiz analysis service | Different purposes |
| **Daily Digest** | digest command | None | LLM Wiki exclusive |
| **Health Checks** | lint command | None (no wiki health) | LLM Wiki exclusive |
| **Multi-User** | Git-based sharing | Full user auth | AetherTutor is multi-user |
| **Vector Search** | None (grep only) | ChromaDB embeddings | AetherTutor is more powerful |
| **Background Jobs** | Claude Code /loop | ARQ + Redis | AetherTutor is production-ready |
| **Obsidian Integration** | Native (vault = wiki folder) | Vault importer | Both support |
| **Web UI** | wiki-viewer.html (static) | React/Vite frontend | AetherTutor is interactive |

### 4.2 Exact Integration Points

#### 4.2.1 Auto-Discovery -> Document Ingestion Pipeline

**LLM Wiki concept:** Auto-discover articles from web, RSS, GitHub trending, Reddit
**AetherTutor integration:** Add a new ARQ worker job `discover_sources` that runs on a schedule

**Mapping to AetherTutor models:**
```python
# New model or extension
class DiscoverySource(Base, TimestampMixin):
    __tablename__ = "discovery_sources"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    url: Mapped[str] = mapped_column(String(2048), unique=True)
    title: Mapped[str] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(50))  # web_search, rss, github, reddit
    topic: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, downloaded, processed, skipped
    content_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default={})
```

**New API endpoints:**
```
POST   /api/v1/discovery/topics          # Add a topic to follow
GET    /api/v1/discovery/topics          # List followed topics
POST   /api/v1/discovery/feeds           # Add a feed (RSS, GitHub, Reddit)
GET    /api/v1/discovery/feeds           # List feeds
POST   /api/v1/discovery/run             # Trigger discovery run
GET    /api/v1/discovery/sources         # List discovered sources
GET    /api/v1/discovery/sources/{id}    # Get source details
DELETE /api/v1/discovery/sources/{id}    # Remove source
GET    /api/v1/discovery/stats           # Discovery statistics
```

**ARQ worker jobs:**
```python
@worker.job
async def discover_web_search(ctx, user_id: str, topic_id: str):
    """Web search for a topic and download articles."""

@worker.job
async def discover_github_trending(ctx, user_id: str):
    """Check GitHub trending repos."""

@worker.job
async def discover_rss_feeds(ctx, user_id: str):
    """Poll RSS feeds for new articles."""

@worker.job
async def discover_snowball(ctx, user_id: str):
    """Follow references from existing documents."""

@worker.job
async def discover_full_cycle(ctx, user_id: str):
    """Full cycle: discover -> download -> trigger ingest."""
```

#### 4.2.2 Wiki Pages -> Knowledge Base Layer

**LLM Wiki concept:** Entity, Concept, Source, Synthesis pages as markdown files
**AetherTutor integration:** Add a `WikiPage` model that maps to the 4 page types

**Proposed SQLAlchemy models:**
```python
class WikiPageType(str, enum.Enum):
    ENTITY = "entity"
    CONCEPT = "concept"
    SOURCE = "source"
    SYNTHESIS = "synthesis"

class WikiPage(Base, TimestampMixin):
    __tablename__ = "wiki_pages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    page_type: Mapped[WikiPageType] = mapped_column(Enum(WikiPageType))
    slug: Mapped[str] = mapped_column(String(255), index=True)  # kebab-case filename
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)  # Markdown content
    category: Mapped[str] = mapped_column(String(100), nullable=True)  # person, org, tool / ai, engineering / article, paper
    source_document_ids: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), default=[])
    frontmatter: Mapped[dict] = mapped_column(JSON, default={})

    __table_args__ = (
        UniqueConstraint("user_id", "slug", name="uq_wiki_pages_user_slug"),
        Index("idx_wiki_pages_user_type", "user_id", "page_type"),
    )

    # Relationships
    user = relationship("User", back_populates="wiki_pages")
    outgoing_links = relationship(
        "WikiLink",
        foreign_keys="WikiLink.source_page_id",
        back_populates="source_page",
        cascade="all, delete-orphan"
    )

class WikiLink(Base, TimestampMixin):
    __tablename__ = "wiki_links"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    source_page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wiki_pages.id"))
    target_page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wiki_pages.id"))

    __table_args__ = (
        Index("uq_wiki_links_source_target", "source_page_id", "target_page_id", unique=True),
    )

    source_page = relationship("WikiPage", foreign_keys=[source_page_id], back_populates="outgoing_links")
    target_page = relationship("WikiPage", foreign_keys=[target_page_id], backref="incoming_links")
```

**New API endpoints:**
```
GET    /api/v1/wiki/pages                # List all wiki pages (filterable by type)
GET    /api/v1/wiki/pages/{slug}         # Get page by slug
POST   /api/v1/wiki/pages                # Create page (LLM-generated)
PUT    /api/v1/wiki/pages/{id}           # Update page
DELETE /api/v1/wiki/wiki/pages/{id}      # Delete page
GET    /api/v1/wiki/pages/{id}/links     # Get outgoing + incoming links
GET    /api/v1/wiki/index                # Get INDEX.md equivalent
GET    /api/v1/wiki/log                  # Get LOG.md equivalent (activity log)
GET    /api/v1/wiki/graph                # Get graph data (nodes + edges)
```

#### 4.2.3 Lint Service -> Wiki Health Monitoring

**LLM Wiki concept:** lint command checks contradictions, orphans, gaps, broken links
**AetherTutor integration:** Extend existing CrossVerificationService + add new health check service

**Proposed service:**
```python
class WikiHealthService:
    """
    Comprehensive wiki health monitoring.
    Maps LLM Wiki lint workflow to AetherTutor.
    """

    async def run_lint(self, user_id: uuid.UUID) -> LintReport:
        """Run full wiki health check."""
        return LintReport(
            total_pages=await self._count_pages(user_id),
            contradictions=await self._detect_contradictions(user_id),
            orphans=await self._find_orphans(user_id),
            missing_pages=await self._find_missing_pages(user_id),
            broken_links=await self._find_broken_links(user_id),
            gaps=await self._find_knowledge_gaps(user_id),
            quality_issues=await self._assess_quality(user_id),
        )

    async def detect_contradictions(self, user_id: uuid.UUID):
        """Use existing CrossVerificationService on wiki pages."""
        # Reuse cross_verification_service.cross_check()
        # Compare wiki page contents pairwise
        pass

    async def find_orphans(self, user_id: uuid.UUID):
        """Find wiki pages with no incoming links."""
        # Query WikiLink table for pages with no incoming_links
        pass

    async def find_knowledge_gaps(self, user_id: uuid.UUID):
        """Find topics mentioned but not covered."""
        # Use LLM to scan wiki pages and find undercovered areas
        # Cross-reference with discovery topics config
        pass
```

**New API endpoint:**
```
POST   /api/v1/wiki/lint                 # Trigger lint check
GET    /api/v1/wiki/lint/report          # Get latest lint report
GET    /api/v1/wiki/gaps                 # Get knowledge gaps (from .discoveries/gaps.json equivalent)
```

#### 4.2.4 Daily Digest -> User Notifications

**LLM Wiki concept:** digest command creates daily brief
**AetherTutor integration:** Use existing NotificationService + scheduled ARQ job

**ARQ worker job:**
```python
@worker.job
async def generate_daily_digest(ctx, user_id: str):
    """
    Generate daily digest for a user.
    Aggregates: new documents, new wiki pages, new insights, study stats.
    """
    # Query documents processed today
    # Query wiki pages created today
    # Query flashcards reviewed today
    # Query quiz results today
    # Query new contradictions detected
    # Generate summary via LLM
    # Store as notification or email
    pass
```

**New API endpoint:**
```
GET    /api/v1/digest/latest             # Get latest daily digest
GET    /api/v1/digest/{date}             # Get digest for specific date
```

#### 4.2.5 Pain Point Ranking -> Learning Analytics

**LLM Wiki concept:** pain-rank scores business opportunities from Reddit
**AetherTutor integration:** Repurpose for "Learning Gap Analysis" -- identify topics the user struggles with

**Concept mapping:**
| LLM Wiki pain-rank | AetherTutor equivalent |
|-------------------|----------------------|
| Pain point from Reddit | Learning gap from quiz results |
| Urgency | How soon is this needed for curriculum? |
| Market Size | How many students struggle with this? |
| Willingness to Pay | How much does this affect grades? |
| AI Solvability | Can AI tutoring solve this? |
| Competition | How many resources exist for this topic? |

**Proposed service:**
```python
class LearningGapAnalysisService:
    """
    Identify learning gaps from quiz results and flashcard performance.
    Adapt the pain-rank scoring framework for education.
    """

    async def analyze_gaps(self, user_id: uuid.UUID) -> GapAnalysisReport:
        """
        Analyze quiz failures and flashcard struggles to identify learning gaps.
        Score each gap and recommend targeted study material.
        """
        pass
```

#### 4.2.6 Graph Viewer -> Enhanced Wiki Graph

**LLM Wiki concept:** wiki-viewer.html with force-directed graph
**AetherTutor integration:** Enhance the existing frontend React graph component with wiki-viewer features

**Features to port:**
1. Color-coded nodes by type (Entity, Concept, Source, Synthesis)
2. Click-to-navigate on graph nodes
3. Incoming/outgoing link display
4. Search with category filtering
5. Dashboard statistics cards

### 4.3 Concept Mapping: LLM Wiki -> AetherTutor Models

| LLM Wiki Concept | AetherTutor Equivalent | Mapping |
|-----------------|----------------------|---------|
| `raw/` folder | `Document` model + `uploads/` | `Document.file_path` points to uploaded file |
| `wiki/entities/` | `GraphEntity` model | `GraphEntity.canonical_name` + `entity_type` |
| `wiki/concepts/` | New `WikiPage` model | page_type=concept |
| `wiki/sources/` | `Document` summary | Could be stored as Document metadata or WikiPage |
| `wiki/syntheses/` | New `WikiPage` model | page_type=synthesis |
| `INDEX.md` | `WikiPage` index endpoint | API endpoint returning paginated list |
| `LOG.md` | Existing `created_at` timestamps + new activity log | Query all models by timestamp |
| `[[wiki-links]]` | `WikiLink` model | Source->target page relationships |
| `.discoveries/gaps.json` | New `KnowledgeGap` model | Stored in PostgreSQL |
| `.discoveries/history.json` | `DiscoverySource` model | Processed source tracking |
| `.discoveries/feeds.json` | `DiscoveryFeed` model | Feed configuration |
| `config.yaml` topics | New `LearningTopic` model | User-configured topics |
| `config.yaml` feeds | New `DiscoveryFeed` model | RSS, GitHub, Reddit feeds |
| `outputs/` | New `Output` model or files | Query results, reports |

---

## 5. Missing Pieces Analysis

### 5.1 What LLM Wiki Lacks (AetherTutor Already Has)

| LLM Wiki Missing | AetherTutor Has | Value |
|-----------------|----------------|-------|
| User authentication | Full multi-user auth with roles | Essential for SaaS |
| Vector search | ChromaDB with embeddings | Far superior to grep |
| Structured knowledge graph | NetworkX + PostgreSQL + GraphEntity/GraphRelation | More queryable than markdown |
| Flashcards with SM-2 | Full spaced repetition system | Critical for learning |
| Quiz generation | LLM-generated quizzes with analysis | Critical for learning |
| Socratic chat | Full conversational AI with context | Core learning feature |
| Background job queue | ARQ + Redis | Production-grade async processing |
| Database migrations | Alembic | Schema evolution |
| API framework | FastAPI with OpenAPI docs | Programmatic access |
| Rate limiting | Built-in rate limiter | Production readiness |
| CORS configuration | Production-ready CORS | Security |
| Testing suite | 18+ unit, 20+ integration tests | Reliability |

### 5.2 What AetherTutor Lacks (LLM Wiki Does Well)

| AetherTutor Missing | LLM Wiki Has | Value |
|---------------------|-------------|-------|
| Auto-discovery of learning material | Web search, RSS, GitHub, Reddit feeds | **HUGE** -- automated content sourcing |
| Self-improving knowledge base | lint -> gaps -> discover -> ingest loop | Wiki grows autonomously |
| Contradiction flagging in wiki | Contradictions marked in wiki pages | Currently only during chat, not persistent |
| Knowledge gap detection | Systematic gap analysis via lint | Currently no proactive gap detection |
| Daily digest | Automated daily summary | Currently no automated summaries |
| Schema co-evolution | CLAUDE.md evolves with LLM usage | Schema is static in AetherTutor |
| Multi-agent compatibility | Works with Claude, Codex, Copilot, Cursor | AetherTutor is model-agnostic but not agent-optimized |
| Pain point analysis | Business opportunity scoring | Could be repurposed for learning analytics |
| Snowball discovery | Follow references from existing sources | Currently no reference-following |
| Immutable source tracking | raw/ never modified | AetherTutor uploads are immutable but not explicitly enforced |

### 5.3 Complementary Areas

| Area | LLM Wiki Approach | AetherTutor Approach | Combined Value |
|------|-------------------|---------------------|----------------|
| **Knowledge Graph** | Markdown wiki-links | NetworkX + PostgreSQL | Wiki-links as UI layer on top of NetworkX data |
| **Content Sourcing** | Auto-discover from web | Upload documents manually | Combine: manual upload + auto-discovery |
| **Learning** | Read wiki and ask questions | Flashcards, quizzes, Socratic chat | Wiki as knowledge base, AetherTutor as learning tools |
| **Health Checks** | Lint for contradictions/gaps | No wiki health | Add lint to cross-verification pipeline |
| **UI** | Static HTML viewer | React/Vite SPA | Port wiki-viewer features into React components |

### 5.4 Potential Conflicts

| Conflict Area | Issue | Resolution |
|--------------|-------|-----------|
| **Storage model** | LLM Wiki uses filesystem; AetherTutor uses PostgreSQL | Store wiki content in PostgreSQL `wiki_pages` table, expose as markdown API |
| **LLM interaction** | LLM Wiki expects LLM to run as agent with file access | AetherTutor uses LLM service API calls | Adapt LLM prompts to use DB operations instead of file I/O |
| **Scheduling** | LLM Wiki uses `/loop` or cron; AetherTutor uses ARQ | Use ARQ for all scheduling -- more robust than cron |
| **Single-user vs multi-user** | LLM Wiki is single-user | AetherTutor is multi-user | All wiki features must be user-scoped with `user_id` |
| **Git versioning** | LLM Wiki uses git for wiki versioning | AetherTutor uses DB transactions + timestamps | Add audit trail table for wiki page versions |

---

## 6. Detailed Implementation Blueprints

### 6.1 Feature: Auto-Discovery System

#### 6.1.1 New SQLAlchemy Models

```python
# app/models/discovery.py

import uuid
import enum
from sqlalchemy import String, Text, Integer, Float, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class DiscoverySourceStatus(str, enum.Enum):
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    SKIPPED = "skipped"
    FAILED = "failed"


class DiscoverySourceType(str, enum.Enum):
    WEB_SEARCH = "web_search"
    RSS_FEED = "rss_feed"
    GITHUB_TRENDING = "github_trending"
    GITHUB_RELEASE = "github_release"
    REDDIT = "reddit"
    HACKER_NEWS = "hacker_news"
    SNOWBALL = "snowball"  # Follow references from existing sources


class DiscoverySource(Base, TimestampMixin):
    """A discovered external source awaiting or undergoing processing."""
    __tablename__ = "discovery_sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[DiscoverySourceType] = mapped_column(
        SAEnum(DiscoverySourceType), nullable=False
    )
    topic: Mapped[str] = mapped_column(String(200), nullable=True)
    status: Mapped[DiscoverySourceStatus] = mapped_column(
        SAEnum(DiscoverySourceStatus), default=DiscoverySourceStatus.PENDING
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    raw_content: Mapped[str] = mapped_column(Text, nullable=True)  # Downloaded content
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default={})
    # Additional metadata: author, published_date, upvotes, stars, etc.

    # After processing
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("idx_discovery_sources_user", "user_id"),
        Index("idx_discovery_sources_status", "user_id", "status"),
        Index("idx_discovery_sources_type", "user_id", "source_type"),
        Index("idx_discovery_sources_topic", "user_id", "topic"),
    )

    user = relationship("User", back_populates="discovery_sources")
    document = relationship("Document", backref="discovery_source")


class DiscoveryFeed(Base, TimestampMixin):
    """A configured feed for auto-discovery (RSS, GitHub, Reddit, etc.)."""
    __tablename__ = "discovery_feeds"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    feed_type: Mapped[str] = mapped_column(String(50), nullable=False)  # rss, github_trending, reddit, hacker_news
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=True)  # For RSS
    is_active: Mapped[bool] = mapped_column(default=True)
    config: Mapped[dict] = mapped_column(JSON, default={})
    # Config examples:
    # RSS: {"url": "..."}
    # GitHub: {"languages": ["python"], "min_stars": 100, "topics": ["ai", "llm"]}
    # Reddit: {"subreddits": ["r/MachineLearning"], "min_upvotes": 20}
    last_checked_at: Mapped[datetime] = mapped_column(nullable=True)
    last_error: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_discovery_feeds_user", "user_id"),
        Index("idx_discovery_feeds_active", "user_id", "is_active"),
    )

    user = relationship("User", back_populates="discovery_feeds")


class LearningTopic(Base, TimestampMixin):
    """A topic the user wants to learn about -- drives discovery."""
    __tablename__ = "learning_topics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    keywords: Mapped[list] = mapped_column(ARRAY(String(200)), default=[])
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # high, medium, low
    is_active: Mapped[bool] = mapped_column(default=True)

    __table_args__ = (
        Index("idx_learning_topics_user", "user_id"),
        Index("idx_learning_topics_priority", "user_id", "priority"),
    )

    user = relationship("User", back_populates="learning_topics")


class KnowledgeGap(Base, TimestampMixin):
    """A gap in the user's knowledge -- identified by lint."""
    __tablename__ = "knowledge_gaps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    gap_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # missing_page, undercovered_topic, suggested_source
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open, in_progress, resolved
    resolved_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    # FK to discovery_source if resolved by a discovered source

    __table_args__ = (
        Index("idx_knowledge_gaps_user", "user_id"),
        Index("idx_knowledge_gaps_status", "user_id", "status"),
    )

    user = relationship("User", back_populates="knowledge_gaps")
```

#### 6.1.2 New API Endpoints

```python
# app/api/discovery.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from uuid import UUID

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])

# --- Topics ---
@router.post("/topics")
async def add_topic(...):
    """Add a learning topic for auto-discovery."""

@router.get("/topics")
async def list_topics(
    user=Depends(get_current_user),
    priority: Optional[str] = None,
    active_only: bool = True
):
    """List all learning topics."""

@router.delete("/topics/{topic_id}")
async def remove_topic(topic_id: UUID, ...):
    """Remove a learning topic."""

# --- Feeds ---
@router.post("/feeds")
async def add_feed(...):
    """Add a discovery feed (RSS, GitHub, Reddit, etc.)."""

@router.get("/feeds")
async def list_feeds(user=Depends(get_current_user)):
    """List all discovery feeds."""

@router.post("/feeds/{feed_id}/test")
async def test_feed(feed_id: UUID, ...):
    """Test a feed and show preview of sources."""

@router.delete("/feeds/{feed_id}")
async def remove_feed(feed_id: UUID, ...):
    """Remove a discovery feed."""

# --- Sources ---
@router.get("/sources")
async def list_sources(
    user=Depends(get_current_user),
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List discovered sources with filtering."""

@router.get("/sources/{source_id}")
async def get_source(source_id: UUID, ...):
    """Get source details including raw content."""

@router.post("/sources/{source_id}/ingest")
async def ingest_source(source_id: UUID, ...):
    """Trigger ingestion of a specific source into the knowledge graph."""

@router.post("/sources/{source_id}/skip")
async def skip_source(source_id: UUID, ...):
    """Mark a source as skipped (won't be re-discovered)."""

# --- Actions ---
@router.post("/run")
async def run_discovery(user=Depends(get_current_user)):
    """Trigger a full discovery cycle: discover -> download -> queue ingest."""

@router.post("/run/strategy")
async def run_strategy(
    strategy: str,  # web_search, github_trending, rss, reddit, snowball
    user=Depends(get_current_user)
):
    """Run a specific discovery strategy."""

# --- Gaps ---
@router.get("/gaps")
async def list_gaps(
    user=Depends(get_current_user),
    status: Optional[str] = None
):
    """List knowledge gaps."""

@router.post("/gaps/resolve")
async def resolve_gap(gap_id: UUID, ...):
    """Mark a gap as resolved."""

# --- Stats ---
@router.get("/stats")
async def discovery_stats(user=Depends(get_current_user)):
    """Get discovery statistics."""
```

#### 6.1.3 ARQ Worker Jobs

```python
# app/worker/discovery_worker.py

from arq import cron
from app.services.discovery_service import discovery_service
from app.services.web_scraper import web_scraper
from app.services.rss_parser import rss_parser
from app.services.github_api import github_api

@worker.job
async def discover_web_search(ctx, user_id: str, topic: str, keywords: list):
    """Web search for articles matching topic + keywords."""
    results = await web_scraper.search(topic, keywords, max_results=5)
    for result in results:
        await discovery_service.add_source(
            user_id=user_id,
            url=result.url,
            title=result.title,
            source_type="web_search",
            topic=topic,
        )

@worker.job
async def discover_github_trending(ctx, user_id: str):
    """Check GitHub trending repos for user's topics."""
    feeds = await discovery_service.get_active_feeds(user_id, feed_type="github_trending")
    for feed in feeds:
        repos = await github_api.get_trending(feed.config)
        for repo in repos:
            await discovery_service.add_source(
                user_id=user_id,
                url=repo.url,
                title=repo.full_name,
                source_type="github_trending",
                topic=feed.name,
                metadata={"stars": repo.stars, "language": repo.language},
            )

@worker.job
async def discover_rss_feeds(ctx, user_id: str):
    """Poll all active RSS feeds."""
    feeds = await discovery_service.get_active_feeds(user_id, feed_type="rss")
    for feed in feeds:
        entries = await rss_parser.parse(feed.url)
        for entry in entries:
            if not await discovery_service.is_duplicate(user_id, entry.url):
                await discovery_service.add_source(
                    user_id=user_id,
                    url=entry.url,
                    title=entry.title,
                    source_type="rss_feed",
                    topic=feed.name,
                )

@worker.job
async def discover_snowball(ctx, user_id: str):
    """Follow references from existing wiki pages and documents."""
    # Get all wiki pages
    pages = await wiki_service.get_all_pages(user_id)
    # Extract URLs from page content
    # Check if URLs are already in discovery_sources
    # Add new ones
    pass

@worker.job
async def download_source_content(ctx, source_id: str):
    """Download and store content for a discovered source."""
    source = await discovery_service.get_source(source_id)
    content = await web_scraper.fetch_and_extract(source.url)
    await discovery_service.update_source(source_id, raw_content=content)

@worker.job
async def discover_full_cycle(ctx, user_id: str):
    """Full discovery cycle: run all strategies, download content, queue ingest."""
    # Phase 1: Discover
    await discover_web_search(ctx, user_id, ...)
    await discover_github_trending(ctx, user_id)
    await discover_rss_feeds(ctx, user_id)
    await discover_snowball(ctx, user_id)

    # Phase 2: Download content for pending sources
    pending = await discovery_service.get_pending_sources(user_id, limit=10)
    for source in pending:
        await download_source_content.queue(source.id)

    # Phase 3: Trigger ingest for downloaded sources
    downloaded = await discovery_service.get_downloaded_sources(user_id, limit=5)
    for source in downloaded:
        from app.worker.tasks import process_document
        await process_document.queue(...)

@worker.job
async def generate_daily_digest(ctx, user_id: str):
    """Generate daily digest for user."""
    # Aggregate today's activity
    # New documents, wiki pages, flashcards, quiz results
    # Contradictions detected, gaps found
    # Generate LLM summary
    # Store as notification
    pass
```

#### 6.1.4 Service Classes

```python
# app/services/discovery_service.py

class DiscoveryService:
    """
    Central service for auto-discovery of learning materials.
    Implements the LLM Wiki discover workflow.
    """

    async def add_source(self, user_id, url, title, source_type, topic, metadata=None):
        """Add a discovered source with dedup check."""
        # Check URL dedup
        if await self.is_duplicate(user_id, url):
            return None
        # Check title similarity
        if await self.is_title_duplicate(user_id, title, threshold=0.9):
            return None
        # Create source record
        return await self.source_repo.create(...)

    async def is_duplicate(self, user_id, url):
        """Check if URL already exists in processed or pending sources."""
        existing = await self.source_repo.get_by_url(user_id, url)
        return existing is not None

    async def is_title_duplicate(self, user_id, title, threshold=0.9):
        """Check title similarity against existing sources."""
        existing = await self.source_repo.get_recent_titles(user_id, limit=100)
        for existing_title in existing:
            if self._similarity(title, existing_title) >= threshold:
                return True
        return False

    def _similarity(self, a, b):
        """Simple string similarity (e.g., Levenshtein or Jaccard)."""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
```

#### 6.1.5 Database Migration Strategy

```bash
# 1. Create new models in app/models/discovery.py
# 2. Update app/models/user.py to add relationships:
#    discovery_sources = relationship("DiscoverySource", ...)
#    discovery_feeds = relationship("DiscoveryFeed", ...)
#    learning_topics = relationship("LearningTopic", ...)
#    knowledge_gaps = relationship("KnowledgeGap", ...)

# 3. Generate migration
alembic revision --autogenerate -m "add discovery system tables"

# 4. Review migration before applying
alembic upgrade head

# 5. Add indexes after initial migration if needed
```

### 6.2 Feature: Wiki Pages System

#### 6.2.1 Models (already described in 4.2.2)

See the `WikiPage` and `WikiLink` model definitions in section 4.2.2 above.

#### 6.2.2 API Router

```python
# app/api/wiki.py

from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from uuid import UUID

router = APIRouter(prefix="/api/v1/wiki", tags=["wiki"])

@router.get("/pages")
async def list_pages(
    page_type: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user=Depends(get_current_user)
):
    """List wiki pages with optional filtering."""

@router.get("/pages/{page_id}")
async def get_page(page_id: UUID, user=Depends(get_current_user)):
    """Get a wiki page with full content and links."""

@router.get("/pages/slug/{slug}")
async def get_page_by_slug(slug: str, user=Depends(get_current_user)):
    """Get a wiki page by its kebab-case slug."""

@router.get("/index")
async def get_index(user=Depends(get_current_user)):
    """Get INDEX.md equivalent -- all pages grouped by category."""

@router.get("/log")
async def get_log(
    limit: int = 100,
    action: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Get LOG.md equivalent -- activity timeline."""

@router.get("/pages/{page_id}/links")
async def get_page_links(page_id: UUID, user=Depends(get_current_user)):
    """Get outgoing and incoming links for a page."""

@router.get("/graph")
async def get_graph_data(user=Depends(get_current_user)):
    """Get graph data for visualization (nodes + edges)."""
    # Returns: {"nodes": [{id, title, type, link_count}], "edges": [[source, target]]}

@router.post("/lint")
async def run_lint(user=Depends(get_current_user)):
    """Trigger wiki health check (lint)."""

@router.get("/lint/report")
async def get_lint_report(user=Depends(get_current_user)):
    """Get the latest lint report."""

@router.get("/gaps")
async def get_gaps(user=Depends(get_current_user)):
    """Get knowledge gaps."""
```

#### 6.2.3 Service Class

```python
# app/services/wiki_service.py

class WikiService:
    """
    Service for managing wiki pages.
    Implements the LLM Wiki ingest, query, and maintenance patterns.
    """

    async def create_page_from_document(
        self, user_id, document_id, page_type, title, content, links=None
    ):
        """Create a wiki page from a processed document."""
        slug = self._to_slug(title)
        page = await self.page_repo.create(
            user_id=user_id,
            page_type=page_type,
            slug=slug,
            title=title,
            content=content,
            source_document_ids=[document_id],
        )
        # Create wiki links
        if links:
            for link_title in links:
                target = await self.page_repo.get_by_slug(user_id, self._to_slug(link_title))
                if target:
                    await self.link_repo.create(
                        user_id=user_id,
                        source_page_id=page.id,
                        target_page_id=target.id,
                    )
        # Log activity
        await self._log_activity(user_id, "create", page_id=page.id)
        return page

    async def detect_wiki_links(self, content):
        """Extract [[wiki-link]] patterns from markdown content."""
        import re
        return re.findall(r'\[\[([^\]]+)\]\]', content)

    async def find_orphans(self, user_id):
        """Find wiki pages with no incoming links."""
        all_pages = await self.page_repo.get_all(user_id)
        linked_pages = await self.link_repo.get_all_target_ids(user_id)
        return [p for p in all_pages if p.id not in linked_pages]

    async def find_broken_links(self, user_id):
        """Find wiki links that point to non-existent pages."""
        pages = await self.page_repo.get_all(user_id)
        page_slugs = {p.slug for p in pages}
        broken = []
        for page in pages:
            links = self._extract_links_from_content(page.content)
            for link in links:
                if link not in page_slugs:
                    broken.append({"page": page.slug, "missing_link": link})
        return broken

    def _to_slug(self, title):
        """Convert title to kebab-case slug."""
        import re
        slug = title.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        return slug

    def _extract_links_from_content(self, content):
        """Extract [[wiki-link]] targets from markdown."""
        import re
        return re.findall(r'\[\[([^\]]+)\]\]', content)
```

#### 6.2.4 ARQ Worker Job

```python
# In app/worker/tasks.py

@worker.job
async def generate_wiki_pages(ctx, document_id: str):
    """
    Generate wiki pages from a processed document.
    Called after document processing completes.
    """
    # Read document content
    # Use LLM to extract:
    #   - Entities -> wiki/entities/
    #   - Concepts -> wiki/concepts/
    #   - Source summary -> wiki/sources/
    #   - Cross-references -> wiki_links
    # Save all to database
    # Update index
    # Log activity
    pass
```

### 6.3 Feature: Frontend Wiki Components

#### 6.3.1 React Components to Build

```
frontend/src/components/wiki/
├── WikiDashboard.jsx        # Stats cards (entities, concepts, sources, syntheses)
├── WikiPageList.jsx         # Searchable, filterable page list
├── WikiPageDetail.jsx       # Full page view with links
├── WikiGraph.jsx            # Force-directed graph (port wiki-viewer logic)
├── WikiIndex.jsx            # INDEX.md equivalent
├── WikiLog.jsx              # LOG.md equivalent (activity timeline)
├── WikiLintReport.jsx       # Lint report display
├── WikiGaps.jsx             # Knowledge gaps display
├── DiscoveryPanel.jsx       # Discovery sources, feeds, topics management
└── DigestCard.jsx           # Daily digest display
```

#### 6.3.2 WikiGraph Component (porting wiki-viewer graph logic)

```jsx
// frontend/src/components/wiki/WikiGraph.jsx
// Port the force-directed graph from wiki-viewer.html to React + Canvas
// Use the same algorithm:
// 1. Initialize nodes on circle
// 2. Run 200 iterations of force simulation
// 3. Draw edges and nodes
// 4. Handle click events

const CATEGORY_COLORS = {
  entity: '#3fb950',
  concept: '#d2a8ff',
  source: '#f0883e',
  synthesis: '#f778ba',
};

function WikiGraph({ nodes, edges, onNodeClick }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    // Force-directed layout (same algorithm as wiki-viewer.html)
    // ... port the JavaScript force simulation
  }, [nodes, edges]);

  return <canvas ref={canvasRef} onClick={handleClick} />;
}
```

#### 6.3.3 Wiki Routes

```jsx
// frontend/src/routes/wiki/
<Route path="/wiki" element={<WikiLayout />}>
  <Route index element={<WikiDashboard />} />
  <Route path="pages" element={<WikiPageList />} />
  <Route path="pages/:slug" element={<WikiPageDetail />} />
  <Route path="graph" element={<WikiGraph />} />
  <Route path="index" element={<WikiIndex />} />
  <Route path="log" element={<WikiLog />} />
  <Route path="lint" element={<WikiLintReport />} />
  <Route path="gaps" element={<WikiGaps />} />
  <Route path="discovery" element={<DiscoveryPanel />} />
  <Route path="digest" element={<DigestCard />} />
</Route>
```

### 6.4 Feature: Contradiction Detection Enhancement

#### 6.4.1 Current State
AetherTutor already has `CrossVerificationService` that:
- Detects contradictions between documents
- Assigns severity (high/medium/low)
- Identifies complementary info
- Finds consensus points
- Generates consolidated answers

#### 6.4.2 Enhancement: Persistent Contradiction Tracking

```python
# app/models/contradiction.py

class Contradiction(Base, TimestampMixin):
    """A detected contradiction between wiki pages or documents."""
    __tablename__ = "contradictions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(20))  # high, medium, low
    description: Mapped[str] = mapped_column(Text)
    source_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))  # document or wiki page
    source_a_snippet: Mapped[str] = mapped_column(Text)
    source_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    source_b_snippet: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open, resolved, dismissed
    resolved_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("idx_contradictions_user", "user_id"),
        Index("idx_contradictions_severity", "user_id", "severity"),
        Index("idx_contradictions_status", "user_id", "status"),
    )
```

#### 6.4.3 Enhanced CrossVerificationService

```python
# Extend existing service to persist contradictions
class CrossVerificationService:
    # ... existing methods ...

    async def cross_check_and_persist(
        self,
        user_id: uuid.UUID,
        document_contexts: list,
    ):
        """Run cross-check and persist contradictions to database."""
        result = await self.cross_check(
            query="",  # Not needed for wiki-wide check
            document_contexts=document_contexts,
        )
        # Persist contradictions
        for contradiction in result.get("contradictions", []):
            await self.contradiction_repo.create(
                user_id=user_id,
                severity=contradiction["severity"],
                description=contradiction["statement"],
                source_a_id=document_contexts[0]["document_id"],
                source_a_snippet=contradiction["snippet_doc1"],
                source_b_id=document_contexts[1]["document_id"],
                source_b_snippet=contradiction["snippet_doc2"],
            )
        return result
```

### 6.5 Feature: Daily Digest

#### 6.5.1 ARQ Worker

```python
@worker.job
async def generate_daily_digest(ctx, user_id: str):
    """
    Generate daily digest for user.
    Runs every day at 8 AM via cron scheduling.
    """
    user = await user_repo.get(uuid.UUID(user_id))
    today = datetime.utcnow().date()

    # Gather today's activity
    new_docs = await doc_repo.get_by_user_and_date(user.id, today)
    new_pages = await wiki_repo.get_by_user_and_date(user.id, today)
    new_gaps = await gap_repo.get_by_user_and_date(user.id, today)
    new_contradictions = await contradiction_repo.get_by_user_and_date(user.id, today)

    # Study activity
    flashcards_reviewed = await sm2_repo.count_reviews_today(user.id)
    quizzes_taken = await quiz_repo.count_today(user.id)
    conversations = await conv_repo.count_today(user.id)

    # Generate LLM summary
    prompt = f"""
Generate a daily learning digest for {today}:
- {len(new_docs)} new documents processed
- {len(new_pages)} new wiki pages created
- {len(new_gaps)} knowledge gaps identified
- {len(new_contradictions)} contradictions detected
- {flashcards_reviewed} flashcards reviewed
- {quizzes_taken} quizzes taken

Write a concise, insightful summary (3-5 paragraphs) highlighting:
1. Key learning progress today
2. Most important new concepts learned
3. Areas needing attention (gaps, contradictions)
4. Suggested focus for tomorrow
"""
    summary = await llm_service.get_chat_completion(...)

    # Store as notification
    await notification_service.create(
        user_id=user.id,
        type="daily_digest",
        title=f"Daily Digest -- {today}",
        content=summary,
        metadata={...}
    )
```

#### 6.5.2 Cron Scheduling

```python
# app/worker/scheduler.py

from arq import cron

CRON_JOBS = [
    cron(
        discover_full_cycle,
        hour={0, 6, 12, 18},  # Every 6 hours
        minute=0,
    ),
    cron(
        generate_daily_digest,
        hour=8,  # Every day at 8 AM
        minute=0,
    ),
    cron(
        run_wiki_lint,
        hour=2,  # Every day at 2 AM
        minute=0,
    ),
]
```

### 6.6 Transition Strategy

#### 6.6.1 Phased Approach

**Phase 1: Foundation (Week 1-2)**
- Add `WikiPage`, `WikiLink`, `LearningTopic` models
- Run migration
- Create basic API endpoints
- No UI changes yet

**Phase 2: Wiki Integration (Week 3-4)**
- Generate wiki pages from existing documents (ARQ job)
- Build WikiDashboard React component
- Add wiki graph visualization
- Link from chat to relevant wiki pages

**Phase 3: Auto-Discovery (Week 5-6)**
- Add `DiscoverySource`, `DiscoveryFeed`, `KnowledgeGap` models
- Implement discovery service
- Add ARQ worker jobs
- Build DiscoveryPanel UI

**Phase 4: Health & Digest (Week 7-8)**
- Implement WikiHealthService (lint)
- Add daily digest ARQ job
- Build LintReport and DigestCard UI
- Add notification system integration

**Phase 5: Polish (Week 9-10)**
- Full wiki-link parsing and rendering in chat responses
- Cross-reference display in page detail
- Search optimization (full-text search with PostgreSQL)
- Performance tuning and caching

#### 6.6.2 Backward Compatibility

- All existing API endpoints remain unchanged
- New endpoints are additive under `/api/v1/wiki/` and `/api/v1/discovery/`
- Existing documents are not modified
- Wiki pages are generated FROM documents, not replacing them
- Users can opt-in to auto-discovery (off by default)

#### 6.6.3 Data Migration

```python
# Migration script to generate initial wiki pages from existing documents
# Run once after Phase 2 deployment

async def generate_initial_wiki():
    """
    For each existing document:
    1. Run LLM to extract entities, concepts
    2. Create wiki pages
    3. Create wiki links
    4. Update INDEX
    """
    documents = await doc_repo.get_all()
    for doc in documents:
        await generate_wiki_pages.queue(str(doc.id))
```

---

## Appendix: File Inventory

### Complete file list in references/llm-wiki:

| File | Lines | Purpose |
|------|-------|---------|
| `CLAUDE.md` | ~200 | Schema for Claude Code |
| `AGENTS.md` | ~200 | Schema for Antigravity/Codex (identical to CLAUDE.md) |
| `.github/copilot-instructions.md` | ~200 | Schema for GitHub Copilot (identical to CLAUDE.md) |
| `config.example.yaml` | ~100 | Configuration template |
| `wiki-viewer.html` | ~600 | Single-file web viewer |
| `README.md` | ~200 | Project documentation |
| `FAQ.md` | ~150 | 7 frequently asked questions |
| `LICENSE` | ~20 | MIT License |
| `.gitignore` | ~50 | Git ignore rules |
| `skills/llm-wiki/SKILL.md` | ~300 | Claude Code skill with 9 sub-commands |
| `scripts/run-wiki.sh` | ~15 | Bash wrapper for schedulers |
| `scripts/setup-scheduler.ps1` | ~25 | Windows Task Scheduler setup |
| `wiki/INDEX.template.md` | ~20 | Wiki index template |
| `wiki/LOG.template.md` | ~10 | Activity log template |

**Total:** ~2070 lines of well-organized, self-documenting code and configuration.

### Key Statistics:
- **9 commands** in SKILL.md
- **4 page types** with defined schemas
- **7 discovery strategies** (web_search, feed_poll, gap_fill, reddit_scan, github_trending, github_watch, snowball)
- **5 scoring criteria** for pain-rank
- **3 layers** of architecture (raw/wiki/outputs)
- **6 golden rules** for system operation
- **0 external dependencies** for wiki-viewer.html
- **MIT license**

---

## Summary

The LLM Wiki repository is a remarkably clean, well-thought-out knowledge base system built on simple primitives: markdown files, wiki-links, and LLM workflows. Its greatest strengths are:

1. **Simplicity** -- No database, no server, just files and an LLM agent
2. **Immutability** -- Raw sources are never modified, enabling trust and rebuild
3. **Self-improvement** -- The lint -> gaps -> discover -> ingest loop creates autonomous growth
4. **Multi-agent** -- Works with Claude, Codex, Copilot, and Cursor without modification

AetherTutor, by contrast, is a production-grade multi-user learning platform with a full tech stack (PostgreSQL, ChromaDB, Redis, NetworkX, FastAPI, ARQ). It has features LLM Wiki doesn't (flashcards, quizzes, Socratic chat, vector search) but lacks the autonomous discovery and self-improvement loops that make LLM Wiki compelling.

The integration blueprint above proposes a phased approach to bring the best of both systems together: wiki pages as a structured knowledge layer on top of AetherTutor's existing document processing, auto-discovery as an ARQ worker system, health monitoring as an extension of the existing cross-verification service, and daily digests as scheduled notifications.

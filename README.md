# NewsLens

**See how different news outlets cover the same story differently** — the
entities they name, the sentiment they express, how they frame the same
details, and what they leave out. NewsLens runs a set of NLP models over
articles from multiple sources and shows the differences side-by-side.

It works two ways:
- **Curated events** from the BASIL dataset (Fox / HuffPost / NYT triplets), and
- **Live topics** — type any current story and it pulls today's coverage across
  outlets from the open GDELT news index.

> This README is about **how to run it**. For *what the pipeline actually does*
> (which models run, what's validated, what's not built yet), see
> [`PIPELINE_OVERVIEW.md`](PIPELINE_OVERVIEW.md).

---

## ⚡ TL;DR — starting the app

Already set up? You need **three things running**: PostgreSQL, the backend, and
the frontend. Open two terminals in the project root
(`c:\VOLUME A\AAANewsLens\newslens`):

```bash
# make sure PostgreSQL is running first (see "Start PostgreSQL" below)

# ── Terminal 1 — backend API ─────────────────────────
.venv\Scripts\activate
python -m uvicorn api.main:app --reload --port 8000

# ── Terminal 2 — frontend ────────────────────────────
cd frontend
npm run dev
```

Then open **http://localhost:5173**.

First time here? Do the **[First-time setup](#first-time-setup)** below once,
then come back to this.

---

## Prerequisites

- **Python 3.11**
- **Node.js 18+** (for the frontend)
- **PostgreSQL** — either Docker Desktop (easiest) or a local Postgres server
- A **Kaggle account** — only if you want the optional bias classifier

---

## First-time setup

Do this **once**. After this, starting the app is just the two terminals above.

### 1. Backend: Python environment

From the project root:

```bash
python -m venv .venv
.venv\Scripts\activate                # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

`torch`/`transformers` are large, so this takes a while. Model **weights**
(RoBERTa, MiniLM, spaCy) download automatically on first use — expect the first
analysis to pause a minute or two on a cold cache.

> **VS Code:** `Ctrl+Shift+P` → "Python: Select Interpreter" → `.venv`.

### 2. Start PostgreSQL

**Option A — Docker (recommended):**
```bash
docker compose up -d
```
Postgres 16 in a container, port 5432, password `dev`. Stop with
`docker compose down` (add `-v` to also wipe data).

**Option B — local Postgres server:** if you already run Postgres on port 5432,
just point `DATABASE_URL` at it in the next step, e.g.
`postgresql://postgres:yourpassword@localhost:5432/postgres`.

### 3. Configure environment variables

```bash
copy .env.example .env                # macOS/Linux: cp .env.example .env
```

Defaults match the Docker Postgres above:
```env
DATABASE_URL=postgresql://postgres:dev@localhost:5432/postgres
BASIL_DATA_DIR=./data/basil
```
Edit `DATABASE_URL` if you're using a local Postgres server.
(`BIAS_MODEL_DIR` stays unset unless you do the optional bias classifier below.)

### 4. Get the BASIL dataset

A helper script downloads, extracts, and structures BASIL into the layout the
loader expects (`data/basil/<event_id>/<source>.json`):

```bash
python scripts/prepare_basil.py                         # download from GitHub
# or, from a local zip:
python scripts/prepare_basil.py --zip-path path\to\BASIL-master.zip
```

> The schema auto-creates on API startup — there's no separate migration step.

You're set up. Start the app with the **[two terminals above](#-tldr--starting-the-app)**.

---

## Using the app

Open **http://localhost:5173**. The backend (Terminal 1) must be running — the
frontend talks to it through a Vite proxy (`/api` → `localhost:8000`).

**Analyze a live topic** — type a current story (e.g. *"world cup final"*) into
the search box and click **Analyze live**. It gathers coverage across outlets,
tags each source's political lean, and runs the full analysis.
*(GDELT's free tier rate-limits to ~1 request / 5s; if you hit a 429, wait a few
seconds and retry. Use broad, currently-active stories for the best results.)*

**Curated BASIL event** — pick one from the dropdown and click **Load + analyze**
the first time (a minute or two while models load); afterwards it's under
"Already analyzed…" for instant reopening.

**What you'll see:** a "How to read this" trust banner, a dateline of sources,
then panels for **Entities**, **Sentiment**, **Framing**, **Omission**,
**Narrative clusters**, and **Bias signal** (empty unless you set up the
optional classifier).

> **Swagger API docs** live at http://localhost:8000/docs — handy for testing
> endpoints directly.

---

## Trust & validation

NewsLens presents **differences** in coverage, not verdicts of bias — and the UI
says so up front. That framing is backed by data. Validate the framing metric
against BASIL's human bias annotations:

```bash
python -m scripts.evaluate_framing
```

Across all 100 BASIL events (4,300+ aligned sentence pairs), framing divergence
predicts a human-flagged sentence with **ROC AUC ≈ 0.56** — a *weak* signal. So
the interface deliberately reads the number as "phrasing differs," never "this
source is biased." Writes `framing_evaluation.csv`; supports `--threshold`,
`--min-span-chars`, `--limit-events`.

---

## Generate the project report

Produce a Word (.docx) report — architecture, methods, validation results, and a
live worked example (pulled from the running API if it's up):

```bash
python -m scripts.generate_report
```

Output: `NewsLens_Project_Report.docx` in the project root.

---

## Optional: bias classifier (Kaggle)

The "Bias signal" panel stays empty until you fine-tune a sentence-level bias
classifier — the one model in the pipeline that isn't pretrained. Everything
else works without this.

1. Zip your BASIL folder, upload it as a private **Kaggle Dataset**.
2. New Kaggle Notebook → upload `newslens_bias_classifier_kaggle.ipynb` → attach
   the dataset. Turn **GPU on** and **Internet on**.
3. Set `BASIL_DIR` in the config cell to the mounted path, then **Run all**
   (trains BERT / RoBERTa / DistilBERT, ~1–3 hrs on a T4).
4. **Pick the winner by F1** (BASIL's labels are imbalanced), download that
   checkpoint's `final/` folder into e.g. `models/bias_classifier/`, and add to
   `.env`:
   ```env
   BIAS_MODEL_DIR=./models/bias_classifier
   ```
5. Restart the API. Events analyzed **after** this point populate the panel;
   re-run older events to backfill.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Frontend loads but no data / errors | The backend (Terminal 1) isn't running or crashed — check its terminal. |
| `BASIL_DATA_DIR not found` | Run `python scripts/prepare_basil.py` (step 4), or fix the path in `.env`. |
| Live search returns HTTP 429 | GDELT rate limit — wait a few seconds and retry; space out requests. |
| Live search finds too few sources | Query too narrow — use a broad, currently-active story (needs ≥2 readable outlets). |
| DB connection refused | PostgreSQL isn't running, or `DATABASE_URL` is wrong. |
| First analysis is very slow | Model weights download on first use — subsequent runs are fast. |

**Debugging the backend in VS Code** — `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "NewsLens API",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["api.main:app", "--reload", "--port", "8000"],
      "jinja": true,
      "justMyCode": true
    }
  ]
}
```

**Recommended VS Code extensions:** Python + Pylance (backend), ESLint (frontend),
Ruff (Python linting), Docker (manage the Postgres container).

---

## How it works (quick tour)

The whole pipeline runs from one request (`POST /events` for a BASIL event, or
`POST /live-events` for a live topic):

```
Ingestion → Preprocessing → NER + cross-source canonicalization → Sentiment
   → Framing → Omission (entity + topic-overlap) → Narrative clustering
   → PostgreSQL → FastAPI → React frontend
```

**Cross-source entity canonicalization** deserves a note: outlets spell the same
entity differently (`Trump` vs `Donald Trump`), which would split one real-world
entity into multiple rows and corrupt every per-source comparison. NewsLens
pools entities from all sources, canonicalizes them together (fuzzy matching +
a subset-matching fallback for people's names), then maps the resolved names
back per source — so frequencies and omission percentages are accurate.

See [`PIPELINE_OVERVIEW.md`](PIPELINE_OVERVIEW.md) for the full model-by-model
breakdown and caveats.

---

## What's not built yet

- **Deployment** — the app runs locally; there's no public URL yet (containerize
  backend, managed Postgres, host frontend, add rate-limiting).
- **NewsAPI / Google News RSS ingestion** — only GDELT is wired in.
- **Omission & clustering validation** — the framing metric is validated (above);
  automated omission labeling and a clustering adjusted-Rand-index check are not.





Every time you want to run it
1. Make sure PostgreSQL is running (it's set up as a Windows service, so it likely starts automatically — but to check/start it):


Get-Service -Name 'postgresql*'
If it says Stopped, start it with:


Start-Service postgresql-x64-18
2. Start the backend — open a terminal in the project folder:


cd "c:\VOLUME A\AAANewsLens\newslens"
.venv\Scripts\activate
python -m uvicorn api.main:app --reload --port 8000
Leave this terminal running.

3. Start the frontend — open a second terminal:


cd "c:\VOLUME A\AAANewsLens\newslens\frontend"
npm run dev
Leave this running too.

4. Open the app:
Go to http://localhost:5173 in your browser.

Using it
Pick a curated event from the "Already downloaded (BASIL)" dropdown and click Load + analyze (first time on an event takes a minute or two while models warm up).
Or type a current news topic into the live search box and click Analyze live.
To stop it
Just close both terminal windows, or press Ctrl+C in each.

A few notes specific to your setup:

Your .env file already has the database password (yash123) and the bias-model path configured, so you don't need to touch it.
No Docker needed — you're using the native Windows PostgreSQL service, which is already running.
If port 8000 or 5173 is ever "already in use," it likely means a previous session is still running in the background — just reuse that one instead of starting a new 
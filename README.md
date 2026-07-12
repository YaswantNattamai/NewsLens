# NewsLens — setup

Covers the full core MVP: BASIL loading → preprocessing → NER/canonicalization
→ sentiment → framing → omission (entity + topic-overlap) → storage → API →
React frontend, plus the optional bias-classifier fine-tuning (section 6.7).

**For exactly what the pipeline currently does** (which models run
automatically, which are optional, what's not built yet), see
`PIPELINE_OVERVIEW.md` — read that alongside this file, this README is about
*how to run it*, that file is about *what it does*.

---

## ⚡ Quick Start: How to Restart the App (Terminal Guide)

If you have already run the setup steps, here is exactly how to start the app from scratch when you open your project.

### Step 0: Ensure your local PostgreSQL is running
Before running the terminals below, make sure your local PostgreSQL database server is active (running on port `5432` with your credentials configured in `.env`).

### Terminal 1: Run the Backend API Server
Open a new terminal window/tab, make sure you are in the project root directory (`c:\VOLUME A\AAANewsLens\newslens`), and run:
```bash
# 1. Activate the Python virtual environment
.venv\Scripts\activate

# 2. Start the FastAPI backend
python -m uvicorn api.main:app --reload --port 8000
```
*(Swagger API docs will be available at http://localhost:8000/docs)*

### Terminal 2: Run the React Frontend Server
Open a second terminal window/tab, make sure you are in the project root directory, and run:
```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Start the Vite dev server
npm run dev
```
*(Open your browser to http://localhost:5173 to view the app!)*

---

## Recommended order

Do these roughly in this order — the Kaggle step is slow and independent of
everything else, so it's worth kicking off first even though it's technically
optional:

1. **(Optional, start this first — it's the slow one) Train the bias
   classifier on Kaggle.** Section "6. Kaggle" below. Takes 1–3 hours. You can
   do the rest of setup while it runs, since it doesn't depend on your local
   backend at all.
2. **Set up the backend locally** (sections 1–5, 7–8 below): venv, Docker
   Postgres, `.env`, download BASIL, run the API.
3. **(Optional) Once Kaggle finishes,** download the winning checkpoint and
   point `BIAS_MODEL_DIR` at it (section 6 below) — this is what turns on the
   "Bias signal" panel in the frontend. Skip this if you don't need it; the
   rest of the app works fine without it.
4. **Set up and run the frontend** (section 9 below).
5. Open `http://localhost:5173`, pick a BASIL event, and look around.

If you skip step 1/3 entirely, everything still works — the four other
models (NER, sentiment, framing, omission) are pretrained and need no
training step. Only the "Bias signal" panel will stay empty.

## 0. Prerequisites

- Python 3.11
- Node.js 18+ (for the frontend)
- Docker Desktop (for Postgres)
- VS Code with the **Python** extension (Microsoft)
- A Kaggle account, if you're doing step 1/3

## 1. Open the project

```bash
cd newslens
code .
```

## 2. Backend: virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

`torch`/`transformers` are large — this step takes a while. Model *weights*
(RoBERTa sentiment, MiniLM, spaCy's model) download on first actual use, not
during `pip install` — expect the first `POST /events` call to pause for a
minute or two on a cold cache.

In VS Code: `Cmd/Ctrl+Shift+P` → "Python: Select Interpreter" →
`./newslens/.venv/bin/python`.

## 3. Start Postgres

### Option A: Using Docker (Recommended)
```bash
docker compose up -d
```
Postgres 16 in a container, port 5432, password `dev`. `docker compose down` stops it; `docker compose down -v` also wipes stored data.

### Option B: Using a Local Postgres Server (Non-Docker)
If you already have PostgreSQL installed directly on your machine (e.g. running as a Windows service on port 5432):
1. Create or use an existing database (e.g. `postgres`).
2. Update the `DATABASE_URL` in your `.env` file to match your local credentials:
   ```env
   DATABASE_URL=postgresql://<username>:<password>@localhost:5432/<database_name>
   ```
   *(e.g., `postgresql://postgres:yash123@localhost:5432/postgres`)*

## 4. Configure environment variables

```bash
cp .env.example .env
```

Defaults match the Docker Postgres above. `BASIL_DATA_DIR` should point at
your BASIL download (next section). Leave `BIAS_MODEL_DIR` unset for now —
you'll add it in section 6 if you want the bias classifier wired in.

## 5. Get BASIL

We have provided a script under [scripts/prepare_basil.py](file:///c:/VOLUME%20A/AAANewsLens/newslens/scripts/prepare_basil.py) to automatically download, extract, merge, and structure the BASIL dataset into the required layout (`data/basil/<event_id>/<source>.json`).

### Option A: Download automatically from GitHub
Ensure your virtual environment is active, and run:
```bash
python scripts/prepare_basil.py
```

### Option B: Use a local zip file
If you already have the dataset repository zipped locally (e.g. `BASIL-master.zip` or `BASIL-main.zip` downloaded from GitHub):
```bash
python scripts/prepare_basil.py --zip-path /path/to/BASIL-master.zip
```

**Before running anything else:** Open one of the generated JSON files in `data/basil/` and verify that the keys match what `ingestion/basil_loader.py` expects.
(`body-paragraphs` / `word-level-annotations`) — I can't verify BASIL's exact
current format without a live check; adjust that file if your copy differs.
Same caveat applies to `newslens_bias_classifier_kaggle.ipynb` in section 6.

## 6. Training the bias classifier on Kaggle (optional, section 6.7 / RQ2)

`analysis/bias_classifier.py` has the reusable training + inference logic.
For Kaggle specifically, use `newslens_bias_classifier_kaggle.ipynb` — it's
self-contained (Kaggle can't import your local repo), so it duplicates the
labeling/loading logic inline.

1. Zip your BASIL folder and upload it as a private Kaggle Dataset.
2. New Kaggle Notebook → Upload Notebook → this `.ipynb` → attach the dataset.
3. **Settings → Accelerator → GPU** on, **Settings → Internet → On**.
4. Run the first cells, note the mounted path from `!ls /kaggle/input`, set
   `BASIL_DIR` in the config cell to match.
5. Run all cells — trains and compares `bert-base-uncased`, `roberta-base`,
   `distilbert-base-uncased`, roughly 1–3 hours on a T4.
6. Commit the notebook ("Save & Run All") to get `bias_classifier_results.csv`
   and each checkpoint's `final/` weights folder into the Output tab.
7. **Pick the winner by F1**, not raw accuracy — BASIL's bias labels are
   imbalanced (most sentences aren't flagged), so F1 is the more honest
   comparison metric. Download that checkpoint's `final/` folder.
8. Drop it into the repo, e.g. `newslens/models/bias_classifier/`, and add to
   your `.env`:
   ```
   BIAS_MODEL_DIR=./models/bias_classifier
   ```
9. Restart the API (section 7). Any event you analyze *after* this point will
   populate the "Bias signal" panel. Events analyzed before you set
   `BIAS_MODEL_DIR` won't retroactively get bias predictions — re-run
   `POST /events` for them if you want that data too.

## 7. Run the API

```bash
uvicorn api.main:app --reload --port 8000
```

Swagger UI at `http://localhost:8000/docs` — useful for testing endpoints
directly before/without the frontend. The schema auto-creates on startup, no
separate migration step needed.

## 8. Debugging the backend in VS Code

`.vscode/launch.json`:

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

## 9. Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. It talks to the backend through a Vite
proxy (`/api` → `http://localhost:8000`, see `frontend/vite.config.js`), so
**the API from section 7 must be running first.**

What you'll see:
- An event picker — BASIL events only, no live search (that's an unbuilt
  extension, see `PIPELINE_OVERVIEW.md`). Pick an event and click
  **Load + analyze** the first time; after that it appears under "Already
  analyzed…" for instant reopening.
- A dateline strip with a colored stamp per source, linking to the original
  article.
- **Entities** — frequency table grouped by type, one column per source.
- **Sentiment** — diverging bar chart, entity sentiment per source.
- **Framing** — pairwise cards; click one to see the actual aligned sentence
  pairs behind the score, most divergent first.
- **Omission** — a bar per source; click to see which entities it's missing.
- **Bias signal** — empty unless you completed section 6.

## 10. Recommended VS Code extensions

- **Python** (ms-python.python), **Pylance** — backend
- **ES7+ React/Redux/React-Native snippets**, **ESLint** — frontend, optional
- **Ruff** (charliermarsh.ruff) — fast Python linter, optional
- **Docker** (ms-azuretools.vscode-docker) — manage the Postgres container
  from the sidebar

## What's still not built

- **Live ingestion** via GDELT/NewsAPI (section 4.3) — extension, explicitly lowest priority in the spec itself.
- **Evaluation scripts** (section 7) — correlating framing score against BASIL's human labels, manual omission labeling, adjusted Rand index. Not automated; the data's in Postgres if you want to script this yourself.

---

## 11. Cross-Source Entity Canonicalization

To prevent name spelling variations from splitting real-world entities into multiple rows across different sources (e.g. Fox using `Trump` and HuffPost using `Donald Trump`), NewsLens uses a pooled cross-source canonicalization process:
1. **Pooling:** Extracted entities from all sources (Fox, NYT, HuffPost) are gathered into a single list.
2. **Global Canonicalization:** The combined list is passed to `canonicalize()`, which applies fuzzy string matching and subset-matching fallbacks (for `PERSON` entities) to align variations under a single canonical name.
3. **De-pooling:** The resolved canonical mappings are mapped back to their respective sources to calculate accurate per-source entity frequencies and entity omission percentages.


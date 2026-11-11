# Hugging Face and Kaggle sources + AI hub page

Unzip over your DEVINTEL folder. It adds new files and replaces six frontend files (App, Nav, Home, Footer, redesign.css, and the new HubPage).
No new Python or npm packages are needed.

## 1. Two small edits to files only you have (the zip does not overwrite them)

`backend/app/main.py` - add the hub router next to the other routers (before the frontend/static part):
```python
from app.routers import hub                 # or add "hub" to your existing "from app.routers import ..." line
app.include_router(hub.router)
```

`backend/run_pipeline.py` - add the imports at the top, and the two lines directly below the `COLLECTORS = {...}` block:
```python
from app.collectors.huggingface import HuggingFaceCollector
from app.collectors.kaggle import KaggleCollector
...
COLLECTORS["huggingface"] = HuggingFaceCollector
COLLECTORS["kaggle"] = KaggleCollector
```

## 2. Keys (optional for Hugging Face, needed for most of Kaggle)
Add to `backend/.env`:
```
HF_TOKEN=            # optional, only gives a higher rate limit (huggingface.co/settings/tokens)
KAGGLE_USERNAME=     # from kaggle.com -> Settings -> API -> Create New Token (the kaggle.json file)
KAGGLE_KEY=
# or instead: KAGGLE_API_TOKEN=KGAT_...
```
Without Kaggle credentials only the Kaggle *datasets* list is collected; notebooks and competitions are skipped.
If Kaggle refuses even that, the Kaggle run is marked failed and the daily workflow turns red. In that case either add the
credentials or remove the `COLLECTORS["kaggle"]` line.

For the daily GitHub Actions run, add the same names as repository secrets (Settings -> Secrets and variables -> Actions)
and pass them in the workflow's `env:` block:
```yaml
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
          KAGGLE_USERNAME: ${{ secrets.KAGGLE_USERNAME }}
          KAGGLE_KEY: ${{ secrets.KAGGLE_KEY }}
```
Never commit `.env`.

## 3. Try it
```powershell
cd backend
pytest tests/test_hub.py                       # new tests (the API test needs the main.py edit above)
python run_pipeline.py --source huggingface
python run_pipeline.py --source kaggle
uvicorn app.main:app --reload --reload-dir app
```
Open http://localhost:5173/#/hub. The new table `hub_items` is created automatically.

## What is collected
- Hugging Face (public API, no key): the 20 trending models, datasets and spaces every day (ranked by Hugging Face's own
  trending score), each linked to a technology of your catalog when a tag matches (for example "pytorch").
  Also the metric `huggingface.top_downloads_30d` for PyTorch and TensorFlow: last-30-day downloads summed over the 100
  most-downloaded models carrying that library tag.
- Kaggle: hot datasets, the hottest notebooks and the competitions with the most teams.
- A failing section does not lose the others: the run is marked "partial" and the error is in `pipeline_runs`.
- Nothing is added to the DevIntel Score. The Hugging Face download metric is stored so it can become a signal later.

## Frontend
- New page `/#/hub` ("AI hub") with Hugging Face and Kaggle tabs, a link in the navigation and a seventh tile on the home page.
- The landing page now shows the real number of data sources (counted from your pipeline runs).
- The 3D scene is aligned to the top of the hero and stays in view while you read, and the headline is smaller so it takes fewer lines.
- The navigation switches to the mobile menu below 1200px, because there are now seven links.

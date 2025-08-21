# Weekly Digest: ML × Computational Biology (arXiv + bioRxiv)

This repository automatically collects **new preprints** from **arXiv** and **bioRxiv** that are relevant to **machine learning methods applied to computational biology and drug discovery**.  

Each week the workflow:
- Fetches new papers from the last 7 days
- Applies strict filters (keywords, ML methods, proximity, subject whitelist, excludes)
- Generates:
  - A human-readable digest at `docs/index.md` (viewable via GitHub Pages)
  - A machine-readable archive at `data/digest.json`
  - An **HTML + plaintext email** sent to your inbox

---

## 📦 What’s Inside

```
.
├── arxiv_digest.py            # Main script: fetches, filters, outputs, emails
├── requirements.txt           # Python dependencies
├── docs/
│   └── index.md               # Auto-generated weekly digest (GitHub Pages)
├── data/
│   └── digest.json            # Auto-generated JSON archive
└── .github/
    └── workflows/
        └── arxiv-digest.yml   # GitHub Action to run the pipeline weekly
```

---

## 🚀 Setup

### 1. Fork / Clone
Clone this repo to your own GitHub account.

### 2. Configure Secrets
Go to **Repository → Settings → Secrets and variables → Actions → New repository secret**, and add:

| Secret         | Value (example)                                                                 |
|----------------|---------------------------------------------------------------------------------|
| `SMTP_HOST`    | e.g. `smtp.gmail.com` or `smtp.office365.com`                                   |
| `SMTP_PORT`    | `587`                                                                           |
| `SMTP_USER`    | your email username (for Gmail use full address, e.g. `you@gmail.com`)          |
| `SMTP_PASS`    | your email password / **App Password** (Gmail/Outlook require App Passwords)    |
| `EMAIL_FROM`   | address to appear in the "From" field                                           |
| `EMAIL_TO`     | recipient(s), e.g. `me@example.com` or `me@example.com,you@example.com`         |

💡 Free option: use Gmail with an [App Password](https://support.google.com/accounts/answer/185833).

### 3. Enable GitHub Pages (optional but recommended)
- Go to **Settings → Pages**
- Set **Source** to *Deploy from a branch*
- Select branch `main` (or `master`), folder `/docs`
- Save → your digest will be live at `https://<your-username>.github.io/<repo-name>/`

### 4. Workflow Schedule
The action runs automatically **every Monday at 13:00 UTC**.  
You can also trigger it manually under **Actions → arxiv-digest → Run workflow**.

---

## ⚙️ Configuration

All filters live at the top of `arxiv_digest.py`:

- **Categories (arXiv):**  
  `CATEGORIES = ["q-bio.BM", "q-bio.QM", "cs.LG", "stat.ML"]`
- **Keywords (domain terms):** proteins, antibodies, ligands, docking, ADMET, etc.
- **Methods (ML terms):** diffusion, transformer, equivariant, GNN, LLM, generative, etc.
- **bioRxiv subjects whitelist:** bioinformatics, computational biology, genomics, biophysics, etc.
- **Excludes:** ecology, zoology, plant biology, psychology, etc.
- **Filters:**  
  - Require both keyword ∩ method  
  - Enforce word-boundaries  
  - Optional proximity (default: within 100 chars)  
  - Drop abstracts shorter than 200 chars

Tune these lists to widen or narrow the digest.

---

## 📧 Email Output

- Sends a nicely formatted HTML + plaintext email
- Subject line:  
  `Weekly Digest: ML × Computational Biology — August 21, 2025`
- Body: list of matching papers with title, authors, category, source (arXiv/bioRxiv), and links to abstract/PDF

---

## 🖥 Local Run (optional)

You can also run the script locally:

```bash
pip install -r requirements.txt
python arxiv_digest.py
```

Without SMTP env vars set, it will just update `docs/index.md` and `data/digest.json`.

---

## 🔄 Customization Ideas

- Change cron schedule in `.github/workflows/arxiv-digest.yml`  
  e.g. run twice per week:  
  ```yaml
  - cron: "0 13 * * 1,4"
  ```
- Expand to medRxiv in the same style
- Push digests to Slack, Notion, or Teams instead of email
- Score/rank papers (e.g. weight if keyword appears in title)

---

## 📝 License

MIT — free to use, modify, and share.

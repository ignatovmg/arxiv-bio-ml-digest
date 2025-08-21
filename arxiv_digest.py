import os
import re
import json
import time
import html
import pathlib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import smtplib
import requests
from urllib.parse import urlencode

import feedparser
from dateutil import parser as dateparser

# ---------------- Config (edit to taste) ----------------
CATEGORIES = ["q-bio.BM", "q-bio.QM", "cs.LG", "stat.ML"]

KEYWORDS = [
    "protein", "antibody", "antibodies", "enzyme", "ligand", "drug", "molecule",
    "molecular", "chem", "binding", "docking", "ADMET", "pharmacokinetics",
    "sequence design", "structure prediction"
]

METHODS = [
    "diffusion", "transformer", "equivariant", "geometric", "graph neural",
    "LLM", "language model", "generative", "denoising", "flow matching"
]

WINDOW_DAYS = 7
MAX_RESULTS = 200

DOCS_MD = pathlib.Path("docs/index.md")
DATA_JSON = pathlib.Path("data/digest.json")
# --------------------------------------------------------


def build_query():
    """
    Build a single search_query string for arXiv.
    We keep quotes for multi-word phrases but let urlencode() percent-encode them.
    """
    cats = " OR ".join([f"cat:{c}" for c in CATEGORIES])

    def phrase(s):
        return f'"{s}"' if " " in s else s

    kw_block = " OR ".join(phrase(k) for k in KEYWORDS)
    meth_block = " OR ".join(phrase(m) for m in METHODS)

    # Require: (categories) AND all:(keywords) AND all:(methods)
    query = f"({cats}) AND all:({kw_block}) AND all:({meth_block})"
    return query


def fetch_arxiv_entries(query, max_results=200, start=0):
    """
    Use requests to handle URL encoding and headers; feedparser parses the returned XML.
    """
    base = "https://export.arxiv.org/api/query"
    params = {
        "search_query": query,          # requests/urlencode will encode spaces/quotes safely
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    headers = {
        # arXiv asks clients to identify themselves
        "User-Agent": "arxiv-digest/1.0 (mailto:your_email@example.com)"
    }
    resp = requests.get(base, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    # feedparser accepts a text/bytes string directly
    parsed = feedparser.parse(resp.text)
    return parsed.entries


def normalize_text(*parts):
    txt = " ".join(filter(None, parts))
    txt = html.unescape(txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def to_pdf_link(link_or_id):
    return link_or_id.replace("/abs/", "/pdf/") + ".pdf" if "/abs/" in link_or_id else link_or_id


def main():
    query = build_query()
    entries = fetch_arxiv_entries(query, MAX_RESULTS, 0)

    week_ago = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    seen_ids = set()
    rows = []

    for e in entries:
        pub = dateparser.parse(e.get("published")) if e.get("published") else None
        upd = dateparser.parse(e.get("updated")) if e.get("updated") else pub
        if not pub or pub < week_ago:
            continue

        blob = normalize_text(e.get("title", ""), e.get("summary", "")).lower()
        kw_ok = any(k.lower() in blob for k in KEYWORDS)
        meth_ok = any(m.lower() in blob for m in METHODS)
        if not (kw_ok and meth_ok):
            continue

        arxiv_id = e.get("id", e.get("link", ""))
        if arxiv_id in seen_ids:
            continue
        seen_ids.add(arxiv_id)

        title = normalize_text(e.get("title", ""))
        summary = normalize_text(e.get("summary", ""))
        link = e.get("link") or arxiv_id
        pdf = to_pdf_link(arxiv_id)
        cats = [t["term"] for t in e.get("tags", [])] if e.get("tags") else []
        primary_cat = cats[0] if cats else "unknown"
        authors = ", ".join([a.get("name") for a in e.get("authors", []) if a.get("name")])

        rows.append({
            "title": title,
            "authors": authors,
            "published": pub.isoformat(),
            "updated": upd.isoformat() if upd else None,
            "category": primary_cat,
            "link": link,
            "pdf": pdf,
            "summary": summary
        })

    rows.sort(key=lambda r: r["published"], reverse=True)

    DOCS_MD.parent.mkdir(parents=True, exist_ok=True)
    DATA_JSON.parent.mkdir(parents=True, exist_ok=True)

    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump({"generated_at": datetime.utcnow().isoformat() + "Z", "items": rows}, f, indent=2)

    now_str = datetime.utcnow().strftime("%B %d, %Y")
    header = f"# Weekly arXiv Digest (ML × Computational Biology)\n\n*Updated: {now_str} UTC*\n\n"
    note = (
        "> Filters: categories **"
        + ", ".join(CATEGORIES)
        + f"**, window **last {WINDOW_DAYS} days**, keywords ∩ methods.\n\n"
        "Tip: Edit `arxiv_digest.py` to change keywords/categories.\n\n"
    )

    if not rows:
        body_md = "_No items matched this week. Try broadening keywords in `arxiv_digest.py`._\n"
    else:
        lines = []
        for r in rows:
            date_str = r["published"][:10]
            lines.append(
                f"- **{r['title']}**  \n"
                f"  {r['authors']} — *{r['category']}*, {date_str}  \n"
                f"  [abs]({r['link']}) · [pdf]({r['pdf']})  \n"
            )
        body_md = "\n".join(lines) + "\n"

    with open(DOCS_MD, "w", encoding="utf-8") as f:
        f.write(header + note + body_md)

    # ---------- Email delivery ----------
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    email_to = os.getenv("EMAIL_TO", "").strip()
    email_from = os.getenv("EMAIL_FROM", "").strip() or smtp_user

    if not (smtp_host and smtp_user and smtp_pass and email_to):
        print("[info] Email not sent: missing SMTP_* or EMAIL_* environment variables.")
        return

    subject = f"Weekly arXiv Digest: ML × Computational Biology — {now_str}"
    # Build a compact HTML email
    if not rows:
        items_html = "<p><em>No items matched this week.</em></p>"
        items_text = "No items matched this week."
    else:
        items_html = "<ul>" + "".join(
            f"<li><b>{html.escape(r['title'])}</b><br>"
            f"{html.escape(r['authors'])} — <i>{html.escape(r['category'])}</i>, {r['published'][:10]}<br>"
            f"<a href='{r['link']}'>abs</a> · <a href='{r['pdf']}'>pdf</a></li>"
            for r in rows
        ) + "</ul>"
        items_text = "\n".join(
            f"- {r['title']} | {r['authors']} — {r['category']}, {r['published'][:10]} | {r['link']} | {r['pdf']}"
            for r in rows
        )

    html_body = f"""
    <div>
      <h2>Weekly arXiv Digest (ML × Computational Biology)</h2>
      <p><small>Updated: {now_str} UTC</small></p>
      <p>Filters: categories <b>{", ".join(CATEGORIES)}</b>, window <b>last {WINDOW_DAYS} days</b>, keywords ∩ methods.</p>
      {items_html}
      <p>Full list & archive in the repo: <code>docs/index.md</code>. JSON at <code>data/digest.json</code>.</p>
    </div>
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to
    msg.set_content(f"Weekly arXiv Digest (ML × Computational Biology)\n\n{items_text}\n")
    msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
            print("[info] Email sent.")
    except Exception as exc:
        print(f"[warn] Email send failed: {exc}")


if __name__ == "__main__":
    main()

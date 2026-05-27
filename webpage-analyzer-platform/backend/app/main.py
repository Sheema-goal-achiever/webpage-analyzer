from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import requests
from bs4 import BeautifulSoup
import datetime
import os
from typing import Any, Dict

app = FastAPI(title="Webpage Analyzer API")

DB_PATH = os.path.join(os.getcwd(), "webpage_analyzer.db")


def db_connect():
    return sqlite3.connect(DB_PATH)


def build_summary(title: str, text: str, metrics: Dict[str, int]) -> Dict[str, Any]:
    return {
        "title": title,
        "word_count": len(text.split()),
        "snippet": text[:500],
        **metrics,
    }


def init_db() -> None:
    with db_connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                title TEXT,
                html TEXT,
                text TEXT,
                total_links INTEGER DEFAULT 0,
                total_buttons INTEGER DEFAULT 0,
                total_forms INTEGER DEFAULT 0,
                total_tables INTEGER DEFAULT 0,
                total_inputs INTEGER DEFAULT 0
            )
            """
        )

        cur.execute("PRAGMA table_info(snapshots)")
        existing_columns = [row[1] for row in cur.fetchall()]
        for column in ["total_links", "total_buttons", "total_forms", "total_tables", "total_inputs"]:
            if column not in existing_columns:
                cur.execute(f"ALTER TABLE snapshots ADD COLUMN {column} INTEGER DEFAULT 0")


def serialize_dom(el, max_depth=20, _depth=0) -> Any:
    from bs4 import NavigableString

    if _depth > max_depth:
        return None

    if isinstance(el, NavigableString):
        text = str(el).strip()
        return text or None

    if not getattr(el, "name", None):
        return None

    node = {"name": el.name}
    if el.attrs:
        node["attrs"] = el.attrs

    children = [child for content in el.contents if (child := serialize_dom(content, max_depth=max_depth, _depth=_depth + 1)) is not None]
    if children:
        node["children"] = children

    return node


def count_page_metrics(soup) -> Dict[str, int]:
    inputs = soup.find_all("input")
    btn_inputs = [inp for inp in inputs if inp.get("type") in {"button", "submit", "reset", "image"}]
    return {
        "total_links": len(soup.find_all("a", href=True)),
        "total_buttons": len(soup.find_all("button")) + len(btn_inputs),
        "total_forms": len(soup.find_all("form")),
        "total_tables": len(soup.find_all("table")),
        "total_inputs": len(inputs),
    }


def parse_page(html: str):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    text = soup.get_text(separator=" ", strip=True)
    tree_root = soup.body or soup
    return soup, title, text, serialize_dom(tree_root), count_page_metrics(soup)


def flatten_dom(tree, path="") -> list[dict]:
    flattened = []
    if isinstance(tree, dict) and "name" in tree:
        current_path = f"{path}/{tree['name']}"
        flattened.append(
            {
                "path": current_path,
                "name": tree["name"],
                "attrs": tree.get("attrs", {}),
                "text": "",
            }
        )
        for child in tree.get("children", []):
            flattened.extend(flatten_dom(child, current_path))
    elif isinstance(tree, str):
        flattened.append(
            {
                "path": f"{path}/#text",
                "name": "#text",
                "attrs": {},
                "text": tree,
            }
        )
    return flattened


class AnalyzeRequest(BaseModel):
    url: str


class CompareRequest(BaseModel):
    left_id: int
    right_id: int


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/")
def root():
    return {"message": "Webpage Analyzer API"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        resp = requests.get(req.url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")

    html = resp.text
    _, title, text, tree, metrics = parse_page(html)
    summary = build_summary(title, text, metrics)
    ts = datetime.datetime.utcnow().isoformat()

    with db_connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO snapshots (url, timestamp, title, html, text, total_links, total_buttons, total_forms, total_tables, total_inputs) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                req.url,
                ts,
                title,
                html,
                text,
                metrics["total_links"],
                metrics["total_buttons"],
                metrics["total_forms"],
                metrics["total_tables"],
                metrics["total_inputs"],
            ),
        )
        snapshot_id = cur.lastrowid

    return {
        "id": snapshot_id,
        "url": req.url,
        "timestamp": ts,
        "summary": summary,
        "tree": tree,
    }


@app.get("/history")
def history():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, url, timestamp, title FROM snapshots ORDER BY timestamp DESC")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "url": r[1], "timestamp": r[2], "title": r[3]} for r in rows]


@app.get("/snapshot/{snapshot_id}")
def get_snapshot(snapshot_id: int):
    with db_connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, url, timestamp, title, html, text, total_links, total_buttons, total_forms, total_tables, total_inputs FROM snapshots WHERE id = ?",
            (snapshot_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    id_, url, ts, title, html, text, total_links, total_buttons, total_forms, total_tables, total_inputs = row
    tree = None
    try:
        _, _, _, tree, _ = parse_page(html)
    except Exception:
        tree = None

    metrics = {
        "total_links": total_links,
        "total_buttons": total_buttons,
        "total_forms": total_forms,
        "total_tables": total_tables,
        "total_inputs": total_inputs,
    }

    return {
        "id": id_,
        "url": url,
        "timestamp": ts,
        "title": title,
        "html": html,
        "text": text,
        "tree": tree,
        "metrics": metrics,
        "summary": build_summary(title, text, metrics),
    }


@app.get("/snapshots/by-url")
def snapshots_by_url(url: str):
    with db_connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, url, timestamp, title FROM snapshots WHERE url = ? ORDER BY timestamp DESC",
            (url,),
        )
        rows = cur.fetchall()
    return [{"id": r[0], "url": r[1], "timestamp": r[2], "title": r[3]} for r in rows]


@app.get("/compare")
def compare(left_id: int, right_id: int):
    with db_connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, html FROM snapshots WHERE id = ?", (left_id,))
        left = cur.fetchone()
        cur.execute("SELECT id, html FROM snapshots WHERE id = ?", (right_id,))
        right = cur.fetchone()

    if not left or not right:
        raise HTTPException(status_code=404, detail="One or both snapshots not found")

    _, left_html = left
    _, right_html = right

    left_tree = serialize_dom(BeautifulSoup(left_html, "html.parser").body or BeautifulSoup(left_html, "html.parser"))
    right_tree = serialize_dom(BeautifulSoup(right_html, "html.parser").body or BeautifulSoup(right_html, "html.parser"))

    left_flat = {node["path"]: node for node in flatten_dom(left_tree)}
    right_flat = {node["path"]: node for node in flatten_dom(right_tree)}

    added_nodes = []
    removed_nodes = []
    changed_nodes = []

    for path, right_node in right_flat.items():
        if path not in left_flat:
            added_nodes.append(right_node)
        else:
            left_node = left_flat[path]
            if left_node["attrs"] != right_node["attrs"] or left_node["text"] != right_node["text"]:
                changed_nodes.append({
                    "path": path,
                    "left": left_node,
                    "right": right_node,
                })

    for path, left_node in left_flat.items():
        if path not in right_flat:
            removed_nodes.append(left_node)

    result = {
        "left_id": left_id,
        "right_id": right_id,
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "changed_nodes": changed_nodes,
        "metrics": {
            "added_nodes": len(added_nodes),
            "removed_nodes": len(removed_nodes),
            "changed_nodes": len(changed_nodes),
        },
    }
    return result


@app.post("/compare")
def compare_post(req: CompareRequest):
    return compare(req.left_id, req.right_id)

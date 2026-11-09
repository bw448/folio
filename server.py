"""Folio — a local-first English reading workbench.

One app that merges the parts we liked from Zotero (three-pane reader + annotations),
PaperLens (ECDICT lookup + vocabulary review), Readwise (highlight -> daily review),
Gloss/SciSpace (AI explain + structured paper summary), and Koodo/Readest
(library + reading modes).

Backend: FastAPI + SQLite + PyMuPDF + ECDICT + FSRS + any OpenAI-compatible LLM.
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import os
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

import genanki
import httpx
import numpy as np
import pymupdf
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fsrs import Card, Rating, Scheduler
from pydantic import BaseModel, Field

FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    BASE_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = BASE_DIR

DEFAULT_DATA_DIR = BASE_DIR / "data"


def _storage_pointer_candidates() -> list[Path]:
    out = [BASE_DIR / "storage.json"]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        out.append(Path(local) / "Folio" / "storage.json")
    return out


def _read_storage_dir() -> Optional[Path]:
    for pointer in _storage_pointer_candidates():
        try:
            payload = json.loads(pointer.read_text(encoding="utf-8"))
            raw = (payload.get("data_dir") or "").strip()
            if raw:
                return Path(raw).expanduser()
        except (OSError, ValueError, TypeError):
            continue
    return None


_chosen_data_dir = _read_storage_dir()
DATA_DIR = _chosen_data_dir or DEFAULT_DATA_DIR
STORAGE_CONFIGURED = _chosen_data_dir is not None
PDF_DIR = DATA_DIR / "pdfs"
CACHE_DIR = DATA_DIR / "cache"
EXPORT_DIR = DATA_DIR / "exports"
STATIC_DIR = RESOURCE_DIR / "static"
DB_PATH = DATA_DIR / "readmate.db"
ECDICT_PATH = DATA_DIR / "ecdict.db"

try:
    for folder in (DATA_DIR, PDF_DIR, CACHE_DIR, EXPORT_DIR, STATIC_DIR):
        folder.mkdir(parents=True, exist_ok=True)
except OSError:
    if FROZEN:
        app_root = Path(os.environ.get("LOCALAPPDATA", str(BASE_DIR))) / "Folio"
        old_root = Path(os.environ.get("LOCALAPPDATA", str(BASE_DIR))) / "ReadMate"
        if not app_root.exists() and (old_root / "data").exists():
            try:
                shutil.copytree(old_root / "data", app_root / "data")
            except OSError:
                pass
        DATA_DIR = app_root / "data"
        STORAGE_CONFIGURED = False
        PDF_DIR = DATA_DIR / "pdfs"
        CACHE_DIR = DATA_DIR / "cache"
        EXPORT_DIR = DATA_DIR / "exports"
        DB_PATH = DATA_DIR / "readmate.db"
        ECDICT_PATH = DATA_DIR / "ecdict.db"
        for folder in (DATA_DIR, PDF_DIR, CACHE_DIR, EXPORT_DIR):
            folder.mkdir(parents=True, exist_ok=True)
    else:
        raise

if STORAGE_CONFIGURED and not ECDICT_PATH.exists():
    seed = RESOURCE_DIR / "seed" / "ecdict.db"
    if seed.exists():
        shutil.copy2(seed, ECDICT_PATH)

app = FastAPI(title="Folio", version="0.9.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

scheduler = Scheduler()
RATINGS = {1: Rating.Again, 2: Rating.Hard, 3: Rating.Good, 4: Rating.Easy}

SETTING_DEFAULTS = {
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "api_key": "",
    "provider": "deepseek",
    "s2_api_key": "",
    "zotero_url": "http://127.0.0.1:23119",
    "sync_url": "",
    "sync_user": "",
    "sync_password": "",
    "sync_pdfs": "1",
    "sync_device": "",
    "last_sync": "",
    "epub_font_size": "15",
    "auto_lookup": "1",
}

TAG_NAMES = {
    "cet4": "四级", "cet6": "六级", "ky": "考研", "toefl": "托福",
    "ielts": "雅思", "gre": "GRE", "gk": "高考", "zk": "中考",
}

EXCHANGE_LABELS = {
    "p": "过去式",
    "d": "过去分词",
    "i": "现在分词",
    "3": "第三人称单数",
    "r": "比较级",
    "t": "最高级",
    "s": "复数",
    "0": "原型",
    "1": "派生",
}


# ---------------------------------------------------------------------------
# database
# ---------------------------------------------------------------------------
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_columns(conn: sqlite3.Connection) -> None:
    """Small forward-only migrations for existing databases."""
    additions = {
        "documents": {
            "authors": "TEXT NOT NULL DEFAULT ''",
            "year": "TEXT NOT NULL DEFAULT ''",
            "doi": "TEXT NOT NULL DEFAULT ''",
            "venue": "TEXT NOT NULL DEFAULT ''",
            "abstract": "TEXT NOT NULL DEFAULT ''",
            "tags": "TEXT NOT NULL DEFAULT ''",
            "collection_id": "INTEGER",
            "favorite": "INTEGER NOT NULL DEFAULT 0",
            "status": "TEXT NOT NULL DEFAULT 'unread'",
            "last_read_at": "TEXT",
            "reading_seconds": "INTEGER NOT NULL DEFAULT 0",
            "rating": "INTEGER NOT NULL DEFAULT 0",
            "summary_json": "TEXT",
            "cover_color": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
            "source_path": "TEXT NOT NULL DEFAULT ''",
        },
        "vocab": {
            "deck": "TEXT NOT NULL DEFAULT '默认'",
            "mastered": "INTEGER NOT NULL DEFAULT 0",
            "source": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
            "sync_uid": "TEXT NOT NULL DEFAULT ''",
        },
        "highlights": {
            "type": "TEXT NOT NULL DEFAULT 'highlight'",
            "updated_at": "TEXT",
            "due": "TEXT",
            "fsrs": "TEXT",
            "reps": "INTEGER NOT NULL DEFAULT 0",
            "sync_uid": "TEXT NOT NULL DEFAULT ''",
        },
        "notes": {
            "title": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT",
            "sync_uid": "TEXT NOT NULL DEFAULT ''",
        },
        "articles": {
            "source": "TEXT NOT NULL DEFAULT ''",
            "category": "TEXT NOT NULL DEFAULT ''",
            "year": "TEXT NOT NULL DEFAULT ''",
            "score": "REAL NOT NULL DEFAULT 0",
        },
    }
    for table, columns in additions.items():
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def _backfill_sync_uids(conn: sqlite3.Connection) -> None:
    """Give every syncable row a stable uid, independent of its content.

    Content-hash keys made edited notes/highlights look like brand-new objects
    across devices. The uid is what lets the merger see "same object, both
    sides changed" and raise a content conflict instead of duplicating it.
    """
    for table in ("vocab", "highlights", "notes"):
        rows = conn.execute(
            f"SELECT id FROM {table} WHERE COALESCE(sync_uid, '') = ''"
        ).fetchall()
        for row in rows:
            conn.execute(
                f"UPDATE {table} SET sync_uid=? WHERE id=?",
                (uuid.uuid4().hex, row["id"]),
            )


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                filename TEXT,
                path TEXT NOT NULL UNIQUE,
                pages INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_page INTEGER NOT NULL DEFAULT 1,
                kind TEXT NOT NULL DEFAULT 'paper'
            );
            CREATE TABLE IF NOT EXISTS pages (
                doc_id INTEGER NOT NULL,
                page INTEGER NOT NULL,
                text TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (doc_id, page),
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS vocab (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL UNIQUE COLLATE NOCASE,
                lemma TEXT,
                phonetic TEXT,
                translation TEXT,
                definition TEXT,
                tag TEXT,
                exchange TEXT,
                context TEXT,
                doc_id INTEGER,
                page INTEGER,
                created_at TEXT NOT NULL,
                due TEXT NOT NULL,
                fsrs TEXT,
                reps INTEGER NOT NULL DEFAULT 0,
                lapses INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vocab_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                reviewed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS highlights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                page INTEGER NOT NULL,
                color TEXT NOT NULL DEFAULT 'yellow',
                text TEXT NOT NULL DEFAULT '',
                rects TEXT NOT NULL DEFAULT '[]',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                page INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS wrong_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER,
                page INTEGER,
                question TEXT NOT NULL,
                options TEXT NOT NULL DEFAULT '',
                answer TEXT NOT NULL DEFAULT '',
                explanation TEXT NOT NULL DEFAULT '',
                question_type TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sync_uid TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL DEFAULT '#0071e3',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                citations TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS page_translations (
                doc_id INTEGER NOT NULL,
                page INTEGER NOT NULL,
                target TEXT NOT NULL DEFAULT 'zh',
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (doc_id, page, target),
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS reading_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER NOT NULL,
                seconds INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS ocr_words (
                doc_id INTEGER NOT NULL,
                page INTEGER NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                w REAL NOT NULL,
                h REAL NOT NULL,
                text TEXT NOT NULL,
                PRIMARY KEY (doc_id, page, text, x, y),
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS ocr_jobs (
                doc_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                total INTEGER NOT NULL DEFAULT 0,
                done INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS export_jobs (
                doc_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                total INTEGER NOT NULL DEFAULT 0,
                done INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                path TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                query TEXT NOT NULL,
                sources TEXT NOT NULL DEFAULT 'arxiv,openalex',
                days INTEGER NOT NULL DEFAULT 30,
                created_at TEXT NOT NULL,
                last_checked TEXT,
                last_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS topic_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                paper_key TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                seen INTEGER NOT NULL DEFAULT 0,
                UNIQUE (topic_id, paper_key),
                FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL DEFAULT 'topic',
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                link TEXT NOT NULL DEFAULT '',
                read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sync_deletions (
                entity_type TEXT NOT NULL,
                entity_key TEXT NOT NULL,
                deleted_at TEXT NOT NULL,
                device TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (entity_type, entity_key)
            );
            CREATE TABLE IF NOT EXISTS sync_ignored_deletions (
                entity_type TEXT NOT NULL,
                entity_key TEXT NOT NULL,
                deleted_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (entity_type, entity_key)
            );
            CREATE TABLE IF NOT EXISTS sync_ignored_restores (
                entity_type TEXT NOT NULL,
                entity_key TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (entity_type, entity_key)
            );
            CREATE TABLE IF NOT EXISTS sync_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_key TEXT NOT NULL,
                local_json TEXT NOT NULL,
                remote_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                resolved INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        _ensure_columns(conn)
        _backfill_sync_uids(conn)
        conn.execute(
            "UPDATE documents SET updated_at=created_at "
            "WHERE updated_at IS NULL OR updated_at=''"
        )
        conn.execute(
            "UPDATE vocab SET updated_at=created_at "
            "WHERE updated_at IS NULL OR updated_at=''"
        )
        for key, value in SETTING_DEFAULTS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (key, value)
            )
        conn.execute(
            "INSERT OR IGNORE INTO settings(key, value) VALUES ('daily_goal', '20')"
        )
        conn.execute(
            "INSERT OR IGNORE INTO settings(key, value) VALUES ('onboarded', '0')"
        )


init_db()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_setting(key: str) -> str:
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else SETTING_DEFAULTS.get(key, "")


def set_setting(key: str, value: str) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


# ---------------------------------------------------------------------------
# dictionary (ECDICT)
# ---------------------------------------------------------------------------
def _dict_conn() -> sqlite3.Connection:
    if not ECDICT_PATH.exists():
        raise HTTPException(
            503,
            "词典还没建好。请在项目目录运行：.venv\\Scripts\\python.exe build_dict.py",
        )
    conn = sqlite3.connect(ECDICT_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _clean_word(word: str) -> str:
    return re.sub(r"^[^A-Za-z]+|[^A-Za-z'’-]+$", "", (word or "").strip()).lower()


def _query_dict(conn: sqlite3.Connection, word: str) -> Optional[sqlite3.Row]:
    row = conn.execute(
        "SELECT * FROM ecdict WHERE word = ? COLLATE NOCASE", (word,)
    ).fetchone()
    if row:
        return row
    row = conn.execute(
        "SELECT lemma FROM forms WHERE form = ? COLLATE NOCASE LIMIT 1", (word,)
    ).fetchone()
    if row:
        return conn.execute(
            "SELECT * FROM ecdict WHERE word = ? COLLATE NOCASE", (row["lemma"],)
        ).fetchone()
    return None


def _candidates(word: str) -> list[str]:
    out: list[str] = []
    w = word.lower()
    if w.endswith("'s"):
        out.append(w[:-2])
    if len(w) > 4 and w.endswith("ies"):
        out.append(w[:-3] + "y")
    if len(w) > 4 and w.endswith("ied"):
        out.append(w[:-3] + "y")
    for suffix, replacements in (
        ("ing", ("", "e")),
        ("ed", ("", "e")),
        ("es", ("",)),
        ("s", ("",)),
        ("er", ("", "e")),
        ("est", ("", "e")),
        ("ly", ("",)),
        ("ment", ("",)),
        ("ness", ("",)),
        ("tion", ("t", "te")),
        ("ation", ("ate", "e")),
    ):
        if len(w) > len(suffix) + 2 and w.endswith(suffix):
            stem = w[: -len(suffix)]
            for rep in replacements:
                out.append(stem + rep)
    seen: set[str] = set()
    return [x for x in out if x and not (x in seen or seen.add(x))]


def lookup_word(raw: str) -> dict[str, Any]:
    word = _clean_word(raw)
    if not word:
        return {"found": False, "query": raw}
    conn = _dict_conn()
    try:
        row = _query_dict(conn, word)
        if row is None:
            for candidate in _candidates(word):
                row = _query_dict(conn, candidate)
                if row:
                    break
        if row is None:
            return {"found": False, "query": word}
        exchange = []
        for part in (row["exchange"] or "").split("/"):
            if ":" not in part:
                continue
            code, value = part.split(":", 1)
            if value:
                exchange.append(
                    {"code": code, "label": EXCHANGE_LABELS.get(code, code), "word": value}
                )
        return {
            "found": True,
            "query": word,
            "word": row["word"],
            "phonetic": row["phonetic"] or "",
            "translation": (row["translation"] or "").replace("\\n", "\n"),
            "definition": (row["definition"] or "").replace("\\n", "\n"),
            "pos": row["pos"] or "",
            "collins": row["collins"] or "",
            "oxford": row["oxford"] or "",
            "tag": (row["tag"] or "").split(),
            "bnc": row["bnc"] or "",
            "frq": row["frq"] or "",
            "exchange": exchange,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------
async def ai_chat(
    messages: list[dict[str, str]], *, json_mode: bool = False, max_tokens: int = 1800
) -> str:
    base_url = get_setting("base_url").rstrip("/")
    api_key = get_setting("api_key").strip()
    model = get_setting("model").strip()
    local = "127.0.0.1" in base_url or "localhost" in base_url
    if not api_key and not local:
        raise HTTPException(
            400,
            "还没有配置 AI 接口。点左下角「设置」，填入 DeepSeek API Key（或本地 Ollama 地址）。",
        )
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.25,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{base_url}/chat/completions", headers=headers, json=payload
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "AI 请求超时，请稍后再试。") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"连接 AI 接口失败：{exc}") from exc
    if response.status_code >= 400:
        detail = response.text[:500]
        raise HTTPException(502, f"AI 接口返回 {response.status_code}：{detail}")
    try:
        return response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise HTTPException(502, "AI 返回格式异常。") from exc


def parse_json_block(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no json object")
    return json.loads(cleaned[start : end + 1])


SYSTEM_PROMPT = (
    "你是一位面向中国大学生的英语阅读与学术文献助手。回答要准确、紧凑、可操作，"
    "使用 Markdown；不要编造词义或论文内容。"
)


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------
class SettingsIn(BaseModel):
    provider: str = "deepseek"
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    s2_api_key: str = ""
    zotero_url: str = ""
    sync_url: str = ""
    sync_user: str = ""
    sync_password: str = ""
    sync_pdfs: str = ""
    epub_font_size: str = ""
    auto_lookup: str = ""


class WordAIIn(BaseModel):
    word: str
    context: str = ""


class TextAIIn(BaseModel):
    text: str
    context: str = ""
    mode: str = "explain_en"


class SolveQuestionIn(BaseModel):
    text: str
    context: str = ""
    doc_id: Optional[int] = None
    page: Optional[int] = None


class ResearchIn(BaseModel):
    doc_id: int
    mode: str = "reading_card"
    text: str = ""


class SummaryIn(BaseModel):
    doc_id: int
    scope: str = "doc"
    page: Optional[int] = None


class TranslateIn(BaseModel):
    doc_id: int
    page: Optional[int] = None


class VocabIn(BaseModel):
    word: str
    context: str = ""
    doc_id: Optional[int] = None
    page: Optional[int] = None


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=4)


class HighlightIn(BaseModel):
    doc_id: int
    page: int
    color: str = "yellow"
    text: str = ""
    rects: list[dict[str, float]] = []
    note: str = ""
    type: str = "highlight"


class HighlightPatch(BaseModel):
    color: Optional[str] = None
    note: Optional[str] = None
    type: Optional[str] = None


class NoteIn(BaseModel):
    doc_id: int
    page: int
    content: str
    title: str = ""


class NotePatch(BaseModel):
    content: Optional[str] = None
    title: Optional[str] = None


class WrongQuestionIn(BaseModel):
    question: str
    options: str = ""
    answer: str = ""
    explanation: str = ""
    question_type: str = ""
    source: str = ""
    doc_id: Optional[int] = None
    page: Optional[int] = None


class WrongQuestionPatch(BaseModel):
    question: Optional[str] = None
    options: Optional[str] = None
    answer: Optional[str] = None
    explanation: Optional[str] = None
    question_type: Optional[str] = None
    source: Optional[str] = None


class ArticleIn(BaseModel):
    title: str = ""
    text: str


# ---------------------------------------------------------------------------
# documents & pages
# ---------------------------------------------------------------------------
COVER_COLORS = ["#0071e3", "#5856d6", "#af52de", "#ff2d55", "#ff9500", "#34c759", "#00c7be"]


def _guess_title(pdf: pymupdf.Document) -> str:
    """Pick the largest horizontal-font line on page 1 as a title guess."""
    try:
        candidates: list[tuple[float, str, float]] = []
        for block in pdf[0].get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                direction = line.get("dir") or (1, 0)
                if abs(direction[0] - 1) > 0.05 or abs(direction[1]) > 0.05:
                    continue  # rotated margin stamps / watermarks
                pieces = []
                sizes = []
                for span in line.get("spans", []):
                    text = (span.get("text") or "").strip()
                    if text:
                        pieces.append(text)
                        sizes.append(float(span.get("size") or 0))
                line_text = re.sub(r"\s+", " ", " ".join(pieces)).strip()
                if not line_text or len(line_text) < 5 or not sizes:
                    continue
                if any(marker in line_text for marker in ("@", "arXiv", "http", "www.")):
                    continue
                size = max(sizes)
                if 12 <= size <= 48:
                    candidates.append((size, line_text, float(line.get("bbox", (0, 0))[1])))
        if not candidates:
            return ""
        largest = max(size for size, _, _ in candidates)
        best = [item for item in candidates if item[0] >= largest - 1.2]
        best.sort(key=lambda item: (item[2], -len(item[1])))
        return best[0][1][:300]
    except Exception:  # noqa: BLE001
        return ""


def _extract_pdf_metadata(pdf: pymupdf.Document, filename: str) -> dict[str, str]:
    meta = pdf.metadata or {}
    title = (meta.get("title") or "").strip()
    authors = (meta.get("author") or "").strip()
    created = meta.get("creationDate") or ""
    match = re.search(r"D:(\d{4})", created)
    year = match.group(1) if match else ""
    venue = ""
    first_text = pdf[0].get_text("text") if pdf.page_count else ""
    doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", first_text)
    doi = doi_match.group(0).rstrip(".,;") if doi_match else ""
    arxiv_match = re.search(r"arXiv:\s*(\d{2})(\d{2})\.(\d{4,5})", first_text)
    if arxiv_match:
        arxiv_id = f"{arxiv_match.group(1)}{arxiv_match.group(2)}.{arxiv_match.group(3)}"
        year = f"20{arxiv_match.group(1)}"
        venue = "arXiv"
        if not doi:
            doi = f"10.48550/arXiv.{arxiv_id}"
    if not title or title.lower() in {"untitled", "microsoft word", "document"}:
        title = _guess_title(pdf) or Path(filename).stem
    if len(title) < 5 or title.lower().endswith(".pdf"):
        title = Path(filename).stem
    abstract = ""
    abstract_match = re.search(r"(?is)\babstract\b\s*[—:\-]?\s*", first_text)
    if abstract_match:
        tail = first_text[abstract_match.end() :]
        end_match = re.search(
            r"(?i)\n\s*(?:1\.?\s*)?introduction\b|\n\s*keywords\b|\n\s*index terms\b",
            tail,
        )
        abstract = tail[: end_match.start()] if end_match else tail[:2200]
        abstract = re.sub(r"\s+", " ", abstract).strip()
    return {
        "title": title[:300],
        "authors": authors[:300],
        "year": year,
        "venue": venue,
        "doi": doi,
        "abstract": abstract[:3000],
        "cover_color": COVER_COLORS[
            int(hashlib.md5(title.encode("utf-8")).hexdigest(), 16) % len(COVER_COLORS)
        ],
    }


def _article_pdf(title: str, body: str, source_url: str = "", authors: str = "") -> bytes:
    doc = pymupdf.open()
    cjk = bool(re.search(r"[一-鿿]", f"{title} {body}"))
    font = "china-s" if cjk else "helv"
    page = doc.new_page(width=595, height=842)
    page.insert_textbox(
        pymupdf.Rect(50, 50, 545, 165), (title or "Untitled")[:400],
        fontsize=20, fontname=font, lineheight=1.25,
    )
    meta = "\n".join(part for part in [authors, source_url] if part)[:500]
    page.insert_textbox(
        pymupdf.Rect(50, 168, 545, 232), meta,
        fontsize=9, fontname=font, color=(0.42, 0.42, 0.45), lineheight=1.4,
    )
    chunks = _text_chunks(body or "（没有正文）", 1400)
    first = True
    for chunk in chunks:
        if first:
            rect = pymupdf.Rect(50, 242, 545, 800)
            first = False
        else:
            page = doc.new_page(width=595, height=842)
            rect = pymupdf.Rect(50, 50, 545, 800)
        result = page.insert_textbox(
            rect, chunk, fontsize=11, fontname=font, lineheight=1.55,
            color=(0.14, 0.14, 0.16),
        )
        if result < 0:
            # Extremely dense chunk: retry with a smaller slice on a fresh page.
            page = doc.new_page(width=595, height=842)
            page.insert_textbox(
                pymupdf.Rect(50, 50, 545, 800), chunk[:1000],
                fontsize=10, fontname=font, lineheight=1.5, color=(0.14, 0.14, 0.16),
            )
    data = doc.write()
    doc.close()
    return data


class WebImportIn(BaseModel):
    url: str
    title: str = ""


@app.post("/api/web/import")
async def import_web(payload: WebImportIn) -> dict[str, Any]:
    url = payload.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "请输入 http/https 网址。")
    try:
        async with httpx.AsyncClient(
            timeout=40, follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"},
        ) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"抓取网页失败：{exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(502, f"网页返回 {response.status_code}")
    try:
        import trafilatura
    except ImportError as exc:
        raise HTTPException(503, "缺少 trafilatura，请先安装依赖。") from exc
    text = trafilatura.extract(
        response.text, include_comments=False, include_tables=True, favor_precision=True
    )
    metadata = trafilatura.extract_metadata(response.text)
    if not text or len(text.strip()) < 200:
        raise HTTPException(400, "没有提取到足够正文，可能被登录/反爬拦住。")
    title = payload.title.strip() or (getattr(metadata, "title", "") if metadata else "") or url
    authors = getattr(metadata, "author", "") if metadata else ""
    pdf_bytes = _article_pdf(title, text, url, authors or "")
    safe_title = re.sub(r"[^\w一-鿿 .-]", "", title)[:100] or "web-article"
    result = _ingest_pdf_bytes(pdf_bytes, safe_title + ".pdf")
    with db() as conn:
        conn.execute(
            "UPDATE documents SET abstract=?, venue=COALESCE(NULLIF(venue,''), 'Web'), "
            "tags=COALESCE(NULLIF(tags,''), 'web') WHERE id=?",
            (text[:2500], result["id"]),
        )
    return result


def _epub_font_size() -> int:
    try:
        return max(11, min(24, int(get_setting("epub_font_size") or 15)))
    except (TypeError, ValueError):
        return 15


def _reflow_epub(source: Path, target: Path, font_size: Optional[int] = None) -> dict[str, str]:
    """Turn a reflowable EPUB into a clean, screen-sized PDF.

    PyMuPDF can re-layout EPUB at an arbitrary page width and font size. Doing
    it once at import keeps the reader, text layer, search, highlights and page
    numbers on the same code path as PDF, instead of a second half-reader.
    """
    epub = pymupdf.open(source)
    meta = dict(epub.metadata or {})
    if epub.is_reflowable:
        epub.layout(width=480, height=720, fontsize=font_size or _epub_font_size())
    toc = epub.get_toc(simple=True)
    temp = target.with_name(target.stem + ".tmp.pdf")
    epub.save(temp, garbage=4, deflate=True)
    epub.close()
    pdf = pymupdf.open(temp)
    if toc:
        pdf.set_toc(toc)
    try:
        pdf.set_metadata({
            "title": (meta.get("title") or "").strip(),
            "author": (meta.get("author") or "").strip(),
            "subject": (meta.get("subject") or "").strip(),
            "keywords": (meta.get("keywords") or "").strip(),
            "creator": "Folio",
            "producer": "Folio EPUB reflow",
        })
    except Exception:  # noqa: BLE001
        pass
    pdf.saveIncr()
    pdf.close()
    temp.replace(target)
    return {
        "title": (meta.get("title") or "").strip(),
        "author": (meta.get("author") or "").strip(),
        "subject": (meta.get("subject") or "").strip(),
        "keywords": (meta.get("keywords") or "").strip(),
    }


def _ingest_pdf_bytes(data: bytes, filename: str) -> dict[str, Any]:
    if not data:
        raise HTTPException(400, "文件为空。")
    digest = hashlib.sha256(data).hexdigest()[:20]
    is_epub = filename.lower().endswith(".epub")
    epub_meta: dict[str, str] = {}
    if is_epub:
        source = PDF_DIR / f"{digest}.epub"
        if not source.exists():
            source.write_bytes(data)
        target = PDF_DIR / f"{digest}-epub.pdf"
        epub_meta = _reflow_epub(source, target)
    else:
        source = None
        suffix = ".pdf"
        target = PDF_DIR / f"{digest}{suffix}"
        if not target.exists():
            target.write_bytes(data)
    try:
        pdf = pymupdf.open(target)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"无法打开文件：{exc}") from exc
    page_count = pdf.page_count
    metadata = _extract_pdf_metadata(pdf, filename or target.name)
    if is_epub:
        if epub_meta.get("title"):
            metadata["title"] = epub_meta["title"][:300]
        if epub_meta.get("author"):
            metadata["authors"] = epub_meta["author"][:300]
    with db() as conn:
        existing = conn.execute(
            "SELECT id FROM documents WHERE path=?", (str(target),)
        ).fetchone()
        if existing:
            pdf.close()
            return {"id": existing["id"], "title": metadata["title"], "existing": True}
        cursor = conn.execute(
            "INSERT INTO documents(title, authors, year, venue, doi, abstract, cover_color, "
            "filename, path, pages, created_at, updated_at, kind, source_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                metadata["title"],
                metadata["authors"],
                metadata["year"],
                metadata["venue"],
                metadata["doi"],
                metadata["abstract"],
                metadata["cover_color"],
                filename or target.name,
                str(target),
                page_count,
                now_iso(),
                now_iso(),
                "epub" if is_epub else "paper",
                str(source) if source else "",
            ),
        )
        doc_id = int(cursor.lastrowid)
        for index in range(page_count):
            text = pdf[index].get_text("text")
            conn.execute(
                "INSERT INTO pages(doc_id, page, text) VALUES (?, ?, ?)",
                (doc_id, index + 1, text),
            )
        conn.execute(
            "DELETE FROM sync_deletions WHERE entity_type='document' AND entity_key=?",
            (_doc_key(metadata["doi"], metadata["title"]),),
        )
    pdf.close()
    return {"id": doc_id, "title": metadata["title"], "pages": page_count, "existing": False}


class EpubLayoutIn(BaseModel):
    font_size: int = Field(default=15, ge=11, le=24)


@app.post("/api/documents")
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = file.filename or "Untitled.pdf"
    if not filename.lower().endswith((".pdf", ".epub")):
        raise HTTPException(400, "目前支持 PDF 和 EPUB。")
    return _ingest_pdf_bytes(await file.read(), filename)


@app.post("/api/documents/{doc_id}/epub/relayout")
def relayout_epub(doc_id: int, payload: EpubLayoutIn) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "文献不存在。")
    source = Path(row["source_path"]) if row["source_path"] else Path(row["path"])
    if row["kind"] == "epub" and row["source_path"]:
        target = Path(row["path"])
    elif source.suffix.lower() == ".epub":
        # Legacy import: the document still points at the original EPUB.
        target = source.with_name(source.stem + "-epub.pdf")
    else:
        raise HTTPException(400, "这篇不是可重排的 EPUB。")
    if not source.exists():
        raise HTTPException(400, "原始 EPUB 不在了，请重新导入。")
    try:
        _reflow_epub(source, target, payload.font_size)
    except OSError as exc:
        raise HTTPException(409, f"EPUB 正在被占用，稍后再试：{exc}") from exc
    pdf = pymupdf.open(target)
    page_count = pdf.page_count
    texts = [pdf[index].get_text("text") for index in range(page_count)]
    pdf.close()
    with db() as conn:
        conn.execute("DELETE FROM pages WHERE doc_id=?", (doc_id,))
        conn.executemany(
            "INSERT INTO pages(doc_id, page, text) VALUES (?, ?, ?)",
            [(doc_id, index + 1, text) for index, text in enumerate(texts)],
        )
        conn.execute(
            "UPDATE documents SET pages=?, path=?, source_path=?, kind='epub', updated_at=? "
            "WHERE id=?",
            (page_count, str(target), str(source), now_iso(), doc_id),
        )
    for cached in CACHE_DIR.glob(f"{doc_id}_*.png"):
        cached.unlink(missing_ok=True)
    set_setting("epub_font_size", str(payload.font_size))
    return get_document(doc_id)


@app.get("/api/documents")
def list_documents(
    q: str = "",
    collection_id: Optional[int] = None,
    favorite: Optional[int] = None,
    status: str = "",
    sort: str = "recent",
    author: str = "",
    venue: str = "",
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> list[dict[str, Any]]:
    sql = (
        "SELECT d.*, c.name AS collection_name, c.color AS collection_color "
        "FROM documents d LEFT JOIN collections c ON c.id = d.collection_id WHERE 1=1"
    )
    params: list[Any] = []
    if q.strip():
        like = f"%{q.strip()}%"
        sql += " AND (d.title LIKE ? OR d.authors LIKE ? OR d.tags LIKE ? OR d.venue LIKE ?)"
        params.extend([like, like, like, like])
    if collection_id is not None:
        sql += " AND d.collection_id = ?"
        params.append(collection_id)
    if favorite:
        sql += " AND d.favorite = 1"
    if status:
        sql += " AND d.status = ?"
        params.append(status)
    if author.strip():
        sql += " AND d.authors LIKE ?"
        params.append(f"%{author.strip()}%")
    if venue.strip():
        sql += " AND d.venue LIKE ?"
        params.append(f"%{venue.strip()}%")
    if year_from is not None:
        sql += " AND CAST(NULLIF(d.year, '') AS INTEGER) >= ?"
        params.append(year_from)
    if year_to is not None:
        sql += " AND CAST(NULLIF(d.year, '') AS INTEGER) <= ?"
        params.append(year_to)
    order = {
        "recent": "COALESCE(d.last_read_at, d.created_at) DESC, d.id DESC",
        "title": "d.title COLLATE NOCASE ASC",
        "year": "d.year DESC, d.id DESC",
        "pages": "d.pages DESC",
        "added": "d.id DESC",
    }.get(sort, "COALESCE(d.last_read_at, d.created_at) DESC, d.id DESC")
    sql += f" ORDER BY {order}"
    with db() as conn:
        rows = conn.execute(sql, params).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["progress"] = (
            round(min(1.0, (item.get("last_page") or 1) / max(1, item.get("pages") or 1)), 3)
        )
        result.append(item)
    return result


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: int) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            "SELECT d.*, c.name AS collection_name, c.color AS collection_color "
            "FROM documents d LEFT JOIN collections c ON c.id = d.collection_id "
            "WHERE d.id=?",
            (doc_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "文献不存在。")
        text_pages = conn.execute(
            "SELECT COUNT(*) FROM pages WHERE doc_id=? AND length(text)>20", (doc_id,)
        ).fetchone()[0]
    result = dict(row)
    result["text_pages"] = text_pages
    result["searchable"] = text_pages > 0
    result["progress"] = round(
        min(1.0, (result.get("last_page") or 1) / max(1, result.get("pages") or 1)), 3
    )
    if result.get("summary_json"):
        try:
            result["summary"] = json.loads(result["summary_json"])
        except json.JSONDecodeError:
            result["summary"] = None
    return result


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int) -> dict[str, str]:
    device = _sync_device()
    with db() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not row:
            raise HTTPException(404, "文献不存在。")
        conn.execute(
            "INSERT OR REPLACE INTO sync_deletions(entity_type, entity_key, deleted_at, device) "
            "VALUES ('document', ?, ?, ?)",
            (_doc_key(row["doi"], row["title"]), now_iso(), device),
        )
        conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    path = Path(row["path"])
    if path.exists() and path.parent == PDF_DIR:
        path.unlink(missing_ok=True)
    source_path = row["source_path"] if "source_path" in row.keys() else ""
    if source_path:
        source = Path(source_path)
        if source.exists() and source.parent == PDF_DIR:
            source.unlink(missing_ok=True)
    for cached in CACHE_DIR.glob(f"{doc_id}_*.png"):
        cached.unlink(missing_ok=True)
    return {"ok": "1"}


@app.post("/api/documents/{doc_id}/progress")
def save_progress(doc_id: int, page: int = 1, seconds: int = 0) -> dict[str, str]:
    seconds = max(0, min(3600, seconds))
    with db() as conn:
        conn.execute(
            "UPDATE documents SET last_page=?, last_read_at=?, "
            "reading_seconds=reading_seconds+? WHERE id=?",
            (page, now_iso(), seconds, doc_id),
        )
        if seconds > 0:
            conn.execute(
                "INSERT INTO reading_sessions(doc_id, seconds, created_at) VALUES (?, ?, ?)",
                (doc_id, seconds, now_iso()),
            )
    return {"ok": "1"}


def _document_path(doc_id: int) -> Path:
    with db() as conn:
        row = conn.execute("SELECT path FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "文献不存在。")
    path = Path(row["path"])
    if not path.exists():
        raise HTTPException(404, "PDF 文件丢失。")
    return path


_OCR_ENGINE = None
_OCR_LOCK = threading.Lock()


def _get_ocr_engine():
    global _OCR_ENGINE
    with _OCR_LOCK:
        if _OCR_ENGINE is None:
            from rapidocr_onnxruntime import RapidOCR

            _OCR_ENGINE = RapidOCR()
    return _OCR_ENGINE


def _ocr_page(doc_id: int, page: int, engine) -> tuple[list[tuple[float, float, float, float, str]], str]:
    path = _document_path(doc_id)
    pdf = pymupdf.open(path)
    if page < 1 or page > pdf.page_count:
        pdf.close()
        raise ValueError("页码超出范围")
    pix = pdf[page - 1].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    pdf.close()
    image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        image = image[:, :, :3]
    image = image[:, :, ::-1]  # RapidOCR expects BGR
    result, _ = engine(image)
    width, height = pix.width, pix.height
    words: list[tuple[float, float, float, float, str]] = []
    lines: list[str] = []
    for item in result or []:
        box, text, score = item
        if float(score) < 0.25:
            continue
        text = str(text).strip()
        if not text:
            continue
        xs = [float(point[0]) for point in box]
        ys = [float(point[1]) for point in box]
        x0, x1 = min(xs) / width, max(xs) / width
        y0, y1 = min(ys) / height, max(ys) / height
        lines.append(text)
        parts = text.split()
        if len(parts) > 1:
            total_chars = sum(len(part) for part in parts) or 1
            cursor = x0
            for part in parts:
                part_width = (x1 - x0) * len(part) / total_chars
                words.append((cursor, y0, part_width, y1 - y0, part))
                cursor += part_width
        else:
            words.append((x0, y0, x1 - x0, y1 - y0, text))
    return words, "\n".join(lines)


def _ocr_worker(doc_id: int, pages: list[int]) -> None:
    try:
        engine = _get_ocr_engine()
        total = len(pages)
        for index, page in enumerate(pages, 1):
            try:
                words, text = _ocr_page(doc_id, page, engine)
                with db() as conn:
                    conn.execute(
                        "DELETE FROM ocr_words WHERE doc_id=? AND page=?", (doc_id, page)
                    )
                    conn.executemany(
                        "INSERT OR REPLACE INTO ocr_words(doc_id, page, x, y, w, h, text) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [(doc_id, page, *word) for word in words],
                    )
                    conn.execute(
                        "UPDATE pages SET text=? WHERE doc_id=? AND page=?",
                        (text, doc_id, page),
                    )
                    conn.execute(
                        "UPDATE ocr_jobs SET status='running', total=?, done=?, updated_at=? "
                        "WHERE doc_id=?",
                        (total, index, now_iso(), doc_id),
                    )
            except Exception as exc:  # noqa: BLE001
                with db() as conn:
                    conn.execute(
                        "UPDATE ocr_jobs SET message=?, updated_at=? WHERE doc_id=?",
                        (f"第 {page} 页失败：{exc}", now_iso(), doc_id),
                    )
        with db() as conn:
            conn.execute(
                "UPDATE ocr_jobs SET status='done', done=?, updated_at=? WHERE doc_id=?",
                (total, now_iso(), doc_id),
            )
    except Exception as exc:  # noqa: BLE001
        with db() as conn:
            conn.execute(
                "UPDATE ocr_jobs SET status='error', message=?, updated_at=? WHERE doc_id=?",
                (str(exc), now_iso(), doc_id),
            )


@app.get("/api/documents/{doc_id}/pages/{page}/image")
def page_image(doc_id: int, page: int, scale: float = 1.6) -> FileResponse:
    scale = max(1.0, min(3.0, round(scale, 2)))
    cache = CACHE_DIR / f"{doc_id}_{page}_{scale}.png"
    if not cache.exists():
        path = _document_path(doc_id)
        pdf = pymupdf.open(path)
        if page < 1 or page > pdf.page_count:
            pdf.close()
            raise HTTPException(404, "页码超出范围。")
        pix = pdf[page - 1].get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        pix.save(cache)
        pdf.close()
    return FileResponse(cache, media_type="image/png", headers={"Cache-Control": "max-age=86400"})


@app.get("/api/documents/{doc_id}/pages/{page}/layout")
def page_layout(doc_id: int, page: int, scale: float = 1.6) -> dict[str, Any]:
    scale = max(1.0, min(3.0, round(scale, 2)))
    path = _document_path(doc_id)
    pdf = pymupdf.open(path)
    if page < 1 or page > pdf.page_count:
        pdf.close()
        raise HTTPException(404, "页码超出范围。")
    page_obj = pdf[page - 1]
    words = [
        {
            "x": round(w[0] * scale, 2),
            "y": round(w[1] * scale, 2),
            "w": round((w[2] - w[0]) * scale, 2),
            "h": round((w[3] - w[1]) * scale, 2),
            "text": w[4],
        }
        for w in page_obj.get_text("words")
    ]
    if not words:
        with db() as conn:
            ocr_rows = conn.execute(
                "SELECT x, y, w, h, text FROM ocr_words WHERE doc_id=? AND page=? ORDER BY y, x",
                (doc_id, page),
            ).fetchall()
        words = [
            {
                "x": round(row["x"] * page_obj.rect.width * scale, 2),
                "y": round(row["y"] * page_obj.rect.height * scale, 2),
                "w": round(row["w"] * page_obj.rect.width * scale, 2),
                "h": round(row["h"] * page_obj.rect.height * scale, 2),
                "text": row["text"],
            }
            for row in ocr_rows
        ]
    result = {
        "page": page,
        "scale": scale,
        "width": round(page_obj.rect.width * scale, 2),
        "height": round(page_obj.rect.height * scale, 2),
        "words": words,
    }
    pdf.close()
    return result


@app.get("/api/documents/{doc_id}/pages/{page}/text")
def page_text(doc_id: int, page: int) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            "SELECT text FROM pages WHERE doc_id=? AND page=?", (doc_id, page)
        ).fetchone()
    if not row:
        raise HTTPException(404, "这一页没有文本。")
    return {"page": page, "text": row["text"]}


class OCRIn(BaseModel):
    pages: Optional[list[int]] = None
    force: bool = False


def _ocr_status(doc_id: int) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT * FROM ocr_jobs WHERE doc_id=?", (doc_id,)).fetchone()
        text_pages = conn.execute(
            "SELECT COUNT(*) FROM pages WHERE doc_id=? AND length(text)>20", (doc_id,)
        ).fetchone()[0]
    if not row:
        return {"status": "idle", "total": 0, "done": 0, "message": "", "text_pages": text_pages}
    return {
        "status": row["status"],
        "total": row["total"],
        "done": row["done"],
        "message": row["message"],
        "text_pages": text_pages,
    }


@app.get("/api/documents/{doc_id}/ocr/status")
def ocr_status(doc_id: int) -> dict[str, Any]:
    return _ocr_status(doc_id)


@app.post("/api/documents/{doc_id}/ocr")
def start_ocr(doc_id: int, payload: OCRIn) -> dict[str, Any]:
    _document_path(doc_id)
    with db() as conn:
        existing = conn.execute(
            "SELECT status FROM ocr_jobs WHERE doc_id=?", (doc_id,)
        ).fetchone()
        if existing and existing["status"] in ("queued", "running") and not payload.pages:
            return _ocr_status(doc_id)
        rows = conn.execute(
            "SELECT page, text FROM pages WHERE doc_id=? ORDER BY page", (doc_id,)
        ).fetchall()
        total_pages = len(rows)
        if payload.pages:
            pages = sorted({page for page in payload.pages if 1 <= page <= total_pages})
        else:
            pages = [
                row["page"]
                for row in rows
                if payload.force or len((row["text"] or "").strip()) < 20
            ]
        if not pages:
            conn.execute(
                "INSERT OR REPLACE INTO ocr_jobs(doc_id, status, total, done, message, updated_at) "
                "VALUES (?, 'done', 0, 0, '所有页面都已有文字', ?)",
                (doc_id, now_iso()),
            )
            return _ocr_status(doc_id)
        conn.execute(
            "INSERT OR REPLACE INTO ocr_jobs(doc_id, status, total, done, message, updated_at) "
            "VALUES (?, 'queued', ?, 0, '', ?)",
            (doc_id, len(pages), now_iso()),
        )
    thread = threading.Thread(target=_ocr_worker, args=(doc_id, pages), daemon=True)
    thread.start()
    return _ocr_status(doc_id)


@app.get("/api/documents/{doc_id}/text")
def document_text(doc_id: int) -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute(
            "SELECT page, text FROM pages WHERE doc_id=? ORDER BY page", (doc_id,)
        ).fetchall()
    return {
        "pages": [{"page": row["page"], "text": row["text"]} for row in rows],
        "text": "\n\n".join(row["text"] for row in rows),
    }


@app.get("/api/documents/{doc_id}/cover")
def document_cover(doc_id: int) -> FileResponse:
    cache = CACHE_DIR / f"{doc_id}_cover.png"
    if not cache.exists():
        path = _document_path(doc_id)
        pdf = pymupdf.open(path)
        page = pdf[0]
        scale = max(0.25, min(1.0, 340 / max(1, page.rect.width)))
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        pix.save(cache)
        pdf.close()
    return FileResponse(cache, media_type="image/png", headers={"Cache-Control": "max-age=86400"})


@app.get("/api/documents/{doc_id}/outline")
def document_outline(doc_id: int) -> list[dict[str, Any]]:
    path = _document_path(doc_id)
    pdf = pymupdf.open(path)
    toc = pdf.get_toc(simple=True)
    if not toc:
        for index in range(min(12, pdf.page_count)):
            for line in pdf[index].get_text("text").split("\n"):
                text = line.strip()
                if re.match(r"^\d+(\.\d+)*\s+[A-Z][A-Za-z].{2,70}$", text):
                    toc.append([1, text, index + 1])
    pdf.close()
    return [
        {"level": int(level), "title": str(title), "page": int(page)}
        for level, title, page in toc
        if page and page > 0
    ]


def _ocr_search_page(doc_id: int, page: int, query: str) -> Optional[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT x, y, w, h, text FROM ocr_words WHERE doc_id=? AND page=? ORDER BY y, x",
            (doc_id, page),
        ).fetchall()
    if not rows:
        return None
    tokens = [token.lower() for token in re.findall(r"[A-Za-z0-9']+", query)]
    if not tokens:
        return None
    words = [dict(row) for row in rows]
    matches: list[dict[str, float]] = []
    if len(tokens) == 1:
        token = tokens[0]
        for word in words:
            if token in (word["text"] or "").lower():
                matches.append(word)
    else:
        for start in range(0, len(words) - len(tokens) + 1):
            chunk = words[start : start + len(tokens)]
            if all(
                tokens[index] in (chunk[index]["text"] or "").lower()
                for index in range(len(tokens))
            ):
                matches.extend(chunk)
                break
    if not matches:
        return None
    full_text = " ".join(word["text"] for word in words)
    position = full_text.lower().find(query.lower())
    snippet = full_text[max(0, position - 70) : position + len(query) + 90] if position >= 0 else full_text[:160]
    return {
        "page": page,
        "snippet": re.sub(r"\s+", " ", snippet).strip(),
        "rects": [
            {
                "x": round(word["x"], 5),
                "y": round(word["y"], 5),
                "w": round(word["w"], 5),
                "h": round(word["h"], 5),
            }
            for word in matches
        ],
    }


@app.get("/api/documents/{doc_id}/search")
def search_document(doc_id: int, q: str = "") -> dict[str, Any]:
    query = q.strip()
    if len(query) < 2:
        return {"hits": [], "query": query}
    path = _document_path(doc_id)
    pdf = pymupdf.open(path)
    hits: list[dict[str, Any]] = []
    for index in range(pdf.page_count):
        page = pdf[index]
        rects = page.search_for(query)
        if not rects:
            ocr_hit = _ocr_search_page(doc_id, index + 1, query)
            if ocr_hit:
                hits.append(ocr_hit)
                if len(hits) >= 40:
                    break
            continue
        width, height = page.rect.width, page.rect.height
        text = page.get_text("text")
        position = text.lower().find(query.lower())
        if position >= 0:
            snippet = text[max(0, position - 70) : position + len(query) + 90]
        else:
            snippet = text[:160]
        hits.append(
            {
                "page": index + 1,
                "snippet": re.sub(r"\s+", " ", snippet).strip(),
                "rects": [
                    {
                        "x": round(r.x0 / width, 5),
                        "y": round(r.y0 / height, 5),
                        "w": round((r.x1 - r.x0) / width, 5),
                        "h": round((r.y1 - r.y0) / height, 5),
                    }
                    for r in rects
                ],
            }
        )
        if len(hits) >= 40:
            break
    pdf.close()
    return {"hits": hits, "query": query}


class DocumentPatch(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[str] = None
    doi: Optional[str] = None
    venue: Optional[str] = None
    abstract: Optional[str] = None
    tags: Optional[str] = None
    collection_id: Optional[int] = None
    favorite: Optional[int] = None
    status: Optional[str] = None
    rating: Optional[int] = None


@app.patch("/api/documents/{doc_id}")
def update_document(doc_id: int, payload: DocumentPatch) -> dict[str, Any]:
    values = payload.model_dump(exclude_unset=True)
    if values:
        values["updated_at"] = now_iso()
        assignments = ", ".join(f"{key}=?" for key in values)
        with db() as conn:
            conn.execute(
                f"UPDATE documents SET {assignments} WHERE id=?",
                [*values.values(), doc_id],
            )
    return get_document(doc_id)


class CollectionIn(BaseModel):
    name: str
    color: str = "#0071e3"


@app.get("/api/collections")
def list_collections() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT c.*, COUNT(d.id) AS count FROM collections c "
            "LEFT JOIN documents d ON d.collection_id = c.id "
            "GROUP BY c.id ORDER BY c.id"
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/collections")
def create_collection(payload: CollectionIn) -> dict[str, Any]:
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "分类名不能为空。")
    with db() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO collections(name, color, created_at) VALUES (?, ?, ?)",
                (name, payload.color, now_iso()),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(400, "这个分类已经存在。") from exc
        row = conn.execute(
            "SELECT * FROM collections WHERE id=?", (cursor.lastrowid,)
        ).fetchone()
    return dict(row)


@app.patch("/api/collections/{collection_id}")
def update_collection(collection_id: int, payload: CollectionIn) -> dict[str, Any]:
    with db() as conn:
        conn.execute(
            "UPDATE collections SET name=?, color=? WHERE id=?",
            (payload.name.strip(), payload.color, collection_id),
        )
        row = conn.execute(
            "SELECT * FROM collections WHERE id=?", (collection_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "分类不存在。")
    return dict(row)


@app.delete("/api/collections/{collection_id}")
def delete_collection(collection_id: int) -> dict[str, str]:
    with db() as conn:
        conn.execute(
            "UPDATE documents SET collection_id=NULL WHERE collection_id=?",
            (collection_id,),
        )
        conn.execute("DELETE FROM collections WHERE id=?", (collection_id,))
    return {"ok": "1"}


@app.get("/api/documents/{doc_id}/cite")
def cite_document(doc_id: int, fmt: str = "bibtex") -> dict[str, Any]:
    with db() as conn:
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not doc:
        raise HTTPException(404, "文献不存在。")
    authors = doc["authors"] or ""
    first_part = authors.split(",")[0].strip()
    surname = first_part.split()[-1] if first_part.split() else "folio"
    first = re.sub(r"[^A-Za-z]", "", surname)
    key = f"{first or 'folio'}{doc['year'] or ''}"
    if fmt == "ris":
        lines = [
            "TY  - JOUR",
            f"TI  - {doc['title']}",
            f"AU  - {authors}",
            f"PY  - {doc['year']}",
            f"JO  - {doc['venue']}",
            f"DO  - {doc['doi']}",
            "ER  - ",
        ]
        text = "\n".join(line for line in lines if line.split("  - ", 1)[-1].strip())
    else:
        text = (
            f"@article{{{key},\n"
            f"  title = {{{doc['title']}}},\n"
            f"  author = {{{authors}}},\n"
            f"  year = {{{doc['year']}}},\n"
            f"  journal = {{{doc['venue']}}},\n"
            f"  doi = {{{doc['doi']}}}\n"
            f"}}"
        )
    return {"text": text, "format": fmt}


@app.post("/api/documents/{doc_id}/enrich")
async def enrich_document(doc_id: int) -> dict[str, Any]:
    with db() as conn:
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not doc:
        raise HTTPException(404, "文献不存在。")
    doi = doc["doi"]
    if not doi:
        with db() as conn:
            rows = conn.execute(
                "SELECT text FROM pages WHERE doc_id=? ORDER BY page LIMIT 3", (doc_id,)
            ).fetchall()
        text = " ".join(row["text"] for row in rows)
        match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text)
        doi = match.group(0).rstrip(".,;") if match else ""
    headers = {"User-Agent": "Folio/0.9 (mailto:local@example.com)"}
    arxiv_id = ""
    if doi.startswith("10.48550/arXiv."):
        arxiv_id = doi.split("arXiv.")[-1]
    if not arxiv_id:
        with db() as conn:
            rows = conn.execute(
                "SELECT text FROM pages WHERE doc_id=? ORDER BY page LIMIT 3", (doc_id,)
            ).fetchall()
        match = re.search(r"arXiv:\s*(\d{4}\.\d{4,5})", " ".join(row["text"] for row in rows))
        if match:
            arxiv_id = match.group(1)

    if arxiv_id:
        try:
            async with httpx.AsyncClient(timeout=25, headers=headers) as client:
                response = await client.get(
                    "https://export.arxiv.org/api/query", params={"id_list": arxiv_id}
                )
            root = ET.fromstring(response.text)
            ns = {"a": "http://www.w3.org/2005/Atom"}
            entry = root.find("a:entry", ns)
            if entry is None:
                raise HTTPException(404, "arXiv 没有找到这篇论文。")
            title = re.sub(r"\s+", " ", entry.findtext("a:title", "", ns)).strip()
            abstract = re.sub(r"\s+", " ", entry.findtext("a:summary", "", ns)).strip()
            authors = ", ".join(
                author.findtext("a:name", "", ns)
                for author in entry.findall("a:author", ns)
            )
            published = entry.findtext("a:published", "", ns)
            year = published[:4] if published else doc["year"]
            with db() as conn:
                conn.execute(
                    "UPDATE documents SET title=?, authors=?, year=?, venue='arXiv', "
                    "doi=?, abstract=? WHERE id=?",
                    (title, authors, year, f"10.48550/arXiv.{arxiv_id}", abstract, doc_id),
                )
            return get_document(doc_id)
        except (httpx.HTTPError, ET.ParseError) as exc:
            raise HTTPException(502, f"连接 arXiv 失败：{exc}") from exc

    try:
        async with httpx.AsyncClient(timeout=25, headers=headers) as client:
            if doi:
                response = await client.get(f"https://api.crossref.org/works/{doi}")
                message = response.json()["message"]
            else:
                response = await client.get(
                    "https://api.crossref.org/works",
                    params={"query.bibliographic": doc["title"], "rows": 1},
                )
                items = response.json()["message"].get("items", [])
                if not items:
                    raise HTTPException(404, "Crossref 没有找到匹配的文献。")
                message = items[0]
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"连接 Crossref 失败：{exc}") from exc
    authors = ", ".join(
        f"{item.get('given', '')} {item.get('family', '')}".strip()
        for item in message.get("author", [])
    )
    published = message.get("published-print") or message.get("published-online") or {}
    year = ""
    if published.get("date-parts"):
        year = str(published["date-parts"][0][0])
    abstract = re.sub(r"<[^>]+>", "", message.get("abstract", "") or "").strip()
    title = (message.get("title") or [doc["title"]])[0]
    venue = (message.get("container-title") or [doc["venue"] or ""])[0]
    with db() as conn:
        conn.execute(
            "UPDATE documents SET title=?, authors=?, year=?, venue=?, doi=?, abstract=?, "
            "updated_at=? WHERE id=?",
            (title, authors, year, venue, message.get("DOI", doi), abstract, now_iso(), doc_id),
        )
    return get_document(doc_id)


def _yaml(value: str) -> str:
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"')


def _obsidian_callout(kind: str, title: str, body: str) -> list[str]:
    lines = [f"> [!{kind}] {title}"] if title else [f"> [!{kind}]"]
    for line in (body or "").splitlines() or [""]:
        lines.append(f"> {line}")
    lines.append("")
    return lines


def _md_meta_line(doc: dict[str, Any]) -> str:
    return " · ".join(
        str(part) for part in [doc.get("authors"), doc.get("year"), doc.get("venue")] if part
    )


def _summary_lines(doc: dict[str, Any], heading: str = "## AI 总结") -> list[str]:
    if not doc.get("summary"):
        return []
    lines = ["", heading, ""]
    for key, label in [
        ("tldr", "TL;DR"),
        ("problem", "研究问题"),
        ("method", "方法"),
        ("results", "结果"),
    ]:
        if doc["summary"].get(key):
            lines.append(f"**{label}**：{doc['summary'][key]}")
    return lines


def _indent_block(text: str, prefix: str = "  ") -> list[str]:
    return [f"{prefix}{line}" if line else prefix.rstrip() for line in str(text or "").splitlines()]


def _note_label(item: sqlite3.Row) -> str:
    return item["title"] or f"第 {item['page']} 页"


@app.get("/api/documents/{doc_id}/export.md")
def export_markdown(doc_id: int, template: str = "full") -> Response:
    doc = get_document(doc_id)
    with db() as conn:
        highlights = conn.execute(
            "SELECT * FROM highlights WHERE doc_id=? ORDER BY page, id", (doc_id,)
        ).fetchall()
        notes = conn.execute(
            "SELECT * FROM notes WHERE doc_id=? ORDER BY page, id", (doc_id,)
        ).fetchall()
    doc_tags = [tag.strip() for tag in (doc.get("tags") or "").replace("，", ",").split(",") if tag.strip()]
    meta = _md_meta_line(doc)
    lines: list[str] = []

    if template == "logseq":
        lines += [
            f"title:: {doc['title']}",
            f"authors:: {doc.get('authors') or ''}",
            f"year:: {doc.get('year') or ''}",
            f"venue:: {doc.get('venue') or ''}",
            f"doi:: {doc.get('doi') or ''}",
            "tags:: folio, paper" + (", " + ", ".join(doc_tags) if doc_tags else ""),
            "",
        ]
        if doc.get("abstract"):
            lines += ["- ## 摘要", *_indent_block(doc["abstract"])]
        if doc.get("summary"):
            lines += ["- ## AI 总结"]
            for key, label in [
                ("tldr", "TL;DR"),
                ("problem", "研究问题"),
                ("method", "方法"),
                ("results", "结果"),
            ]:
                if doc["summary"].get(key):
                    lines += [f"  - **{label}**：{doc['summary'][key]}"]
        if highlights:
            lines += ["- ## 高亮"]
            for item in highlights:
                lines += [f"  - > {item['text']}", f"    - 第 {item['page']} 页"]
                if item["note"]:
                    lines += _indent_block(item["note"], "    - ")
        if notes:
            lines += ["- ## 笔记"]
            for item in notes:
                lines += [f"  - **{_note_label(item)}**"]
                lines += _indent_block(item["content"], "    ")
    elif template == "notion":
        lines += [f"# {doc['title']}", ""]
        meta_lines: list[str] = []
        if meta:
            meta_lines += [meta, ""]
        for label, value in [
            ("DOI", doc.get("doi")), ("分类", doc.get("collection")),
            ("标签", " ".join(f"#{tag}" for tag in doc_tags)),
        ]:
            if value:
                meta_lines += [f"**{label}**：{value}", ""]
        if meta_lines:
            lines += meta_lines + ["---", ""]
        if doc.get("abstract"):
            lines += ["## 摘要", "", doc["abstract"], ""]
        lines += _summary_lines(doc)
        if highlights:
            lines += ["", "## 高亮", ""]
            for item in highlights:
                lines += [f"> {item['text']}", f"> — 第 {item['page']} 页", ""]
                if item["note"]:
                    lines += [f"**备注**：{item['note']}", ""]
        if notes:
            lines += ["## 笔记", ""]
            for item in notes:
                lines += [f"### {_note_label(item)}", item["content"], ""]
    elif template == "obsidian":
        lines += [
            "---",
            f'title: "{_yaml(doc["title"])}"',
            f'authors: "{_yaml(doc.get("authors") or "")}"',
            f'year: "{_yaml(doc.get("year") or "")}"',
            f'venue: "{_yaml(doc.get("venue") or "")}"',
            f'doi: "{_yaml(doc.get("doi") or "")}"',
            f'tags: [folio, paper{", " + ", ".join(doc_tags) if doc_tags else ""}]',
            f'updated: "{now_iso()}"',
            "---",
            "",
            f"# {doc['title']}",
            "",
        ]
        if doc.get("abstract"):
            lines += _obsidian_callout("abstract", "摘要", doc["abstract"])
        if doc.get("summary"):
            lines += ["", "## AI 总结", ""]
            for key, label in [
                ("tldr", "TL;DR"), ("problem", "研究问题"),
                ("method", "方法"), ("results", "结果"),
            ]:
                if doc["summary"].get(key):
                    lines.append(f"**{label}**：{doc['summary'][key]}")
        if highlights:
            lines += ["## 高亮", ""]
            for item in highlights:
                lines += _obsidian_callout(
                    "quote", f"第 {item['page']} 页", item["text"]
                    + (f"\n\n**备注**：{item['note']}" if item["note"] else "")
                )
        if notes:
            lines += ["## 笔记", ""]
            for item in notes:
                lines += [f"### {_note_label(item)}", item["content"], ""]
    elif template == "highlights":
        lines += [f"# {doc['title']}", "", meta, ""]
        for item in highlights:
            lines += [f"> {item['text']}", f"> — 第 {item['page']} 页", ""]
            if item["note"]:
                lines += [f"**备注**：{item['note']}", ""]
    else:
        lines += [f"# {doc['title']}", "", meta, ""]
        if doc.get("doi"):
            lines.append(f"DOI: {doc['doi']}")
        if doc.get("abstract"):
            lines += ["", "## 摘要", "", doc["abstract"]]
        lines += _summary_lines(doc)
        if highlights:
            lines += ["", "## 高亮", ""]
            for item in highlights:
                lines += [f"### 第 {item['page']} 页", f"> {item['text']}"]
                if item["note"]:
                    lines += ["", item["note"]]
                lines.append("")
        if notes:
            lines += ["## 笔记", ""]
            for item in notes:
                lines += [f"### {_note_label(item)}", item["content"], ""]

    content = "\n".join(lines)
    suffix = {"obsidian": "-obsidian", "highlights": "-highlights", "notion": "-notion", "logseq": "-logseq"}.get(template, "")
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=folio-{doc_id}{suffix}.md"
        },
    )


@app.get("/api/export/highlights.md")
def export_all_highlights(template: str = "obsidian") -> Response:
    with db() as conn:
        rows = conn.execute(
            "SELECT h.*, d.title AS doc_title, d.authors AS doc_authors, d.year AS doc_year "
            "FROM highlights h JOIN documents d ON d.id=h.doc_id "
            "ORDER BY d.title, h.page, h.id"
        ).fetchall()
    lines = ["# Folio 高亮汇总", "", f"导出时间：{now_iso()}", ""]
    current = None
    for row in rows:
        if row["doc_title"] != current:
            current = row["doc_title"]
            if template == "logseq":
                lines += ["", f"- ## {current}"]
            else:
                lines += ["", f"## {current}", ""]
            meta = " · ".join(part for part in [row["doc_authors"], row["doc_year"]] if part)
            if meta:
                lines += [meta, ""] if template != "logseq" else [f"  - {meta}"]
        if template == "logseq":
            lines += [f"  - > {row['text']}", f"    - 第 {row['page']} 页"]
            if row["note"]:
                lines += _indent_block(row["note"], "    - ")
        elif template == "notion":
            lines += [f"> {row['text']}", f"> — 第 {row['page']} 页", ""]
            if row["note"]:
                lines += [f"**备注**：{row['note']}", ""]
        else:
            lines += _obsidian_callout(
                "quote", f"第 {row['page']} 页", row["text"]
                + (f"\n\n**备注**：{row['note']}" if row["note"] else "")
            )
    return Response(
        content="\n".join(lines),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="folio-highlights.md"'},
    )


# ---------------------------------------------------------------------------
# dictionary & CET
# ---------------------------------------------------------------------------
@app.get("/api/dict/{word:path}")
def dictionary(word: str) -> dict[str, Any]:
    return lookup_word(word)


class CETIn(BaseModel):
    text: str


@app.post("/api/cet/analyze")
def cet_analyze(payload: CETIn) -> dict[str, Any]:
    tokens = re.findall(r"[A-Za-z][A-Za-z'’-]*", payload.text)
    counts: dict[str, int] = {}
    for token in tokens:
        key = token.lower()
        counts[key] = counts.get(key, 0) + 1
    tags: dict[str, str] = {}
    if ECDICT_PATH.exists():
        conn = sqlite3.connect(ECDICT_PATH, timeout=10)
        try:
            keys = list(counts.keys())
            for start in range(0, len(keys), 500):
                chunk = keys[start : start + 500]
                placeholders = ",".join("?" for _ in chunk)
                rows = conn.execute(
                    f"SELECT word, tag FROM ecdict WHERE word COLLATE NOCASE IN ({placeholders})",
                    chunk,
                ).fetchall()
                for row in rows:
                    tags[row[0].lower()] = row[1] or ""
        finally:
            conn.close()
    return {
        "tags": tags,
        "counts": counts,
        "total": len(tokens),
        "unique": len(counts),
        "cet4": sum(1 for w in counts if "cet4" in tags.get(w, "").split()),
        "cet6": sum(1 for w in counts if "cet6" in tags.get(w, "").split()),
    }


# ---------------------------------------------------------------------------
# AI endpoints
# ---------------------------------------------------------------------------
@app.get("/api/settings")
def read_settings() -> dict[str, Any]:
    return {
        "provider": get_setting("provider"),
        "base_url": get_setting("base_url"),
        "model": get_setting("model"),
        "has_key": bool(get_setting("api_key")),
        "has_s2_key": bool(get_setting("s2_api_key")),
        "zotero_url": get_setting("zotero_url"),
        "sync_url": get_setting("sync_url"),
        "sync_user": get_setting("sync_user"),
        "has_sync_password": bool(get_setting("sync_password")),
        "sync_pdfs": get_setting("sync_pdfs") == "1",
        "epub_font_size": get_setting("epub_font_size") or "15",
        "auto_lookup": get_setting("auto_lookup") != "0",
        "last_sync": get_setting("last_sync"),
    }


class StoragePathIn(BaseModel):
    path: str


def _storage_status() -> dict[str, Any]:
    return {
        "configured": bool(STORAGE_CONFIGURED),
        "data_dir": str(DATA_DIR),
        "default_dir": str(DATA_DIR if not STORAGE_CONFIGURED else DEFAULT_DATA_DIR),
        "database": str(DB_PATH),
    }


def _write_storage_pointer(path: Path) -> None:
    payload = json.dumps(
        {"data_dir": str(path), "configured_at": datetime.now(timezone.utc).isoformat()},
        ensure_ascii=False,
    )
    errors = []
    for pointer in _storage_pointer_candidates():
        try:
            pointer.parent.mkdir(parents=True, exist_ok=True)
            pointer.write_text(payload, encoding="utf-8")
            return
        except OSError as exc:
            errors.append(str(exc))
    raise HTTPException(500, "无法保存资料库位置：" + "；".join(errors))


def _copy_storage(source: Path, target: Path) -> list[str]:
    copied: list[str] = []
    for name in ("readmate.db", "ecdict.db", "ecdict.csv"):
        src = source / name
        dst = target / name
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            copied.append(name)
    for name in ("pdfs", "exports"):
        src = source / name
        if src.exists():
            shutil.copytree(src, target / name, dirs_exist_ok=True)
            copied.append(name)
    return copied


@app.get("/api/storage/status")
def storage_status() -> dict[str, Any]:
    return _storage_status()


@app.post("/api/storage/pick")
def storage_pick() -> dict[str, str]:
    if os.name != "nt":
        raise HTTPException(400, "当前系统请直接输入文件夹路径。")
    script = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = "选择 Folio 资料库文件夹"
$dialog.ShowNewFolderButton = $true
$result = $dialog.ShowDialog()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $dialog.SelectedPath }
"""
    try:
        flags = 0x08000000 if os.name == "nt" else 0
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=180, creationflags=flags,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(500, f"无法打开文件夹选择窗口：{exc}") from exc
    lines = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
    return {"path": lines[-1] if lines else ""}


@app.post("/api/storage/set")
def storage_set(payload: StoragePathIn) -> dict[str, Any]:
    global DATA_DIR, PDF_DIR, CACHE_DIR, EXPORT_DIR, DB_PATH, ECDICT_PATH, STORAGE_CONFIGURED
    raw = (payload.path or "").strip().strip('"')
    if not raw:
        raise HTTPException(400, "请选择一个文件夹。")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        raise HTTPException(400, "请填写完整的绝对路径，例如 D:/FolioData。")
    target = candidate.resolve()
    source = DATA_DIR.resolve()
    if target != source and (target in source.parents or source in target.parents):
        raise HTTPException(400, "请选择当前资料库之外的文件夹。")
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".folio_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise HTTPException(400, f"这个文件夹不可写：{exc}") from exc

    existing_db = (target / "readmate.db").exists()
    copied = _copy_storage(source, target) if target != source else []
    DATA_DIR = target
    PDF_DIR = target / "pdfs"
    CACHE_DIR = target / "cache"
    EXPORT_DIR = target / "exports"
    DB_PATH = target / "readmate.db"
    ECDICT_PATH = target / "ecdict.db"
    for folder in (DATA_DIR, PDF_DIR, CACHE_DIR, EXPORT_DIR):
        folder.mkdir(parents=True, exist_ok=True)
    if not ECDICT_PATH.exists():
        seed = RESOURCE_DIR / "seed" / "ecdict.db"
        if seed.exists():
            shutil.copy2(seed, ECDICT_PATH)
        elif (source / "ecdict.db").exists():
            shutil.copy2(source / "ecdict.db", ECDICT_PATH)
    init_db()
    _write_storage_pointer(target)
    STORAGE_CONFIGURED = True
    return {
        "configured": True,
        "data_dir": str(DATA_DIR),
        "database": str(DB_PATH),
        "copied": copied,
        "existing": existing_db,
    }


@app.post("/api/settings")
def write_settings(payload: SettingsIn) -> dict[str, Any]:
    set_setting("provider", payload.provider or "custom")
    if payload.base_url:
        set_setting("base_url", payload.base_url.strip())
    if payload.model:
        set_setting("model", payload.model.strip())
    if payload.api_key:
        set_setting("api_key", payload.api_key.strip())
    if payload.s2_api_key:
        set_setting("s2_api_key", payload.s2_api_key.strip())
    if payload.zotero_url:
        set_setting("zotero_url", payload.zotero_url.strip())
    if payload.sync_url:
        set_setting("sync_url", payload.sync_url.strip())
    if payload.sync_user:
        set_setting("sync_user", payload.sync_user.strip())
    if payload.sync_password:
        set_setting("sync_password", payload.sync_password.strip())
    if payload.sync_pdfs:
        set_setting("sync_pdfs", "1" if payload.sync_pdfs == "1" else "0")
    if payload.epub_font_size:
        try:
            size = max(11, min(24, int(payload.epub_font_size)))
        except ValueError:
            size = 15
        set_setting("epub_font_size", str(size))
    if payload.auto_lookup:
        set_setting("auto_lookup", "1" if payload.auto_lookup == "1" else "0")
    return read_settings()


@app.post("/api/settings/test")
async def test_settings() -> dict[str, str]:
    answer = await ai_chat(
        [{"role": "user", "content": "只回复两个字：正常"}], max_tokens=20
    )
    return {"ok": "1", "answer": answer.strip()[:50]}


@app.post("/api/ai/word")
async def ai_word(payload: WordAIIn) -> dict[str, str]:
    word = _clean_word(payload.word) or payload.word
    prompt = f"""学生在读英文文献时选中了单词 “{word}”。
上下文（可能为空）：{payload.context[:1200] or "无"}

请严格按下面六节输出，使用 Markdown：
## 核心释义
词性 + 中文释义 + 一句英文释义。
## 常见搭配
3–5 个 collocation / 短语动词 / 习语，格式：**搭配** — 中文。
## 词根与派生
词根词缀、派生词、词形变化。
## 近义辨析
2–3 个近义词的区别。
## 例句
一个学术语境、一个四六级语境，均附中文。
## 考点提示
如果这个词是四六级高频词或本文专业术语，指出考点或领域义。"""
    content = await ai_chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        max_tokens=1400,
    )
    return {"markdown": content}


@app.post("/api/ai/text")
async def ai_text(payload: TextAIIn) -> dict[str, str]:
    text = payload.text.strip()
    if not text:
        raise HTTPException(400, "没有选中文本。")
    context = payload.context[:1500]
    prompts = {
        "translate": f"""把下面的英文翻译成准确、通顺的中文。专业术语保留英文并用括号注明。
上下文：{context}

原文：
{text}""",
        "explain_en": f"""Explain the following sentence to a Chinese undergraduate in English.
Cover: (1) sentence structure and main clause, (2) grammar points that trip learners up,
(3) a plain-English paraphrase, (4) key academic vocabulary. Then give a one-sentence
Chinese summary at the end.
Context: {context}

Sentence:
{text}""",
        "simplify": f"""把下面这段英文改写成 CEFR B1 水平的简单英语，保留原意和关键术语；
然后用中文解释它在说什么。上下文：{context}

原文：
{text}""",
        "grammar": f"""拆解下面英文长难句的语法：主干、从句、修饰关系、指代关系，并给出中文翻译。
上下文：{context}

原句：
{text}""",
        "translate_en": f"""Explain the following Chinese text in simple English for a learner.
Context: {context}

Text:
{text}""",
    }
    prompt = prompts.get(payload.mode, prompts["explain_en"])
    content = await ai_chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        max_tokens=1600,
    )
    return {"markdown": content}


async def _summarize_chunk(text: str, title: str) -> str:
    prompt = f"""下面是论文《{title}》的一部分。请用中文提炼 5–8 条要点，保留方法、数据、结论中的关键信息。
不要客套，不要重复原文。

{text[:14000]}"""
    return await ai_chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        max_tokens=900,
    )


@app.post("/api/ai/solve-question")
async def solve_question(payload: SolveQuestionIn) -> dict[str, str]:
    text = payload.text.strip()
    if not text:
        raise HTTPException(400, "没有选中题目。")
    prompt = f"""你是四六级阅读、听力、写作、翻译题的解析老师。学生从试卷或文章里选中了下面这段内容：

{text[:5000]}

上下文（可能为空）：
{payload.context[:2000] or "无"}

请用 Markdown 输出，严格按这些小节：
## 题目判断
判断题型（细节题/主旨题/推断题/词义题/写作/翻译等）和考点。

## 答案
如果题干和选项完整，给出明确答案。若文中包含答案或答案键，指出依据；若信息不足，说明缺什么，并给出最可能的答案，不要假装确定。

## 解析
如果有 A–D 选项，逐项分析：正确项为什么对，干扰项错在哪里。标出同义替换、定位句、关键词。

## 关键表达
列出 3–6 个值得记的单词/短语，给中文。

## 同类题方法
用 2–4 条可复用的做题步骤收尾。"""
    content = await ai_chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        max_tokens=1600,
    )
    return {"markdown": content}


def _research_context(doc_id: int, selected: str = "") -> tuple[str, str]:
    with db() as conn:
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not doc:
            raise HTTPException(404, "文献不存在。")
        pages = conn.execute(
            "SELECT page, text FROM pages WHERE doc_id=? AND length(text)>20 "
            "ORDER BY page LIMIT 20",
            (doc_id,),
        ).fetchall()
    title = doc["title"] or "Untitled"
    parts = []
    if selected.strip():
        parts.append(f"学生选中的片段：\n{selected.strip()[:6000]}")
    if doc["abstract"]:
        parts.append(f"摘要：\n{doc['abstract'][:3000]}")
    if doc["summary_json"]:
        try:
            summary = json.loads(doc["summary_json"])
            parts.append("已有结构化摘要：\n" + json.dumps(summary, ensure_ascii=False)[:3000])
        except (TypeError, ValueError):
            pass
    body = []
    for row in pages:
        chunk = (row["text"] or "").strip()
        if chunk:
            body.append(f"[p.{row['page']}] {chunk[:1200]}")
    if body:
        joined = "\n\n".join(body)
        parts.append("正文节选：\n" + joined[:14000])
    return title, "\n\n".join(parts)


RESEARCH_MODES = {
    "reading_card": (
        "速读卡",
        """输出一张论文速读卡，Markdown 表格或小节均可，必须覆盖：
研究问题、核心方法、数据/实验、主要结果、真正的新意、局限、可复现性、和我接下来该读什么。""",
    ),
    "method": (
        "方法拆解",
        """把论文的方法拆成可复述的流程：输入、关键模块、训练/推理、假设、基线、评价指标、可能的失败模式。
用编号步骤，最后给一段 150 字以内的中文方法摘要。""",
    ),
    "reviewer": (
        "审稿人视角",
        """以严格但建设性的审稿人身份输出：一句话总结、主要优点、主要问题（按严重程度）、
小问题、需要作者补充的实验/证据、以及你会问作者的 3 个问题。""",
    ),
    "related_work": (
        "相关工作段落",
        """写一段可以直接放进 Related Work 的英文段落（120–180 词），准确概括这篇论文的贡献，
并说明它与相邻工作的区别。随后给中文解释和 3 个可替换的引用句式。不要编造论文没有的结论。""",
    ),
    "gaps": (
        "研究空白",
        """基于这篇论文，指出 3–5 个仍然开放的问题、可能的下一步实验、以及适合入门者的一个小切口。
每条说明为什么值得做、需要什么数据或方法。""",
    ),
    "notes": (
        "精读笔记",
        """生成一份精读笔记：一句话结论、章节脉络、5 个关键概念（中英对照）、
3 个可直接引用的句子、方法与结果的对应关系、我的疑问清单。""",
    ),
}


@app.post("/api/ai/research")
async def ai_research(payload: ResearchIn) -> dict[str, str]:
    if payload.mode not in RESEARCH_MODES:
        raise HTTPException(400, "未知的研究工具。")
    label, instruction = RESEARCH_MODES[payload.mode]
    title, context = _research_context(payload.doc_id, payload.text)
    prompt = f"""你是一位帮助本科生读论文、写论文的研究助理。当前论文：《{title}》。

任务：{label}
{instruction}

要求：
- 只依据给出的论文内容；不确定的地方明确说“论文节选未说明”，不要编造数据、引用或结论。
- 用中文为主，必要的学术术语保留英文。
- 输出 Markdown，结构清楚，适合直接保存为笔记。

论文材料：
{context}"""
    content = await ai_chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        max_tokens=2000,
    )
    return {"markdown": content, "label": label}


@app.post("/api/ai/translate")
async def translate_document(payload: TranslateIn) -> dict[str, Any]:
    with db() as conn:
        doc = conn.execute(
            "SELECT title FROM documents WHERE id=?", (payload.doc_id,)
        ).fetchone()
        if not doc:
            raise HTTPException(404, "文献不存在。")
        if payload.page:
            rows = conn.execute(
                "SELECT text FROM pages WHERE doc_id=? AND page=?",
                (payload.doc_id, payload.page),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT text FROM pages WHERE doc_id=? ORDER BY page", (payload.doc_id,)
            ).fetchall()
    text = "\n\n".join(row["text"] for row in rows).strip()
    if len(text) < 30:
        raise HTTPException(400, "这一部分没有可提取的文字（可能是扫描版），暂时无法翻译。")

    # Translate in chunks so long papers don't overflow the context window.
    chunks = [text[i : i + 14000] for i in range(0, len(text), 14000)][:10]
    translations = []
    for chunk in chunks:
        prompt = f"""把下面的英文学术文本翻译成准确、通顺的中文。
要求：保留段落结构；专业术语首次出现时在括号里注英文；不要总结，不要省略。
只输出译文。

{chunk}"""
        translations.append(
            await ai_chat(
                [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
                max_tokens=2400,
            )
        )
    return {"markdown": "\n\n".join(translations), "chunks": len(chunks)}


@app.post("/api/ai/summarize")
async def summarize(payload: SummaryIn) -> dict[str, Any]:
    with db() as conn:
        doc = conn.execute(
            "SELECT title FROM documents WHERE id=?", (payload.doc_id,)
        ).fetchone()
        if not doc:
            raise HTTPException(404, "文献不存在。")
        if payload.scope == "page" and payload.page:
            rows = conn.execute(
                "SELECT text FROM pages WHERE doc_id=? AND page=?",
                (payload.doc_id, payload.page),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT text FROM pages WHERE doc_id=? ORDER BY page", (payload.doc_id,)
            ).fetchall()
    text = "\n\n".join(row["text"] for row in rows).strip()
    if len(text) < 80:
        raise HTTPException(400, "这篇 PDF 没有可提取的文字（可能是扫描版），暂时无法总结。")
    title = doc["title"]

    # Long papers: map-reduce so the model sees the whole document.
    if len(text) > 45000:
        chunks = [text[i : i + 14000] for i in range(0, len(text), 14000)][:8]
        notes = []
        for chunk in chunks:
            notes.append(await _summarize_chunk(chunk, title))
        text = "以下是分块摘要，请综合：\n\n" + "\n\n".join(notes)

    prompt = f"""阅读下面的论文内容，输出一个 JSON 对象（不要任何 JSON 以外的文字）：
{{
  "tldr": "一句话中文总结",
  "problem": "研究问题",
  "method": "方法",
  "data": "数据/实验对象",
  "results": "主要结果",
  "contributions": ["贡献1", "贡献2"],
  "limitations": ["局限1", "局限2"],
  "key_terms": [{{"term": "英文术语", "meaning": "中文解释"}}],
  "ideas": ["可复用的核心 idea 1", "idea 2"]
}}

论文标题：{title}

内容：
{text[:52000]}"""
    raw = await ai_chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        json_mode=True,
        max_tokens=2200,
    )
    try:
        data = parse_json_block(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "AI 返回的摘要格式无法解析，请重试。") from exc
    with db() as conn:
        conn.execute(
            "UPDATE documents SET summary_json=? WHERE id=?",
            (json.dumps(data, ensure_ascii=False), payload.doc_id),
        )
    return {"summary": data}


# ---------------------------------------------------------------------------
# AI reading: bilingual page view, document chat, key points, quizzes
# ---------------------------------------------------------------------------
def _paragraphs(text: str, limit: int = 18) -> list[str]:
    raw = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if len(raw) <= 1:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        raw = [" ".join(lines[i : i + 4]) for i in range(0, len(lines), 4)]
    cleaned = [re.sub(r"[ \t]+", " ", part) for part in raw if len(part) > 8]
    return cleaned[:limit]


def _page_paragraphs(doc_id: int, page: int, fallback_text: str) -> list[str]:
    """Use PyMuPDF text blocks when available; they preserve paragraphs far better."""
    try:
        path = _document_path(doc_id)
        pdf = pymupdf.open(path)
        if page < 1 or page > pdf.page_count:
            pdf.close()
            return _paragraphs(fallback_text)
        blocks = pdf[page - 1].get_text("blocks", sort=False)
        title_guess = _guess_title(pdf) if page == 1 else ""
        pdf.close()
        parts = []
        for block in blocks:
            if len(block) < 7 or block[6] != 0:
                continue
            content = re.sub(r"\s+", " ", block[4]).strip()
            if not content:
                continue
            lowered = content.lower()
            if "provided proper attribution" in lowered or "arxiv:" in lowered:
                continue
            if "@" in content and len(content) < 300:
                continue
            if content.startswith(("∗", "†", "‡")):
                continue
            if lowered.startswith(("31st conference", "proceedings of", "published as")):
                continue
            if title_guess and content.lower() == title_guess.lower():
                parts.append(content)
            elif len(content) >= 80:
                parts.append(content)
        return parts[:18] if len(parts) >= 2 else _paragraphs(fallback_text)
    except Exception:  # noqa: BLE001
        return _paragraphs(fallback_text)


class PageTranslateIn(BaseModel):
    doc_id: int
    page: int
    force: bool = False


@app.get("/api/translate/page")
def get_page_translation(doc_id: int, page: int) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            "SELECT payload FROM page_translations WHERE doc_id=? AND page=? AND target='zh'",
            (doc_id, page),
        ).fetchone()
    if not row:
        raise HTTPException(404, "这一页还没有翻译。")
    return {"cached": True, "paragraphs": json.loads(row["payload"])["paragraphs"]}


async def _translate_page_pairs(doc_id: int, page: int, force: bool = False) -> list[dict[str, str]]:
    if not force:
        with db() as conn:
            row = conn.execute(
                "SELECT payload FROM page_translations WHERE doc_id=? AND page=? AND target='zh'",
                (doc_id, page),
            ).fetchone()
        if row:
            return json.loads(row["payload"])["paragraphs"]
    with db() as conn:
        row = conn.execute(
            "SELECT text FROM pages WHERE doc_id=? AND page=?", (doc_id, page)
        ).fetchone()
    if not row or len(row["text"].strip()) < 20:
        raise HTTPException(400, f"第 {page} 页没有可提取的文字（可能是扫描版）。")
    paragraphs = _page_paragraphs(doc_id, page, row["text"])
    numbered = "\n\n".join(f"[{i + 1}] {part}" for i, part in enumerate(paragraphs))
    prompt = f"""把下面编号的英文学术段落逐段翻译成准确、通顺的中文。
要求：顺序、编号和段落数量必须与原文一致；术语首次出现时在括号里注英文；不要合并段落。
只输出 JSON：{{"translations": ["第1段译文", "第2段译文"]}}

{numbered}"""
    raw = await ai_chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        json_mode=True,
        max_tokens=2600,
    )
    try:
        translations = parse_json_block(raw).get("translations", [])
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "AI 返回的译文格式无法解析，请重试。") from exc
    if not isinstance(translations, list) or not translations:
        raise HTTPException(502, "AI 没有返回译文，请重试。")
    pairs = [
        {"en": part, "zh": (translations[index] if index < len(translations) else "")}
        for index, part in enumerate(paragraphs)
    ]
    with db() as conn:
        conn.execute(
            "INSERT INTO page_translations(doc_id, page, target, payload, created_at) "
            "VALUES (?, ?, 'zh', ?, ?) ON CONFLICT(doc_id, page, target) DO UPDATE "
            "SET payload=excluded.payload, created_at=excluded.created_at",
            (doc_id, page, json.dumps({"paragraphs": pairs}, ensure_ascii=False), now_iso()),
        )
    return pairs


@app.post("/api/translate/page")
async def translate_page(payload: PageTranslateIn) -> dict[str, Any]:
    before = None
    with db() as conn:
        row = conn.execute(
            "SELECT payload FROM page_translations WHERE doc_id=? AND page=? AND target='zh'",
            (payload.doc_id, payload.page),
        ).fetchone()
    if row:
        before = json.loads(row["payload"])["paragraphs"]
    pairs = await _translate_page_pairs(payload.doc_id, payload.page, payload.force)
    return {"cached": bool(before and not payload.force), "paragraphs": pairs}


def _text_chunks(text: str, limit: int = 1600) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= limit:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                chunks.append(current)
            if len(paragraph) <= limit:
                current = paragraph
            else:
                chunks.extend(paragraph[i : i + limit] for i in range(0, len(paragraph), limit))
                current = ""
    if current:
        chunks.append(current)
    return chunks or [text]


def _draw_translation_chunks(
    out: pymupdf.Document, page: pymupdf.Page, chunks: list[str], width: float, height: float,
    page_no: int, total: int,
) -> None:
    right_rect = pymupdf.Rect(width + 14, 20, width * 2 + 8, height - 14)
    for index, chunk in enumerate(chunks):
        if index > 0:
            page = out.new_page(width=width * 2 + 24, height=height)
            page.insert_text(
                (24, 14), f"第 {page_no} / {total} 页译文（续）",
                fontsize=7, fontname="helv", color=(0.55, 0.55, 0.55),
            )
            right_rect = pymupdf.Rect(24, 20, width * 2 - 8, height - 14)
        page.insert_textbox(
            right_rect, chunk, fontsize=10.5, fontname="china-s",
            lineheight=1.5, color=(0.12, 0.12, 0.12),
        )


def _build_bilingual_pdf(doc_id: int, progress) -> Path:
    source_path = _document_path(doc_id)
    source = pymupdf.open(source_path)
    output = pymupdf.open()
    total = source.page_count
    for index in range(total):
        page = source[index]
        with db() as conn:
            row = conn.execute(
                "SELECT payload FROM page_translations WHERE doc_id=? AND page=? AND target='zh'",
                (doc_id, index + 1),
            ).fetchone()
        if row:
            pairs = json.loads(row["payload"])["paragraphs"]
        else:
            pairs = asyncio.run(_translate_page_pairs(doc_id, index + 1, False))
        text = "\n\n".join(pair.get("zh", "") for pair in pairs if pair.get("zh")).strip()
        if not text:
            text = "（本页没有译文）"
        width, height = page.rect.width, page.rect.height
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4), alpha=False)
        out_page = output.new_page(width=width * 2 + 24, height=height)
        out_page.insert_image(pymupdf.Rect(0, 0, width, height), pixmap=pix)
        out_page.draw_line(
            (width + 12, 0), (width + 12, height), color=(0.85, 0.85, 0.85), width=0.6
        )
        out_page.insert_text(
            (width + 14, 12), f"Folio · 第 {index + 1} / {total} 页",
            fontsize=7, fontname="helv", color=(0.55, 0.55, 0.55),
        )
        _draw_translation_chunks(
            output, out_page, _text_chunks(text), width, height, index + 1, total
        )
        progress(index + 1, total)
    target = EXPORT_DIR / f"{doc_id}-bilingual.pdf"
    output.save(target)
    output.close()
    source.close()
    return target


def _bilingual_worker(doc_id: int) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE export_jobs SET status='running', updated_at=? WHERE doc_id=?",
            (now_iso(), doc_id),
        )

    def progress(done: int, total: int) -> None:
        with db() as conn:
            conn.execute(
                "UPDATE export_jobs SET done=?, total=?, updated_at=? WHERE doc_id=?",
                (done, total, now_iso(), doc_id),
            )

    try:
        target = _build_bilingual_pdf(doc_id, progress)
        with db() as conn:
            conn.execute(
                "UPDATE export_jobs SET status='done', path=?, updated_at=? WHERE doc_id=?",
                (str(target), now_iso(), doc_id),
            )
    except Exception as exc:  # noqa: BLE001
        with db() as conn:
            conn.execute(
                "UPDATE export_jobs SET status='error', message=?, updated_at=? WHERE doc_id=?",
                (str(exc), now_iso(), doc_id),
            )


def _export_status(doc_id: int) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT * FROM export_jobs WHERE doc_id=?", (doc_id,)).fetchone()
    if not row:
        return {"status": "idle", "total": 0, "done": 0, "message": "", "path": ""}
    return {
        "status": row["status"],
        "total": row["total"],
        "done": row["done"],
        "message": row["message"],
        "path": row["path"],
    }


@app.get("/api/documents/{doc_id}/bilingual/status")
def bilingual_status(doc_id: int) -> dict[str, Any]:
    return _export_status(doc_id)


@app.post("/api/documents/{doc_id}/bilingual/start")
def start_bilingual(doc_id: int) -> dict[str, Any]:
    doc = get_document(doc_id)
    with db() as conn:
        existing = conn.execute(
            "SELECT status FROM export_jobs WHERE doc_id=?", (doc_id,)
        ).fetchone()
        if existing and existing["status"] in ("queued", "running"):
            return _export_status(doc_id)
        conn.execute(
            "INSERT OR REPLACE INTO export_jobs(doc_id, status, total, done, message, path, updated_at) "
            "VALUES (?, 'queued', ?, 0, '', '', ?)",
            (doc_id, doc["pages"], now_iso()),
        )
    threading.Thread(target=_bilingual_worker, args=(doc_id,), daemon=True).start()
    return _export_status(doc_id)


@app.get("/api/documents/{doc_id}/bilingual.pdf")
def download_bilingual(doc_id: int) -> FileResponse:
    target = EXPORT_DIR / f"{doc_id}-bilingual.pdf"
    if not target.exists():
        raise HTTPException(404, "还没有生成双语 PDF。")
    return FileResponse(
        target,
        media_type="application/pdf",
        filename=f"folio-{doc_id}-bilingual.pdf",
    )


STOPWORDS = set(
    "the a an of to in and or for on with is are was were be been this that these those "
    "it its as by from at we our you your they their can could may might will would should "
    "not no do does did has have had than then there here what which who whom whose how why".split()
)


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-zA-Z]{2,}", text.lower()) if token not in STOPWORDS]


def _retrieve_pages(doc_id: int, query: str, current_page: Optional[int] = None, top_k: int = 4):
    with db() as conn:
        rows = conn.execute(
            "SELECT page, text FROM pages WHERE doc_id=? ORDER BY page", (doc_id,)
        ).fetchall()
    if not rows:
        return []
    terms = _tokens(query)
    scored = []
    for row in rows:
        tokens = _tokens(row["text"])
        if not tokens:
            continue
        frequency = sum(tokens.count(term) for term in terms)
        score = frequency / ((len(tokens) ** 0.5) + 1)
        if current_page and row["page"] == current_page:
            score += 0.35
        if row["page"] == 1:
            score += 0.12
        scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [row for _score, row in scored[:top_k]]
    if current_page and all(row["page"] != current_page for row in selected):
        current = next((row for row in rows if row["page"] == current_page), None)
        if current:
            selected.append(current)
    selected.sort(key=lambda row: row["page"])
    return selected


class ChatIn(BaseModel):
    doc_id: int
    message: str
    page: Optional[int] = None


@app.get("/api/chat/{doc_id}")
def list_chat(doc_id: int) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE doc_id=? ORDER BY id", (doc_id,)
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["citations"] = json.loads(item["citations"])
        except json.JSONDecodeError:
            item["citations"] = []
        result.append(item)
    return result


@app.delete("/api/chat/{doc_id}")
def clear_chat(doc_id: int) -> dict[str, str]:
    with db() as conn:
        conn.execute("DELETE FROM chat_messages WHERE doc_id=?", (doc_id,))
    return {"ok": "1"}


@app.post("/api/chat")
async def document_chat(payload: ChatIn) -> dict[str, Any]:
    question = payload.message.strip()
    if not question:
        raise HTTPException(400, "问题为空。")
    with db() as conn:
        doc = conn.execute(
            "SELECT title, authors, year FROM documents WHERE id=?", (payload.doc_id,)
        ).fetchone()
        if not doc:
            raise HTTPException(404, "文献不存在。")
        history_rows = conn.execute(
            "SELECT role, content FROM chat_messages WHERE doc_id=? ORDER BY id DESC LIMIT 8",
            (payload.doc_id,),
        ).fetchall()[::-1]
    pages = _retrieve_pages(payload.doc_id, question, payload.page)
    if not pages:
        raise HTTPException(400, "这篇 PDF 没有可提取的文字，无法提问。")
    context_parts = []
    budget = 15000
    for row in pages:
        excerpt = row["text"][:3600]
        if budget <= 0:
            break
        excerpt = excerpt[:budget]
        context_parts.append(f"[第 {row['page']} 页]\n{excerpt}")
        budget -= len(excerpt)
    context = "\n\n".join(context_parts)
    citation_pages = [row["page"] for row in pages]
    prompt = f"""你是论文《{doc['title']}》的阅读助手。下面是从论文中检索到的页面。
只根据这些页面回答；每个关键结论后面用 [p.页码] 标注来源；资料不足时明确说“论文这部分没有提到”。
回答用中文，必要时保留英文术语。

{context}

学生的问题：{question}"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for row in history_rows:
        messages.append({"role": row["role"], "content": row["content"][:2000]})
    messages.append({"role": "user", "content": prompt})
    answer = await ai_chat(messages, max_tokens=1600)
    citations = sorted(
        {int(match) for match in re.findall(r"\[p\.?\s*(\d+)\]", answer) if int(match) in citation_pages}
    )
    with db() as conn:
        conn.execute(
            "INSERT INTO chat_messages(doc_id, role, content, citations, created_at) "
            "VALUES (?, 'user', ?, '[]', ?)",
            (payload.doc_id, question, now_iso()),
        )
        conn.execute(
            "INSERT INTO chat_messages(doc_id, role, content, citations, created_at) "
            "VALUES (?, 'assistant', ?, ?, ?)",
            (payload.doc_id, answer, json.dumps(citations), now_iso()),
        )
    return {"answer": answer, "citations": citations, "pages": citation_pages}


class KeypointsIn(BaseModel):
    doc_id: int
    page: int
    count: int = 5


@app.post("/api/ai/keypoints")
async def ai_keypoints(payload: KeypointsIn) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            "SELECT text FROM pages WHERE doc_id=? AND page=?",
            (payload.doc_id, payload.page),
        ).fetchone()
    if not row or len(row["text"].strip()) < 40:
        raise HTTPException(400, "这一页没有可提取的文字。")
    prompt = f"""从下面这一页论文中挑出 {payload.count} 个最值得高亮的关键句。
quote 必须是原文中逐字出现的完整句子（不要改写、不要省略中间的词），reason 用中文说明为什么重要。
只输出 JSON：{{"points": [{{"quote": "原文句子", "reason": "中文理由"}}]}}

{row['text'][:9000]}"""
    raw = await ai_chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        json_mode=True,
        max_tokens=1200,
    )
    try:
        points = parse_json_block(raw).get("points", [])
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "AI 返回的重点格式无法解析，请重试。") from exc
    return {"points": points if isinstance(points, list) else []}


class CompareIn(BaseModel):
    doc_ids: list[int]


@app.post("/api/ai/compare")
async def compare_documents(payload: CompareIn) -> dict[str, str]:
    doc_ids = list(dict.fromkeys(payload.doc_ids))[:6]
    if len(doc_ids) < 2:
        raise HTTPException(400, "至少选 2 篇文献。")
    blocks = []
    with db() as conn:
        for index, doc_id in enumerate(doc_ids, 1):
            doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
            if not doc:
                continue
            pages = conn.execute(
                "SELECT text FROM pages WHERE doc_id=? ORDER BY page LIMIT 2", (doc_id,)
            ).fetchall()
            summary = ""
            if doc["summary_json"]:
                try:
                    summary = json.dumps(json.loads(doc["summary_json"]), ensure_ascii=False)
                except json.JSONDecodeError:
                    summary = ""
            blocks.append(
                f"[{index}] {doc['title']} ({doc['year']})\n"
                f"作者：{doc['authors']}\n期刊：{doc['venue']}\n"
                f"摘要：{doc['abstract'][:900]}\nAI 摘要：{summary[:900]}\n"
                f"正文节选：{' '.join(row['text'] for row in pages)[:1200]}"
            )
    if len(blocks) < 2:
        raise HTTPException(400, "可用的文献不足 2 篇。")
    prompt = f"""你是文献综述助手。请对比下面几篇论文，输出 Markdown：
## 对比表
用一张 Markdown 表格，列是 [1]…[N]，行至少包括：研究问题、方法、数据/实验、主要结果、创新点、局限。
## 共同点
## 关键差异
## 适合的阅读顺序
用 [编号] 引用，并说明先读哪篇、为什么。
只依据下面提供的摘要/正文，不要编造。

{chr(10).join(blocks)}"""
    content = await ai_chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        max_tokens=3200,
    )
    return {"markdown": content}


class WritingIn(BaseModel):
    prompt: str = ""
    essay: str


@app.post("/api/ai/write-review")
async def write_review(payload: WritingIn) -> dict[str, str]:
    essay = payload.essay.strip()
    if len(essay) < 80:
        raise HTTPException(400, "作文太短，至少写 80 词。")
    prompt = f"""你是四六级作文阅卷老师。请按 15 分制批改下面这篇作文，使用 Markdown 输出：
## 分数
给出分数（15 分制）和档次（例如 11–13 分）。
## 内容
是否切题、论点是否清楚、例子是否充分。
## 结构
段落、衔接、逻辑。
## 语言
语法错误、词汇搭配、句式多样性；指出最影响分数的 3 个问题。
## 逐句修改
列出 3–5 个问题句，原句 → 修改，并说明原因。
## 升级版
保持原意，改写成 CET-6 水平的范文（150–180 词），不要另起炉灶。

作文题目：{payload.prompt or "（未提供，按常见议论文判断）"}

学生作文：
{essay[:4000]}"""
    content = await ai_chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        max_tokens=2600,
    )
    return {"markdown": content}


class QuizIn(BaseModel):
    doc_id: Optional[int] = None
    article_id: Optional[int] = None
    text: str = ""
    count: int = 5


@app.post("/api/ai/quiz")
async def ai_quiz(payload: QuizIn) -> dict[str, Any]:
    source = payload.text.strip()
    if not source and payload.doc_id:
        with db() as conn:
            rows = conn.execute(
                "SELECT text FROM pages WHERE doc_id=? ORDER BY page LIMIT 4",
                (payload.doc_id,),
            ).fetchall()
        source = "\n\n".join(row["text"] for row in rows)
    if not source and payload.article_id:
        with db() as conn:
            row = conn.execute(
                "SELECT text FROM articles WHERE id=?", (payload.article_id,)
            ).fetchone()
        source = row["text"] if row else ""
    if len(source.strip()) < 100:
        raise HTTPException(400, "文本太短，无法出题。")
    prompt = f"""基于下面文本出 {payload.count} 道四六级风格的阅读理解单选题（英文题干 + 4 个英文选项）。
难度接近 CET-6；正确答案必须有原文依据；每题附中文解析。
只输出 JSON：{{"questions": [{{"question": "...", "options": ["...", "...", "...", "..."],
"answer": 0, "explanation": "..."}}]}}，answer 是 0-3 的选项下标。

{source[:12000]}"""
    raw = await ai_chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        json_mode=True,
        max_tokens=2200,
    )
    try:
        questions = parse_json_block(raw).get("questions", [])
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "AI 返回的题目格式无法解析，请重试。") from exc
    return {"questions": questions if isinstance(questions, list) else []}


# ---------------------------------------------------------------------------
# literature discovery & research agent
# ---------------------------------------------------------------------------
DISCOVER_SOURCES = ("arxiv", "openalex", "crossref", "semantic", "pubmed")
DISCOVER_HEADERS = {"User-Agent": "Folio/0.9 (mailto:local@example.com)"}


def _paper(
    source: str, title: str, authors: list[str], year: str, venue: str,
    abstract: str, url: str, pdf_url: str, doi: str, citations: int, published: str,
) -> dict[str, Any]:
    return {
        "source": source,
        "title": re.sub(r"\s+", " ", title or "").strip(),
        "authors": [author for author in authors if author],
        "year": year or "",
        "venue": venue or "",
        "abstract": re.sub(r"\s+", " ", abstract or "").strip()[:2200],
        "url": url or "",
        "pdf_url": pdf_url or "",
        "doi": (doi or "").replace("https://doi.org/", "").strip(),
        "citations": int(citations or 0),
        "published": published or "",
    }


async def _search_arxiv(client: httpx.AsyncClient, query: str, days: int, limit: int) -> list[dict[str, Any]]:
    date_filter = ""
    if days:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y%m%d")
        date_filter = f" AND submittedDate:[{since}0000 TO 999912312359]"
    response = await client.get(
        "https://export.arxiv.org/api/query",
        params={
            "search_query": f"all:{query}{date_filter}",
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        },
    )
    response.raise_for_status()
    root = ET.fromstring(response.text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    papers = []
    for entry in root.findall("a:entry", ns):
        url = entry.findtext("a:id", "", ns)
        arxiv_id = url.rsplit("/", 1)[-1]
        authors = [author.findtext("a:name", "", ns) for author in entry.findall("a:author", ns)]
        published = entry.findtext("a:published", "", ns)
        title = entry.findtext("a:title", "", ns)
        summary = entry.findtext("a:summary", "", ns)
        papers.append(
            _paper(
                "arXiv", title, authors, published[:4], "arXiv", summary, url,
                f"https://arxiv.org/pdf/{arxiv_id}", f"10.48550/arXiv.{arxiv_id}",
                0, published[:10],
            )
        )
    return papers


async def _search_openalex(client: httpx.AsyncClient, query: str, days: int, limit: int) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "search": query,
        "per-page": limit,
        "mailto": "local@example.com",
    }
    if days:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        params["filter"] = f"from_publication_date:{since}"
    response = await client.get("https://api.openalex.org/works", params=params)
    response.raise_for_status()
    papers = []
    for item in response.json().get("results", []):
        inverted = item.get("abstract_inverted_index") or {}
        positions = []
        for word, indexes in inverted.items():
            for index in indexes:
                positions.append((index, word))
        abstract = " ".join(word for _, word in sorted(positions))
        location = item.get("best_oa_location") or {}
        pdf_url = location.get("pdf_url") or (item.get("open_access") or {}).get("oa_url") or ""
        authors = [
            (authorship.get("author") or {}).get("display_name", "")
            for authorship in item.get("authorships", [])
        ]
        venue = ((item.get("primary_location") or {}).get("source") or {}).get("display_name", "")
        papers.append(
            _paper(
                "OpenAlex", item.get("title") or "", authors,
                str(item.get("publication_year") or ""), venue, abstract,
                item.get("id") or "", pdf_url, item.get("doi") or "",
                item.get("cited_by_count") or 0, item.get("publication_date") or "",
            )
        )
    return papers


async def _search_crossref(client: httpx.AsyncClient, query: str, days: int, limit: int) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "query.title": query,
        "rows": limit,
    }
    filters = ["type:journal-article"]
    if days:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        filters.append(f"from-pub-date:{since}")
    params["filter"] = ",".join(filters)
    response = await client.get("https://api.crossref.org/works", params=params)
    response.raise_for_status()
    papers = []
    for item in response.json().get("message", {}).get("items", []):
        date_parts = (item.get("issued") or {}).get("date-parts") or [[None]]
        year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""
        authors = [
            f"{author.get('given', '')} {author.get('family', '')}".strip()
            for author in item.get("author", [])
        ]
        links = item.get("link") or []
        pdf_url = next(
            (link.get("URL") for link in links if "pdf" in (link.get("content-type") or "")),
            "",
        )
        title = (item.get("title") or [""])[0]
        abstract = re.sub(r"<[^>]+>", " ", item.get("abstract") or "")
        papers.append(
            _paper(
                "Crossref", title, authors, year,
                (item.get("container-title") or [""])[0], abstract,
                item.get("URL") or "", pdf_url, item.get("DOI") or "",
                item.get("is-referenced-by-count") or 0,
                f"{year}-01-01" if year else "",
            )
        )
    return papers


async def _search_semantic(client: httpx.AsyncClient, query: str, days: int, limit: int) -> list[dict[str, Any]]:
    headers = {}
    api_key = get_setting("s2_api_key").strip()
    if api_key:
        headers["x-api-key"] = api_key
    params: dict[str, Any] = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,venue,abstract,url,externalIds,openAccessPdf,citationCount,publicationDate",
    }
    if days:
        current_year = datetime.now(timezone.utc).year
        params["year"] = f"{current_year - max(1, days // 365)}-{current_year}"
    response = await client.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params=params, headers=headers,
    )
    if response.status_code == 429:
        raise RuntimeError("Semantic Scholar 限流，稍后重试或填 API Key")
    response.raise_for_status()
    papers = []
    for item in response.json().get("data", []):
        external = item.get("externalIds") or {}
        papers.append(
            _paper(
                "Semantic Scholar", item.get("title") or "",
                [author.get("name", "") for author in item.get("authors", [])],
                str(item.get("year") or ""), item.get("venue") or "",
                item.get("abstract") or "", item.get("url") or "",
                (item.get("openAccessPdf") or {}).get("url") or "",
                external.get("DOI") or "", item.get("citationCount") or 0,
                item.get("publicationDate") or "",
            )
        )
    return papers


async def _search_pubmed(client: httpx.AsyncClient, query: str, days: int, limit: int) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "db": "pubmed", "term": query, "retmax": limit, "sort": "relevance", "retmode": "json"
    }
    if days:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).date()
        params.update(
            {"datetype": "pdat", "mindate": since.isoformat(), "maxdate": datetime.now(timezone.utc).date().isoformat()}
        )
    search = await client.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params=params)
    search.raise_for_status()
    ids = search.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    fetch = await client.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml"},
    )
    fetch.raise_for_status()
    root = ET.fromstring(fetch.text)
    papers = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID", "")
        title = "".join(article.find(".//ArticleTitle").itertext()) if article.find(".//ArticleTitle") is not None else ""
        abstract = " ".join(
            "".join(node.itertext()) for node in article.findall(".//AbstractText")
        )
        authors = []
        for author in article.findall(".//AuthorList/Author"):
            name = " ".join(
                part for part in [author.findtext("ForeName", ""), author.findtext("LastName", "")] if part
            )
            if name:
                authors.append(name)
        year = article.findtext(".//PubDate/Year", "") or article.findtext(".//MedlineDate", "")[:4]
        doi = ""
        for identifier in article.findall(".//ArticleId"):
            if identifier.get("IdType") == "doi":
                doi = identifier.text or ""
                break
        papers.append(
            _paper(
                "PubMed", title, authors, year, article.findtext(".//Journal/Title", ""),
                abstract, f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", "", doi, 0,
                f"{year}-01-01" if year else "",
            )
        )
    return papers


OPEN_PDF_HINTS = (
    "arxiv.org", "ncbi.nlm.nih.gov", "pmc.", "mdpi.com", "frontiersin.org",
    "plos.org", "figshare.com", "zenodo.org", "hal.science", "osf.io",
    "biorxiv.org", "medrxiv.org", "copernicus.org", "eartharxiv.org",
)


def _openish(paper: dict[str, Any]) -> bool:
    url = (paper.get("pdf_url") or "").lower()
    return any(hint in url for hint in OPEN_PDF_HINTS)


def _dedupe_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_doi: dict[str, int] = {}
    by_title: dict[str, int] = {}
    unique: list[dict[str, Any]] = []
    for paper in papers:
        doi = (paper.get("doi") or "").lower().strip()
        title = re.sub(r"[^a-z0-9]+", "", (paper.get("title") or "").lower())[:120]
        existing_index = by_doi.get(doi) if doi else None
        if existing_index is None and title:
            existing_index = by_title.get(title)
        if existing_index is not None:
            # Prefer an open-access PDF over a paywalled landing page.
            if _openish(paper) and not _openish(unique[existing_index]):
                unique[existing_index] = paper
            continue
        index = len(unique)
        unique.append(paper)
        if doi:
            by_doi[doi] = index
        if title:
            by_title[title] = index
    return unique


async def _run_discovery(query: str, sources: list[str], days: int, limit: int) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=35, headers=DISCOVER_HEADERS, follow_redirects=True) as client:
        tasks = []
        names = []
        for source in sources:
            if source == "arxiv":
                tasks.append(_search_arxiv(client, query, days, limit)); names.append("arXiv")
            elif source == "openalex":
                tasks.append(_search_openalex(client, query, days, limit)); names.append("OpenAlex")
            elif source == "crossref":
                tasks.append(_search_crossref(client, query, days, limit)); names.append("Crossref")
            elif source == "semantic":
                tasks.append(_search_semantic(client, query, days, limit)); names.append("Semantic Scholar")
            elif source == "pubmed":
                tasks.append(_search_pubmed(client, query, days, limit)); names.append("PubMed")
        results = await asyncio.gather(*tasks, return_exceptions=True)
    papers: list[dict[str, Any]] = []
    errors = []
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            errors.append({"source": name, "message": str(result)})
        else:
            papers.extend(result)
    papers = _dedupe_papers(papers)
    if days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        cutoff_year = cutoff[:4]
        papers = [
            paper for paper in papers
            if (
                (paper.get("published") and len(paper["published"]) >= 10 and paper["published"] >= cutoff)
                or (paper.get("year") and paper["year"].isdigit() and paper["year"] >= cutoff_year)
            )
        ]
    return {"papers": papers, "errors": errors}


def _rank_discover(papers: list[dict[str, Any]], query: str, sort: str) -> list[dict[str, Any]]:
    terms = [
        term for term in re.findall(r"[a-z0-9]+", query.lower())
        if len(term) > 2 and term not in STOPWORDS
    ]
    if not terms:
        terms = re.findall(r"[a-z0-9]+", query.lower())
    scored = []
    for paper in papers:
        text = f"{paper['title']} {paper['abstract']}".lower()
        title = paper["title"].lower()
        distinct = sum(1 for term in terms if term in text)
        if distinct < max(1, min(3, (len(terms) + 1) // 2)):
            continue
        score = distinct * 10 + sum(text.count(term) for term in terms) + sum(title.count(term) for term in terms) * 2
        score += min(5, (paper["citations"] or 0) ** 0.35)
        item = dict(paper)
        item["_score"] = score
        scored.append(item)
    if not scored:
        scored = [dict(paper, _score=0) for paper in papers]
    if sort == "citations":
        scored.sort(key=lambda item: (item["citations"], item["_score"]), reverse=True)
    elif sort == "recent":
        scored.sort(key=lambda item: (item.get("published") or "", item["_score"]), reverse=True)
    else:
        scored.sort(key=lambda item: item["_score"], reverse=True)
    for item in scored:
        item.pop("_score", None)
    return scored


@app.get("/api/discover/search")
async def discover_search(
    q: str = "", sources: str = "arxiv,openalex",
    days: int = 365, limit: int = 20, sort: str = "recent",
) -> dict[str, Any]:
    query = q.strip()
    if not query:
        raise HTTPException(400, "请输入搜索主题。")
    selected = [source.strip() for source in sources.split(",") if source.strip() in DISCOVER_SOURCES]
    if not selected:
        selected = ["arxiv", "openalex"]
    limit = max(3, min(30, limit))
    days = max(0, min(3650, days))
    result = await _run_discovery(query, selected, days, limit * 2)
    current_year = datetime.now(timezone.utc).year
    papers = [
        paper for paper in result["papers"]
        if not paper["year"] or not paper["year"].isdigit() or int(paper["year"]) <= current_year
    ]
    ranked = _rank_discover(papers, query, sort)
    return {
        "query": query,
        "sources": selected,
        "days": days,
        "papers": ranked[: limit * 3],
        "errors": result["errors"],
    }


class AgentIn(BaseModel):
    query: str
    sources: str = "arxiv,openalex"
    days: int = 365
    limit: int = 20


@app.post("/api/agent/research")
async def agent_research(payload: AgentIn) -> dict[str, Any]:
    query = payload.query.strip()
    if not query:
        raise HTTPException(400, "请输入研究主题。")
    plan_prompt = f"""你是文献检索规划助手。根据用户主题，规划 1-3 条英文检索式。
可选来源：arxiv, openalex, crossref, semantic, pubmed。
只输出 JSON：{{"queries": ["英文检索式"], "sources": ["arxiv", "openalex"], "days": 365, "focus": "一句话说明重点"}}

用户主题：{query}"""
    raw_plan = await ai_chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": plan_prompt}],
        json_mode=True, max_tokens=500,
    )
    try:
        plan = parse_json_block(raw_plan)
    except (ValueError, json.JSONDecodeError):
        plan = {"queries": [query], "sources": ["arxiv", "openalex"], "days": payload.days}
    queries = [item for item in (plan.get("queries") or [query]) if isinstance(item, str)][:3]
    selected = [source for source in (plan.get("sources") or []) if source in DISCOVER_SOURCES]
    if not selected:
        selected = [source.strip() for source in payload.sources.split(",") if source.strip() in DISCOVER_SOURCES]
    if not selected:
        selected = ["arxiv", "openalex"]
    days = int(plan.get("days") or payload.days or 365)
    days = max(0, min(3650, days))

    gathered: list[dict[str, Any]] = []
    errors = []
    for item in queries:
        result = await _run_discovery(item, selected, days, payload.limit)
        gathered.extend(result["papers"])
        errors.extend(result["errors"])
    papers = _dedupe_papers(gathered)
    papers.sort(key=lambda paper: (paper["citations"], paper["published"]), reverse=True)
    papers = papers[:24]
    if not papers:
        return {"plan": plan, "papers": [], "errors": errors, "markdown": "没有检索到结果，请换一个更具体的主题或扩大时间范围。"}

    context = "\n\n".join(
        f"[{index + 1}] {paper['title']} ({paper['year']}, {paper['venue'] or paper['source']})\n"
        f"作者：{', '.join(paper['authors'][:6])}\n摘要：{paper['abstract'][:900]}"
        for index, paper in enumerate(papers)
    )
    synthesis = f"""你是严谨的科研助理。下面是刚刚检索到的论文。请写一份中文研究简报：
1. 研究现状（3-5 条）
2. 关键论文与各自贡献，用 [编号] 引用
3. 趋势与共识
4. 空白、争议或机会
5. 建议阅读顺序（3-5 篇）
只依据下面的论文，不要编造不存在的文献。

用户主题：{query}

{context}"""
    markdown = await ai_chat(
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": synthesis}],
        max_tokens=2600,
    )
    return {"plan": plan, "papers": papers, "errors": errors, "markdown": markdown}


class DiscoverImportIn(BaseModel):
    paper: dict[str, Any]


async def _download_pdf(client: httpx.AsyncClient, paper: dict[str, Any]) -> bytes:
    candidates: list[str] = []
    pdf_url = (paper.get("pdf_url") or "").strip()
    if pdf_url:
        candidates.append(pdf_url)
    if "arxiv.org/abs/" in pdf_url:
        candidates.append(pdf_url.replace("/abs/", "/pdf/"))
    doi = (paper.get("doi") or "").strip()
    if doi.lower().startswith("10.48550/arxiv."):
        arxiv_id = doi.split("arXiv.")[-1]
        candidates.append(f"https://arxiv.org/pdf/{arxiv_id}")
    page_url = (paper.get("url") or "").strip()
    if page_url.endswith(".pdf"):
        candidates.append(page_url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "application/pdf,application/octet-stream,*/*",
    }
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            response = await client.get(candidate, headers=headers)
        except httpx.HTTPError:
            continue
        if response.status_code == 200 and response.content.startswith(b"%PDF"):
            return response.content
    if doi:
        try:
            unpaywall = await client.get(
                f"https://api.unpaywall.org/v2/{doi}",
                params={"email": "local@example.com"},
            )
            if unpaywall.status_code == 200:
                best = unpaywall.json().get("best_oa_location") or {}
                fallback = best.get("url_for_pdf") or best.get("url") or ""
                if fallback and fallback not in seen:
                    response = await client.get(fallback, headers=headers)
                    if response.status_code == 200 and response.content.startswith(b"%PDF"):
                        return response.content
        except (httpx.HTTPError, ValueError):
            pass
    raise HTTPException(400, "没有找到可下载的开放获取 PDF，请点「原文」查看。")


@app.post("/api/discover/import")
async def discover_import(payload: DiscoverImportIn) -> dict[str, Any]:
    paper = payload.paper or {}
    async with httpx.AsyncClient(timeout=120, headers=DISCOVER_HEADERS, follow_redirects=True) as client:
        data = await _download_pdf(client, paper)
    filename = re.sub(r"[^\w一-鿿 .-]", "", paper.get("title") or "paper")[:120] or "paper"
    result = _ingest_pdf_bytes(data, filename + ".pdf")
    if paper.get("doi") or paper.get("abstract"):
        with db() as conn:
            conn.execute(
                "UPDATE documents SET doi=COALESCE(NULLIF(doi,''), ?), "
                "abstract=COALESCE(NULLIF(abstract,''), ?) WHERE id=?",
                (paper.get("doi") or "", paper.get("abstract") or "", result["id"]),
            )
    return result


# ---------------------------------------------------------------------------
# Zotero import
# ---------------------------------------------------------------------------
ZOTERO_HEADERS = {"Zotero-API-Version": "3"}


def _zotero_base() -> str:
    return (get_setting("zotero_url") or "http://127.0.0.1:23119").rstrip("/")


def _zotero_meta(data: dict[str, Any]) -> dict[str, Any]:
    creators = data.get("creators") or []
    authors = ", ".join(
        (creator.get("name") or f"{creator.get('firstName', '')} {creator.get('lastName', '')}".strip())
        for creator in creators
        if creator.get("name") or creator.get("lastName")
    )
    date = data.get("date") or ""
    match = re.search(r"\b(1[89]\d{2}|20\d{2})\b", date)
    year = match.group(1) if match else ""
    venue = (
        data.get("publicationTitle") or data.get("bookTitle") or data.get("proceedingsTitle")
        or data.get("conferenceName") or data.get("publisher") or ""
    )
    tags = ", ".join(
        tag.get("tag", "") for tag in (data.get("tags") or []) if tag.get("tag")
    )
    return {
        "title": data.get("title") or "Untitled",
        "authors": authors,
        "year": year,
        "venue": venue,
        "doi": data.get("DOI") or "",
        "abstract": data.get("abstractNote") or "",
        "tags": tags,
        "url": data.get("url") or (f"https://doi.org/{data['DOI']}" if data.get("DOI") else ""),
        "item_type": data.get("itemType") or "",
    }


def _zotero_file_path(url: str) -> Optional[Path]:
    parsed = urlparse(url.strip())
    if parsed.scheme != "file":
        return None
    raw = unquote(parsed.path)
    if os.name == "nt" and re.match(r"^/[A-Za-z]:", raw):
        raw = raw[1:]
    path = Path(url2pathname(raw) if os.name != "nt" else raw)
    return path if path.exists() else None


def _reference_document(meta: dict[str, Any]) -> dict[str, Any]:
    title = meta.get("title") or "Untitled"
    abstract = meta.get("abstract") or "（这个条目没有摘要，也没有附加 PDF。）"
    url = meta.get("url") or (f"https://doi.org/{meta['doi']}" if meta.get("doi") else "")
    pdf = _article_pdf(title, abstract, url, meta.get("authors") or "")
    safe = re.sub(r"[^\w一-鿿 .-]", "", title)[:100] or "reference"
    result = _ingest_pdf_bytes(pdf, safe + ".pdf")
    with db() as conn:
        conn.execute(
            "UPDATE documents SET title=?, authors=?, year=?, venue=?, doi=?, abstract=?, "
            "tags=?, status='unread', updated_at=? WHERE id=?",
            (
                title, meta.get("authors") or "", meta.get("year") or "",
                meta.get("venue") or "", meta.get("doi") or "",
                meta.get("abstract") or "", meta.get("tags") or "", now_iso(), result["id"],
            ),
        )
    return result


@app.get("/api/zotero/status")
async def zotero_status() -> dict[str, Any]:
    base = _zotero_base()
    try:
        async with httpx.AsyncClient(timeout=8, headers=ZOTERO_HEADERS) as client:
            response = await client.get(f"{base}/api/users/0/items", params={"limit": 1})
        return {
            "available": response.status_code < 400,
            "message": "已连接 Zotero 本地 API" if response.status_code < 400 else f"Zotero 返回 {response.status_code}",
            "url": base,
        }
    except httpx.HTTPError as exc:
        return {
            "available": False,
            "message": f"连不上 Zotero：{exc}。请在 Zotero 设置 → 高级 → 勾选允许其他应用通信。",
            "url": base,
        }


@app.get("/api/zotero/items")
async def zotero_items(limit: int = 60, q: str = "") -> dict[str, Any]:
    base = _zotero_base()
    limit = max(1, min(100, limit))
    params: dict[str, Any] = {
        "limit": limit, "itemType": "-note",
        "sort": "dateModified", "direction": "desc",
    }
    if q.strip():
        params["q"] = q.strip()
    try:
        async with httpx.AsyncClient(timeout=30, headers=ZOTERO_HEADERS) as client:
            response = await client.get(f"{base}/api/users/0/items", params=params)
        response.raise_for_status()
        raw_items = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, f"读取 Zotero 失败：{exc}") from exc
    attachments: dict[str, list[dict[str, Any]]] = {}
    for item in raw_items:
        data = item.get("data") or {}
        parent = data.get("parentItem")
        if data.get("itemType") == "attachment" and parent:
            attachments.setdefault(parent, []).append(data)
    items = []
    for item in raw_items:
        data = item.get("data") or {}
        if data.get("itemType") in ("attachment", "note", "annotation") or data.get("deleted"):
            continue
        meta = _zotero_meta(data)
        pdfs = [
            attachment for attachment in attachments.get(item.get("key"), [])
            if (attachment.get("contentType") == "application/pdf"
                or (attachment.get("filename") or "").lower().endswith(".pdf"))
        ]
        items.append(
            {
                "key": item.get("key"),
                "title": meta["title"],
                "authors": meta["authors"],
                "year": meta["year"],
                "venue": meta["venue"],
                "doi": meta["doi"],
                "abstract": meta["abstract"][:800],
                "tags": meta["tags"],
                "item_type": meta["item_type"],
                "has_pdf": bool(pdfs),
                "pdf_key": pdfs[0].get("key") if pdfs else None,
            }
        )
    return {"items": items, "url": base}


class ZoteroImportIn(BaseModel):
    keys: list[str]


@app.post("/api/zotero/import")
async def zotero_import(payload: ZoteroImportIn) -> dict[str, Any]:
    base = _zotero_base()
    imported = []
    errors = []
    async with httpx.AsyncClient(timeout=60, headers=ZOTERO_HEADERS) as client:
        for key in payload.keys[:50]:
            try:
                item_response = await client.get(f"{base}/api/users/0/items/{key}")
                item_response.raise_for_status()
                data = item_response.json().get("data") or {}
                meta = _zotero_meta(data)
                children = await client.get(f"{base}/api/users/0/items/{key}/children")
                children.raise_for_status()
                pdf_key = None
                for child in children.json():
                    child_data = child.get("data") or {}
                    if child_data.get("itemType") == "attachment" and (
                        child_data.get("contentType") == "application/pdf"
                        or (child_data.get("filename") or "").lower().endswith(".pdf")
                    ):
                        pdf_key = child.get("key")
                        break
                result = None
                if pdf_key:
                    file_response = await client.get(
                        f"{base}/api/users/0/items/{pdf_key}/file/view/url"
                    )
                    if file_response.status_code == 200:
                        path = _zotero_file_path(file_response.text)
                        if path:
                            result = _ingest_pdf_bytes(path.read_bytes(), path.name)
                if result is None:
                    result = _reference_document(meta)
                else:
                    with db() as conn:
                        conn.execute(
                            "UPDATE documents SET title=?, authors=?, year=?, venue=?, doi=?, "
                            "abstract=?, tags=? WHERE id=?",
                            (
                                meta["title"], meta["authors"], meta["year"], meta["venue"],
                                meta["doi"], meta["abstract"], meta["tags"], result["id"],
                            ),
                        )
                imported.append({"id": result["id"], "title": meta["title"], "has_pdf": bool(pdf_key)})
            except Exception as exc:  # noqa: BLE001
                errors.append({"key": key, "message": str(exc)})
    return {"imported": imported, "errors": errors}


class MetadataImportIn(BaseModel):
    format: str = "csl"
    text: str


def _parse_csl(text: str) -> list[dict[str, Any]]:
    data = json.loads(text)
    if isinstance(data, dict):
        data = [data]
    entries = []
    for item in data:
        authors = ", ".join(
            f"{author.get('given', '')} {author.get('family', '')}".strip()
            for author in item.get("author", [])
        )
        date_parts = (item.get("issued") or {}).get("date-parts") or [[None]]
        year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""
        entries.append(
            {
                "title": item.get("title") or "Untitled",
                "authors": authors,
                "year": year,
                "venue": item.get("container-title") or "",
                "doi": item.get("DOI") or "",
                "abstract": item.get("abstract") or "",
                "tags": ", ".join(item.get("keyword") or []),
                "url": item.get("URL") or "",
            }
        )
    return entries


def _parse_bibtex(text: str) -> list[dict[str, Any]]:
    entries = []
    for block in re.split(r"(?=@\w+\s*\{)", text):
        match = re.match(r"\s*@(\w+)\s*\{\s*([^,]+),", block)
        if not match:
            continue
        body = block[match.end():].strip()
        if body.endswith("}"):
            body = body[:-1]
        fields = {}
        for field in re.finditer(r"(\w+)\s*=\s*[\{\"](.*?)[\}\"]\s*,?", body, re.S):
            fields[field.group(1).lower()] = re.sub(r"\s+", " ", field.group(2)).strip()
        title = fields.get("title")
        if not title:
            continue
        entries.append(
            {
                "title": title,
                "authors": fields.get("author", "").replace(" and ", ", "),
                "year": fields.get("year", ""),
                "venue": fields.get("journal") or fields.get("booktitle") or fields.get("publisher", ""),
                "doi": fields.get("doi", ""),
                "abstract": fields.get("abstract", ""),
                "tags": "",
                "url": fields.get("url", ""),
            }
        )
    return entries


@app.post("/api/zotero/import-metadata")
def import_metadata(payload: MetadataImportIn) -> dict[str, Any]:
    try:
        entries = _parse_csl(payload.text) if payload.format.lower() == "csl" else _parse_bibtex(payload.text)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(400, f"解析失败：{exc}") from exc
    if not entries:
        raise HTTPException(400, "没有解析到条目。")
    imported = []
    for entry in entries[:100]:
        try:
            result = _reference_document(entry)
            imported.append({"id": result["id"], "title": entry["title"]})
        except Exception as exc:  # noqa: BLE001
            imported.append({"error": str(exc), "title": entry.get("title", "")})
    return {"imported": imported}


# ---------------------------------------------------------------------------
# WebDAV cross-device sync
# ---------------------------------------------------------------------------
def _sync_device() -> str:
    device = get_setting("sync_device")
    if not device:
        device = uuid.uuid4().hex[:8]
        set_setting("sync_device", device)
    return device


def _doc_key(doi: str, title: str) -> str:
    doi = (doi or "").lower().strip()
    if doi:
        return doi
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())[:120]


def _highlight_sync_key(doc_key: str, page: int, text: str) -> str:
    digest = hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:12]
    return f"{doc_key}|{page}|{digest}"


def _note_sync_key(doc_key: str, page: int, content: str) -> str:
    digest = hashlib.sha1((content or "").encode("utf-8")).hexdigest()[:12]
    return f"{doc_key}|{page}|{digest}"


def _add_deletion(entity_type: str, entity_key: str) -> None:
    if not entity_key:
        return
    device = _sync_device()
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sync_deletions(entity_type, entity_key, deleted_at, device) "
            "VALUES (?, ?, ?, ?)",
            (entity_type, entity_key, now_iso(), device),
        )


VOCAB_CONFLICT_FIELDS = (
    "lemma", "phonetic", "translation", "definition", "tag",
    "exchange", "context", "deck", "mastered",
)
HIGHLIGHT_CONFLICT_FIELDS = ("color", "text", "rects", "note", "type", "page")
NOTE_CONFLICT_FIELDS = ("title", "content", "page")


def _norm_conflict_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _conflict_diff(item: sqlite3.Row | dict[str, Any], remote: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return any(
        _norm_conflict_value(item[field] if isinstance(item, sqlite3.Row) else item.get(field))
        != _norm_conflict_value(remote.get(field))
        for field in fields
        if field in (item.keys() if isinstance(item, sqlite3.Row) else item)
    )


def _sync_local_payload(
    entity_type: str, item: sqlite3.Row, fields: tuple[str, ...]
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": item["id"],
        "uid": item["sync_uid"] or "",
        "updated_at": item["updated_at"] or item["created_at"] or "",
    }
    for field in fields:
        payload[field] = item[field] if field in item.keys() else ""
    if entity_type == "highlight":
        payload["doc_key"] = _doc_key(
            item["doi"] if "doi" in item.keys() else "",
            item["doc_title"] if "doc_title" in item.keys() else "",
        )
        payload["page"] = item["page"]
    elif entity_type == "note":
        payload["doc_key"] = _doc_key(
            item["doi"] if "doi" in item.keys() else "",
            item["doc_title"] if "doc_title" in item.keys() else "",
        )
        payload["page"] = item["page"]
    return payload


def _record_sync_conflict(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_key: str,
    local: dict[str, Any],
    remote: dict[str, Any],
) -> bool:
    """Keep one open conflict per object and refresh its two sides.

    Returns True when a new conflict was created, so the sync summary does not
    count the same disagreement on every pass.
    """
    if not entity_key:
        return False
    local_json = json.dumps(local, ensure_ascii=False)
    remote_json = json.dumps(remote, ensure_ascii=False)
    existing = conn.execute(
        "SELECT id FROM sync_conflicts WHERE entity_type=? AND entity_key=? "
        "AND resolved=0 ORDER BY id DESC LIMIT 1",
        (entity_type, entity_key),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE sync_conflicts SET local_json=?, remote_json=? WHERE id=?",
            (local_json, remote_json, existing["id"]),
        )
        return False
    conn.execute(
        "INSERT INTO sync_conflicts(entity_type, entity_key, local_json, remote_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (entity_type, entity_key, local_json, remote_json, now_iso()),
    )
    return True


def _build_sync_snapshot() -> dict[str, Any]:
    with db() as conn:
        collections = [row["name"] for row in conn.execute("SELECT name FROM collections").fetchall()]
        docs = conn.execute(
            "SELECT d.*, c.name AS collection_name FROM documents d "
            "LEFT JOIN collections c ON c.id=d.collection_id ORDER BY d.id"
        ).fetchall()
        vocabs = conn.execute("SELECT * FROM vocab").fetchall()
        highlights = conn.execute("SELECT * FROM highlights").fetchall()
        notes = conn.execute("SELECT * FROM notes").fetchall()
        topics = conn.execute("SELECT * FROM topics").fetchall()
        articles = conn.execute("SELECT * FROM articles").fetchall()
        deletions = [
            dict(row) for row in conn.execute(
                "SELECT entity_type, entity_key, deleted_at, device FROM sync_deletions"
            ).fetchall()
        ]
    document_items = []
    for row in docs:
        item = {
            "key": _doc_key(row["doi"], row["title"]),
            "title": row["title"],
            "authors": row["authors"],
            "year": row["year"],
            "venue": row["venue"],
            "doi": row["doi"],
            "abstract": row["abstract"],
            "tags": row["tags"],
            "collection": row["collection_name"] or "",
            "favorite": row["favorite"],
            "status": row["status"],
            "last_page": row["last_page"],
            "reading_seconds": row["reading_seconds"],
            "summary_json": row["summary_json"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "pdf_name": Path(row["path"]).name,
            "kind": row["kind"] or "paper",
            "epub_name": Path(row["source_path"]).name if row["source_path"] else "",
        }
        document_items.append(item)
    doc_key_by_id = {
        row["id"]: _doc_key(row["doi"], row["title"]) for row in docs
    }
    vocab_items = []
    for row in vocabs:
        item = {key: row[key] for key in row.keys() if key not in ("id", "doc_id", "sync_uid")}
        item["uid"] = row["sync_uid"] or ""
        item["doc_key"] = doc_key_by_id.get(row["doc_id"], "")
        vocab_items.append(item)
    highlight_items = []
    for row in highlights:
        highlight_items.append(
            {
                "uid": row["sync_uid"] or "",
                "doc_key": doc_key_by_id.get(row["doc_id"], ""),
                "page": row["page"],
                "color": row["color"],
                "text": row["text"],
                "rects": row["rects"],
                "note": row["note"],
                "type": row["type"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "due": row["due"],
                "fsrs": row["fsrs"],
                "reps": row["reps"],
            }
        )
    note_items = [
        {
            "uid": row["sync_uid"] or "",
            "doc_key": doc_key_by_id.get(row["doc_id"], ""),
            "page": row["page"],
            "title": row["title"],
            "content": row["content"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in notes
    ]
    return {
        "version": 1,
        "device": _sync_device(),
        "timestamp": now_iso(),
        "collections": collections,
        "documents": document_items,
        "vocab": vocab_items,
        "highlights": highlight_items,
        "notes": note_items,
        "topics": [dict(row) for row in topics],
        "articles": [dict(row) for row in articles],
        "deletions": deletions,
    }


def _sync_auth() -> Optional[httpx.BasicAuth]:
    user = get_setting("sync_user")
    password = get_setting("sync_password")
    return httpx.BasicAuth(user, password) if user else None


def _sync_base() -> str:
    url = get_setting("sync_url").strip().rstrip("/")
    if not url:
        raise HTTPException(400, "还没有配置 WebDAV 地址。")
    return url


async def _ensure_dav(client: httpx.AsyncClient, url: str) -> None:
    response = await client.request("MKCOL", url)
    if response.status_code not in (201, 405, 301, 302, 409):
        response.raise_for_status()


async def _merge_sync_snapshot(snapshot: dict[str, Any], client: httpx.AsyncClient) -> dict[str, Any]:
    counts = {
        "documents": 0, "vocab": 0, "highlights": 0, "notes": 0,
        "topics": 0, "articles": 0, "deleted": 0, "conflicts": 0,
    }
    with db() as conn:
        for name in snapshot.get("collections") or []:
            if name:
                conn.execute(
                    "INSERT OR IGNORE INTO collections(name, color, created_at) VALUES (?, ?, ?)",
                    (name, "#0071e3", now_iso()),
                )
        collection_ids = {
            row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM collections")
        }
        local_docs = {}
        for row in conn.execute("SELECT * FROM documents"):
            local_docs[_doc_key(row["doi"], row["title"])] = row
        doc_map = {key: row["id"] for key, row in local_docs.items()}
        for deletion in snapshot.get("deletions") or []:
            entity_type = deletion.get("entity_type") or ""
            key = deletion.get("entity_key") or ""
            deleted_at = deletion.get("deleted_at") or ""
            local = None
            conflict_local = None
            if entity_type == "document":
                local = local_docs.get(key)
                if local:
                    conflict_local = {
                        "id": local["id"], "title": local["title"],
                        "authors": local["authors"], "year": local["year"],
                        "venue": local["venue"], "doi": local["doi"],
                        "updated_at": local["updated_at"] or "",
                    }
            elif entity_type == "vocab":
                local = conn.execute(
                    "SELECT * FROM vocab WHERE word=? COLLATE NOCASE OR sync_uid=?",
                    (key, key),
                ).fetchone()
                if local:
                    conflict_local = _sync_local_payload("vocab", local, VOCAB_CONFLICT_FIELDS)
                    conflict_local["word"] = local["word"]
            elif entity_type == "highlight":
                rows = conn.execute(
                    "SELECT h.*, d.doi, d.title AS doc_title FROM highlights h "
                    "JOIN documents d ON d.id=h.doc_id"
                ).fetchall()
                local = next(
                    (
                        row for row in rows
                        if (row["sync_uid"] and row["sync_uid"] == key)
                        or _highlight_sync_key(
                            _doc_key(row["doi"], row["doc_title"]), row["page"], row["text"]
                        ) == key
                    ),
                    None,
                )
                if local:
                    conflict_local = _sync_local_payload("highlight", local, HIGHLIGHT_CONFLICT_FIELDS)
            elif entity_type == "note":
                rows = conn.execute(
                    "SELECT n.*, d.doi, d.title AS doc_title FROM notes n "
                    "JOIN documents d ON d.id=n.doc_id"
                ).fetchall()
                local = next(
                    (
                        row for row in rows
                        if (row["sync_uid"] and row["sync_uid"] == key)
                        or _note_sync_key(
                            _doc_key(row["doi"], row["doc_title"]), row["page"], row["content"]
                        ) == key
                    ),
                    None,
                )
                if local:
                    conflict_local = _sync_local_payload("note", local, NOTE_CONFLICT_FIELDS)
            if local:
                local_updated = local["updated_at"] or local["created_at"] or ""
                if local_updated <= deleted_at:
                    if entity_type == "document":
                        conn.execute("DELETE FROM documents WHERE id=?", (local["id"],))
                        path = Path(local["path"])
                        if path.exists() and path.parent == PDF_DIR:
                            path.unlink(missing_ok=True)
                        source_path = local["source_path"] if "source_path" in local.keys() else ""
                        if source_path:
                            source = Path(source_path)
                            if source.exists() and source.parent == PDF_DIR:
                                source.unlink(missing_ok=True)
                        local_docs.pop(key, None)
                        doc_map.pop(key, None)
                    elif entity_type == "vocab":
                        conn.execute("DELETE FROM vocab WHERE id=?", (local["id"],))
                    elif entity_type == "highlight":
                        conn.execute("DELETE FROM highlights WHERE id=?", (local["id"],))
                    elif entity_type == "note":
                        conn.execute("DELETE FROM notes WHERE id=?", (local["id"],))
                    counts["deleted"] += 1
                    conn.execute(
                        "INSERT OR REPLACE INTO sync_deletions"
                        "(entity_type, entity_key, deleted_at, device) VALUES (?, ?, ?, ?)",
                        (entity_type, key, deleted_at, deletion.get("device") or ""),
                    )
                elif conflict_local is not None:
                    # Local edited after the cloud deletion: keep the object and
                    # leave the tombstone out until the user picks a side.
                    if not _deletion_is_ignored(conn, entity_type, key, deleted_at):
                        if _record_sync_conflict(
                            conn, entity_type, key, conflict_local,
                            {"deleted": True, "deleted_at": deleted_at},
                        ):
                            counts["conflicts"] += 1
            else:
                conn.execute(
                    "INSERT OR REPLACE INTO sync_deletions"
                    "(entity_type, entity_key, deleted_at, device) VALUES (?, ?, ?, ?)",
                    (entity_type, key, deleted_at, deletion.get("device") or ""),
                )
    base = _sync_base()
    for doc in snapshot.get("documents") or []:
        key = doc.get("key") or _doc_key(doc.get("doi", ""), doc.get("title", ""))
        if not key:
            continue
        if key in doc_map:
            local = local_docs[key]
            remote_updated = doc.get("updated_at") or ""
            local_updated = local["updated_at"] or ""
            fields = ("title", "authors", "year", "venue", "doi", "abstract", "tags")
            changed = any((local[field] or "") != (doc.get(field) or "") for field in fields)
            if changed and remote_updated > local_updated:
                with db() as conn:
                    if _record_sync_conflict(
                        conn, "document", key,
                        {field: local[field] for field in fields}
                        | {"updated_at": local_updated, "id": local["id"]},
                        doc,
                    ):
                        counts["conflicts"] += 1
            continue
        with db() as conn:
            tombstone = conn.execute(
                "SELECT deleted_at FROM sync_deletions WHERE entity_type='document' AND entity_key=?",
                (key,),
            ).fetchone()
        if tombstone:
            if (doc.get("updated_at") or "") > tombstone["deleted_at"]:
                with db() as conn:
                    if not _restore_is_ignored(
                        conn, "document", key, doc.get("updated_at") or ""
                    ) and _record_sync_conflict(
                        conn, "document", key,
                        {"deleted": True, "deleted_at": tombstone["deleted_at"]},
                        doc,
                    ):
                        counts["conflicts"] += 1
            continue
        epub_name = Path(doc.get("epub_name") or "").name
        epub_path = PDF_DIR / epub_name if epub_name else None
        if epub_path and not epub_path.exists() and get_setting("sync_pdfs") == "1":
            try:
                response = await client.get(f"{base}/pdfs/{epub_name}")
                if response.status_code == 200 and response.content.startswith(b"PK"):
                    epub_path.write_bytes(response.content)
            except httpx.HTTPError:
                pass
        pdf_name = Path(doc.get("pdf_name") or "").name
        local_path = PDF_DIR / pdf_name if pdf_name else None
        if local_path and not local_path.exists() and get_setting("sync_pdfs") == "1":
            try:
                response = await client.get(f"{base}/pdfs/{pdf_name}")
                if response.status_code == 200 and response.content.startswith((b"%PDF", b"PK")):
                    local_path.write_bytes(response.content)
            except httpx.HTTPError:
                pass
        doc_id = None
        if epub_path and epub_path.exists():
            result = _ingest_pdf_bytes(epub_path.read_bytes(), epub_name)
            doc_id = result["id"]
        elif local_path and local_path.exists():
            result = _ingest_pdf_bytes(local_path.read_bytes(), pdf_name)
            doc_id = result["id"]
        if doc_id is None:
            result = _reference_document(doc)
            doc_id = result["id"]
        with db() as conn:
            conn.execute(
                "UPDATE documents SET title=?, authors=?, year=?, venue=?, doi=?, abstract=?, "
                "tags=?, collection_id=?, favorite=?, status=?, last_page=?, reading_seconds=?, "
                "summary_json=?, updated_at=? WHERE id=?",
                (
                    doc.get("title") or "Untitled", doc.get("authors") or "",
                    doc.get("year") or "", doc.get("venue") or "", doc.get("doi") or "",
                    doc.get("abstract") or "", doc.get("tags") or "",
                    collection_ids.get(doc.get("collection") or ""),
                    doc.get("favorite") or 0, doc.get("status") or "unread",
                    doc.get("last_page") or 1, doc.get("reading_seconds") or 0,
                    doc.get("summary_json"), doc.get("updated_at") or now_iso(), doc_id,
                ),
            )
        doc_map[key] = doc_id
        counts["documents"] += 1
    with db() as conn:
        local_vocab: dict[tuple[str, str], sqlite3.Row] = {}
        for row in conn.execute("SELECT * FROM vocab"):
            if row["sync_uid"]:
                local_vocab[("uid", row["sync_uid"])] = row
            local_vocab[("word", (row["word"] or "").lower())] = row
        local_highlights: dict[tuple[str, str], sqlite3.Row] = {}
        for row in conn.execute(
            "SELECT h.*, d.doi, d.title AS doc_title FROM highlights h "
            "JOIN documents d ON d.id=h.doc_id"
        ):
            if row["sync_uid"]:
                local_highlights[("uid", row["sync_uid"])] = row
            local_highlights[(
                "content",
                _highlight_sync_key(_doc_key(row["doi"], row["doc_title"]), row["page"], row["text"]),
            )] = row
        local_notes: dict[tuple[str, str], sqlite3.Row] = {}
        for row in conn.execute(
            "SELECT n.*, d.doi, d.title AS doc_title FROM notes n "
            "JOIN documents d ON d.id=n.doc_id"
        ):
            if row["sync_uid"]:
                local_notes[("uid", row["sync_uid"])] = row
            local_notes[(
                "content",
                _note_sync_key(_doc_key(row["doi"], row["doc_title"]), row["page"], row["content"]),
            )] = row

        for item in snapshot.get("vocab") or []:
            word = item.get("word")
            if not word:
                continue
            uid = item.get("uid") or ""
            local = local_vocab.get(("uid", uid)) if uid else None
            if local is None:
                local = local_vocab.get(("word", word.lower()))
                if local is not None and uid and not local["sync_uid"]:
                    conn.execute(
                        "UPDATE vocab SET sync_uid=? WHERE id=?", (uid, local["id"])
                    )
            if local is not None:
                if _conflict_diff(local, item, VOCAB_CONFLICT_FIELDS):
                    local_updated = local["updated_at"] or local["created_at"] or ""
                    remote_updated = item.get("updated_at") or item.get("created_at") or ""
                    if remote_updated > local_updated:
                        key = local["sync_uid"] or uid or word.lower()
                        if _record_sync_conflict(
                            conn, "vocab", key,
                            _sync_local_payload("vocab", local, VOCAB_CONFLICT_FIELDS), item,
                        ):
                            counts["conflicts"] += 1
                continue
            tombstone = None
            for tomb_key in (uid, word.lower()):
                if not tomb_key:
                    continue
                row = conn.execute(
                    "SELECT deleted_at FROM sync_deletions "
                    "WHERE entity_type='vocab' AND entity_key=?",
                    (tomb_key,),
                ).fetchone()
                if row and (tombstone is None or row["deleted_at"] > tombstone["deleted_at"]):
                    tombstone = row
            if tombstone:
                if (item.get("updated_at") or "") > tombstone["deleted_at"]:
                    if not _restore_is_ignored(
                        conn, "vocab", uid or word.lower(), item.get("updated_at") or ""
                    ):
                        if _record_sync_conflict(
                            conn, "vocab", uid or word.lower(),
                            {"deleted": True, "deleted_at": tombstone["deleted_at"]},
                            item,
                        ):
                            counts["conflicts"] += 1
                continue
            card = Card()
            cursor = conn.execute(
                "INSERT OR IGNORE INTO vocab(word, lemma, phonetic, translation, definition, tag, "
                "exchange, context, doc_id, page, created_at, due, fsrs, reps, lapses, deck, mastered, "
                "source, updated_at, sync_uid) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    word, item.get("lemma") or word, item.get("phonetic") or "",
                    item.get("translation") or "", item.get("definition") or "",
                    item.get("tag") or "", item.get("exchange") or "",
                    item.get("context") or "", doc_map.get(item.get("doc_key")),
                    item.get("page"), item.get("created_at") or now_iso(),
                    item.get("due") or card.due.isoformat(),
                    item.get("fsrs") or card.to_json(),
                    item.get("reps") or 0, item.get("lapses") or 0,
                    item.get("deck") or "默认", item.get("mastered") or 0,
                    item.get("source") or "sync",
                    item.get("updated_at") or item.get("created_at") or now_iso(),
                    uid or uuid.uuid4().hex,
                ),
            )
            counts["vocab"] += cursor.rowcount

        for item in snapshot.get("highlights") or []:
            doc_id = doc_map.get(item.get("doc_key"))
            if not doc_id:
                continue
            uid = item.get("uid") or ""
            sync_key = _highlight_sync_key(
                item.get("doc_key") or "", item.get("page") or 0, item.get("text") or ""
            )
            local = local_highlights.get(("uid", uid)) if uid else None
            if local is None:
                local = local_highlights.get(("content", sync_key))
                if local is not None and uid and not local["sync_uid"]:
                    conn.execute(
                        "UPDATE highlights SET sync_uid=? WHERE id=?", (uid, local["id"])
                    )
            if local is not None:
                if _conflict_diff(local, item, HIGHLIGHT_CONFLICT_FIELDS):
                    local_updated = local["updated_at"] or local["created_at"] or ""
                    remote_updated = item.get("updated_at") or item.get("created_at") or ""
                    if remote_updated > local_updated:
                        key = local["sync_uid"] or uid or sync_key
                        if _record_sync_conflict(
                            conn, "highlight", key,
                            _sync_local_payload("highlight", local, HIGHLIGHT_CONFLICT_FIELDS), item,
                        ):
                            counts["conflicts"] += 1
                continue
            tombstone = None
            for tomb_key in (uid, sync_key):
                if not tomb_key:
                    continue
                row = conn.execute(
                    "SELECT deleted_at FROM sync_deletions "
                    "WHERE entity_type='highlight' AND entity_key=?",
                    (tomb_key,),
                ).fetchone()
                if row and (tombstone is None or row["deleted_at"] > tombstone["deleted_at"]):
                    tombstone = row
            if tombstone:
                if (item.get("updated_at") or "") > tombstone["deleted_at"]:
                    if not _restore_is_ignored(
                        conn, "highlight", uid or sync_key, item.get("updated_at") or ""
                    ):
                        if _record_sync_conflict(
                            conn, "highlight", uid or sync_key,
                            {"deleted": True, "deleted_at": tombstone["deleted_at"]},
                            item,
                        ):
                            counts["conflicts"] += 1
                continue
            card = Card()
            conn.execute(
                "INSERT INTO highlights(doc_id, page, color, text, rects, note, type, created_at, "
                "updated_at, due, fsrs, reps, sync_uid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    doc_id, item.get("page"), item.get("color") or "yellow",
                    item.get("text") or "", item.get("rects") or "[]",
                    item.get("note") or "", item.get("type") or "highlight",
                    item.get("created_at") or now_iso(),
                    item.get("updated_at") or item.get("created_at") or now_iso(),
                    item.get("due") or card.due.isoformat(),
                    item.get("fsrs") or card.to_json(), item.get("reps") or 0,
                    uid or uuid.uuid4().hex,
                ),
            )
            counts["highlights"] += 1

        for item in snapshot.get("notes") or []:
            doc_id = doc_map.get(item.get("doc_key"))
            if not doc_id:
                continue
            uid = item.get("uid") or ""
            sync_key = _note_sync_key(
                item.get("doc_key") or "", item.get("page") or 0, item.get("content") or ""
            )
            local = local_notes.get(("uid", uid)) if uid else None
            if local is None:
                local = local_notes.get(("content", sync_key))
                if local is not None and uid and not local["sync_uid"]:
                    conn.execute(
                        "UPDATE notes SET sync_uid=? WHERE id=?", (uid, local["id"])
                    )
            if local is not None:
                if _conflict_diff(local, item, NOTE_CONFLICT_FIELDS):
                    local_updated = local["updated_at"] or local["created_at"] or ""
                    remote_updated = item.get("updated_at") or item.get("created_at") or ""
                    if remote_updated > local_updated:
                        key = local["sync_uid"] or uid or sync_key
                        if _record_sync_conflict(
                            conn, "note", key,
                            _sync_local_payload("note", local, NOTE_CONFLICT_FIELDS), item,
                        ):
                            counts["conflicts"] += 1
                continue
            tombstone = None
            for tomb_key in (uid, sync_key):
                if not tomb_key:
                    continue
                row = conn.execute(
                    "SELECT deleted_at FROM sync_deletions "
                    "WHERE entity_type='note' AND entity_key=?",
                    (tomb_key,),
                ).fetchone()
                if row and (tombstone is None or row["deleted_at"] > tombstone["deleted_at"]):
                    tombstone = row
            if tombstone:
                if (item.get("updated_at") or "") > tombstone["deleted_at"]:
                    if not _restore_is_ignored(
                        conn, "note", uid or sync_key, item.get("updated_at") or ""
                    ):
                        if _record_sync_conflict(
                            conn, "note", uid or sync_key,
                            {"deleted": True, "deleted_at": tombstone["deleted_at"]},
                            item,
                        ):
                            counts["conflicts"] += 1
                continue
            conn.execute(
                "INSERT INTO notes(doc_id, page, content, title, created_at, updated_at, sync_uid) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    doc_id, item.get("page"), item.get("content") or "",
                    item.get("title") or "", item.get("created_at") or now_iso(),
                    item.get("updated_at") or item.get("created_at") or now_iso(),
                    uid or uuid.uuid4().hex,
                ),
            )
            counts["notes"] += 1
        for item in snapshot.get("topics") or []:
            if not item.get("name") or not item.get("query"):
                continue
            exists = conn.execute("SELECT id FROM topics WHERE name=?", (item["name"],)).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT INTO topics(name, query, sources, days, created_at, last_checked, last_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    item["name"], item["query"], item.get("sources") or "arxiv,openalex",
                    item.get("days") or 30, item.get("created_at") or now_iso(),
                    item.get("last_checked"), item.get("last_count") or 0,
                ),
            )
            counts["topics"] += 1
        for item in snapshot.get("articles") or []:
            if not item.get("title") or not item.get("text"):
                continue
            exists = conn.execute(
                "SELECT id FROM articles WHERE title=? AND text=?", (item["title"], item["text"])
            ).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT INTO articles(title, text, created_at, source, category, year, score) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    item["title"], item["text"], item.get("created_at") or now_iso(),
                    item.get("source") or "", item.get("category") or "",
                    item.get("year") or "", item.get("score") or 0,
                ),
            )
            counts["articles"] += 1
    return counts


async def _push_sync_snapshot(client: httpx.AsyncClient, base: str, snapshot: dict[str, Any]) -> dict[str, int]:
    uploaded = 0
    if get_setting("sync_pdfs") == "1":
        for doc in snapshot.get("documents") or []:
            names = [doc.get("pdf_name"), doc.get("epub_name")]
            for name in dict.fromkeys(name for name in names if name):
                path = PDF_DIR / name
                if not path.exists():
                    continue
                head = await client.request("HEAD", f"{base}/pdfs/{name}")
                if head.status_code != 200:
                    content_type = (
                        "application/epub+zip" if name.lower().endswith(".epub")
                        else "application/pdf"
                    )
                    response = await client.put(
                        f"{base}/pdfs/{name}", content=path.read_bytes(),
                        headers={"Content-Type": content_type},
                    )
                    if response.status_code < 400:
                        uploaded += 1
    response = await client.put(
        f"{base}/snapshot.json",
        content=json.dumps(snapshot, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    response.raise_for_status()
    return {"pdfs": uploaded}


@app.get("/api/sync/status")
async def sync_status() -> dict[str, Any]:
    url = get_setting("sync_url")
    if not url:
        return {"configured": False, "reachable": False, "last_sync": get_setting("last_sync"), "message": "还没有配置 WebDAV"}
    try:
        async with httpx.AsyncClient(timeout=15, auth=_sync_auth()) as client:
            response = await client.request("PROPFIND", url, headers={"Depth": "0"})
        return {
            "configured": True,
            "reachable": response.status_code < 400,
            "last_sync": get_setting("last_sync"),
            "message": "已连接" if response.status_code < 400 else f"WebDAV 返回 {response.status_code}",
        }
    except httpx.HTTPError as exc:
        return {"configured": True, "reachable": False, "last_sync": get_setting("last_sync"), "message": str(exc)}


@app.post("/api/sync/test")
async def sync_test() -> dict[str, Any]:
    base = _sync_base()
    try:
        async with httpx.AsyncClient(timeout=20, auth=_sync_auth(), follow_redirects=True) as client:
            await _ensure_dav(client, base)
            await _ensure_dav(client, f"{base}/pdfs")
        return {"ok": "1", "message": "WebDAV 可用"}
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"WebDAV 连接失败：{exc}") from exc


@app.get("/api/sync/conflicts")
def sync_conflicts() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM sync_conflicts WHERE resolved=0 ORDER BY id DESC"
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["local"] = json.loads(item.pop("local_json"))
        except json.JSONDecodeError:
            item["local"] = {}
        try:
            item["remote"] = json.loads(item.pop("remote_json"))
        except json.JSONDecodeError:
            item["remote"] = {}
        result.append(item)
    return result


def _doc_row_for(conn: sqlite3.Connection, key: str) -> Optional[sqlite3.Row]:
    if not key:
        return None
    for row in conn.execute("SELECT * FROM documents").fetchall():
        if _doc_key(row["doi"], row["title"]) == key:
            return row
    return None


def _vocab_row_for(
    conn: sqlite3.Connection, key: str, local: Optional[dict[str, Any]] = None
) -> Optional[sqlite3.Row]:
    if local:
        if local.get("id"):
            row = conn.execute("SELECT * FROM vocab WHERE id=?", (local["id"],)).fetchone()
            if row:
                return row
        if local.get("uid"):
            row = conn.execute("SELECT * FROM vocab WHERE sync_uid=?", (local["uid"],)).fetchone()
            if row:
                return row
        if local.get("word"):
            row = conn.execute(
                "SELECT * FROM vocab WHERE word=? COLLATE NOCASE", (local["word"],)
            ).fetchone()
            if row:
                return row
    return conn.execute(
        "SELECT * FROM vocab WHERE sync_uid=? OR word=? COLLATE NOCASE", (key, key)
    ).fetchone()


def _highlight_row_for(
    conn: sqlite3.Connection, key: str, local: Optional[dict[str, Any]] = None
) -> Optional[sqlite3.Row]:
    rows = conn.execute(
        "SELECT h.*, d.doi, d.title AS doc_title FROM highlights h "
        "JOIN documents d ON d.id=h.doc_id"
    ).fetchall()
    if local:
        if local.get("id"):
            row = next((item for item in rows if item["id"] == local["id"]), None)
            if row:
                return row
        if local.get("uid"):
            row = next((item for item in rows if item["sync_uid"] == local["uid"]), None)
            if row:
                return row
    return next(
        (
            item for item in rows
            if (item["sync_uid"] and item["sync_uid"] == key)
            or _highlight_sync_key(
                _doc_key(item["doi"], item["doc_title"]), item["page"], item["text"]
            ) == key
        ),
        None,
    )


def _note_row_for(
    conn: sqlite3.Connection, key: str, local: Optional[dict[str, Any]] = None
) -> Optional[sqlite3.Row]:
    rows = conn.execute(
        "SELECT n.*, d.doi, d.title AS doc_title FROM notes n "
        "JOIN documents d ON d.id=n.doc_id"
    ).fetchall()
    if local:
        if local.get("id"):
            row = next((item for item in rows if item["id"] == local["id"]), None)
            if row:
                return row
        if local.get("uid"):
            row = next((item for item in rows if item["sync_uid"] == local["uid"]), None)
            if row:
                return row
    return next(
        (
            item for item in rows
            if (item["sync_uid"] and item["sync_uid"] == key)
            or _note_sync_key(
                _doc_key(item["doi"], item["doc_title"]), item["page"], item["content"]
            ) == key
        ),
        None,
    )


def _forget_deletions(conn: sqlite3.Connection, entity_type: str, keys: list[str]) -> None:
    for key in {key for key in keys if key}:
        conn.execute(
            "DELETE FROM sync_deletions WHERE entity_type=? AND entity_key=?",
            (entity_type, key),
        )


def _ignore_deletion(
    conn: sqlite3.Connection, entity_type: str, keys: list[str], deleted_at: str
) -> None:
    """Remember that the user kept a local object against this cloud deletion.

    Without this, the still-existing remote tombstone would raise the same
    conflict again on the very next sync, before the local snapshot is pushed.
    """
    for key in {key for key in keys if key}:
        conn.execute(
            "INSERT OR REPLACE INTO sync_ignored_deletions"
            "(entity_type, entity_key, deleted_at, created_at) VALUES (?, ?, ?, ?)",
            (entity_type, key, deleted_at, now_iso()),
        )


def _deletion_is_ignored(
    conn: sqlite3.Connection, entity_type: str, key: str, deleted_at: str
) -> bool:
    row = conn.execute(
        "SELECT deleted_at FROM sync_ignored_deletions "
        "WHERE entity_type=? AND entity_key=?",
        (entity_type, key),
    ).fetchone()
    return bool(row and deleted_at <= row["deleted_at"])


def _ignore_restore(
    conn: sqlite3.Connection, entity_type: str, keys: list[str], updated_at: str
) -> None:
    for key in {key for key in keys if key}:
        conn.execute(
            "INSERT OR REPLACE INTO sync_ignored_restores"
            "(entity_type, entity_key, updated_at, created_at) VALUES (?, ?, ?, ?)",
            (entity_type, key, updated_at, now_iso()),
        )


def _restore_is_ignored(
    conn: sqlite3.Connection, entity_type: str, key: str, updated_at: str
) -> bool:
    row = conn.execute(
        "SELECT updated_at FROM sync_ignored_restores "
        "WHERE entity_type=? AND entity_key=?",
        (entity_type, key),
    ).fetchone()
    return bool(row and updated_at <= row["updated_at"])


def _insert_remote_vocab(conn: sqlite3.Connection, remote: dict[str, Any]) -> None:
    word = remote.get("word")
    if not word:
        return
    card = Card()
    conn.execute(
        "INSERT INTO vocab(word, lemma, phonetic, translation, definition, tag, exchange, "
        "context, doc_id, page, created_at, due, fsrs, reps, lapses, deck, mastered, source, "
        "updated_at, sync_uid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            word, remote.get("lemma") or word, remote.get("phonetic") or "",
            remote.get("translation") or "", remote.get("definition") or "",
            remote.get("tag") or "", remote.get("exchange") or "",
            remote.get("context") or "", None, remote.get("page"),
            remote.get("created_at") or now_iso(),
            remote.get("due") or card.due.isoformat(),
            remote.get("fsrs") or card.to_json(),
            remote.get("reps") or 0, remote.get("lapses") or 0,
            remote.get("deck") or "默认", remote.get("mastered") or 0,
            remote.get("source") or "sync",
            remote.get("updated_at") or now_iso(),
            remote.get("uid") or uuid.uuid4().hex,
        ),
    )


def _insert_remote_highlight(conn: sqlite3.Connection, remote: dict[str, Any]) -> None:
    doc = _doc_row_for(conn, remote.get("doc_key") or "")
    if not doc:
        return
    card = Card()
    conn.execute(
        "INSERT INTO highlights(doc_id, page, color, text, rects, note, type, created_at, "
        "updated_at, due, fsrs, reps, sync_uid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            doc["id"], remote.get("page") or 1, remote.get("color") or "yellow",
            remote.get("text") or "", remote.get("rects") or "[]",
            remote.get("note") or "", remote.get("type") or "highlight",
            remote.get("created_at") or now_iso(),
            remote.get("updated_at") or now_iso(),
            remote.get("due") or card.due.isoformat(),
            remote.get("fsrs") or card.to_json(), remote.get("reps") or 0,
            remote.get("uid") or uuid.uuid4().hex,
        ),
    )


def _insert_remote_note(conn: sqlite3.Connection, remote: dict[str, Any]) -> None:
    doc = _doc_row_for(conn, remote.get("doc_key") or "")
    if not doc:
        return
    conn.execute(
        "INSERT INTO notes(doc_id, page, content, title, created_at, updated_at, sync_uid) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            doc["id"], remote.get("page") or 1, remote.get("content") or "",
            remote.get("title") or "", remote.get("created_at") or now_iso(),
            remote.get("updated_at") or now_iso(),
            remote.get("uid") or uuid.uuid4().hex,
        ),
    )


class ConflictResolveIn(BaseModel):
    choice: str = "local"


@app.post("/api/sync/conflicts/{conflict_id}/resolve")
def resolve_sync_conflict(conflict_id: int, payload: ConflictResolveIn) -> dict[str, str]:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM sync_conflicts WHERE id=?", (conflict_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "冲突不存在。")
        local = json.loads(row["local_json"])
        remote = json.loads(row["remote_json"])
        key = row["entity_key"]
        entity_type = row["entity_type"]
        if payload.choice == "cloud":
            if entity_type == "document":
                doc = _doc_row_for(conn, key)
                if remote.get("deleted"):
                    if doc:
                        path = Path(doc["path"])
                        conn.execute("DELETE FROM documents WHERE id=?", (doc["id"],))
                        if path.exists() and path.parent == PDF_DIR:
                            path.unlink(missing_ok=True)
                        source_path = doc["source_path"] if "source_path" in doc.keys() else ""
                        if source_path:
                            source = Path(source_path)
                            if source.exists() and source.parent == PDF_DIR:
                                source.unlink(missing_ok=True)
                else:
                    if not doc:
                        result = _reference_document(remote)
                        doc = conn.execute(
                            "SELECT * FROM documents WHERE id=?", (result["id"],)
                        ).fetchone()
                    if doc:
                        conn.execute(
                            "UPDATE documents SET title=?, authors=?, year=?, venue=?, doi=?, "
                            "abstract=?, tags=?, favorite=?, status=?, last_page=?, "
                            "reading_seconds=?, summary_json=?, updated_at=? WHERE id=?",
                            (
                                remote.get("title") or doc["title"],
                                remote.get("authors") or doc["authors"],
                                remote.get("year") or doc["year"],
                                remote.get("venue") or doc["venue"],
                                remote.get("doi") or doc["doi"],
                                remote.get("abstract") or doc["abstract"],
                                remote.get("tags") or doc["tags"],
                                remote.get("favorite") or doc["favorite"],
                                remote.get("status") or doc["status"],
                                remote.get("last_page") or doc["last_page"],
                                remote.get("reading_seconds") or doc["reading_seconds"],
                                remote.get("summary_json") or doc["summary_json"],
                                remote.get("updated_at") or now_iso(),
                                doc["id"],
                            ),
                        )
            elif entity_type == "vocab":
                target = _vocab_row_for(conn, key, local)
                if remote.get("deleted"):
                    if target:
                        conn.execute("DELETE FROM vocab WHERE id=?", (target["id"],))
                else:
                    if target:
                        conn.execute(
                            "UPDATE vocab SET lemma=?, phonetic=?, translation=?, definition=?, "
                            "tag=?, exchange=?, context=?, deck=?, mastered=?, updated_at=?, "
                            "sync_uid=COALESCE(NULLIF(sync_uid, ''), ?) WHERE id=?",
                            (
                                remote.get("lemma") or target["lemma"],
                                remote.get("phonetic") or target["phonetic"],
                                remote.get("translation") or target["translation"],
                                remote.get("definition") or target["definition"],
                                remote.get("tag") or target["tag"],
                                remote.get("exchange") or target["exchange"],
                                remote.get("context") or target["context"],
                                remote.get("deck") or target["deck"],
                                remote.get("mastered") if remote.get("mastered") is not None else target["mastered"],
                                remote.get("updated_at") or now_iso(),
                                remote.get("uid") or "",
                                target["id"],
                            ),
                        )
                    else:
                        _insert_remote_vocab(conn, remote)
                    _forget_deletions(
                        conn, "vocab",
                        [key, local.get("uid") or "", remote.get("uid") or "", (remote.get("word") or "").lower()],
                    )
            elif entity_type == "highlight":
                target = _highlight_row_for(conn, key, local)
                if remote.get("deleted"):
                    if target:
                        conn.execute("DELETE FROM highlights WHERE id=?", (target["id"],))
                else:
                    if target:
                        conn.execute(
                            "UPDATE highlights SET page=?, color=?, text=?, rects=?, note=?, type=?, "
                            "updated_at=?, sync_uid=COALESCE(NULLIF(sync_uid, ''), ?) WHERE id=?",
                            (
                                remote.get("page") or target["page"],
                                remote.get("color") or target["color"],
                                remote.get("text") or target["text"],
                                remote.get("rects") or target["rects"],
                                remote.get("note") or target["note"],
                                remote.get("type") or target["type"],
                                remote.get("updated_at") or now_iso(),
                                remote.get("uid") or "",
                                target["id"],
                            ),
                        )
                    else:
                        _insert_remote_highlight(conn, remote)
                    _forget_deletions(
                        conn, "highlight",
                        [key, local.get("uid") or "", remote.get("uid") or ""],
                    )
            elif entity_type == "note":
                target = _note_row_for(conn, key, local)
                if remote.get("deleted"):
                    if target:
                        conn.execute("DELETE FROM notes WHERE id=?", (target["id"],))
                else:
                    if target:
                        conn.execute(
                            "UPDATE notes SET page=?, title=?, content=?, updated_at=?, "
                            "sync_uid=COALESCE(NULLIF(sync_uid, ''), ?) WHERE id=?",
                            (
                                remote.get("page") or target["page"],
                                remote.get("title") or target["title"],
                                remote.get("content") or target["content"],
                                remote.get("updated_at") or now_iso(),
                                remote.get("uid") or "",
                                target["id"],
                            ),
                        )
                    else:
                        _insert_remote_note(conn, remote)
                    _forget_deletions(
                        conn, "note",
                        [key, local.get("uid") or "", remote.get("uid") or ""],
                    )
        else:
            # Local wins: keep the local object, retract the cloud deletion and
            # bump its timestamp so the next merge sees it as the newer side.
            target = None
            if entity_type == "document":
                target = _doc_row_for(conn, key)
            elif entity_type == "vocab":
                target = _vocab_row_for(conn, key, local)
            elif entity_type == "highlight":
                target = _highlight_row_for(conn, key, local)
            elif entity_type == "note":
                target = _note_row_for(conn, key, local)
            if target and not local.get("deleted"):
                table = {
                    "document": "documents", "vocab": "vocab",
                    "highlight": "highlights", "note": "notes",
                }[entity_type]
                conn.execute(
                    f"UPDATE {table} SET updated_at=? WHERE id=?",
                    (now_iso(), target["id"]),
                )
                keys = [key, local.get("uid") or ""]
                if entity_type == "vocab":
                    keys.append((target["word"] or "").lower())
                elif entity_type in ("highlight", "note"):
                    sync_key = (
                        _highlight_sync_key(
                            _doc_key(target["doi"], target["doc_title"]),
                            target["page"], target["text"],
                        )
                        if entity_type == "highlight"
                        else _note_sync_key(
                            _doc_key(target["doi"], target["doc_title"]),
                            target["page"], target["content"],
                        )
                    )
                    keys += [target["sync_uid"] or "", sync_key]
                if remote.get("deleted"):
                    _forget_deletions(conn, entity_type, keys)
                    _ignore_deletion(
                        conn, entity_type, keys,
                        remote.get("deleted_at") or now_iso(),
                    )
            elif local.get("deleted") and not remote.get("deleted"):
                # Local deleted, cloud still has the object: keep the deletion
                # and suppress this exact cloud version until it is pushed away.
                keys = [key, local.get("uid") or "", remote.get("uid") or ""]
                if entity_type == "vocab":
                    keys += [
                        (local.get("word") or "").lower(),
                        (remote.get("word") or "").lower(),
                    ]
                elif entity_type in ("highlight", "note"):
                    doc_key = remote.get("doc_key") or ""
                    if entity_type == "highlight":
                        keys.append(_highlight_sync_key(
                            doc_key, remote.get("page") or 0, remote.get("text") or ""
                        ))
                    else:
                        keys.append(_note_sync_key(
                            doc_key, remote.get("page") or 0, remote.get("content") or ""
                        ))
                _ignore_restore(
                    conn, entity_type, keys, remote.get("updated_at") or ""
                )
        conn.execute("UPDATE sync_conflicts SET resolved=1 WHERE id=?", (conflict_id,))
    return {"ok": "1"}


@app.post("/api/sync/now")
async def sync_now() -> dict[str, Any]:
    base = _sync_base()
    counts = {"documents": 0, "vocab": 0, "highlights": 0, "notes": 0, "topics": 0, "articles": 0}
    uploaded = 0
    async with httpx.AsyncClient(timeout=180, auth=_sync_auth(), follow_redirects=True) as client:
        await _ensure_dav(client, base)
        await _ensure_dav(client, f"{base}/pdfs")
        response = await client.get(f"{base}/snapshot.json")
        if response.status_code == 200:
            try:
                remote = response.json()
            except ValueError:
                remote = {}
            counts.update(await _merge_sync_snapshot(remote, client))
        snapshot = _build_sync_snapshot()
        result = await _push_sync_snapshot(client, base, snapshot)
        uploaded = result["pdfs"]
    set_setting("last_sync", now_iso())
    return {"counts": counts, "uploaded_pdfs": uploaded, "last_sync": get_setting("last_sync"), "device": _sync_device()}


# ---------------------------------------------------------------------------
# topic subscriptions / daily refresh
# ---------------------------------------------------------------------------
class TopicIn(BaseModel):
    name: str
    query: str
    sources: str = "arxiv,openalex"
    days: int = 30


def _list_topics() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT t.*, (SELECT COUNT(*) FROM topic_items ti "
            "WHERE ti.topic_id=t.id AND ti.seen=0) AS new_count "
            "FROM topics t ORDER BY t.id"
        ).fetchall()
    return [dict(row) for row in rows]


def _topic_key(paper: dict[str, Any]) -> str:
    doi = (paper.get("doi") or "").lower().strip()
    if doi:
        return doi
    return re.sub(r"[^a-z0-9]+", "", (paper.get("title") or "").lower())[:120]


async def _refresh_topic_async(topic_id: int) -> dict[str, Any]:
    with db() as conn:
        topic = conn.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()
    if not topic:
        raise HTTPException(404, "主题不存在。")
    sources = [source for source in (topic["sources"] or "").split(",") if source in DISCOVER_SOURCES]
    result = await _run_discovery(topic["query"], sources or ["arxiv", "openalex"], topic["days"], 12)
    current_year = datetime.now(timezone.utc).year
    papers = [
        paper for paper in result["papers"]
        if not paper["year"] or not paper["year"].isdigit() or int(paper["year"]) <= current_year
    ]
    papers = _rank_discover(papers, topic["query"], "recent")[:12]
    new_count = 0
    with db() as conn:
        previous = {
            row["paper_key"]
            for row in conn.execute(
                "SELECT paper_key FROM topic_items WHERE topic_id=?", (topic_id,)
            ).fetchall()
        }
        conn.execute("DELETE FROM topic_items WHERE topic_id=?", (topic_id,))
        for paper in papers:
            key = _topic_key(paper)
            if not key:
                continue
            unseen = 0 if key in previous else 1
            new_count += unseen
            conn.execute(
                "INSERT OR IGNORE INTO topic_items(topic_id, paper_key, payload, created_at, seen) "
                "VALUES (?, ?, ?, ?, ?)",
                (topic_id, key, json.dumps(paper, ensure_ascii=False), now_iso(), 0 if unseen else 1),
            )
        conn.execute(
            "UPDATE topics SET last_checked=?, last_count=? WHERE id=?",
            (now_iso(), new_count, topic_id),
        )
        if new_count:
            title = f"「{topic['name']}」有 {new_count} 篇新论文"
            body = "；".join(paper["title"] for paper in papers[:2])[:240]
            conn.execute(
                "INSERT INTO notifications(kind, title, body, link, read, created_at) "
                "VALUES ('topic', ?, ?, ?, 0, ?)",
                (title, body, f"topic:{topic_id}", now_iso()),
            )
    if new_count:
        _show_system_toast(title, body)
    return {"topic_id": topic_id, "new_count": new_count, "papers": len(papers), "errors": result["errors"]}


def _show_system_toast(title: str, body: str) -> None:
    try:
        from winotify import Notification

        Notification(
            app_id="Folio", title=title, msg=body[:200], duration="short"
        ).show()
    except Exception:  # noqa: BLE001
        pass


def _background_topic_loop() -> None:
    import time

    time.sleep(15)
    while True:
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
            with db() as conn:
                rows = conn.execute(
                    "SELECT id FROM topics WHERE last_checked IS NULL OR last_checked < ?",
                    (cutoff,),
                ).fetchall()
            for row in rows:
                asyncio.run(_refresh_topic_async(row["id"]))
        except Exception:  # noqa: BLE001
            pass
        time.sleep(3600)


threading.Thread(target=_background_topic_loop, daemon=True).start()


@app.get("/api/topics")
def list_topics() -> list[dict[str, Any]]:
    return _list_topics()


@app.post("/api/topics")
def create_topic(payload: TopicIn) -> dict[str, Any]:
    name = payload.name.strip()
    query = payload.query.strip()
    if not name or not query:
        raise HTTPException(400, "主题名和检索词不能为空。")
    sources = [source for source in payload.sources.split(",") if source in DISCOVER_SOURCES]
    with db() as conn:
        cursor = conn.execute(
            "INSERT INTO topics(name, query, sources, days, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, query, ",".join(sources) or "arxiv,openalex", max(0, min(3650, payload.days)), now_iso()),
        )
        topic_id = int(cursor.lastrowid)
    return {"id": topic_id}


@app.delete("/api/topics/{topic_id}")
def delete_topic(topic_id: int) -> dict[str, str]:
    with db() as conn:
        conn.execute("DELETE FROM topics WHERE id=?", (topic_id,))
    return {"ok": "1"}


@app.post("/api/topics/{topic_id}/refresh")
async def refresh_topic(topic_id: int) -> dict[str, Any]:
    return await _refresh_topic_async(topic_id)


@app.post("/api/topics/refresh-due")
def refresh_due_topics() -> dict[str, Any]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=20)).isoformat()
    with db() as conn:
        rows = conn.execute(
            "SELECT id FROM topics WHERE last_checked IS NULL OR last_checked < ?", (cutoff,)
        ).fetchall()
    for row in rows:
        threading.Thread(target=lambda topic_id=row["id"]: asyncio.run(_refresh_topic_async(topic_id)), daemon=True).start()
    return {"started": len(rows)}


@app.get("/api/topics/{topic_id}/items")
def topic_items(topic_id: int, limit: int = 30) -> dict[str, Any]:
    with db() as conn:
        topic = conn.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()
        if not topic:
            raise HTTPException(404, "主题不存在。")
        rows = conn.execute(
            "SELECT payload, seen, created_at FROM topic_items WHERE topic_id=? "
            "ORDER BY id DESC LIMIT ?",
            (topic_id, max(1, min(100, limit))),
        ).fetchall()
    papers = []
    for row in rows:
        try:
            paper = json.loads(row["payload"])
        except json.JSONDecodeError:
            continue
        paper["seen"] = bool(row["seen"])
        papers.append(paper)
    return {"topic": dict(topic), "papers": papers}


@app.post("/api/topics/{topic_id}/seen")
def mark_topic_seen(topic_id: int) -> dict[str, str]:
    with db() as conn:
        conn.execute("UPDATE topic_items SET seen=1 WHERE topic_id=?", (topic_id,))
    return {"ok": "1"}


@app.get("/api/notifications")
def list_notifications(limit: int = 30) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM notifications ORDER BY id DESC LIMIT ?",
            (max(1, min(100, limit)),),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["read"] = bool(item["read"])
        result.append(item)
    return result


@app.post("/api/notifications/{notification_id}/read")
def read_notification(notification_id: int) -> dict[str, str]:
    with db() as conn:
        conn.execute("UPDATE notifications SET read=1 WHERE id=?", (notification_id,))
    return {"ok": "1"}


@app.post("/api/notifications/read-all")
def read_all_notifications() -> dict[str, str]:
    with db() as conn:
        conn.execute("UPDATE notifications SET read=1 WHERE read=0")
    return {"ok": "1"}


# ---------------------------------------------------------------------------
# vocabulary & FSRS
# ---------------------------------------------------------------------------
def _vocab_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item.pop("fsrs", None)
    item.pop("sync_uid", None)
    item["translation"] = (item.get("translation") or "").replace("\\n", "\n")
    item["definition"] = (item.get("definition") or "").replace("\\n", "\n")
    return item


@app.get("/api/vocab")
def list_vocab(
    q: str = "", tag: str = "", deck: str = "", status: str = ""
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM vocab WHERE 1=1"
    params: list[Any] = []
    if q.strip():
        like = f"%{q.strip()}%"
        sql += " AND (word LIKE ? OR translation LIKE ?)"
        params.extend([like, like])
    if tag:
        sql += " AND (' ' || tag || ' ') LIKE ?"
        params.append(f"% {tag} %")
    if deck:
        sql += " AND deck = ?"
        params.append(deck)
    if status == "due":
        sql += " AND due <= ? AND mastered = 0"
        params.append(now_iso())
    elif status == "mastered":
        sql += " AND mastered = 1"
    elif status == "learning":
        sql += " AND due > ? AND mastered = 0"
        params.append(now_iso())
    sql += " ORDER BY created_at DESC"
    with db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_vocab_row(row) for row in rows]


class VocabPatch(BaseModel):
    mastered: Optional[int] = None
    deck: Optional[str] = None


@app.patch("/api/vocab/{vocab_id}")
def update_vocab(vocab_id: int, payload: VocabPatch) -> dict[str, Any]:
    values = payload.model_dump(exclude_unset=True)
    if values:
        values["updated_at"] = now_iso()
        assignments = ", ".join(f"{key}=?" for key in values)
        with db() as conn:
            conn.execute(
                f"UPDATE vocab SET {assignments} WHERE id=?",
                [*values.values(), vocab_id],
            )
    with db() as conn:
        row = conn.execute("SELECT * FROM vocab WHERE id=?", (vocab_id,)).fetchone()
    if not row:
        raise HTTPException(404, "生词不存在。")
    return _vocab_row(row)


@app.get("/api/vocab/stats")
def vocab_stats() -> dict[str, Any]:
    now = now_iso()
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
        due = conn.execute(
            "SELECT COUNT(*) FROM vocab WHERE due <= ? AND mastered = 0", (now,)
        ).fetchone()[0]
        mastered = conn.execute(
            "SELECT COUNT(*) FROM vocab WHERE mastered = 1"
        ).fetchone()[0]
        tag_rows = conn.execute("SELECT tag FROM vocab").fetchall()
        reviews = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        today = datetime.now(timezone.utc).date().isoformat()
        reviews_today = conn.execute(
            "SELECT COUNT(*) FROM reviews WHERE reviewed_at LIKE ?", (today + "%",)
        ).fetchone()[0]
    tags: dict[str, int] = {}
    for row in tag_rows:
        for tag in (row["tag"] or "").split():
            tags[tag] = tags.get(tag, 0) + 1
    return {
        "total": total,
        "due": due,
        "mastered": mastered,
        "learning": max(0, total - due - mastered),
        "reviews": reviews,
        "reviews_today": reviews_today,
        "tags": tags,
    }


@app.get("/api/review/history")
def review_history(days: int = 90) -> dict[str, Any]:
    days = max(7, min(365, days))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    with db() as conn:
        rows = conn.execute(
            "SELECT substr(reviewed_at, 1, 10) AS day, COUNT(*) AS count "
            "FROM reviews WHERE reviewed_at >= ? GROUP BY day ORDER BY day",
            (since,),
        ).fetchall()
    return {"days": days, "data": [dict(row) for row in rows]}


@app.post("/api/vocab")
def add_vocab(payload: VocabIn) -> dict[str, Any]:
    entry = lookup_word(payload.word)
    word = (entry.get("word") or _clean_word(payload.word) or payload.word).strip()
    if not word:
        raise HTTPException(400, "单词为空。")
    with db() as conn:
        existing = conn.execute("SELECT * FROM vocab WHERE word=?", (word,)).fetchone()
        if existing:
            for tomb_key in (word.lower(), existing["sync_uid"]):
                if tomb_key:
                    conn.execute(
                        "DELETE FROM sync_deletions WHERE entity_type='vocab' AND entity_key=?",
                        (tomb_key,),
                    )
            return _vocab_row(existing)
        card = Card()
        cursor = conn.execute(
            """INSERT INTO vocab(word, lemma, phonetic, translation, definition, tag,
               exchange, context, doc_id, page, created_at, due, fsrs, updated_at, sync_uid)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                word,
                entry.get("word", word),
                entry.get("phonetic", ""),
                entry.get("translation", ""),
                entry.get("definition", ""),
                " ".join(entry.get("tag", [])) if isinstance(entry.get("tag"), list) else entry.get("tag", ""),
                json.dumps(entry.get("exchange", []), ensure_ascii=False)
                if isinstance(entry.get("exchange"), list)
                else (entry.get("exchange") or ""),
                payload.context[:1000],
                payload.doc_id,
                payload.page,
                now_iso(),
                card.due.isoformat(),
                card.to_json(),
                now_iso(),
                uuid.uuid4().hex,
            ),
        )
        conn.execute(
            "DELETE FROM sync_deletions WHERE entity_type='vocab' AND entity_key=?",
            (word.lower(),),
        )
        row = conn.execute("SELECT * FROM vocab WHERE id=?", (cursor.lastrowid,)).fetchone()
    return _vocab_row(row)


@app.get("/api/vocab/export.csv")
def export_vocab() -> Response:
    with db() as conn:
        rows = conn.execute(
            "SELECT word, phonetic, translation, definition, tag, context, due "
            "FROM vocab ORDER BY word"
        ).fetchall()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["word", "phonetic", "translation", "definition", "tags", "context", "due"])
    for row in rows:
        writer.writerow(
            [
                row["word"],
                row["phonetic"],
                (row["translation"] or "").replace("\\n", " / "),
                (row["definition"] or "").replace("\\n", " / "),
                row["tag"],
                row["context"],
                row["due"],
            ]
        )
    return Response(
        content="﻿" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="folio-vocab.csv"'},
    )


@app.get("/api/vocab/export.apkg")
def export_vocab_apkg() -> FileResponse:
    with db() as conn:
        rows = conn.execute(
            "SELECT word, phonetic, translation, definition, tag, context "
            "FROM vocab ORDER BY word"
        ).fetchall()
    model = genanki.Model(
        1747395211,
        "Folio Vocabulary",
        fields=[
            {"name": "Word"},
            {"name": "Phonetic"},
            {"name": "Translation"},
            {"name": "Definition"},
            {"name": "Context"},
        ],
        templates=[
            {
                "name": "Folio Card",
                "qfmt": '<div class="word">{{Word}}</div>'
                        '<div class="phonetic">{{Phonetic}}</div>'
                        '<div class="context">{{Context}}</div>',
                "afmt": '{{FrontSide}}<hr id="answer">'
                        '<div class="trans">{{Translation}}</div>'
                        '<div class="def">{{Definition}}</div>',
            }
        ],
        css="""
        .card { font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 20px; text-align: left; color: #1d1d1f; background: #ffffff; }
        .word { font-size: 34px; font-weight: 700; }
        .phonetic { color: #6e6e73; font-family: Georgia, serif; margin: 4px 0 14px; }
        .context { color: #6e6e73; font-size: 16px; line-height: 1.7;
                   background: #f2f2f7; padding: 12px; border-radius: 8px; }
        .trans { font-size: 19px; line-height: 1.8; }
        .def { color: #6e6e73; font-size: 15px; line-height: 1.6; margin-top: 10px; }
        """,
    )
    deck = genanki.Deck(2058469307, "Folio 生词")
    for row in rows:
        context = (row["context"] or "").replace("&", "&amp;").replace("<", "&lt;")
        deck.add_note(
            genanki.Note(
                model=model,
                fields=[
                    row["word"],
                    f"/{row['phonetic']}/" if row["phonetic"] else "",
                    (row["translation"] or "").replace("\\n", "<br>"),
                    (row["definition"] or "").replace("\\n", "<br>"),
                    context,
                ],
                tags=(row["tag"] or "").split(),
            )
        )
    target = DATA_DIR / "folio-vocab.apkg"
    genanki.Package(deck).write_to_file(target)
    return FileResponse(
        target,
        media_type="application/octet-stream",
        filename="folio-vocab.apkg",
    )


@app.delete("/api/vocab/{vocab_id}")
def delete_vocab(vocab_id: int) -> dict[str, str]:
    device = _sync_device()
    with db() as conn:
        row = conn.execute(
            "SELECT word, sync_uid FROM vocab WHERE id=?", (vocab_id,)
        ).fetchone()
        if row:
            for key in (row["sync_uid"], (row["word"] or "").lower()):
                if key:
                    conn.execute(
                        "INSERT OR REPLACE INTO sync_deletions"
                        "(entity_type, entity_key, deleted_at, device) "
                        "VALUES ('vocab', ?, ?, ?)",
                        (key, now_iso(), device),
                    )
        conn.execute("DELETE FROM vocab WHERE id=?", (vocab_id,))
    return {"ok": "1"}


@app.get("/api/review/due")
def due_vocab(limit: int = 50) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM vocab WHERE due <= ? AND mastered = 0 ORDER BY due LIMIT ?",
            (now_iso(), max(1, min(200, limit))),
        ).fetchall()
    return [_vocab_row(row) for row in rows]


@app.post("/api/vocab/{vocab_id}/review")
def review_vocab(vocab_id: int, payload: ReviewIn) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT * FROM vocab WHERE id=?", (vocab_id,)).fetchone()
        if not row:
            raise HTTPException(404, "生词不存在。")
        card = Card.from_json(row["fsrs"]) if row["fsrs"] else Card()
        card, _log = scheduler.review_card(card, RATINGS[payload.rating])
        conn.execute(
            "UPDATE vocab SET due=?, fsrs=?, reps=reps+1, lapses=lapses+?, updated_at=? WHERE id=?",
            (
                card.due.isoformat(),
                card.to_json(),
                1 if payload.rating == 1 else 0,
                now_iso(),
                vocab_id,
            ),
        )
        conn.execute(
            "INSERT INTO reviews(vocab_id, rating, reviewed_at) VALUES (?, ?, ?)",
            (vocab_id, payload.rating, now_iso()),
        )
    return {"ok": "1", "due": card.due.isoformat()}


# ---------------------------------------------------------------------------
# highlights & notes
# ---------------------------------------------------------------------------
@app.get("/api/highlights/{doc_id}")
def list_highlights(doc_id: int, page: Optional[int] = None) -> list[dict[str, Any]]:
    with db() as conn:
        if page:
            rows = conn.execute(
                "SELECT * FROM highlights WHERE doc_id=? AND page=? ORDER BY id",
                (doc_id, page),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM highlights WHERE doc_id=? ORDER BY page, id", (doc_id,)
            ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["rects"] = json.loads(item["rects"])
        except json.JSONDecodeError:
            item["rects"] = []
        result.append(item)
    return result


@app.post("/api/highlights")
def add_highlight(payload: HighlightIn) -> dict[str, Any]:
    with db() as conn:
        card = Card()
        sync_uid = uuid.uuid4().hex
        cursor = conn.execute(
            """INSERT INTO highlights(doc_id, page, color, text, rects, note, type,
               created_at, updated_at, due, fsrs, reps, sync_uid)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (
                payload.doc_id,
                payload.page,
                payload.color,
                payload.text,
                json.dumps(payload.rects, ensure_ascii=False),
                payload.note,
                payload.type,
                now_iso(),
                now_iso(),
                card.due.isoformat(),
                card.to_json(),
                sync_uid,
            ),
        )
        row = conn.execute(
            "SELECT * FROM highlights WHERE id=?", (cursor.lastrowid,)
        ).fetchone()
        doc = conn.execute(
            "SELECT doi, title FROM documents WHERE id=?", (payload.doc_id,)
        ).fetchone()
        if doc:
            conn.execute(
                "DELETE FROM sync_deletions WHERE entity_type='highlight' AND entity_key=?",
                (
                    _highlight_sync_key(
                        _doc_key(doc["doi"], doc["title"]), payload.page, payload.text
                    ),
                ),
            )
    item = dict(row)
    item["rects"] = payload.rects
    return item


@app.patch("/api/highlights/{highlight_id}")
def update_highlight(highlight_id: int, payload: HighlightPatch) -> dict[str, Any]:
    values = payload.model_dump(exclude_unset=True)
    values["updated_at"] = now_iso()
    assignments = ", ".join(f"{key}=?" for key in values)
    with db() as conn:
        conn.execute(
            f"UPDATE highlights SET {assignments} WHERE id=?",
            [*values.values(), highlight_id],
        )
        row = conn.execute(
            "SELECT * FROM highlights WHERE id=?", (highlight_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "标注不存在。")
    item = dict(row)
    try:
        item["rects"] = json.loads(item["rects"])
    except json.JSONDecodeError:
        item["rects"] = []
    return item


@app.get("/api/annotations")
def all_annotations() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT h.*, d.title AS doc_title FROM highlights h "
            "JOIN documents d ON d.id = h.doc_id ORDER BY h.created_at DESC LIMIT 500"
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["rects"] = json.loads(item["rects"])
        except json.JSONDecodeError:
            item["rects"] = []
        result.append(item)
    return result


@app.delete("/api/highlights/{highlight_id}")
def delete_highlight(highlight_id: int) -> dict[str, str]:
    device = _sync_device()
    with db() as conn:
        row = conn.execute(
            "SELECT h.*, d.doi, d.title FROM highlights h "
            "JOIN documents d ON d.id=h.doc_id WHERE h.id=?",
            (highlight_id,),
        ).fetchone()
        if row:
            key = _highlight_sync_key(
                _doc_key(row["doi"], row["title"]), row["page"], row["text"]
            )
            for tomb_key in (row["sync_uid"], key):
                if tomb_key:
                    conn.execute(
                        "INSERT OR REPLACE INTO sync_deletions"
                        "(entity_type, entity_key, deleted_at, device) "
                        "VALUES ('highlight', ?, ?, ?)",
                        (tomb_key, now_iso(), device),
                    )
        conn.execute("DELETE FROM highlights WHERE id=?", (highlight_id,))
    return {"ok": "1"}


@app.get("/api/review/highlights/due")
def due_highlights(limit: int = 50) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT h.*, d.title AS doc_title FROM highlights h "
            "JOIN documents d ON d.id = h.doc_id "
            "WHERE h.due IS NULL OR h.due <= ? "
            "ORDER BY COALESCE(h.due, '') LIMIT ?",
            (now_iso(), max(1, min(200, limit))),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["rects"] = json.loads(item["rects"])
        except json.JSONDecodeError:
            item["rects"] = []
        result.append(item)
    return result


@app.post("/api/highlights/{highlight_id}/review")
def review_highlight(highlight_id: int, payload: ReviewIn) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT * FROM highlights WHERE id=?", (highlight_id,)).fetchone()
        if not row:
            raise HTTPException(404, "标注不存在。")
        card = Card.from_json(row["fsrs"]) if row["fsrs"] else Card()
        card, _log = scheduler.review_card(card, RATINGS[payload.rating])
        conn.execute(
            "UPDATE highlights SET due=?, fsrs=?, reps=reps+1, updated_at=? WHERE id=?",
            (card.due.isoformat(), card.to_json(), now_iso(), highlight_id),
        )
    return {"ok": "1", "due": card.due.isoformat()}


@app.get("/api/notes")
def all_notes(q: str = "") -> list[dict[str, Any]]:
    sql = (
        "SELECT n.*, d.title AS doc_title FROM notes n "
        "JOIN documents d ON d.id = n.doc_id WHERE 1=1"
    )
    params: list[Any] = []
    if q.strip():
        sql += " AND (n.content LIKE ? OR n.title LIKE ?)"
        params.extend([f"%{q.strip()}%", f"%{q.strip()}%"])
    sql += " ORDER BY n.updated_at DESC, n.id DESC LIMIT 300"
    with db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/notes/{doc_id}")
def list_notes(doc_id: int) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM notes WHERE doc_id=? ORDER BY page, id", (doc_id,)
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/notes")
def add_note(payload: NoteIn) -> dict[str, Any]:
    with db() as conn:
        sync_uid = uuid.uuid4().hex
        cursor = conn.execute(
            "INSERT INTO notes(doc_id, page, content, title, created_at, updated_at, sync_uid) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                payload.doc_id,
                payload.page,
                payload.content,
                payload.title,
                now_iso(),
                now_iso(),
                sync_uid,
            ),
        )
        row = conn.execute("SELECT * FROM notes WHERE id=?", (cursor.lastrowid,)).fetchone()
        doc = conn.execute(
            "SELECT doi, title FROM documents WHERE id=?", (payload.doc_id,)
        ).fetchone()
        if doc:
            conn.execute(
                "DELETE FROM sync_deletions WHERE entity_type='note' AND entity_key=?",
                (
                    _note_sync_key(
                        _doc_key(doc["doi"], doc["title"]), payload.page, payload.content
                    ),
                ),
            )
    return dict(row)


@app.patch("/api/notes/{note_id}")
def update_note(note_id: int, payload: NotePatch) -> dict[str, Any]:
    values = payload.model_dump(exclude_unset=True)
    values["updated_at"] = now_iso()
    assignments = ", ".join(f"{key}=?" for key in values)
    with db() as conn:
        conn.execute(
            f"UPDATE notes SET {assignments} WHERE id=?",
            [*values.values(), note_id],
        )
        row = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    if not row:
        raise HTTPException(404, "笔记不存在。")
    return dict(row)


@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int) -> dict[str, str]:
    device = _sync_device()
    with db() as conn:
        row = conn.execute(
            "SELECT n.*, d.doi, d.title FROM notes n "
            "JOIN documents d ON d.id=n.doc_id WHERE n.id=?",
            (note_id,),
        ).fetchone()
        if row:
            key = _note_sync_key(
                _doc_key(row["doi"], row["title"]), row["page"], row["content"]
            )
            for tomb_key in (row["sync_uid"], key):
                if tomb_key:
                    conn.execute(
                        "INSERT OR REPLACE INTO sync_deletions"
                        "(entity_type, entity_key, deleted_at, device) "
                        "VALUES ('note', ?, ?, ?)",
                        (tomb_key, now_iso(), device),
                    )
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    return {"ok": "1"}


# ---------------------------------------------------------------------------
# wrong-question notebook (manual only)
# ---------------------------------------------------------------------------
@app.get("/api/wrong-questions")
def list_wrong_questions(q: str = "", question_type: str = "") -> list[dict[str, Any]]:
    sql = (
        "SELECT w.*, d.title AS doc_title FROM wrong_questions w "
        "LEFT JOIN documents d ON d.id=w.doc_id WHERE 1=1"
    )
    params: list[Any] = []
    if q.strip():
        like = f"%{q.strip()}%"
        sql += " AND (w.question LIKE ? OR w.explanation LIKE ? OR w.source LIKE ?)"
        params.extend([like, like, like])
    if question_type:
        sql += " AND w.question_type=?"
        params.append(question_type)
    sql += " ORDER BY w.id DESC"
    with db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/wrong-questions/count")
def wrong_questions_count() -> dict[str, int]:
    with db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM wrong_questions").fetchone()[0]
    return {"count": count}


@app.post("/api/wrong-questions")
def add_wrong_question(payload: WrongQuestionIn) -> dict[str, Any]:
    question = payload.question.strip()
    if not question:
        raise HTTPException(400, "题目不能为空。")
    with db() as conn:
        cursor = conn.execute(
            "INSERT INTO wrong_questions(doc_id, page, question, options, answer, explanation, "
            "question_type, source, created_at, updated_at, sync_uid) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                payload.doc_id, payload.page, question, payload.options.strip(),
                payload.answer.strip(), payload.explanation.strip(),
                payload.question_type.strip(), payload.source.strip(),
                now_iso(), now_iso(), uuid.uuid4().hex,
            ),
        )
        row = conn.execute(
            "SELECT * FROM wrong_questions WHERE id=?", (cursor.lastrowid,)
        ).fetchone()
    return dict(row)


@app.patch("/api/wrong-questions/{question_id}")
def update_wrong_question(question_id: int, payload: WrongQuestionPatch) -> dict[str, Any]:
    values = payload.model_dump(exclude_unset=True)
    if values:
        values["updated_at"] = now_iso()
        assignments = ", ".join(f"{key}=?" for key in values)
        with db() as conn:
            conn.execute(
                f"UPDATE wrong_questions SET {assignments} WHERE id=?",
                [*values.values(), question_id],
            )
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM wrong_questions WHERE id=?", (question_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "错题不存在。")
    return dict(row)


@app.delete("/api/wrong-questions/{question_id}")
def delete_wrong_question(question_id: int) -> dict[str, str]:
    with db() as conn:
        conn.execute("DELETE FROM wrong_questions WHERE id=?", (question_id,))
    return {"ok": "1"}


# ---------------------------------------------------------------------------
# CET articles
# ---------------------------------------------------------------------------
@app.get("/api/articles")
def list_articles() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, length(text) AS chars FROM articles ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/articles")
def add_article(payload: ArticleIn) -> dict[str, Any]:
    text = payload.text.strip()
    if not text:
        raise HTTPException(400, "文章为空。")
    title = payload.title.strip() or text[:28].replace("\n", " ") + "…"
    with db() as conn:
        cursor = conn.execute(
            "INSERT INTO articles(title, text, created_at) VALUES (?, ?, ?)",
            (title, text, now_iso()),
        )
        row = conn.execute(
            "SELECT * FROM articles WHERE id=?", (cursor.lastrowid,)
        ).fetchone()
    return dict(row)


@app.get("/api/articles/{article_id}")
def get_article(article_id: int) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT * FROM articles WHERE id=?", (article_id,)).fetchone()
    if not row:
        raise HTTPException(404, "文章不存在。")
    return dict(row)


@app.delete("/api/articles/{article_id}")
def delete_article(article_id: int) -> dict[str, str]:
    with db() as conn:
        conn.execute("DELETE FROM articles WHERE id=?", (article_id,))
    return {"ok": "1"}


# ---------------------------------------------------------------------------
# stats, home & backup
# ---------------------------------------------------------------------------
def _streak(conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        "SELECT DISTINCT substr(reviewed_at, 1, 10) AS day FROM reviews "
        "UNION SELECT DISTINCT substr(created_at, 1, 10) AS day FROM reading_sessions"
    ).fetchall()
    dates = {row["day"] for row in rows if row["day"]}
    streak = 0
    cursor = datetime.now(timezone.utc).date()
    if cursor.isoformat() not in dates:
        cursor -= timedelta(days=1)
    while cursor.isoformat() in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _heatmap(conn: sqlite3.Connection, days: int = 120) -> list[dict[str, Any]]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    rows = conn.execute(
        "SELECT substr(reviewed_at, 1, 10) AS day, COUNT(*) AS count "
        "FROM reviews WHERE reviewed_at >= ? GROUP BY day "
        "UNION ALL "
        "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count "
        "FROM reading_sessions WHERE created_at >= ? GROUP BY day",
        (since, since),
    ).fetchall()
    merged: dict[str, int] = {}
    for row in rows:
        merged[row["day"]] = merged.get(row["day"], 0) + row["count"]
    return [{"day": day, "count": count} for day, count in sorted(merged.items())]


@app.get("/api/home")
def home() -> dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    with db() as conn:
        documents = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        vocab = conn.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
        due = conn.execute(
            "SELECT COUNT(*) FROM vocab WHERE due <= ? AND mastered = 0", (now_iso(),)
        ).fetchone()[0]
        reviews_today = conn.execute(
            "SELECT COUNT(*) FROM reviews WHERE reviewed_at LIKE ?", (today + "%",)
        ).fetchone()[0]
        reading_seconds = conn.execute(
            "SELECT COALESCE(SUM(reading_seconds), 0) FROM documents"
        ).fetchone()[0]
        streak = _streak(conn)
        daily = conn.execute(
            "SELECT * FROM vocab WHERE due <= ? AND mastered = 0 ORDER BY RANDOM() LIMIT 1",
            (now_iso(),),
        ).fetchone()
        if not daily:
            daily = conn.execute("SELECT * FROM vocab ORDER BY RANDOM() LIMIT 1").fetchone()
        continue_rows = conn.execute(
            "SELECT * FROM documents WHERE last_read_at IS NOT NULL "
            "ORDER BY last_read_at DESC LIMIT 4"
        ).fetchall()
        notifications_unread = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE read=0"
        ).fetchone()[0]
        highlight_due = conn.execute(
            "SELECT COUNT(*) FROM highlights WHERE due IS NULL OR due <= ?", (now_iso(),)
        ).fetchone()[0]
    continue_list = []
    for row in continue_rows:
        item = dict(row)
        item["progress"] = round(
            min(1.0, (item.get("last_page") or 1) / max(1, item.get("pages") or 1)), 3
        )
        continue_list.append(item)
    recent = list_documents(sort="recent")[:6]
    with db() as conn:
        heatmap = _heatmap(conn)
    return {
        "documents": documents,
        "vocab": vocab,
        "due": due,
        "reviews_today": reviews_today,
        "reading_seconds": reading_seconds,
        "streak": streak,
        "heatmap": heatmap,
        "daily_word": _vocab_row(daily) if daily else None,
        "recent": recent,
        "continue_reading": continue_list,
        "collections": list_collections(),
        "topics": _list_topics(),
        "notifications_unread": notifications_unread,
        "highlight_due": highlight_due,
    }


@app.get("/api/report/annual")
def annual_report(year: Optional[int] = None) -> dict[str, Any]:
    target_year = year or datetime.now(timezone.utc).year
    start = f"{target_year}-01-01"
    end = f"{target_year + 1}-01-01"
    with db() as conn:
        documents = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE created_at >= ? AND created_at < ?",
            (start, end),
        ).fetchone()[0]
        reading_seconds = conn.execute(
            "SELECT COALESCE(SUM(seconds), 0) FROM reading_sessions "
            "WHERE created_at >= ? AND created_at < ?",
            (start, end),
        ).fetchone()[0]
        vocab = conn.execute(
            "SELECT COUNT(*) FROM vocab WHERE created_at >= ? AND created_at < ?",
            (start, end),
        ).fetchone()[0]
        reviews = conn.execute(
            "SELECT COUNT(*) FROM reviews WHERE reviewed_at >= ? AND reviewed_at < ?",
            (start, end),
        ).fetchone()[0]
        highlights = conn.execute(
            "SELECT COUNT(*) FROM highlights WHERE created_at >= ? AND created_at < ?",
            (start, end),
        ).fetchone()[0]
        notes = conn.execute(
            "SELECT COUNT(*) FROM notes WHERE created_at >= ? AND created_at < ?",
            (start, end),
        ).fetchone()[0]
        top_docs = conn.execute(
            "SELECT title, reading_seconds FROM documents "
            "ORDER BY reading_seconds DESC LIMIT 5"
        ).fetchall()
        tags: dict[str, int] = {}
        for row in conn.execute("SELECT tag FROM vocab").fetchall():
            for tag in (row["tag"] or "").split():
                tags[tag] = tags.get(tag, 0) + 1
        monthly = conn.execute(
            "SELECT substr(reviewed_at, 6, 2) AS month, COUNT(*) AS count "
            "FROM reviews WHERE reviewed_at >= ? AND reviewed_at < ? "
            "GROUP BY month ORDER BY month",
            (start, end),
        ).fetchall()
    month_names = ["1 月", "2 月", "3 月", "4 月", "5 月", "6 月", "7 月", "8 月", "9 月", "10 月", "11 月", "12 月"]
    monthly_map = {row["month"]: row["count"] for row in monthly}
    monthly_lines = "\n".join(
        f"| {month_names[int(month) - 1]} | {monthly_map.get(month, 0)} |"
        for month in [f"{i:02d}" for i in range(1, 13)]
    )
    tag_lines = "\n".join(
        f"| {TAG_NAMES.get(tag, tag)} | {count} |"
        for tag, count in sorted(tags.items(), key=lambda item: item[1], reverse=True)[:8]
    ) or "| — | 0 |"
    doc_lines = "\n".join(
        f"| {row['title']} | {fmt_duration(row['reading_seconds'])} |"
        for row in top_docs
    ) or "| — | 0 分钟 |"
    markdown = f"""# {target_year} 年阅读报告

## 总览

| 指标 | 数值 |
|---|---|
| 新增文献 | {documents} |
| 阅读时长 | {fmt_duration(reading_seconds)} |
| 新增生词 | {vocab} |
| 复习次数 | {reviews} |
| 高亮 | {highlights} |
| 笔记 | {notes} |

## 月度复习

| 月份 | 复习次数 |
|---|---|
{monthly_lines}

## 生词标签

| 标签 | 数量 |
|---|---|
{tag_lines}

## 阅读时长 Top 5

| 文献 | 阅读时长 |
|---|---|
{doc_lines}
"""
    return {"year": target_year, "markdown": markdown}


def fmt_duration(seconds: int) -> str:
    seconds = int(seconds or 0)
    if seconds < 60:
        return f"{seconds} 秒"
    if seconds < 3600:
        return f"{round(seconds / 60)} 分钟"
    hours = seconds // 3600
    minutes = round((seconds % 3600) / 60)
    return f"{hours} 小时 {minutes} 分"


@app.get("/api/stats/overview")
def stats_overview() -> dict[str, Any]:
    with db() as conn:
        documents = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        reading_seconds = conn.execute(
            "SELECT COALESCE(SUM(reading_seconds), 0) FROM documents"
        ).fetchone()[0]
        highlights = conn.execute("SELECT COUNT(*) FROM highlights").fetchone()[0]
        notes = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        pages = conn.execute("SELECT COALESCE(SUM(pages), 0) FROM documents").fetchone()[0]
        streak = _streak(conn)
        heatmap = _heatmap(conn, 180)
    vocab = vocab_stats()
    return {
        "documents": documents,
        "pages": pages,
        "reading_seconds": reading_seconds,
        "highlights": highlights,
        "notes": notes,
        "streak": streak,
        "heatmap": heatmap,
        "vocab": vocab,
    }


@app.get("/api/stats")
def stats() -> dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    with db() as conn:
        docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        vocab = conn.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
        due = conn.execute(
            "SELECT COUNT(*) FROM vocab WHERE due <= ? AND mastered = 0", (now_iso(),)
        ).fetchone()[0]
        reviews_today = conn.execute(
            "SELECT COUNT(*) FROM reviews WHERE reviewed_at LIKE ?", (today + "%",)
        ).fetchone()[0]
        highlights = conn.execute("SELECT COUNT(*) FROM highlights").fetchone()[0]
    return {
        "documents": docs,
        "vocab": vocab,
        "due": due,
        "reviews_today": reviews_today,
        "highlights": highlights,
    }


@app.get("/api/backup")
def backup_database() -> FileResponse:
    target = DATA_DIR / "folio-backup.db"
    source = sqlite3.connect(DB_PATH)
    destination = sqlite3.connect(target)
    source.backup(destination)
    destination.close()
    source.close()
    return FileResponse(
        target,
        media_type="application/octet-stream",
        filename="folio-backup.db",
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

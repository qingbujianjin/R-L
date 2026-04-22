<<<<<<< HEAD
import os
import re
import sqlite3
from pathlib import Path

import requests


# 项目根目录
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "books.db"
OFFICIAL_DIR = BASE_DIR / "uploads" / "official"

# 预设书单（Project Gutenberg EBook ID）
BOOK_LIST = [
    {"id": 1342, "title": "Pride and Prejudice", "author": "Jane Austen"},
    {"id": 1661, "title": "Sherlock Holmes", "author": "Arthur Conan Doyle"},
    {"id": 64316, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald"},
    {"id": 11, "title": "Alice in Wonderland", "author": "Lewis Carroll"},
    {"id": 55, "title": "The Wizard of Oz", "author": "L. Frank Baum"},
    {"id": 84, "title": "Frankenstein", "author": "Mary Shelley"},
]


def ensure_dirs():
    OFFICIAL_DIR.mkdir(parents=True, exist_ok=True)


def ensure_tables(conn: sqlite3.Connection):
    cur = conn.cursor()
    # 按你的要求，写入 books 表
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gutenberg_id INTEGER UNIQUE,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            file_path TEXT NOT NULL,
            is_official INTEGER NOT NULL DEFAULT 1,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # 兼容当前项目已有 local_books 表，方便前端直接读取
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS local_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            content_text TEXT NOT NULL,
            title TEXT DEFAULT '',
            author TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            is_official INTEGER DEFAULT 0,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def safe_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "untitled"


def build_urls(book_id: int):
    # 按要求使用这个 URL 规则
    primary = f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"
    # 额外兜底，避免部分书没有 -0 后缀
    fallback = f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt"
    return [primary, fallback]


def download_text(book_id: int):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GutenbergFetcher/1.0)"}
    last_error = ""
    for url in build_urls(book_id):
        try:
            resp = requests.get(url, timeout=20, headers=headers)
            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}: {url}"
                continue
            # requests 会按响应头自动解码；异常再回退 utf-8
            text = resp.text
            if not text:
                last_error = f"empty body: {url}"
                continue
            return text, url, None
        except Exception as exc:
            last_error = f"{url} -> {exc}"
    return "", "", last_error or "download failed"


def strip_gutenberg_license(raw_text: str) -> str:
    """
    去除 Gutenberg 头尾声明，只保留正文。
    常见分隔符：
    *** START OF THE PROJECT GUTENBERG EBOOK ...
    *** END OF THE PROJECT GUTENBERG EBOOK ...
    """
    text = (raw_text or "").replace("\r\n", "\n")

    start_pattern = re.compile(
        r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
        re.IGNORECASE | re.DOTALL,
    )
    end_pattern = re.compile(
        r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
        re.IGNORECASE | re.DOTALL,
    )

    start_match = start_pattern.search(text)
    if start_match:
        text = text[start_match.end():]

    end_match = end_pattern.search(text)
    if end_match:
        text = text[:end_match.start()]

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def upsert_books(conn: sqlite3.Connection, book: dict, file_path: Path, content: str, source_url: str):
    cur = conn.cursor()

    # 1) 写入 books 表
    cur.execute(
        """
        INSERT INTO books (gutenberg_id, title, author, file_path, is_official)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(gutenberg_id) DO UPDATE SET
            title = excluded.title,
            author = excluded.author,
            file_path = excluded.file_path,
            is_official = 1
        """,
        (book["id"], book["title"], book["author"], str(file_path)),
    )

    # 2) 同步写入 local_books（兼容现有页面）
    original_filename = file_path.name
    stored_filename = f"official/{file_path.name}"
    row = cur.execute(
        """
        SELECT id FROM local_books
        WHERE is_official = 1 AND lower(title) = lower(?)
        LIMIT 1
        """,
        (book["title"],),
    ).fetchone()

    if row:
        cur.execute(
            """
            UPDATE local_books
            SET original_filename = ?, stored_filename = ?, content_text = ?,
                title = ?, author = ?, source_url = ?, is_official = 1
            WHERE id = ?
            """,
            (
                original_filename,
                stored_filename,
                content,
                book["title"],
                book["author"],
                source_url,
                row[0],
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO local_books (
                original_filename, stored_filename, content_text,
                title, author, source_url, is_official, added_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """,
            (
                original_filename,
                stored_filename,
                content,
                book["title"],
                book["author"],
                source_url,
            ),
        )

    conn.commit()


def main():
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    ensure_tables(conn)

    ok_count = 0
    fail_count = 0
    failed = []

    for book in BOOK_LIST:
        print(f"[DOWNLOADING] {book['title']} (ID={book['id']})")
        raw_text, source_url, error = download_text(book["id"])
        if error:
            fail_count += 1
            failed.append((book["title"], error))
            print(f"  -> FAILED: {error}")
            continue

        clean_text = strip_gutenberg_license(raw_text)
        if not clean_text:
            fail_count += 1
            failed.append((book["title"], "cleaned content is empty"))
            print("  -> FAILED: cleaned content is empty")
            continue

        filename = f"{safe_filename(book['title'])}.txt"
        file_path = OFFICIAL_DIR / filename
        file_path.write_text(clean_text, encoding="utf-8")

        upsert_books(conn, book, file_path, clean_text, source_url)
        ok_count += 1
        print(f"  -> OK: saved to {file_path}")

    conn.close()

    print("\n===== FETCH SUMMARY =====")
    print(f"success: {ok_count}")
    print(f"failed : {fail_count}")
    if failed:
        print("failed items:")
        for title, msg in failed:
            print(f" - {title}: {msg}")


if __name__ == "__main__":
    main()
=======
import os
import re
import sqlite3
from pathlib import Path

import requests


# 项目根目录
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "books.db"
OFFICIAL_DIR = BASE_DIR / "uploads" / "official"

# 预设书单（Project Gutenberg EBook ID）
BOOK_LIST = [
    {"id": 1342, "title": "Pride and Prejudice", "author": "Jane Austen"},
    {"id": 1661, "title": "Sherlock Holmes", "author": "Arthur Conan Doyle"},
    {"id": 64316, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald"},
    {"id": 11, "title": "Alice in Wonderland", "author": "Lewis Carroll"},
    {"id": 55, "title": "The Wizard of Oz", "author": "L. Frank Baum"},
    {"id": 84, "title": "Frankenstein", "author": "Mary Shelley"},
]


def ensure_dirs():
    OFFICIAL_DIR.mkdir(parents=True, exist_ok=True)


def ensure_tables(conn: sqlite3.Connection):
    cur = conn.cursor()
    # 按你的要求，写入 books 表
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gutenberg_id INTEGER UNIQUE,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            file_path TEXT NOT NULL,
            is_official INTEGER NOT NULL DEFAULT 1,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # 兼容当前项目已有 local_books 表，方便前端直接读取
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS local_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            content_text TEXT NOT NULL,
            title TEXT DEFAULT '',
            author TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            is_official INTEGER DEFAULT 0,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def safe_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "untitled"


def build_urls(book_id: int):
    # 按要求使用这个 URL 规则
    primary = f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"
    # 额外兜底，避免部分书没有 -0 后缀
    fallback = f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt"
    return [primary, fallback]


def download_text(book_id: int):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GutenbergFetcher/1.0)"}
    last_error = ""
    for url in build_urls(book_id):
        try:
            resp = requests.get(url, timeout=20, headers=headers)
            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}: {url}"
                continue
            # requests 会按响应头自动解码；异常再回退 utf-8
            text = resp.text
            if not text:
                last_error = f"empty body: {url}"
                continue
            return text, url, None
        except Exception as exc:
            last_error = f"{url} -> {exc}"
    return "", "", last_error or "download failed"


def strip_gutenberg_license(raw_text: str) -> str:
    """
    去除 Gutenberg 头尾声明，只保留正文。
    常见分隔符：
    *** START OF THE PROJECT GUTENBERG EBOOK ...
    *** END OF THE PROJECT GUTENBERG EBOOK ...
    """
    text = (raw_text or "").replace("\r\n", "\n")

    start_pattern = re.compile(
        r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
        re.IGNORECASE | re.DOTALL,
    )
    end_pattern = re.compile(
        r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
        re.IGNORECASE | re.DOTALL,
    )

    start_match = start_pattern.search(text)
    if start_match:
        text = text[start_match.end():]

    end_match = end_pattern.search(text)
    if end_match:
        text = text[:end_match.start()]

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def upsert_books(conn: sqlite3.Connection, book: dict, file_path: Path, content: str, source_url: str):
    cur = conn.cursor()

    # 1) 写入 books 表
    cur.execute(
        """
        INSERT INTO books (gutenberg_id, title, author, file_path, is_official)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(gutenberg_id) DO UPDATE SET
            title = excluded.title,
            author = excluded.author,
            file_path = excluded.file_path,
            is_official = 1
        """,
        (book["id"], book["title"], book["author"], str(file_path)),
    )

    # 2) 同步写入 local_books（兼容现有页面）
    original_filename = file_path.name
    stored_filename = f"official/{file_path.name}"
    row = cur.execute(
        """
        SELECT id FROM local_books
        WHERE is_official = 1 AND lower(title) = lower(?)
        LIMIT 1
        """,
        (book["title"],),
    ).fetchone()

    if row:
        cur.execute(
            """
            UPDATE local_books
            SET original_filename = ?, stored_filename = ?, content_text = ?,
                title = ?, author = ?, source_url = ?, is_official = 1
            WHERE id = ?
            """,
            (
                original_filename,
                stored_filename,
                content,
                book["title"],
                book["author"],
                source_url,
                row[0],
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO local_books (
                original_filename, stored_filename, content_text,
                title, author, source_url, is_official, added_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """,
            (
                original_filename,
                stored_filename,
                content,
                book["title"],
                book["author"],
                source_url,
            ),
        )

    conn.commit()


def main():
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    ensure_tables(conn)

    ok_count = 0
    fail_count = 0
    failed = []

    for book in BOOK_LIST:
        print(f"[DOWNLOADING] {book['title']} (ID={book['id']})")
        raw_text, source_url, error = download_text(book["id"])
        if error:
            fail_count += 1
            failed.append((book["title"], error))
            print(f"  -> FAILED: {error}")
            continue

        clean_text = strip_gutenberg_license(raw_text)
        if not clean_text:
            fail_count += 1
            failed.append((book["title"], "cleaned content is empty"))
            print("  -> FAILED: cleaned content is empty")
            continue

        filename = f"{safe_filename(book['title'])}.txt"
        file_path = OFFICIAL_DIR / filename
        file_path.write_text(clean_text, encoding="utf-8")

        upsert_books(conn, book, file_path, clean_text, source_url)
        ok_count += 1
        print(f"  -> OK: saved to {file_path}")

    conn.close()

    print("\n===== FETCH SUMMARY =====")
    print(f"success: {ok_count}")
    print(f"failed : {fail_count}")
    if failed:
        print("failed items:")
        for title, msg in failed:
            print(f" - {title}: {msg}")


if __name__ == "__main__":
    main()
>>>>>>> d490cee180814eecf12c3a91283f9c9719b4abe6

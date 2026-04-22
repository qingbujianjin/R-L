import re
import shutil
import argparse
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
OFFICIAL_DIR = BASE_DIR / "uploads" / "official"
BACKUP_DIR = BASE_DIR / "uploads" / "official_backup"


def clean_text(raw_text: str) -> str:
    text = (raw_text or "").replace("\r\n", "\n")

    # 1) 定位正文：仅在同时找到 START/END 时截取；否则保留全文
    start_match = re.search(
        r"\*\*\*\s*START OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    end_match = re.search(
        r"\*\*\*\s*END OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if start_match and end_match and start_match.end() < end_match.start():
        text = text[start_match.end():end_match.start()]

    # 1.1) 删除花括号包围的纯文本标记（如 {ix}、{23}）
    text = re.sub(r"\{[^\}]+\}", "", text)

    # 1.2) 删除古腾堡文本中用于斜体标记的下划线（如 _Northanger Abbey_）
    text = text.replace("_", "")

    # 2.1) 删除 [Illustration: ...] / [Image: ...]
    text = re.sub(r"\[(?:Illustration|Image):[^\]]*\]", "", text, flags=re.IGNORECASE)

    # 2.1-b) 删除包含 [Illustration: / [Image: 的整行文本
    text = re.sub(
        r"(?im)^.*\[(?:Illustration|Image):[^\]]*\].*\n?",
        "",
        text,
    )

    # 2.2) 删除所有以 http://www.gutenberg.org 开头的整行链接
    text = re.sub(
        r"(?im)^[ \t]*http://www\.gutenberg\.org[^\n]*\n?",
        "",
        text,
    )

    # 2.3) 删除 HTML 图片标签残留（如 <img ...>）
    text = re.sub(r"(?is)<img\b[^>]*>", "", text)

    # 2.4) 删除 Markdown 图片残留（如 ![alt](url)）
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)

    # 2.5) 删除明显的图片链接行（包含 image/illustration/cover 且是整行 URL）
    text = re.sub(
        r"(?im)^[ \t]*https?://\S*(?:image|illustration|cover)\S*[ \t]*\n?",
        "",
        text,
    )

    # 2.6) 删除常见“图片说明行”残留（整行以 illustration/image/plate/fig. 开头）
    text = re.sub(
        r"(?im)^[ \t]*(?:illustration|image|plate|fig\.?|figure)\b[^\n]*\n?",
        "",
        text,
    )

    # 3) 连续超过 3 个换行压缩为 2 个换行
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip() + "\n"


def clean_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="ignore")
    cleaned = clean_text(original)
    changed = cleaned != original
    path.write_text(cleaned, encoding="utf-8")
    return changed


def backup_files(files):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for file_path in files:
        target = BACKUP_DIR / file_path.name
        shutil.copy2(file_path, target)
        print(f"[BACKUP] {file_path.name} -> {target}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="批量清洗 uploads/official 下的 Gutenberg 文本。"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="不执行备份，直接覆盖原文件。",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not OFFICIAL_DIR.exists():
        print(f"目录不存在: {OFFICIAL_DIR}")
        return

    txt_files = sorted(OFFICIAL_DIR.glob("*.txt"))
    if not txt_files:
        print("未找到 .txt 文件")
        return

    if args.no_backup:
        print("[INFO] 已关闭备份，将直接覆盖原文件。")
    else:
        backup_files(txt_files)

    changed_count = 0
    for file_path in txt_files:
        changed = clean_file(file_path)
        if changed:
            changed_count += 1
        print(f"[CLEANED] {file_path.name} | changed={changed}")

    print("\n===== CLEAN SUMMARY =====")
    print(f"total files : {len(txt_files)}")
    print(f"changed     : {changed_count}")
    print(f"unchanged   : {len(txt_files) - changed_count}")


if __name__ == "__main__":
    main()

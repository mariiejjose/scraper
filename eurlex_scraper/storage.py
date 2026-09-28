import hashlib
import json
import os
import re


DOWNLOAD_FOLDER = "downloads"
MANIFEST_FILE = "manifest.json"


def load_manifest():
    if not os.path.exists(MANIFEST_FILE):
        return []

    with open(MANIFEST_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_manifest(manifest):
    with open(MANIFEST_FILE, "w", encoding="utf-8") as file:
        json.dump(
            manifest,
            file,
            indent=4,
            ensure_ascii=False
        )


def calculate_hash(content):
    return hashlib.sha256(content).hexdigest()


def create_safe_filename(title, file_hash):
    filename = re.sub(
        r'[<>:"/\\|?*]',
        "",
        title
    )

    filename = filename.strip()

    if not filename:
        filename = "document"

    if len(filename) > 120:
        filename = filename[:120]

    return f"{filename}_{file_hash[:10]}.pdf"


def save_pdf(
    content,
    title,
    work_url,
    date,
    celex=None
):
    os.makedirs(
        DOWNLOAD_FOLDER,
        exist_ok=True
    )

    manifest = load_manifest()

    file_hash = calculate_hash(content)

    for document in manifest:
        if document.get("hash") == file_hash:
            print(
                "DUPLICATE: PDF already downloaded"
            )

            return "duplicate"

    filename = create_safe_filename(
        title,
        file_hash
    )

    file_path = os.path.join(
        DOWNLOAD_FOLDER,
        filename
    )

    with open(file_path, "wb") as file:
        file.write(content)

    manifest.append(
        {
            "title": title,
            "date": date,
            "work": work_url,
            "celex": celex,
            "filename": filename,
            "hash": file_hash
        }
    )

    save_manifest(manifest)

    print(
        "DOWNLOADED:",
        filename
    )

    return "downloaded"
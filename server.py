
import json
import os
import re
import shutil
import uuid
from pathlib import Path

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


HOST = "127.0.0.1"
PORT = 8000
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5-coder:3b"

BASE_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = BASE_DIR / "sample_files"
HISTORY_FILE = BASE_DIR / "operation_history.json"

MAX_FILES = 200
MAX_FILE_BYTES = 5 * 1024 * 1024

# Only these file types may be renamed or moved by this first version.
SUPPORTED_EXTENSIONS = {
    ".pdf", ".txt", ".md", ".csv",
    ".docx", ".xlsx", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif",
    ".webp", ".py", ".js", ".html",
    ".css", ".json", ".zip"
}

CATEGORIES = {
    "Documents",
    "Images",
    "Code",
    "Spreadsheets",
    "Presentations",
    "Archives",
    "Other"
}


def json_response(handler, status, data):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def read_history():
    if not HISTORY_FILE.exists():
        return []

    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def write_history(history):
    temporary = HISTORY_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(history, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    os.replace(temporary, HISTORY_FILE)


def safe_child(root, relative_name):
    """Resolve a relative path and reject paths escaping the root."""
    relative = Path(relative_name)

    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Invalid relative path.")

    target = (root / relative).resolve()

    if not target.is_relative_to(root.resolve()):
        raise ValueError("Path escapes the selected folder.")

    return target


def get_root(folder):
    """Only permit folders inside this project's sample_files directory."""
    if not isinstance(folder, str) or not folder.strip():
        raise ValueError("Choose a folder inside sample_files.")

    root = (SAMPLE_DIR / folder).resolve()

    if not root.is_relative_to(SAMPLE_DIR.resolve()):
        raise ValueError("Folder is outside the permitted sample area.")

    if not root.exists() or not root.is_dir():
        raise ValueError("The selected sample folder does not exist.")

    return root


def scan_folder(root):
    files = []

    for item in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not item.is_file() or item.is_symlink():
            continue

        if item.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            stat = item.stat()
            files.append({
                "name": item.name,
                "extension": item.suffix.lower(),
                "size_bytes": stat.st_size,
                "modified": int(stat.st_mtime)
            })
        except OSError:
            continue

        if len(files) >= MAX_FILES:
            break

    return files


def category_for_extension(extension):
    extension = extension.lower()

    if extension in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        return "Images"
    if extension in {".py", ".js", ".html", ".css", ".json"}:
        return "Code"
    if extension in {".csv", ".xlsx"}:
        return "Spreadsheets"
    if extension == ".pptx":
        return "Presentations"
    if extension == ".zip":
        return "Archives"
    if extension in {".pdf", ".txt", ".md", ".docx"}:
        return "Documents"

    return "Other"


def ollama_health():
    request = Request(
        "http://127.0.0.1:11434/api/tags",
        headers={"Accept": "application/json"}
    )

    try:
        with urlopen(request, timeout=4) as response:
            data = json.loads(response.read().decode("utf-8"))

        models = [model.get("name", "") for model in data.get("models", [])]
        available = any(name.split(":")[0] == MODEL.split(":")[0]
                        for name in models)

        return {
            "available": True,
            "model_installed": available,
            "model": MODEL,
            "models": models
        }

    except (OSError, URLError, HTTPError, json.JSONDecodeError):
        return {
            "available": False,
            "model_installed": False,
            "model": MODEL,
            "error": "Ollama is not responding. Start Ollama and try again."
        }


def ask_ollama(files):
    instructions = """
You are LaterLess, a cautious local file organization assistant.

Return ONLY a JSON object in this format:
{
  "suggestions": [
    {
      "original_name": "existing filename",
      "category": "Documents",
      "suggested_name": "clean_filename.pdf",
      "reason": "Short explanation"
    }
  ]
}

Rules:
- Return exactly one suggestion for each input file.
- Copy every original_name exactly from the input.
- Allowed categories: Documents, Images, Code, Spreadsheets,
  Presentations, Archives, Other.
- Preserve each file's original extension.
- Never invent file contents; you only know the supplied filename
  and metadata.
- Keep names short and descriptive.
- Do not include folder paths in suggested_name.
- Do not use slashes, backslashes, or control characters in names.
- Do not overwrite files or delete anything.
- If unsure, use the extension-based category.
"""

    payload = {
        "model": MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": instructions},
            {
                "role": "user",
                "content": json.dumps(files, ensure_ascii=False)
            }
        ],
        "options": {
            "temperature": 0.1,
            "num_predict": 1800
        }
    }

    request = Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result.get("message", {}).get("content", "")
        parsed = json.loads(content)

        if not isinstance(parsed, dict):
            raise ValueError("The AI returned an unexpected response.")

        suggestions = parsed.get("suggestions")

        if not isinstance(suggestions, list):
            raise ValueError("The AI response has no suggestions list.")

        return suggestions

    except (URLError, HTTPError, TimeoutError) as exc:
        raise RuntimeError(
            "Could not contact Ollama. Check that it is running."
        ) from exc
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        raise RuntimeError(
            "The AI returned invalid output. Please try again."
        ) from exc


def validate_suggestions(files, suggestions):
    originals = {item["name"]: item for item in files}
    validated = []
    seen = set()

    for suggestion in suggestions:
        if not isinstance(suggestion, dict):
            continue

        original = suggestion.get("original_name")
        if original not in originals or original in seen:
            continue

        source_info = originals[original]
        extension = source_info["extension"]
        category = suggestion.get("category")

        if category not in CATEGORIES:
            category = category_for_extension(extension)

        proposed = suggestion.get("suggested_name", "")
        if not isinstance(proposed, str):
            proposed = ""

        # Keep the AI suggestion as a filename, never a path.
        proposed = Path(proposed).name.strip()
        proposed = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", proposed)
        proposed = proposed.strip(" .")

        if not proposed or proposed in {".", ".."}:
            proposed = original

        # Preserve the original extension.
        if Path(proposed).suffix.lower() != extension:
            proposed = Path(proposed).stem + extension

        # Limit filename length.
        proposed = proposed[:180]
        if Path(proposed).suffix.lower() != extension:
            proposed = Path(proposed).stem[:170] + extension

        validated.append({
            "original_name": original,
            "category": category,
            "suggested_name": proposed,
            "reason": str(suggestion.get("reason", ""))[:200]
        })
        seen.add(original)

    # Fill any omissions with deterministic suggestions.
    for item in files:
        if item["name"] not in seen:
            validated.append({
                "original_name": item["name"],
                "category": category_for_extension(item["extension"]),
                "suggested_name": item["name"],
                "reason": "Used the file extension as a safe fallback."
            })

    return validated


class LaterLessHandler(BaseHTTPRequestHandler):
    def log_message(self, format_string, *args):
        print("[LaterLess]", format_string % args)

    
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            page = BASE_DIR / "index.html"

            try:
                content = page.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(content)
            except OSError:
                json_response(
                    self, 500,
                    {"error": "Could not read index.html."}
                )
            return

        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if self.path == "/api/health":
            health = ollama_health()
            json_response(
                self, 200 if health["available"] else 503, health
            )
            return

        if self.path == "/api/sample-folders":
            SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
            folders = [
                item.name for item in SAMPLE_DIR.iterdir()
                if item.is_dir() and not item.is_symlink()
            ]
            json_response(self, 200, {"folders": sorted(folders)})
            return

        json_response(self, 404, {"error": "Endpoint not found."})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 100_000:
                json_response(self, 400, {"error": "Invalid request size."})
                return

            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(body, dict):
                raise ValueError("Expected a JSON object.")

            if self.path == "/api/scan":
                root = get_root(body.get("folder"))
                files = scan_folder(root)
                json_response(self, 200, {
                    "folder": body["folder"],
                    "count": len(files),
                    "files": files
                })
                return

            if self.path == "/api/suggest":
                root = get_root(body.get("folder"))
                files = scan_folder(root)

                if not files:
                    json_response(self, 200, {
                        "suggestions": [],
                        "message": "No supported files found."
                    })
                    return

                suggestions = validate_suggestions(
                    files, ask_ollama(files)
                )
                json_response(self, 200, {
                    "folder": body["folder"],
                    "suggestions": suggestions
                })
                return

            if self.path == "/api/organize":
                self.organize(body)
                return

            if self.path == "/api/undo":
                self.undo(body)
                return

            json_response(self, 404, {"error": "Endpoint not found."})

        except (ValueError, json.JSONDecodeError) as exc:
            json_response(self, 400, {"error": str(exc)})
        except RuntimeError as exc:
            json_response(self, 502, {"error": str(exc)})
        except Exception as exc:
            print("[LaterLess] Error:", repr(exc))
            json_response(self, 500, {"error": "Unexpected server error."})

    def organize(self, body):
        folder = body.get("folder")
        root = get_root(folder)
        choices = body.get("suggestions")

        if not isinstance(choices, list) or len(choices) > MAX_FILES:
            raise ValueError("Invalid suggestions list.")

        current_files = {item["name"] for item in scan_folder(root)}
        operations = []
        plan_id = str(uuid.uuid4())

        for choice in choices:
            if not isinstance(choice, dict):
                raise ValueError("Invalid suggestion entry.")

            original = choice.get("original_name")
            category = choice.get("category")
            proposed = choice.get("suggested_name")

            if original not in current_files:
                raise ValueError("A source file no longer exists.")

            if category not in CATEGORIES:
                raise ValueError("Invalid category.")

            if not isinstance(proposed, str) or Path(proposed).name != proposed:
                raise ValueError("Invalid suggested filename.")

            if Path(proposed).suffix.lower() != Path(original).suffix.lower():
                raise ValueError("File extension cannot be changed.")

            source = safe_child(root, original)
            destination = safe_child(root, category + "/" + proposed)

            if not source.is_file() or source.is_symlink():
                raise ValueError("Source is not a regular file.")

            if source == destination:
                continue

            if destination.exists():
                raise ValueError(
                    "Destination already exists: " + destination.name
                )

            operations.append({
                "source": str(source.relative_to(root)),
                "destination": str(destination.relative_to(root))
            })

        # Validate all destinations before making changes.
        destinations = [op["destination"] for op in operations]
        if len(destinations) != len(set(destinations)):
            raise ValueError("Two files have the same destination.")

        completed = []
        try:
            for op in operations:
                source = safe_child(root, op["source"])
                destination = safe_child(root, op["destination"])

                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    raise ValueError("Destination appeared during operation.")

                shutil.move(str(source), str(destination))
                completed.append(op)

        except Exception:
            # Roll back completed moves if a later move fails.
            for op in reversed(completed):
                try:
                    source = safe_child(root, op["source"])
                    destination = safe_child(root, op["destination"])
                    source.parent.mkdir(parents=True, exist_ok=True)
                    if destination.exists() and not source.exists():
                        shutil.move(str(destination), str(source))
                except OSError:
                    pass
            raise

        history = read_history()
        history.append({
            "id": plan_id,
            "folder": folder,
            "operations": completed,
            "undone": False
        })
        write_history(history)

        json_response(self, 200, {
            "message": "Organization complete.",
            "plan_id": plan_id,
            "moved": len(completed)
        })

    def undo(self, body):
        plan_id = body.get("plan_id")
        history = read_history()

        entry = next(
            (item for item in reversed(history)
             if item.get("id") == plan_id),
            None
        )

        if not entry:
            raise ValueError("Operation history was not found.")

        if entry.get("undone"):
            raise ValueError("This operation has already been undone.")

        root = get_root(entry.get("folder"))
        operations = entry.get("operations", [])

        # Check all reverse moves before performing any.
        for op in operations:
            source = safe_child(root, op["source"])
            destination = safe_child(root, op["destination"])

            if not destination.is_file():
                raise ValueError("Cannot undo: an organized file is missing.")
            if source.exists():
                raise ValueError(
                    "Cannot undo: original filename is already in use."
                )

        completed = []
        try:
            for op in reversed(operations):
                source = safe_child(root, op["source"])
                destination = safe_child(root, op["destination"])
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(destination), str(source))
                completed.append(op)

        except Exception:
            # Restore the organized state if undo fails partway.
            for op in reversed(completed):
                try:
                    source = safe_child(root, op["source"])
                    destination = safe_child(root, op["destination"])
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if source.exists() and not destination.exists():
                        shutil.move(str(source), str(destination))
                except OSError:
                    pass
            raise

        entry["undone"] = True
        write_history(history)

        json_response(self, 200, {
            "message": "Undo complete.",
            "restored": len(completed)
        })


def main():
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    server = ThreadingHTTPServer((HOST, PORT), LaterLessHandler)
    print(f"LaterLess server running at http://{HOST}:{PORT}")
    print(f"Sample folder area: {SAMPLE_DIR}")
    print("Only folders inside sample_files are permitted.")
    print("Press Ctrl+C to stop the server.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping LaterLess...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

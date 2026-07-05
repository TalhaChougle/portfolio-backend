import os
import re
import json
import requests
import google.generativeai as genai
from io import BytesIO
from pypdf import PdfReader

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.0-flash"


def _model():
    return genai.GenerativeModel(MODEL_NAME)


def extract_text_from_file(content: bytes, content_type: str, filename: str, max_chars: int = 6000) -> str:
    """Best-effort text extraction from PDF or plain text. Returns '' for unsupported types (e.g. images, docx)."""
    try:
        if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
            reader = PdfReader(BytesIO(content))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
            return text[:max_chars]
        if content_type and content_type.startswith("text/"):
            return content.decode("utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""
    return ""


def fetch_github_repo(github_url: str) -> dict:
    """Fetch repo name, description, and language breakdown from GitHub's public API."""
    m = re.search(r"github\.com/([^/]+)/([^/?#]+)", github_url)
    if not m:
        raise ValueError("Not a valid GitHub URL")
    owner, repo = m.group(1), m.group(2).rstrip(".git")

    repo_res = requests.get(f"https://api.github.com/repos/{owner}/{repo}", timeout=10)
    if repo_res.status_code != 200:
        raise ValueError("Repository not found or private")
    repo_data = repo_res.json()

    langs_res = requests.get(f"https://api.github.com/repos/{owner}/{repo}/languages", timeout=10)
    languages = list(langs_res.json().keys()) if langs_res.status_code == 200 else []

    return {
        "name": repo_data.get("name", repo),
        "raw_description": repo_data.get("description") or "",
        "languages": languages,
        "topics": repo_data.get("topics", []),
    }


def rewrite_project_description(raw_description: str, languages: list, topics: list) -> str:
    """Use Gemini to turn a raw GitHub description into a polished 3-4 line portfolio description."""
    if not GEMINI_API_KEY:
        return raw_description
    prompt = (
        "Rewrite this into a polished 3-4 line project description for a cybersecurity/software "
        "portfolio. Be specific and concrete, no fluff, no marketing language. "
        f"Raw description: {raw_description or '(none provided)'}\n"
        f"Languages/tech: {', '.join(languages) if languages else 'unknown'}\n"
        f"Topics: {', '.join(topics) if topics else 'none'}\n"
        "Return ONLY the description text, no preamble."
    )
    try:
        resp = _model().generate_content(prompt)
        return resp.text.strip()
    except Exception:
        return raw_description


def extract_cert_info(text: str) -> dict:
    """Ask Gemini for {date, description} from extracted certificate text. Never asks for title."""
    if not text.strip() or not GEMINI_API_KEY:
        return {"date": "", "description": ""}
    prompt = (
        "This is text extracted from a certificate. Extract ONLY the date (format: Month Year, e.g. "
        "'May 2026', or just the year if that's all you can find) and write a 3-4 line description of "
        "what the certificate is for, what was covered/achieved. Do NOT include the certificate title "
        "or recipient name in the description.\n"
        'Return strict JSON only, no markdown fences: {"date": "...", "description": "..."}\n\n'
        f"Certificate text:\n{text}"
    )
    try:
        resp = _model().generate_content(prompt)
        raw = resp.text.strip().strip("`").removeprefix("json").strip()
        data = json.loads(raw)
        return {"date": data.get("date", ""), "description": data.get("description", "")}
    except Exception:
        return {"date": "", "description": ""}


def extract_multi_cert_info(texts: list) -> list:
    """Same as extract_cert_info but for a multi-page merged PDF (list of per-page text)."""
    return [extract_cert_info(t) for t in texts]


def extract_doc_description(text: str) -> str:
    """Ask Gemini for a 3-4 line description of a lab report / publication from its extracted text."""
    if not text.strip() or not GEMINI_API_KEY:
        return ""
    prompt = (
        "This is text extracted from a lab report or academic publication. Write a 3-4 line description "
        "summarizing its purpose, methodology, and findings/conclusions. No preamble, no title, just the "
        "description text.\n\n"
        f"Document text:\n{text}"
    )
    try:
        resp = _model().generate_content(prompt)
        return resp.text.strip()
    except Exception:
        return ""


def extract_pdf_page_texts(content: bytes, max_chars_per_page: int = 4000) -> list:
    """Return a list of extracted text, one entry per PDF page (for multi-cert merged PDFs)."""
    try:
        reader = PdfReader(BytesIO(content))
        return [(p.extract_text() or "")[:max_chars_per_page] for p in reader.pages]
    except Exception:
        return []

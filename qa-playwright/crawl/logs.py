"""
Logging with two sinks:

  - TERMINAL (stdout)  -> INFO level, previews only. Same verbosity as before.
  - FILE (run.log)     -> DEBUG level, EVERYTHING in full: full system prompts,
                          full DOM we send to the AI, full AI responses, every
                          Playwright action.

The pattern: we log a short INFO "preview" line (goes to both) AND a DEBUG
"full" line (goes only to the file). So the terminal stays readable and the
file has the complete record for after-the-fact analysis.

Env knobs:
  LOG_FILE=path   change the file (default run.log, overwritten each run)
  LOG_LEVEL=DEBUG make the terminal verbose too
"""
import json
import logging
import os
import sys

LOG_FILE = os.environ.get("LOG_FILE", "run.log")
_FMT = logging.Formatter(
    "%(asctime)s | %(levelname)-5s | %(name)-12s | %(message)s", "%H:%M:%S"
)


def setup() -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()  # idempotent if called twice

    term = logging.StreamHandler(sys.stdout)
    term.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
    term.setFormatter(_FMT)
    root.addHandler(term)

    fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(_FMT)
    root.addHandler(fh)

    # silence noisy third-party transport logs so run.log stays our trace
    for noisy in ("httpcore", "httpx", "urllib3", "google_genai", "google"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("logs").info(
        "logging -> terminal (%s, previews) + %s (DEBUG, full)",
        term.level and logging.getLevelName(term.level) or "INFO", LOG_FILE,
    )


def get(name: str) -> logging.Logger:
    return logging.getLogger(name)


def preview(text: str, n: int = 1200) -> str:
    """Truncate long text for the terminal."""
    text = text or ""
    if len(text) <= n:
        return text
    return text[:n] + f"\n... [+{len(text) - n} more chars — see {LOG_FILE} for full]"


def pretty(obj) -> str:
    """Pretty-print a pydantic model or dict as JSON."""
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump()
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


def block(logger: logging.Logger, label: str, content: str) -> None:
    """Log a big blob: a preview line (terminal + file) and the full content
    (file only, via DEBUG)."""
    content = content or ""
    logger.info("%s (%d chars, preview):\n%s", label, len(content), preview(content))
    logger.debug("%s (FULL):\n%s", label, content)

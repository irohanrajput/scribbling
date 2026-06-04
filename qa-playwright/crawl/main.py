"""
Orchestrator. The whole flow:

  1. cache-first: if a session file exists, reuse it and SKIP login entirely.
  2. otherwise (option A): open the start URL, let the AI analyze it to find the
     login link, run the login agent there, then cache the session.
  3. crawl the (now authenticated) site BFS to depth 2.
  4. write a JSON + markdown report.

All config (target URL, test credentials) is read from .env — nothing secret
or site-specific is hardcoded here. See .env.example for the expected keys.
"""
import json
import os
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

import logs
from logs import get

logs.setup()
log = get("main")

# Load .env (simple parser, no extra dependency) before importing modules that
# read GEMINI_API_KEY / MODEL from the environment.
def _load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

_load_dotenv()

from ai import AIClient
from browser import has_cache, save_session, load_context, load_page
from crawler import crawl
from login_agent import run_login


def _env(key: str, default=None, required: bool = False) -> str:
    val = os.environ.get(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required env var {key} — set it in .env "
                           f"(see .env.example)")
    return val


CONFIG = {
    "url": _env("TARGET_URL", required=True),       # site under test
    "email": _env("TEST_EMAIL", required=True),     # test credentials
    "password": _env("TEST_PASSWORD", required=True),
    "storage_path": _env("STORAGE_PATH", "session_alpha.json"),
    "max_depth": int(_env("MAX_DEPTH", "2")),
    "max_links": int(_env("MAX_LINKS", "10")),
}


def authenticate(browser, ai: AIClient, config: dict):
    """Return an authenticated context, reusing cache if present."""
    if has_cache(config["storage_path"]):
        log.info("=== AUTH === cache present -> reusing session, skipping login")
        return load_context(browser, config["storage_path"])

    log.info("=== AUTH === no cache -> opening %s to discover the login link",
             config["url"])
    context = browser.new_context()
    page = context.new_page()
    dom = load_page(page, config["url"])

    analysis = ai.analyze_page(dom)
    if not analysis.login_link:
        raise RuntimeError("AI could not find a login link on the start page.")

    login_url = urljoin(config["url"], analysis.login_link)
    log.info("login link discovered: %s", login_url)

    creds = {"email": config["email"], "password": config["password"]}
    if not run_login(page, ai, login_url, creds):
        raise RuntimeError("Authentication failed -> aborting test run.")

    save_session(context, page, config["storage_path"])
    page.close()
    return context


def write_report(results: list[dict], path: str = "report") -> None:
    with open(f"{path}.json", "w") as f:
        json.dump(results, f, indent=2)

    lines = ["# QA Crawl Report\n"]
    for r in results:
        lines.append(f"## {r['url']}  (depth {r['depth']})")
        lines.append(f"_{r['site_type']} — {r['summary']}_\n")
        for tc in r["test_cases"]:
            lines.append(f"- **{tc['title']}**")
            for s in tc["steps"]:
                lines.append(f"  - {s}")
            lines.append(f"  - _Expected:_ {tc['expected']}")
        lines.append("")
    with open(f"{path}.md", "w") as f:
        f.write("\n".join(lines))
    log.info("report written to %s.json / %s.md", path, path)


def main():
    log.info("QA crawler starting | target=%s", CONFIG["url"])
    ai = AIClient()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = authenticate(browser, ai, CONFIG)
        results = crawl(context, ai, CONFIG["url"],
                        CONFIG["max_depth"], CONFIG["max_links"])
        write_report(results)
        browser.close()
    log.info("DONE")


if __name__ == "__main__":
    main()

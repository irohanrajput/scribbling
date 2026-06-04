"""
Playwright plumbing: session creation, the cache-first session reuse, executing
a single AI-decided login action, and capturing as much client-side state as we
can.

`context.storage_state()` already persists cookies + localStorage (under
"origins"). It does NOT capture sessionStorage, so we grab that ourselves from
the live page and re-inject it on reuse via an init script. (Token expiry /
validity checks are explicitly out of scope for phase 1.)
"""
import json
import os

from schemas import LoginAction
from disambiguate import resolve_unique
from logs import get

log = get("browser")


def has_cache(path: str) -> bool:
    """A cache is usable only if it exists AND is valid JSON. An empty/corrupt
    file (e.g. left by an interrupted run) is treated as no cache, so we just
    log in fresh instead of crashing."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    try:
        with open(path) as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, OSError):
        log.warning("ignoring corrupt session cache at %s (will log in fresh)", path)
        return False


def save_session(context, page, path: str) -> None:
    """Persist cookies + localStorage (via storage_state) AND sessionStorage."""
    state = context.storage_state()  # {"cookies": [...], "origins": [...]}
    try:
        session_storage = page.evaluate(
            "() => Object.fromEntries(Object.entries(sessionStorage))"
        )
    except Exception:
        session_storage = {}
    state["sessionStorage"] = session_storage  # our own extra key
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
    log.info("session cached at %s (%d cookies, %d localStorage origins, "
             "%d sessionStorage keys)", path,
             len(state.get("cookies", [])),
             len(state.get("origins", [])),
             len(session_storage))


def load_context(browser, path: str):
    """Recreate an authenticated context from cache (no login attempt)."""
    with open(path) as f:
        data = json.load(f)

    # sessionStorage is our own addition; strip it before handing the rest to
    # Playwright (which would reject the unknown key), then re-inject it.
    session_storage = data.pop("sessionStorage", {})
    context = browser.new_context(storage_state=data)

    if session_storage:
        context.add_init_script(
            "(() => { const d = "
            + json.dumps(session_storage)
            + "; for (const k in d) sessionStorage.setItem(k, d[k]); })();"
        )
    log.info("session cache found at %s, reusing (%d cookies, %d sessionStorage keys)",
             path, len(data.get("cookies", [])), len(session_storage))
    return context


def do_login_action(page, action: LoginAction, credentials: dict, ai) -> None:
    """Execute one LoginAction. Real credentials are substituted HERE, so they
    never travel through the AI prompt. Selectors are resolved to a single
    element first (handling ambiguity via keywords + AI)."""
    if action.action == "fill":
        value = action.value
        masked = action.value  # what we show in logs (never the real secret)
        if value == "EMAIL":
            value, masked = credentials["email"], "<email>"
        elif value == "PASSWORD":
            value, masked = credentials["password"], "<password>"
        loc = resolve_unique(page, action.selector, "login", ai)
        log.info("  ▶ executing: FILL  %s  ←  %s", action.selector, masked)
        loc.fill(value)

    elif action.action == "click":
        loc = resolve_unique(page, action.selector, "login", ai)
        log.info("  ▶ executing: CLICK %s  (expect_navigation=%s)",
                 action.selector, action.expect_navigation)
        if action.expect_navigation:
            with page.expect_navigation():
                loc.click()
        else:
            loc.click()

    elif action.action == "goto":
        log.info("  ▶ executing: GOTO  %s", action.value)
        page.goto(action.value)

    elif action.action == "wait":
        log.info("  ▶ executing: WAIT  1000ms")
        page.wait_for_timeout(1000)

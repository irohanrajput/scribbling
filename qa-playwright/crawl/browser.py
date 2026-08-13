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
from logs import get, block

log = get("browser")


# Settle knobs
_MIN_WAIT_MS = 1500    # floor: give JS time to fire its initial data fetch
_QUIET_MS = 1200       # DOM must be mutation-free this long to count as quiet
_POLL_MS = 200
_MAX_WAIT_MS = 20000   # hard cap so a never-quiet page can't hang us
_NET_TYPES = ("xhr", "fetch")  # only these count; ignore ws/eventsource/img/etc.

# Installs a MutationObserver (idempotent, re-installs after a full navigation
# wiped it) and returns ms since the last DOM mutation.
_DOM_QUIET_JS = """
() => {
  if (!window.__qaObserver) {
    window.__qaLastMutation = Date.now();
    window.__qaObserver = new MutationObserver(() => { window.__qaLastMutation = Date.now(); });
    window.__qaObserver.observe(document.documentElement,
      { childList: true, subtree: true, attributes: true, characterData: true });
  }
  return Date.now() - window.__qaLastMutation;
}
"""


def wait_for_settled(page) -> None:
    """Wait until the page is genuinely done loading, generically:

      settled = (no xhr/fetch requests in flight) AND (DOM mutation-quiet)

    Why both: a loading skeleton is static HTML (DOM-quiet) while its data
    fetch is still pending (network-busy) - so requiring BOTH waits past the
    skeleton until the real content fetch returns and renders. No site-specific
    markup/text. Floor avoids snapshotting before JS even fires its fetch; cap
    means a never-quiet page just proceeds with what it has."""
    inflight = {"n": 0}

    def _on_request(req):
        if req.resource_type in _NET_TYPES:
            inflight["n"] += 1

    def _on_done(req):
        if req.resource_type in _NET_TYPES:
            inflight["n"] = max(0, inflight["n"] - 1)

    page.on("request", _on_request)
    page.on("requestfinished", _on_done)
    page.on("requestfailed", _on_done)

    waited = 0
    try:
        while waited < _MAX_WAIT_MS:
            try:  # also (re)installs the observer, incl. after a redirect
                since_mut = page.evaluate(_DOM_QUIET_JS)
            except Exception:
                since_mut = 0  # mid-navigation: treat as just-changed, keep waiting
            net_idle = inflight["n"] == 0
            dom_quiet = since_mut >= _QUIET_MS
            log.debug("  settle: inflight_xhr=%d net_idle=%s dom_idle=%sms (need>=%d) waited=%dms",
                      inflight["n"], net_idle, since_mut, _QUIET_MS, waited)
            if waited >= _MIN_WAIT_MS and net_idle and dom_quiet:
                log.info("  page settled (no xhr/fetch in-flight + DOM quiet %dms) after %dms",
                         _QUIET_MS, waited)
                return
            page.wait_for_timeout(_POLL_MS)
            waited += _POLL_MS
        log.info("  settle cap reached (%dms), proceeding (inflight_xhr=%d)",
                 _MAX_WAIT_MS, inflight["n"])
    finally:
        page.remove_listener("request", _on_request)
        page.remove_listener("requestfinished", _on_done)
        page.remove_listener("requestfailed", _on_done)


def load_page(page, url: str) -> str:
    """Navigate and return the fully-rendered DOM (after the settle wait)."""
    log.info("navigating to %s", url)
    page.goto(url, wait_until="domcontentloaded")
    wait_for_settled(page)
    try:  # nudge lazy/infinite-scroll content, then let it settle again
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        wait_for_settled(page)
    except Exception:
        pass
    dom = page.content()
    block(log, "captured DOM", dom)  # full DOM -> file, preview -> terminal
    return dom


def has_password_field(page) -> bool:
    """Deterministic 'is this a login page?' backstop: a password input exists.
    Generic across stacks; complements the AI's is_login_page judgment (which
    also catches email-first steps where no password field is shown yet)."""
    try:
        return page.locator("input[type=password]").count() > 0
    except Exception:
        return False


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

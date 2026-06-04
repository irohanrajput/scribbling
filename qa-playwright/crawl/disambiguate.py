"""
Turn a (possibly ambiguous) CSS selector into a SINGLE locator.

Flow:
  count == 1  -> use it, no extra work
  count == 0  -> selector is wrong / element not present -> error
  count  > 1  -> ambiguous:
                   1. read each match's surrounding form text
                   2. score it with the keyword bank (cheap, deterministic)
                   3. if one candidate clearly wins -> use it
                   4. else -> ask the AI to pick the index (the tiebreaker)

`intent` is what we are trying to do here ("login"), which is what we score the
surrounding text against.
"""
from keywords import pick_index, normalize
from logs import get, preview

log = get("disambig")

CTX_CHARS = 400  # how much surrounding text to keep per candidate

# climb to the nearest <form> (or parent) and return its visible text
_CONTEXT_JS = "(n) => { const f = n.closest('form') || n.parentElement; return f ? f.innerText : ''; }"


def _context(locator_nth) -> str:
    try:
        txt = locator_nth.evaluate(_CONTEXT_JS)
    except Exception:
        txt = ""
    return normalize(txt)[:CTX_CHARS]


def resolve_unique(page, selector: str, intent: str, ai):
    loc = page.locator(selector)
    n = loc.count()
    log.info("resolving selector %r -> %d match(es)", selector, n)

    if n == 0:
        raise RuntimeError(f"selector {selector!r} matched 0 elements")
    if n == 1:
        log.info("  unique match, proceeding")
        return loc.first

    # ---- ambiguous ----
    log.warning("  AMBIGUOUS: %d matches; disambiguating (intent=%s)", n, intent)
    candidates = [(i, _context(loc.nth(i))) for i in range(n)]
    for i, ctx in candidates:
        log.info("  candidate[%d] surrounding text: %s", i, preview(ctx, 160))

    # ---- step 1: keyword bank ----
    scored, pick = pick_index(candidates, intent)
    for idx, net, s in scored:
        log.info("  candidate[%d] keywords: login=%d %s | signup=%d %s | net(%s)=%+d",
                 idx, s["login"], s["login_hits"],
                 s["signup"], s["signup_hits"], intent, net)

    if pick is not None:
        log.info("  ✓ KEYWORD pick -> candidate[%d] (confident, no AI needed)", pick)
        return loc.nth(pick)

    # ---- step 2: AI tiebreaker ----
    log.info("  keywords inconclusive -> asking AI to disambiguate")
    pick = ai.disambiguate(selector, candidates, intent)
    pick = max(0, min(pick, n - 1))  # clamp to a valid index
    log.info("  ✓ AI pick -> candidate[%d]", pick)
    return loc.nth(pick)

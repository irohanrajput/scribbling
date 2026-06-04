"""
Keyword bank for telling a LOGIN region apart from a SIGNUP region.

Why this exists: login and signup forms often have identical fields (email +
password), so the fields carry no signal. What separates them is the
*surrounding action text* - the submit button, heading, and helper links. We
score that text against two lists.

Two lists, not one, on purpose: 'sign in' and 'sign up' differ by a single word,
so a login-only list can't disambiguate. We score against BOTH and take the net.

Matching is word-boundary + normalized (lowercased, whitespace-collapsed) so
'signing' does not match 'sign' and 'Sign In' == 'sign in'. English-only for
now; non-English wording falls through to the AI tiebreaker.
"""
import re

LOGIN_KEYWORDS = [
    "login", "log in", "log-in", "sign in", "signin", "sign-in",
    "forgot password", "remember me",  # login-only tells
]

SIGNUP_KEYWORDS = [
    "sign up", "signup", "sign-up", "register", "registration",
    "create account", "create an account", "create your account",
    "join", "get started", "already have an account",  # signup-only tells
]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _count(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    hits = [kw for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text)]
    return len(hits), hits


def score(text: str) -> dict:
    """Return login/signup keyword counts + which keywords hit, for one text."""
    t = normalize(text)
    login_n, login_hits = _count(t, LOGIN_KEYWORDS)
    signup_n, signup_hits = _count(t, SIGNUP_KEYWORDS)
    return {
        "login": login_n, "login_hits": login_hits,
        "signup": signup_n, "signup_hits": signup_hits,
    }


def pick_index(candidates: list[tuple[int, str]], intent: str):
    """Score each candidate's surrounding text and pick the best match for
    `intent` ('login' or 'signup').

    Returns (scored, pick) where:
      - scored = [(index, net, score_dict), ...] for logging
      - pick   = the chosen index if we are CONFIDENT (a single clear winner
                 with a positive net), else None -> caller asks the AI.
    """
    other = "signup" if intent == "login" else "login"
    scored = []
    for idx, ctx in candidates:
        s = score(ctx)
        net = s[intent] - s[other]
        scored.append((idx, net, s))

    best_net = max(n for _, n, _ in scored)
    winners = [idx for idx, n, _ in scored if n == best_net]
    confident = len(winners) == 1 and best_net > 0
    return scored, (winners[0] if confident else None)

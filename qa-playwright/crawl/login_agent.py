"""
The login agent. This is the ONE place in the system with a real perceive->act
loop: read DOM -> ask AI for the next action -> execute it -> read DOM again.

Because we ask for one action at a time and re-read the DOM each iteration, the
SAME loop handles a single-page login (email+password together) and a multi-step
login (email -> continue -> password) without any special-casing. The AI simply
sees a different DOM on each pass.

Phase 1: one attempt, no retries. If we run out of steps, login failed.
"""
from ai import AIClient
from browser import do_login_action, wait_for_settled
from logs import get

log = get("login")


def run_login(page, ai: AIClient, credentials: dict, login_url: str = None,
              max_steps: int = 8) -> bool:
    if login_url:
        log.info("=== LOGIN START === navigating to %s", login_url)
        page.goto(login_url, wait_until="domcontentloaded")
        wait_for_settled(page)
    else:
        log.info("=== LOGIN START === logging in on the current page")

    history: list[str] = []
    for step in range(1, max_steps + 1):
        dom = page.content()
        log.info("--- login step %d/%d | current DOM=%d chars | asking Gemini what to do next",
                 step, max_steps, len(dom))
        action = ai.decide_login_action(dom, history)
        log.info("[login step %d] decision: %s", step, action.reasoning)

        if action.done:
            log.info("=== LOGIN SUCCESS === (Gemini reports the user is authenticated)")
            return True

        do_login_action(page, action, credentials, ai)
        history.append(action.reasoning)
        page.wait_for_timeout(500)  # let the DOM settle before re-reading

    log.error("=== LOGIN FAILED === ran out of steps (%d)", max_steps)
    return False

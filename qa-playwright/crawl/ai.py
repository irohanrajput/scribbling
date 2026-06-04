"""
Gemini client. Three jobs, each a single structured call:

  1. decide_login_action(dom, history)  -> LoginAction   (called in a loop)
  2. analyze_page(dom)                   -> PageAnalysis
  3. generate_test_cases(actionables)    -> TestCaseSet

Few-shot examples below use ONLY fictional sites/selectors on purpose. Feeding
the model real markup from a target would bias it toward those exact selectors
instead of reading the DOM it is actually given. The examples teach the SHAPE
of a good answer, not the content.
"""
import os

from google import genai
from google.genai import types

from schemas import LoginAction, PageAnalysis, TestCaseSet, Actionable, Disambiguation
from logs import get, preview, pretty, block

log = get("ai")

MODEL = os.environ.get("MODEL", "gemini-2.5-flash")

# Raw DOM can be huge. We are intentionally NOT cleaning it yet (phase 1), but a
# generous guardrail stops a multi-megabyte page from blowing up a request.
MAX_DOM_CHARS = 200_000


def _trim(dom: str) -> str:
    return dom[:MAX_DOM_CHARS]


class AIClient:
    def __init__(self, api_key: str | None = None):
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("Set GEMINI_API_KEY (or GOOGLE_API_KEY) in the env.")
        self.client = genai.Client(api_key=key)

    def _generate(self, job: str, system: str, prompt: str, schema):
        log.info("→ calling Gemini [%s] | model=%s | prompt=%d chars",
                 job, MODEL, len(prompt))
        # full system + prompt (incl. full DOM) go to the file; previews to term
        block(log, f"  [{job}] SYSTEM instruction", system)
        block(log, f"  [{job}] PROMPT", prompt)

        resp = self.client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0,
            ),
        )
        parsed = resp.parsed
        block(log, f"← Gemini [{job}] RESPONSE", pretty(parsed))
        return parsed

    # ---------- 1. Login agent ----------

    def decide_login_action(self, dom: str, history: list[str]) -> LoginAction:
        system = (
            "You are a browser automation agent logging a user in. You are given "
            "the CURRENT page DOM and the history of what you already did. Decide "
            "the ONE next action. Never output the real credentials: for filling "
            "the email field use value 'EMAIL', for the password field use value "
            "'PASSWORD'. When the DOM shows the user is already authenticated "
            "(e.g. a logout/sign-out control, an account avatar, or you are no "
            "longer on a login form), set done=true and leave other fields null.\n\n"
            "FEW-SHOT (fictional examples, do not copy selectors literally):\n"
            "Ex A - single-page form visible (email, password, submit all present):\n"
            "  step 1 -> {reasoning:'fill email', done:false, action:'fill', "
            "selector:'#email', value:'EMAIL', expect_navigation:false}\n"
            "  step 2 -> {reasoning:'fill password', done:false, action:'fill', "
            "selector:'#password', value:'PASSWORD', expect_navigation:false}\n"
            "  step 3 -> {reasoning:'submit', done:false, action:'click', "
            "selector:'button[type=submit]', value:null, expect_navigation:true}\n"
            "  step 4 (dashboard now shows a 'Log out' button) -> {reasoning:'logged in', done:true}\n\n"
            "Ex B - two-step form (only email + Continue visible first):\n"
            "  step 1 -> {reasoning:'fill email', done:false, action:'fill', "
            "selector:'input[name=identifier]', value:'EMAIL', expect_navigation:false}\n"
            "  step 2 -> {reasoning:'advance to password step', done:false, action:'click', "
            "selector:'button:has-text(\"Continue\")', value:null, expect_navigation:false}\n"
            "  step 3 (DOM now shows a password field) -> {reasoning:'fill password', "
            "done:false, action:'fill', selector:'input[type=password]', value:'PASSWORD'}\n"
            "  step 4 -> {reasoning:'submit', done:false, action:'click', "
            "selector:'button:has-text(\"Sign in\")', value:null, expect_navigation:true}\n"
        )
        hist = "\n".join(f"- {h}" for h in history) or "(nothing yet)"
        prompt = f"History of actions so far:\n{hist}\n\nCURRENT DOM:\n{_trim(dom)}"
        return self._generate("login-action", system, prompt, LoginAction)

    def disambiguate(self, selector: str, candidates: list[tuple[int, str]], intent: str) -> int:
        """Tiebreaker: a selector matched several elements and the keyword bank
        couldn't pick. Given each candidate's surrounding text, choose the one
        belonging to the `intent` (e.g. login) region. Returns an index."""
        system = (
            f"A CSS selector matched multiple elements while we were trying to "
            f"perform a '{intent}' action. Each candidate is described by the "
            f"visible text of its surrounding form. Choose the index of the "
            f"element that belongs to the {intent.upper()} flow (NOT signup or "
            f"any other form). Return that index."
        )
        listing = "\n".join(
            f"[{i}] surrounding text: {ctx}" for i, ctx in candidates
        )
        prompt = f"Selector: {selector!r}\nGoal: {intent.upper()}\n\nCandidates:\n{listing}"
        result = self._generate("disambiguate", system, prompt, Disambiguation)
        return result.index

    # ---------- 2. Page analysis ----------

    def analyze_page(self, dom: str) -> PageAnalysis:
        system = (
            "You are a QA crawler analyzing a web page from its DOM. Return:\n"
            "- site_type and a one-line summary,\n"
            "- login_link: the sign-in/login URL if one is present, else null,\n"
            "- links: navigation links, each flagged is_feature (true = a product "
            "feature worth QA testing; false = boilerplate like terms/privacy/careers),\n"
            "- actionables: buttons, forms, inputs, toggles a user can interact with.\n\n"
            "FEW-SHOT (fictional, do not copy):\n"
            "For an imaginary recipe-sharing site you might return site_type "
            "'recipe community site', links like {text:'Browse Recipes', url:'/recipes', "
            "is_feature:true} and {text:'Privacy', url:'/privacy', is_feature:false}, "
            "and actionables like {label:'Add Recipe', kind:'button', "
            "selector:'a.add-recipe', description:'opens the recipe creation form'}.\n"
            "Always read the ACTUAL DOM given; the example only shows the output shape."
        )
        return self._generate("analyze-page", system, f"DOM:\n{_trim(dom)}", PageAnalysis)

    # ---------- 3. Test case generation ----------

    def generate_test_cases(self, actionables: list[Actionable]) -> TestCaseSet:
        system = (
            "You are a QA engineer. Given a page's actionable elements, write "
            "natural-language test cases (no code). Each case: a title, ordered "
            "steps, and an expected result. Cover the obvious happy path plus one "
            "edge/validation case where it makes sense.\n\n"
            "FEW-SHOT (fictional): for an actionable {label:'Subscribe', "
            "kind:'form', description:'newsletter email signup'} a good case is "
            "{title:'Subscribe with a valid email', steps:['Enter a valid email', "
            "'Click Subscribe'], expected:'A success confirmation is shown'} and an "
            "edge case {title:'Reject invalid email', steps:['Enter \"abc\"', "
            "'Click Subscribe'], expected:'A validation error is shown'}."
        )
        items = "\n".join(
            f"- {a.label} ({a.kind}): {a.description}" for a in actionables
        )
        return self._generate("test-cases", system, f"Actionable elements:\n{items}", TestCaseSet)

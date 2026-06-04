"""
Structured shapes the AI must return.

We use pydantic models as Gemini `response_schema`s. That forces the model to
reply with JSON matching these shapes (no prose, no regex parsing) and we get
back validated python objects via `response.parsed`.
"""
from typing import Optional
from pydantic import BaseModel, Field


# ---------- Login agent ----------

class LoginAction(BaseModel):
    """One single step the login agent wants Playwright to perform next.

    The agent sees the current DOM and decides ONE action at a time. Doing it
    one-at-a-time is what lets the same loop handle both single-page logins
    (email + password together) and multi-step logins (email -> continue ->
    password): we just re-read the DOM after every action and ask again.
    """
    reasoning: str = Field(description="Why this action, in one short sentence.")
    done: bool = Field(description="True ONLY when the user is already logged in.")
    action: Optional[str] = Field(
        default=None, description="One of: fill, click, goto, wait. Null when done."
    )
    selector: Optional[str] = Field(
        default=None, description="CSS selector for the target element."
    )
    value: Optional[str] = Field(
        default=None,
        description=(
            "For 'fill': use the literal placeholder 'EMAIL' or 'PASSWORD' for "
            "credentials (never the real value), or literal text otherwise. "
            "For 'goto': the URL."
        ),
    )
    expect_navigation: bool = Field(
        default=False, description="True if this action triggers a page navigation."
    )


# ---------- Page analysis ----------

class Link(BaseModel):
    text: str = Field(description="Visible link text.")
    url: str = Field(description="href value (may be relative).")
    is_feature: bool = Field(
        description=(
            "True if this is a product feature a QA engineer would test "
            "(e.g. a trips list, a story editor). False for boilerplate like "
            "terms, privacy, careers."
        )
    )


class Actionable(BaseModel):
    label: str = Field(description="What the user sees / the element's purpose.")
    kind: str = Field(description="button | form | input | toggle | link-action")
    selector: str = Field(description="CSS selector to reach it.")
    description: str = Field(description="What this element is expected to do.")


class PageAnalysis(BaseModel):
    site_type: str = Field(description="One line: what kind of site/page is this.")
    summary: str = Field(description="One line: what this page is for.")
    login_link: Optional[str] = Field(
        default=None,
        description="URL of the login / sign-in entry point if present on this page.",
    )
    links: list[Link] = Field(default_factory=list)
    actionables: list[Actionable] = Field(default_factory=list)


# ---------- Test case generation ----------

class TestCase(BaseModel):
    title: str
    steps: list[str] = Field(description="Natural-language steps a tester would follow.")
    expected: str = Field(description="Expected result.")


class TestCaseSet(BaseModel):
    cases: list[TestCase] = Field(default_factory=list)

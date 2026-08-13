"""
The crawler. Unlike the login agent, this is NOT agentic - it is a plain
breadth-first walk that *uses* the AI for extraction at each node:

  for each page (depth <= 2):
      analyze_page(dom)            -> links + actionables
      generate_test_cases(actionables)

Depth model: home = depth 0, its links = depth 1, their links = depth 2. We
analyze depth-2 pages but do not expand them further. Same-origin only, capped
at max_links per page.
"""
from urllib.parse import urljoin, urlparse

from ai import AIClient
from browser import load_page, wait_for_settled
from logs import get

log = get("crawler")


def read_page(page, ai: AIClient, url: str, max_loading_retries: int = 3):
    """Load a URL and return (dom, analysis), reliably.

    Timing-based waits can snapshot a page mid-load (e.g. during the quiet gap
    before a redirect fires), so we use the AI itself as the oracle: if it says
    the page is still loading, wait and re-check. This rides out spinners,
    delayed redirects and slow client renders generically — no markup guessing."""
    dom = load_page(page, url)
    analysis = ai.analyze_page(dom)

    tries = 0
    while analysis.is_loading and tries < max_loading_retries:
        tries += 1
        log.info("  AI says page still loading — waiting and re-checking (%d/%d)",
                 tries, max_loading_retries)
        page.wait_for_timeout(2000)   # give the app time to progress past loading
        wait_for_settled(page)
        dom = page.content()
        analysis = ai.analyze_page(dom)

    if analysis.is_loading:
        log.warning("  page still reports loading after %d retries; proceeding anyway",
                    max_loading_retries)
    return dom, analysis


def _in_scope(start: str, candidate: str) -> bool:
    """True only if `candidate` is under the start URL's path prefix on the same
    host. From https://abc.com/rohan we allow /rohan and /rohan/... but NOT /
    (climbing back up), NOT /rohanXYZ (sibling), and NOT other hosts. If the
    start URL has no path (e.g. https://abc.com), the whole host is in scope."""
    s, c = urlparse(start), urlparse(candidate)
    if c.netloc != s.netloc:
        return False
    base = s.path.rstrip("/")
    if not base:
        return True  # whole-host scope
    cpath = c.path.rstrip("/")
    return cpath == base or cpath.startswith(base + "/")


def crawl(context, ai: AIClient, start_url: str,
          max_depth: int = 2, max_links: int = 10) -> list[dict]:
    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(start_url, 0)]
    results: list[dict] = []

    _s = urlparse(start_url)
    log.info("=== CRAWL START === root=%s | scope=%s%s/* | max_depth=%d | max_links=%d",
             start_url, _s.netloc, _s.path.rstrip("/") or "", max_depth, max_links)

    while queue:
        url, depth = queue.pop(0)
        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        log.info("→ visiting [depth %d] %s  (queue=%d, visited=%d)",
                 depth, url, len(queue), len(visited))
        page = context.new_page()
        try:
            dom, analysis = read_page(page, ai, url)
        except Exception as e:
            log.warning("  skip %s: %s", url, e)
            page.close()
            continue

        log.info("  found %d links, %d actionables (site_type=%s)",
                 len(analysis.links), len(analysis.actionables), analysis.site_type)

        if analysis.actionables:
            log.info("  generating test cases for %d actionables", len(analysis.actionables))
            cases = ai.generate_test_cases(analysis.actionables).cases
            log.info("  generated %d test cases", len(cases))
        else:
            cases = []

        results.append({
            "url": url,
            "depth": depth,
            "site_type": analysis.site_type,
            "summary": analysis.summary,
            "actionables": [a.model_dump() for a in analysis.actionables],
            "test_cases": [c.model_dump() for c in cases],
        })
        page.close()

        if depth < max_depth:
            enqueued = skipped = 0
            for link in analysis.links[:max_links]:
                full = urljoin(url, link.url).split("#")[0]  # resolve + drop fragment
                if full in visited:
                    continue
                if not _in_scope(start_url, full):
                    log.debug("  out-of-scope, discarding: %s", full)
                    skipped += 1
                    continue
                queue.append((full, depth + 1))
                enqueued += 1
            log.info("  enqueued %d child links, discarded %d out-of-scope (depth %d)",
                     enqueued, skipped, depth + 1)

    log.info("=== CRAWL DONE === analyzed %d pages", len(results))
    return results

#!/usr/bin/env python3
"""Discover, validate and link-check resources for the WRISES Tools & Resources directory.

The website only reads ``data/resources.json``. This script helps maintainers keep that file
accurate. It never edits the catalog: it produces a report for a person to review.

What it does
  1. Validates ``data/resources.json`` and ``data/repo-review.json``.
  2. Lists the public repositories of the GitHub organization and compares them with the
     catalog: new (unreviewed) repositories, activity since the last review, and listed
     repositories that were archived, renamed, deleted or made private.
  3. Checks every URL in the catalog, plus absolute links in ``index.html`` and ``404.html``.
  4. Writes a Markdown report (default ``reports/discovery-report.md``).

Examples
  python scripts/discover_resources.py --validate-only
  python scripts/discover_resources.py
  python scripts/discover_resources.py --skip-links --output my-report.md

Set GITHUB_TOKEN (or GH_TOKEN) to raise the GitHub API rate limit (60 requests per hour
without a token). Requires Python 3.10+ and only the standard library.

Exit codes: 0 OK, 1 catalog validation errors, 2 broken links or new repositories (only with
--fail-on-broken / --fail-on-new), 3 the GitHub API could not be reached.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import html.parser
import http.cookiejar
import http.client
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ORG = "USACE-WRISES"
API_ROOT = "https://api.github.com"
USER_AGENT = ("Mozilla/5.0 (compatible; wrises-tools-link-check/1.0; "
              "+https://github.com/USACE-WRISES/tools)")

LINK_TYPES = ("app", "download", "documentation", "dataset", "repository", "publication", "reference")
STATUS_LABELS = {"Draft", "Alpha", "Beta", "Preliminary", "Experimental", "Archived"}
RESOURCE_TYPES = {
    "Web app", "Desktop app", "Website", "R package", "Python package", "ArcGIS toolbox",
    "Notebooks", "Dataset", "Training", "Report", "Model report", "R script", "Local application",
    "Assessment method",
}
CATEGORY_KEYS = {"id", "name", "description"}
RESOURCE_KEYS = {"id", "name", "fullName", "description", "category", "type", "tags", "featured",
                 "status", "note", "links", "repos"}
LINK_KEYS = {"type", "url", "label"}
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_TAGS = 8
MAX_DESCRIPTION = 280
MAX_NOTE = 160
REVIEW_DECISIONS = {"included", "excluded", "pending"}
REVIEW_IGNORE = {"pages", "homepage"}

# Hosts whose links are worth suggesting when a new repository's README is scanned. Anything
# else is ignored so that personal or internal links never end up in public CI logs.
README_LINK_HOSTS = ("github.io", "github.com", "shinyapps.io", "posit.cloud", "r-project.org",
                     "pypi.org", "doi.org", "zenodo.org", "hdl.handle.net", "huggingface.co")
SIGN_IN_HINTS = ("login", "signin", "sign-in", "sso", "oauth", "auth/", "cac", "adfs")
BOT_WALL_TITLES = ("verifying", "just a moment", "attention required", "access denied", "are you a robot",
                   "captcha", "security check")


# --------------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------------

def is_date(value: object) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def nonempty_str(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def md_cell(value: object) -> str:
    """Make a value safe for a Markdown table cell."""
    text = "" if value is None else str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").strip()


def norm_url(url: str) -> str:
    """Compare URLs loosely: ignore scheme, letter case, query, fragment and trailing slash."""
    parts = urllib.parse.urlsplit(url.strip())
    return f"{parts.netloc.lower()}{parts.path.rstrip('/').lower()}"


def pages_url(org: str, repo: str) -> str:
    host = f"{org.lower()}.github.io"
    return f"https://{host}/" if repo.lower() == host else f"https://{host}/{repo}/"


def parse_github_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def after_date(timestamp: str | None, date: str | None) -> bool:
    moment = parse_github_time(timestamp)
    if moment is None or not is_date(date):
        return False
    return moment.date() > dt.date.fromisoformat(date)


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


# --------------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------------

@dataclass
class Issue:
    level: str  # "error" or "warning"
    where: str
    message: str

    def line(self) -> str:
        return f"{self.level.upper()}: {self.where}: {self.message}"


def validate_catalog(catalog: object) -> list[Issue]:
    issues: list[Issue] = []

    def error(where: str, message: str) -> None:
        issues.append(Issue("error", where, message))

    def warning(where: str, message: str) -> None:
        issues.append(Issue("warning", where, message))

    if not isinstance(catalog, dict):
        error("catalog", "the top level must be a JSON object")
        return issues
    extra = set(catalog) - {"schemaVersion", "updated", "categories", "resources"}
    if extra:
        warning("catalog", f"unknown field(s): {', '.join(sorted(extra))}")
    if catalog.get("schemaVersion") != 1:
        error("schemaVersion", "must be 1")
    if not is_date(catalog.get("updated")):
        error("updated", "must be a date in YYYY-MM-DD format")

    category_ids: list[str] = []
    categories = catalog.get("categories")
    if not isinstance(categories, list) or not categories:
        error("categories", "must be a non-empty list")
        categories = []
    for index, category in enumerate(categories):
        where = f"categories[{index}]"
        if not isinstance(category, dict):
            error(where, "must be an object")
            continue
        cid = category.get("id")
        if not isinstance(cid, str) or not ID_RE.match(cid):
            error(where, "id must be a lowercase slug such as 'data-gis'")
        elif cid in category_ids:
            error(where, f"duplicate category id '{cid}'")
        else:
            category_ids.append(cid)
        if not nonempty_str(category.get("name")):
            error(where, "name is required")
        if "description" in category and not isinstance(category["description"], str):
            error(where, "description must be text")
        extra = set(category) - CATEGORY_KEYS
        if extra:
            warning(where, f"unknown field(s): {', '.join(sorted(extra))}")

    resources = catalog.get("resources")
    if not isinstance(resources, list):
        error("resources", "must be a list")
        return issues
    seen_ids: set[str] = set()
    used_categories: set[str] = set()
    for index, resource in enumerate(resources):
        where = f"resources[{index}]"
        if not isinstance(resource, dict):
            error(where, "must be an object")
            continue
        rid = resource.get("id")
        if isinstance(rid, str) and rid:
            where = f"resource '{rid}'"
        if not isinstance(rid, str) or not ID_RE.match(rid):
            error(where, "id must be a lowercase slug such as 'hype'")
        elif rid in seen_ids:
            error(where, "duplicate id")
        else:
            seen_ids.add(rid)
        extra = set(resource) - RESOURCE_KEYS
        if extra:
            warning(where, f"unknown field(s): {', '.join(sorted(extra))}")

        if not nonempty_str(resource.get("name")):
            error(where, "name is required")
        if "fullName" in resource and not nonempty_str(resource["fullName"]):
            error(where, "fullName must be non-empty text when present")
        description = resource.get("description")
        if not nonempty_str(description):
            error(where, "description is required")
        elif len(description) > MAX_DESCRIPTION:
            warning(where, f"description is {len(description)} characters; keep it to one or two "
                           f"sentences (under {MAX_DESCRIPTION})")
        category = resource.get("category")
        if category not in category_ids:
            error(where, f"category '{category}' is not defined in 'categories'")
        else:
            used_categories.add(category)
        rtype = resource.get("type")
        if not nonempty_str(rtype):
            error(where, "type is required (for example 'Web app' or 'R package')")
        elif rtype not in RESOURCE_TYPES:
            warning(where, f"type '{rtype}' is not one of the usual values: "
                           f"{', '.join(sorted(RESOURCE_TYPES))}")

        tags = resource.get("tags", [])
        if not isinstance(tags, list) or not all(nonempty_str(tag) for tag in tags):
            error(where, "tags must be a list of text values")
        else:
            if len(tags) > MAX_TAGS:
                warning(where, f"{len(tags)} tags; the page shows the first 4, search uses all "
                               f"(keep it to {MAX_TAGS} or fewer)")
            lowered = [tag.strip().lower() for tag in tags]
            if len(set(lowered)) != len(lowered):
                warning(where, "duplicate tags")

        if "featured" in resource and not isinstance(resource["featured"], bool):
            error(where, "featured must be true or false")
        if "status" in resource and resource["status"] is not None:
            if not nonempty_str(resource["status"]):
                error(where, "status must be text")
            elif resource["status"] not in STATUS_LABELS:
                warning(where, f"status '{resource['status']}' is unusual; use a documented label "
                               f"such as {', '.join(sorted(STATUS_LABELS))}")
        if "note" in resource and resource["note"] is not None:
            if not nonempty_str(resource["note"]):
                error(where, "note must be text")
            elif len(resource["note"]) > MAX_NOTE:
                warning(where, f"note is {len(resource['note'])} characters; keep it short")
        if "repos" in resource:
            repos = resource["repos"]
            if not isinstance(repos, list) or not all(nonempty_str(repo) for repo in repos):
                error(where, "repos must be a list of repository names")

        links = resource.get("links", [])
        if not isinstance(links, list):
            error(where, "links must be a list")
            continue
        if not links:
            warning(where, "has no links; the card will only show its description")
        seen_urls: set[str] = set()
        for link_index, link in enumerate(links):
            link_where = f"{where} links[{link_index}]"
            if not isinstance(link, dict):
                error(link_where, "must be an object with 'type' and 'url'")
                continue
            extra = set(link) - LINK_KEYS
            if extra:
                warning(link_where, f"unknown field(s): {', '.join(sorted(extra))}")
            if link.get("type") not in LINK_TYPES:
                error(link_where, f"type must be one of: {', '.join(LINK_TYPES)}")
            url = link.get("url")
            if not nonempty_str(url):
                error(link_where, "url is required")
                continue
            parts = urllib.parse.urlsplit(url)
            if parts.scheme != "https" or not parts.netloc:
                if parts.scheme == "http" and parts.netloc:
                    warning(link_where, "uses http://; prefer https:// when the site supports it")
                else:
                    error(link_where, "url must be an absolute https:// address")
            if any(ch.isspace() for ch in url):
                error(link_where, "url must not contain spaces")
            if url in seen_urls:
                warning(link_where, "duplicate url in this resource")
            seen_urls.add(url)
            if "label" in link and not nonempty_str(link["label"]):
                error(link_where, "label must be non-empty text when present")

    for cid in category_ids:
        if cid not in used_categories:
            warning(f"category '{cid}'", "has no resources and will not be shown")
    return issues


def validate_review(review: object) -> list[Issue]:
    issues: list[Issue] = []
    if not isinstance(review, dict):
        return [Issue("error", "repo-review", "the top level must be a JSON object")]
    if not is_date(review.get("lastReviewed")):
        issues.append(Issue("error", "repo-review lastReviewed", "must be a date in YYYY-MM-DD format"))
    repos = review.get("repos", {})
    if not isinstance(repos, dict):
        issues.append(Issue("error", "repo-review repos", "must be an object keyed by repository name"))
        return issues
    for name, entry in repos.items():
        where = f"repo-review '{name}'"
        if not isinstance(entry, dict):
            issues.append(Issue("error", where, "must be an object"))
            continue
        if entry.get("decision") not in REVIEW_DECISIONS:
            issues.append(Issue("error", where, f"decision must be one of: {', '.join(sorted(REVIEW_DECISIONS))}"))
        if not nonempty_str(entry.get("reason")):
            issues.append(Issue("error", where, "reason is required"))
        ignore = entry.get("ignore", [])
        if not isinstance(ignore, list) or not set(ignore) <= REVIEW_IGNORE:
            issues.append(Issue("error", where, f"ignore must be a list containing only: {', '.join(sorted(REVIEW_IGNORE))}"))
    return issues


# --------------------------------------------------------------------------------------------
# GitHub API
# --------------------------------------------------------------------------------------------

class ApiUnavailable(Exception):
    """The GitHub API could not be used (network blocked, rate limited, or unexpected error)."""


class GitHub:
    def __init__(self, token: str | None, timeout: float) -> None:
        self.token = token
        self.timeout = timeout
        self.calls = 0
        self._repo_cache: dict[str, tuple[int, object]] = {}
        self._release_cache: dict[str, tuple[int, object]] = {}

    def get(self, path: str, accept: str = "application/vnd.github+json"):
        url = path if path.startswith("https://") else API_ROOT + path
        headers = {"Accept": accept, "User-Agent": USER_AGENT, "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers)
        self.calls += 1
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, response.headers, self._decode(response.read(), accept)
        except urllib.error.HTTPError as exc:
            body = exc.read()
            if exc.code in (403, 429) and exc.headers.get("X-RateLimit-Remaining") == "0":
                reset = exc.headers.get("X-RateLimit-Reset")
                when = (dt.datetime.fromtimestamp(int(reset), dt.timezone.utc).strftime("%H:%M UTC")
                        if reset and reset.isdigit() else "later")
                raise ApiUnavailable(f"GitHub API rate limit reached (resets at {when}); "
                                     "set GITHUB_TOKEN to raise the limit") from None
            return exc.code, exc.headers, self._decode(body, accept)
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            reason = getattr(exc, "reason", exc)
            raise ApiUnavailable(f"cannot reach the GitHub API ({reason})") from None

    @staticmethod
    def _decode(body: bytes, accept: str) -> object:
        text = body.decode("utf-8", errors="replace")
        if "json" in accept:
            try:
                return json.loads(text) if text else None
            except json.JSONDecodeError:
                return None
        return text

    def paginate(self, path: str) -> list:
        items: list = []
        url: str | None = path
        while url:
            status, headers, data = self.get(url)
            if status != 200 or not isinstance(data, list):
                raise ApiUnavailable(f"GET {url} returned HTTP {status}")
            items.extend(data)
            url = None
            for part in (headers.get("Link") or "").split(","):
                match = re.search(r'<([^>]+)>;\s*rel="next"', part)
                if match:
                    url = match.group(1)
        return items

    def repo(self, owner: str, name: str) -> tuple[int, object]:
        key = f"{owner}/{name}".lower()
        if key not in self._repo_cache:
            status, _, data = self.get(f"/repos/{owner}/{name}")
            self._repo_cache[key] = (status, data)
        return self._repo_cache[key]

    def release(self, owner: str, name: str, which: str) -> tuple[int, object]:
        """``which`` is 'latest' or a tag name."""
        key = f"{owner}/{name}@{which}".lower()
        if key not in self._release_cache:
            if which == "latest":
                path = f"/repos/{owner}/{name}/releases/latest"
            else:
                path = f"/repos/{owner}/{name}/releases/tags/{urllib.parse.quote(which, safe='')}"
            status, _, data = self.get(path)
            self._release_cache[key] = (status, data)
        return self._release_cache[key]


def fetch_org_repos(gh: GitHub, org: str) -> list[dict]:
    repos = gh.paginate(f"/orgs/{org}/repos?type=public&per_page=100&sort=full_name")
    result = []
    for repo in repos:
        if repo.get("private"):
            continue
        result.append({
            "name": repo["name"],
            "url": repo["html_url"],
            "description": repo.get("description") or "",
            "homepage": (repo.get("homepage") or "").strip(),
            "topics": repo.get("topics") or [],
            "archived": bool(repo.get("archived")),
            "fork": bool(repo.get("fork")),
            "has_pages": bool(repo.get("has_pages")),
            "pages_url": pages_url(org, repo["name"]) if repo.get("has_pages") else "",
            "default_branch": repo.get("default_branch") or "",
            "pushed_at": repo.get("pushed_at") or "",
            "empty": repo.get("size", 0) == 0,
            "latest_release": None,
        })
    for repo in result:
        if repo["empty"]:
            continue
        status, _, data = gh.get(f"/repos/{org}/{repo['name']}/releases?per_page=1")
        if status == 200 and isinstance(data, list) and data:
            release = data[0]
            repo["latest_release"] = {
                "tag": release.get("tag_name"),
                "published_at": release.get("published_at") or release.get("created_at"),
                "prerelease": bool(release.get("prerelease")),
                "url": release.get("html_url"),
            }
    return result


def readme_links(gh: GitHub, org: str, repo: str) -> list[str]:
    """Candidate links from a README. Only allowlisted hosts; query strings and fragments removed."""
    status, _, text = gh.get(f"/repos/{org}/{repo}/readme", accept="application/vnd.github.raw+json")
    if status != 200 or not isinstance(text, str):
        return []
    found: list[str] = []
    for raw in re.findall(r"https?://[^\s<>\"')\]]+", text):
        parts = urllib.parse.urlsplit(raw.rstrip(".,;:"))
        host = (parts.hostname or "").lower()
        if not any(host == allowed or host.endswith("." + allowed) for allowed in README_LINK_HOSTS):
            continue
        clean = urllib.parse.urlunsplit(("https", parts.netloc, parts.path, "", ""))
        if clean not in found:
            found.append(clean)
    return found[:15]


# --------------------------------------------------------------------------------------------
# Comparing the organization with the catalog
# --------------------------------------------------------------------------------------------

def catalog_repo_refs(catalog: dict, org: str) -> dict[str, set[str]]:
    """Map lower-case org repository names to the ids of resources that reference them."""
    org_lower = org.lower()
    pages_host = f"{org_lower}.github.io"
    refs: dict[str, set[str]] = defaultdict(set)
    for resource in catalog.get("resources", []):
        rid = resource.get("id", "?")
        for name in resource.get("repos", []) or []:
            refs[name.lower()].add(rid)
        for link in resource.get("links", []) or []:
            parts = urllib.parse.urlsplit(link.get("url", ""))
            host = (parts.hostname or "").lower()
            segments = [segment for segment in parts.path.split("/") if segment]
            if host == "github.com" and len(segments) >= 2 and segments[0].lower() == org_lower:
                refs[segments[1].lower().removesuffix(".git")].add(rid)
            elif host == pages_host:
                refs[segments[0].lower() if segments else pages_host].add(rid)
    return refs


def compare(org: str, org_repos: list[dict], catalog: dict, review: dict, inventory_text: str | None,
            gh: GitHub, scan_readmes: bool = True) -> dict:
    refs = catalog_repo_refs(catalog, org)
    reviewed = {name.lower(): entry for name, entry in (review.get("repos") or {}).items()}
    last_reviewed = review.get("lastReviewed")
    by_name = {repo["name"].lower(): repo for repo in org_repos}
    resources = {res.get("id"): res for res in catalog.get("resources", [])}
    out: dict = {"new": [], "pending": [], "changes": [], "problems": []}

    for repo in org_repos:
        key = repo["name"].lower()
        users = sorted(refs.get(key, set()))
        decision = (reviewed.get(key) or {}).get("decision")
        repo["listed_in"] = users
        repo["state"] = "listed" if users else (decision or "new")
        if not users and decision is None:
            entry = {"name": repo["name"], "url": repo["url"], "description": repo["description"],
                     "homepage": repo["homepage"], "pages_url": repo["pages_url"],
                     "latest_release": repo["latest_release"], "archived": repo["archived"],
                     "readme_links": readme_links(gh, org, repo["name"]) if scan_readmes else []}
            out["new"].append(entry)
            continue
        if not users and decision == "included":
            out["problems"].append(("warning", repo["name"], "marked 'included' in repo-review.json "
                                    "but no resource in the catalog references it"))
        if repo["state"] == "pending":
            out["pending"].append({"name": repo["name"], "url": repo["url"],
                                   "reason": reviewed[key].get("reason", "")})
        if users and decision in ("excluded", "pending"):
            out["problems"].append(("warning", repo["name"], f"marked '{decision}' in repo-review.json "
                                    "but referenced by the catalog"))

        notes: list[str] = []
        if after_date(repo["pushed_at"], last_reviewed):
            notes.append(f"new commits since review (last push {repo['pushed_at'][:10]})")
        release = repo["latest_release"]
        if release and after_date(release["published_at"], last_reviewed):
            kind = "pre-release" if release["prerelease"] else "release"
            notes.append(f"new {kind} {release['tag']} ({(release['published_at'] or '')[:10]})")
        if users:
            link_urls = [link["url"] for rid in users for link in (resources.get(rid, {}).get("links") or [])]
            normalized = [norm_url(url) for url in link_urls]
            if repo["archived"]:
                out["problems"].append(("warning", repo["name"], "repository is archived but listed by "
                                        + ", ".join(users)))
            ignore = set((reviewed.get(key) or {}).get("ignore", []))
            if repo["homepage"] and "homepage" not in ignore and norm_url(repo["homepage"]) not in normalized:
                notes.append(f"GitHub homepage {repo['homepage']} is not linked from the catalog")
            if (repo["pages_url"] and "pages" not in ignore
                    and not any(url.startswith(norm_url(repo["pages_url"])) for url in normalized)):
                notes.append(f"has a GitHub Pages site ({repo['pages_url']}) that the catalog does not link")
        if notes:
            out["changes"].append({"name": repo["name"], "state": repo["state"], "notes": notes})

    for name, users in sorted(refs.items()):
        if name not in by_name:
            out["problems"].append(("error", name, "referenced by " + ", ".join(sorted(users))
                                    + " but not a public repository in the organization "
                                      "(renamed, deleted or private?)"))
    for name in sorted(reviewed):
        if name not in by_name:
            out["problems"].append(("warning", name, "listed in repo-review.json but not a public "
                                    "repository in the organization"))
    if inventory_text is not None:
        lowered = inventory_text.lower()
        for repo in org_repos:
            if repo["name"].lower() not in lowered:
                out["problems"].append(("warning", repo["name"], "not mentioned in docs/RESOURCE_INVENTORY.md"))
    return out


# --------------------------------------------------------------------------------------------
# Link checking
# --------------------------------------------------------------------------------------------

@dataclass
class LinkResult:
    url: str
    used_by: list[str] = field(default_factory=list)
    status: str = "unchecked"  # ok | redirected | unverified | broken
    code: int | None = None
    final_url: str | None = None
    detail: str = ""
    method: str = "http"

    def set(self, status: str, detail: str = "", code: int | None = None, final_url: str | None = None) -> None:
        self.status = status
        self.detail = detail
        if code is not None:
            self.code = code
        if final_url is not None:
            self.final_url = final_url


class PageScanner(html.parser.HTMLParser):
    """Pull the title, meta refresh target and canonical URL from the start of an HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.refresh = ""
        self.canonical = ""
        self._in_title = False
        self._title_done = False  # only the page's own <title>, not <title> elements inside SVG icons

    def handle_starttag(self, tag, attrs):
        attributes = {key.lower(): (value or "") for key, value in attrs}
        if tag == "title" and not self._title_done:
            self._in_title = True
        elif tag == "meta" and attributes.get("http-equiv", "").lower() == "refresh":
            match = re.search(r"url\s*=\s*['\"]?([^'\";]+)", attributes.get("content", ""), re.I)
            if match:
                self.refresh = match.group(1).strip()
        elif tag == "link" and "canonical" in attributes.get("rel", "").lower().split():
            self.canonical = attributes.get("href", "").strip()

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
            self._title_done = True

    def handle_data(self, data):
        if self._in_title and len(self.title) < 300:
            self.title += data


def retry_after_seconds(headers, default: float = 5.0) -> float:
    value = (headers.get("Retry-After") if headers else None) or ""
    return min(float(value), 30.0) if value.strip().isdigit() else default


def http_fetch(url: str, timeout: float, accept: str = "text/html,application/xhtml+xml,*/*;q=0.8"):
    """GET a URL (following redirects). Returns (status, final_url, headers, first 64 KB of HTML)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept,
                                                   "Accept-Language": "en-US,en;q=0.8"})
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    with opener.open(request, timeout=timeout) as response:
        content_type = response.headers.get_content_type()
        wants_body = content_type in ("text/html", "application/xhtml+xml", "application/json")
        body = response.read(65536) if wants_body else b""
        return response.status, response.geturl(), response.headers, body


def check_http(result: LinkResult, timeout: float, follow_stub: bool = True) -> None:
    result.method = "http"
    for attempt in (1, 2):
        try:
            status, final_url, _headers, body = http_fetch(result.url, timeout)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 502, 503, 504) and attempt == 1:
                time.sleep(retry_after_seconds(exc.headers))
                continue
            if exc.code in (404, 410):
                result.set("broken", f"HTTP {exc.code}", exc.code, exc.geturl())
            elif exc.code in (401, 403, 407):
                result.set("unverified", f"HTTP {exc.code} (access denied to automated check)", exc.code)
            else:
                result.set("unverified", f"HTTP {exc.code}", exc.code)
            return
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.gaierror):
                result.set("broken", "DNS lookup failed")
            elif isinstance(reason, ssl.SSLCertVerificationError):
                result.set("broken", "TLS certificate could not be verified")
            elif isinstance(reason, ConnectionRefusedError):
                result.set("broken", "connection refused")
            elif isinstance(reason, (TimeoutError, socket.timeout)):
                if attempt == 1:
                    continue
                result.set("unverified", "timed out")
            elif "tunnel connection failed" in str(reason).lower():
                result.set("unverified", "blocked by the network proxy of this environment")
            else:
                result.set("unverified", f"connection error ({reason})")
            return
        except (TimeoutError, socket.timeout):
            if attempt == 1:
                continue
            result.set("unverified", "timed out")
            return
        except (ConnectionError, http.client.HTTPException, OSError) as exc:
            if attempt == 1:
                time.sleep(2)
                continue
            result.set("unverified", f"connection error ({exc.__class__.__name__})")
            return

        result.code = status
        scanner = PageScanner()
        if body:
            try:
                scanner.feed(body.decode("utf-8", errors="replace"))
            except Exception:  # noqa: BLE001 - a malformed page must not stop the run
                pass
        notes: list[str] = []
        final_lower = final_url.lower()
        if norm_url(final_url) != norm_url(result.url):
            result.final_url = final_url
            if any(hint in urllib.parse.urlsplit(final_lower).netloc + urllib.parse.urlsplit(final_lower).path
                   for hint in SIGN_IN_HINTS):
                result.set("unverified", f"redirects to what looks like a sign-in page: {final_url}")
                return
        title = " ".join(scanner.title.split())
        final_path = urllib.parse.urlsplit(final_lower).path
        if any(hint in title.lower() for hint in BOT_WALL_TITLES) or "verify" in final_path:
            result.set("unverified", f"bot-protection page ('{title[:60]}'); check in a browser")
            return
        if result.final_url and re.search(r"(^|/)(error|errors|notfound|not-found|404)([./_-]|$)", final_path):
            result.set("broken", f"redirects to an error page: {final_url}")
            return
        if re.search(r"\b(404|page not found|not found|an error has occurred|server error)\b", title, re.I):
            result.set("unverified", f"HTTP {status} but the page title is '{title[:80]}'")
            return
        if re.search(rb"<input[^>]+type=[\"']?password", body, re.I):
            result.set("unverified", f"page asks for a password (sign-in required?); title '{title[:60]}'")
            return
        host = (urllib.parse.urlsplit(result.url).hostname or "").lower()
        if host.endswith("r-project.org") and b"removed from the CRAN repository" in body:
            result.set("broken", "CRAN reports that the package was removed from the repository")
            return
        if title:
            notes.append(f"title '{title[:90]}'")
        if scanner.refresh:
            target = urllib.parse.urljoin(final_url, scanner.refresh)
            notes.append(f"redirect page -> {target}")
            if follow_stub and target.startswith(("http://", "https://")) and norm_url(target) != norm_url(final_url):
                probe = LinkResult(target)
                check_http(probe, timeout, follow_stub=False)
                notes.append(f"target: {probe.status}" + (f" ({probe.detail})" if probe.detail else ""))
                if probe.status == "broken":
                    result.set("broken", "redirect page points to a broken target; " + "; ".join(notes), status)
                    return
        # Redirects within the same host (canonical paths, trailing slashes) are routine.
        same_host = (urllib.parse.urlsplit(final_lower).hostname
                     == (urllib.parse.urlsplit(result.url).hostname or "").lower())
        if result.final_url and same_host:
            notes.append(f"redirects to {final_url}")
        status_name = "redirected" if result.final_url and not same_host else "ok"
        result.set(status_name, "; ".join(notes), status)
        return


def check_handle(result: LinkResult, ident: str, kind: str, timeout: float) -> None:
    """Verify a DOI or Handle through the registry API instead of the publisher's website."""
    base = "https://doi.org" if kind == "DOI" else "https://hdl.handle.net"
    result.method = kind.lower()
    api = f"{base}/api/handles/{urllib.parse.quote(ident, safe='/')}"
    try:
        status, _, _, body = http_fetch(api, timeout, accept="application/json")
        data = json.loads(body.decode("utf-8", errors="replace") or "{}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            result.set("broken", f"{kind} is not registered", 404)
        else:
            result.set("unverified", f"{kind} registry returned HTTP {exc.code}", exc.code)
        return
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as exc:
        result.set("unverified", f"{kind} registry could not be reached ({getattr(exc, 'reason', exc)})")
        return
    if data.get("responseCode") == 1:
        target = next((value.get("data", {}).get("value") for value in data.get("values", [])
                       if value.get("type") == "URL"), None)
        result.set("ok", f"{kind} registered" + (f"; resolves to {target}" if target else ""), status)
    else:
        result.set("broken", f"{kind} is not registered (responseCode {data.get('responseCode')})", status)


def check_github(result: LinkResult, gh: GitHub) -> bool:
    """Check a github.com URL through the API. Returns False if the URL should use plain HTTP."""
    match = re.match(r"^https://github\.com/([^/]+)/([^/?#]+)/?([^?#]*)", result.url, re.I)
    if not match:
        return False
    owner, name = match.group(1), match.group(2).removesuffix(".git")
    parts = [urllib.parse.unquote(part) for part in match.group(3).split("/") if part]
    result.method = "github-api"
    status, repo = gh.repo(owner, name)
    if status == 404:
        result.set("broken", "repository not found (deleted, renamed or private)", 404)
        return True
    if status != 200 or not isinstance(repo, dict):
        result.set("unverified", f"GitHub API returned HTTP {status}", status)
        return True
    if repo.get("private"):
        result.set("broken", "repository is private", status)
        return True
    detail = ["archived repository"] if repo.get("archived") else []
    canonical = f"https://github.com/{repo.get('full_name', owner + '/' + name)}"
    if canonical.lower() != f"https://github.com/{owner}/{name}".lower():
        result.final_url = canonical + ("/" + "/".join(parts) if parts else "")
        detail.append(f"repository moved to {canonical}")

    def finish(ok: bool, message: str) -> bool:
        if message:
            detail.append(message)
        if ok:
            result.set("redirected" if result.final_url else "ok", "; ".join(detail), 200)
        else:
            result.set("broken", "; ".join(detail), 404)
        return True

    if not parts:
        return finish(True, "")
    if parts[0] == "releases":
        rest = parts[1:]
        if rest == ["latest"]:
            code, release = gh.release(owner, name, "latest")
            return finish(code == 200, f"latest release {release.get('tag_name')}" if code == 200 and isinstance(release, dict)
                          else "no published (non-pre-release) release")
        if len(rest) >= 3 and rest[0] == "latest" and rest[1] == "download":
            asset = "/".join(rest[2:])
            code, release = gh.release(owner, name, "latest")
            names = [a.get("name") for a in (release or {}).get("assets", [])] if code == 200 and isinstance(release, dict) else []
            return finish(asset in names, f"asset '{asset}' " + ("found" if asset in names else "not found")
                          + " in the latest release")
        if len(rest) >= 2 and rest[0] == "tag":
            tag = "/".join(rest[1:])
            code, _ = gh.release(owner, name, tag)
            return finish(code == 200, f"release '{tag}' " + ("found" if code == 200 else "not found"))
        if len(rest) >= 3 and rest[0] == "download":
            tag, asset = rest[1], "/".join(rest[2:])
            code, release = gh.release(owner, name, tag)
            names = [a.get("name") for a in (release or {}).get("assets", [])] if code == 200 and isinstance(release, dict) else []
            return finish(asset in names, f"asset '{asset}' " + ("found" if asset in names else "not found")
                          + f" in release '{tag}'")
        if not rest:
            return finish(True, "")
        return False
    if parts[0] == "issues":
        return finish(bool(repo.get("has_issues")), "" if repo.get("has_issues") else "issues are disabled")
    if parts[0] in ("blob", "tree", "raw") and len(parts) >= 3:
        ref, path = parts[1], "/".join(parts[2:])
        code, _, _ = gh.get(f"/repos/{owner}/{name}/contents/{urllib.parse.quote(path)}?ref={urllib.parse.quote(ref)}")
        return finish(code == 200, f"'{path}' " + ("found" if code == 200 else "not found") + f" on {ref}")
    return False


def check_link(result: LinkResult, gh: GitHub | None, timeout: float) -> None:
    url = result.url
    doi = re.match(r"^https?://(?:dx\.)?doi\.org/(10\.\d{4,9}/\S+)$", url, re.I)
    handle = re.match(r"^https?://hdl\.handle\.net/(\d[\w.]*/\S+)$", url, re.I)
    try:
        if doi:
            check_handle(result, urllib.parse.unquote(doi.group(1)), "DOI", timeout)
        elif handle:
            check_handle(result, urllib.parse.unquote(handle.group(1)), "Handle", timeout)
        elif gh is not None and url.lower().startswith("https://github.com/") and check_github(result, gh):
            pass
        else:
            check_http(result, timeout)
    except ApiUnavailable as exc:
        result.set("unverified", str(exc))
    except Exception as exc:  # noqa: BLE001 - one bad URL must not abort the whole report
        result.set("unverified", f"checker error: {exc.__class__.__name__}: {exc}")


def collect_links(catalog: dict, site_files: list[Path]) -> dict[str, LinkResult]:
    links: dict[str, LinkResult] = {}
    for resource in catalog.get("resources", []):
        for link in resource.get("links", []) or []:
            url = link.get("url")
            if isinstance(url, str) and url.startswith(("http://", "https://")):
                links.setdefault(url, LinkResult(url)).used_by.append(resource.get("id", "?"))
    for path in site_files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for url in re.findall(r'href="(https?://[^"]+)"', text):
            entry = links.setdefault(url, LinkResult(url))
            if path.name not in entry.used_by:
                entry.used_by.append(path.name)
    return links


def run_link_checks(links: dict[str, LinkResult], gh: GitHub | None, timeout: float, workers: int = 8) -> None:
    """Check hosts in parallel, but URLs on the same host one at a time to be polite."""
    by_host: dict[str, list[LinkResult]] = defaultdict(list)
    for result in links.values():
        by_host[(urllib.parse.urlsplit(result.url).hostname or "").lower()].append(result)

    def check_host(results: list[LinkResult]) -> None:
        for position, result in enumerate(results):
            if position and result.method == "http" and not result.url.startswith("https://github.com/"):
                time.sleep(0.5)
            check_link(result, gh, timeout)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(check_host, by_host.values()))


# --------------------------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------------------------

def render_markdown(ctx: dict) -> str:
    lines: list[str] = []
    add = lines.append
    catalog = ctx["catalog"]
    issues: list[Issue] = ctx["issues"]
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    resources = catalog.get("resources", []) if isinstance(catalog, dict) else []
    categories = catalog.get("categories", []) if isinstance(catalog, dict) else []

    add("# WRISES resource discovery report")
    add("")
    add(f"Generated {ctx['generated']} for the `{ctx['org']}` organization. "
        f"Catalog: {len(resources)} resources in {len(categories)} categories "
        f"(updated {catalog.get('updated', '?') if isinstance(catalog, dict) else '?'}). "
        f"Last repository review: {ctx['review'].get('lastReviewed', '?')}.")
    add("")
    add("| Check | Result |")
    add("|---|---|")
    add(f"| Catalog validation | {len(errors)} error(s), {len(warnings)} warning(s) |")
    if ctx["api_error"]:
        add(f"| Organization repositories | not checked: {md_cell(ctx['api_error'])} |")
    elif ctx["org_repos"] is not None:
        repos = ctx["org_repos"]
        listed = sum(1 for r in repos if r.get("state") == "listed")
        excluded = sum(1 for r in repos if r.get("state") == "excluded")
        pending = sum(1 for r in repos if r.get("state") == "pending")
        add(f"| Organization repositories | {len(repos)} public: {listed} listed, {excluded} excluded, "
            f"{pending} pending, {len(ctx['comparison']['new'])} new |")
        add(f"| Changes since last review | {len(ctx['comparison']['changes'])} repositories |")
        add(f"| Problems | {len(ctx['comparison']['problems'])} |")
    if ctx["links"] is None:
        add("| Links | not checked (--skip-links) |")
    else:
        counts = defaultdict(int)
        for result in ctx["links"].values():
            counts[result.status] += 1
        add(f"| Links | {len(ctx['links'])} checked: {counts['ok']} ok, {counts['redirected']} redirected, "
            f"{counts['unverified']} unverified, {counts['broken']} broken |")
    add(f"| GitHub API | {'authenticated' if ctx['authenticated'] else 'unauthenticated'}, "
        f"{ctx['api_calls']} request(s) |")
    add("")

    if issues:
        add("## Catalog validation")
        add("")
        for issue in issues:
            add(f"- **{issue.level}** {issue.where}: {issue.message}")
        add("")

    comparison = ctx["comparison"]
    if comparison:
        add("## New repositories (not in the catalog and not reviewed)")
        add("")
        if comparison["new"]:
            add("Review each one, then either add a resource to `data/resources.json` or record a decision "
                "in `data/repo-review.json`.")
            add("")
            add("| Repository | Description | Homepage / Pages | Latest release | Links found in README |")
            add("|---|---|---|---|---|")
            for repo in comparison["new"]:
                release = repo["latest_release"]
                release_text = f"{release['tag']} ({(release['published_at'] or '')[:10]})" if release else ""
                sites = " ".join(filter(None, [repo["homepage"], repo["pages_url"]]))
                add(f"| [{md_cell(repo['name'])}]({repo['url']}){' (archived)' if repo['archived'] else ''} "
                    f"| {md_cell(repo['description'])} | {md_cell(sites)} | {md_cell(release_text)} "
                    f"| {md_cell(' '.join(repo['readme_links']))} |")
        else:
            add("None.")
        add("")
        if comparison["pending"]:
            add("## Pending review")
            add("")
            for repo in comparison["pending"]:
                add(f"- [{repo['name']}]({repo['url']}): {repo['reason']}")
            add("")
        add(f"## Changes since the last review ({ctx['review'].get('lastReviewed', '?')})")
        add("")
        if comparison["changes"]:
            for change in comparison["changes"]:
                add(f"- **{change['name']}** ({change['state']}): " + "; ".join(change["notes"]))
        else:
            add("None.")
        add("")
        if comparison["problems"]:
            add("## Problems")
            add("")
            for level, name, message in comparison["problems"]:
                add(f"- **{level}** {name}: {message}")
            add("")

    if ctx["links"] is not None:
        add("## Link check")
        add("")
        order = ("broken", "unverified", "redirected", "ok")
        grouped = {status: [r for r in ctx["links"].values() if r.status == status] for status in order}
        for status in order:
            results = sorted(grouped[status], key=lambda r: r.url)
            if not results:
                continue
            title = {"broken": "Broken", "unverified": "Could not be verified automatically",
                     "redirected": "Redirected", "ok": "OK"}[status]
            if status == "ok":
                add(f"<details><summary>{title} ({len(results)})</summary>")
                add("")
            else:
                add(f"### {title} ({len(results)})")
                add("")
            add("| URL | Used by | Result |")
            add("|---|---|---|")
            for result in results:
                outcome = result.detail or (f"HTTP {result.code}" if result.code else "")
                if result.final_url and result.final_url not in outcome:
                    outcome = (outcome + "; " if outcome else "") + f"final URL {result.final_url}"
                add(f"| {md_cell(result.url)} | {md_cell(', '.join(result.used_by))} | {md_cell(outcome)} |")
            add("")
            if status == "ok":
                add("</details>")
                add("")

    if ctx["org_repos"]:
        add("## Organization repositories")
        add("")
        add("| Repository | State | Archived | Pages | Homepage | Latest release | Last push | Description |")
        add("|---|---|---|---|---|---|---|---|")
        for repo in sorted(ctx["org_repos"], key=lambda r: r["name"].lower()):
            release = repo["latest_release"]
            release_text = (f"{release['tag']}{' (pre)' if release['prerelease'] else ''} "
                            f"{(release['published_at'] or '')[:10]}") if release else ""
            state = repo.get("state", "")
            if repo.get("listed_in"):
                state += ": " + ", ".join(repo["listed_in"])
            add(f"| [{md_cell(repo['name'])}]({repo['url']}) | {md_cell(state)} | {'yes' if repo['archived'] else ''} "
                f"| {'yes' if repo['has_pages'] else ''} | {md_cell(repo['homepage'])} | {md_cell(release_text)} "
                f"| {repo['pushed_at'][:10]} | {md_cell(repo['description'])} |")
        add("")
    return "\n".join(lines)


def build_json(ctx: dict) -> dict:
    return {
        "generated": ctx["generated"],
        "org": ctx["org"],
        "authenticated": ctx["authenticated"],
        "apiError": ctx["api_error"],
        "validation": [asdict(issue) for issue in ctx["issues"]],
        "repositories": ctx["org_repos"],
        "new": ctx["comparison"]["new"] if ctx["comparison"] else None,
        "pending": ctx["comparison"]["pending"] if ctx["comparison"] else None,
        "changes": ctx["comparison"]["changes"] if ctx["comparison"] else None,
        "problems": [{"level": l, "name": n, "message": m} for l, n, m in ctx["comparison"]["problems"]]
        if ctx["comparison"] else None,
        "links": [asdict(result) for result in sorted(ctx["links"].values(), key=lambda r: r.url)]
        if ctx["links"] is not None else None,
    }


# --------------------------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------------------------

def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--org", default=DEFAULT_ORG, help="GitHub organization (default: %(default)s)")
    parser.add_argument("--catalog", default=str(ROOT / "data" / "resources.json"), help="catalog JSON file")
    parser.add_argument("--review", default=str(ROOT / "data" / "repo-review.json"), help="review JSON file")
    parser.add_argument("--inventory", default=str(ROOT / "docs" / "RESOURCE_INVENTORY.md"),
                        help="inventory document that should mention every repository")
    parser.add_argument("--validate-only", action="store_true", help="only validate the JSON files (offline)")
    parser.add_argument("--skip-links", action="store_true", help="do not check links")
    parser.add_argument("--fail-on-broken", action="store_true", help="exit 2 if any link is broken")
    parser.add_argument("--fail-on-new", action="store_true", help="exit 2 if there are unreviewed repositories")
    parser.add_argument("--output", default=str(ROOT / "reports" / "discovery-report.md"),
                        help="Markdown report path (default: %(default)s)")
    parser.add_argument("--json", dest="json_path", help="also write the results as JSON to this path")
    parser.add_argument("--print-json", action="store_true",
                        help="print the JSON results between marker lines (for CI logs)")
    parser.add_argument("--quiet", action="store_true", help="do not print the Markdown report")
    parser.add_argument("--timeout", type=float, default=30.0, help="per-request timeout in seconds")
    parser.add_argument("--extra-url", action="append", default=[], metavar="URL",
                        help="also check this URL (repeatable), e.g. a link you plan to add")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args(argv)

    issues: list[Issue] = []
    catalog: object = {}
    review: dict = {"lastReviewed": None, "repos": {}}
    try:
        catalog = load_json(Path(args.catalog))
        issues += validate_catalog(catalog)
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(Issue("error", args.catalog, f"cannot read catalog: {exc}"))
    try:
        loaded = load_json(Path(args.review))
        issues += validate_review(loaded)
        if isinstance(loaded, dict):
            review = loaded
    except FileNotFoundError:
        issues.append(Issue("warning", args.review, "review file not found; every uncatalogued repository "
                                                    "will be reported as new"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(Issue("error", args.review, f"cannot read review file: {exc}"))
    errors = [issue for issue in issues if issue.level == "error"]

    if args.validate_only:
        for issue in issues:
            print(issue.line())
        resources = catalog.get("resources", []) if isinstance(catalog, dict) else []
        print(f"{len(errors)} error(s), {len(issues) - len(errors)} warning(s) in "
              f"{len(resources)} resource(s).")
        return 1 if errors else 0

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None
    gh = GitHub(token, args.timeout)
    ctx: dict = {
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "org": args.org, "catalog": catalog if isinstance(catalog, dict) else {}, "review": review,
        "issues": issues, "api_error": None, "org_repos": None, "comparison": None, "links": None,
        "authenticated": bool(token), "api_calls": 0,
    }

    if isinstance(catalog, dict) and not errors:
        try:
            org_repos = fetch_org_repos(gh, args.org)
            inventory_path = Path(args.inventory)
            inventory_text = inventory_path.read_text(encoding="utf-8") if inventory_path.exists() else None
            ctx["comparison"] = compare(args.org, org_repos, catalog, review, inventory_text, gh)
            ctx["org_repos"] = org_repos
        except ApiUnavailable as exc:
            ctx["api_error"] = str(exc)

        if not args.skip_links:
            links = collect_links(catalog, [ROOT / "index.html", ROOT / "404.html"])
            for url in args.extra_url:
                links.setdefault(url, LinkResult(url)).used_by.append("--extra-url")
            # Without a token, API-based checks of github.com links would exhaust the rate limit.
            use_api = gh if (token and not ctx["api_error"]) else None
            run_link_checks(links, use_api, args.timeout)
            ctx["links"] = links
    ctx["api_calls"] = gh.calls

    report = render_markdown(ctx)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report + "\n", encoding="utf-8")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(report[:900_000] + "\n")
    data = build_json(ctx)
    if args.json_path:
        Path(args.json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not args.quiet:
        print(report)
    if args.print_json:
        print("=== BEGIN DISCOVERY JSON ===")
        print(json.dumps(data, indent=1))
        print("=== END DISCOVERY JSON ===")
    # Status messages go to stdout too: CI logs merge stdout and stderr in arrival order, which
    # could split the JSON block.
    print(f"Report written to {output}", flush=True)

    if errors:
        return 1
    if ctx["api_error"]:
        print(f"GitHub API unavailable: {ctx['api_error']}", flush=True)
        return 3
    broken = [r for r in (ctx["links"] or {}).values() if r.status == "broken"]
    problems = [p for p in ctx["comparison"]["problems"] if p[0] == "error"] if ctx["comparison"] else []
    if args.fail_on_broken and (broken or problems):
        return 2
    if args.fail_on_new and ctx["comparison"] and ctx["comparison"]["new"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

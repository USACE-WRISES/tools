# WRISES Tools & Resources

A directory of tools, applications, data and technical resources from the USACE-WRISES team,
published with GitHub Pages at **https://usace-wrises.github.io/tools/**.

The site is plain HTML, CSS and JavaScript. Every card on the page comes from one file,
[`data/resources.json`](data/resources.json). Adding or editing a resource never requires changing
the page layout or the JavaScript. Resources stay in their own repositories and websites; this site
only links to them.

## What's in this repository

| Path | Purpose |
|---|---|
| `index.html`, `404.html` | The page and the "not found" page |
| `css/styles.css` | All styling (colors and spacing are defined once at the top) |
| `js/app.js` | Loads the catalog and renders search, filters and cards |
| `data/resources.json` | **The catalog**: every resource shown on the site |
| `data/repo-review.json` | Decisions for organization repositories that are not listed (not published) |
| `fonts/` | Public Sans (self-hosted; SIL Open Font License, see `fonts/OFL.txt`) |
| `scripts/discover_resources.py` | Validates the catalog, finds new repositories and checks links |
| `docs/RESOURCE_INVENTORY.md` | Inventory of every repository reviewed, with verification notes |
| `.github/workflows/deploy.yml` | Publishes the site when `main` changes |
| `.github/workflows/check-resources.yml` | Runs the discovery script and link check (weekly and on changes) |

## Add a resource

1. Add an entry to the `resources` list in `data/resources.json`. Cards appear in the order they are
   listed, grouped by category. Copy an existing entry as a starting point:

   ```json
   {
     "id": "xs-calc",
     "name": "Cross-Section Calculator",
     "fullName": "1D Cross-Section Hydraulics Calculator",
     "description": "One or two sentences on what it does and who it is for.",
     "category": "hydrology-hydraulics",
     "type": "Web app",
     "tags": ["Manning's equation", "Cross-section"],
     "links": [
       { "type": "app", "url": "https://usace-wrises.github.io/xs-calc/" },
       { "type": "repository", "url": "https://github.com/USACE-WRISES/xs-calc" }
     ],
     "repos": ["xs-calc"]
   }
   ```

2. Check the file: `python scripts/discover_resources.py --validate-only`
3. Preview the page (see [Preview locally](#preview-locally)), then commit and open a pull request.
   The **Check resources** workflow validates the catalog and tests every link.

### Fields

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Unique, lowercase with hyphens (`terrain-to-stl`) |
| `name` | yes | Short name shown as the card title |
| `fullName` | no | Expansion of an acronym, shown under the name |
| `description` | yes | One or two sentences (under 280 characters), based on the resource's own documentation |
| `category` | yes | The `id` of an entry in `categories` |
| `type` | yes | Short label such as `Web app`, `Desktop app`, `R package`, `Python package`, `Dataset`, `Training`, `Report`, `Model report`, `Assessment method` |
| `tags` | no | Up to 8 keywords; the first 4 are shown, all are searchable |
| `featured` | no | `true` to also show the card in the Featured section |
| `status` | no | Only a status the resource itself documents: `Draft`, `Alpha`, `Beta`, `Preliminary`, `Experimental`, `Archived` |
| `note` | no | One short caveat from the resource's documentation (license pending, sign-in required, dated review status) |
| `links` | yes | List of `{ "type", "url", "label" }`; see below |
| `repos` | no | Names of USACE-WRISES repositories this entry covers (used by the discovery script only) |

### Link types

| `type` | Default label | Use for |
|---|---|---|
| `app` | Launch tool | A working web application (always shown first) |
| `download` | Download | Installers, releases, packages (CRAN), calculators |
| `documentation` | Documentation | User guides, technical reports, documentation websites |
| `dataset` | Dataset | Data downloads or data repositories |
| `repository` | Repository | Source code on GitHub |
| `publication` | Publication | Journal articles and conference papers (prefer `https://doi.org/...` links) |
| `reference` | More information | Webinars, related pages |

Add `"label"` to replace the default text, for example `"label": "Windows installer"`. When a
card's first link is one of the first five types, it is shown as the filled button. Only add links that work for the public:
no intranet or sign-in pages, no personal or tokenized links.

## Change a description, feature a resource or add a category

- **Description:** edit `description` (and `note` or `status` if they changed). Keep it accurate to
  the resource's own documentation. Do not describe a tool as certified, approved or production-ready
  unless its documentation says so.
- **Featured:** set `"featured": true` (or remove the field to unfeature). Keep the Featured section
  small; it currently shows four resources with releases or published packages, live applications or
  installers, and active maintenance.
- **Category:** add `{ "id", "name", "description" }` to `categories`. Categories appear in the order
  listed; a category with no resources is hidden automatically.
- Update `"updated"` at the top of the file; the page footer shows it.

## Preview locally

Clone the repository into a folder named `tools`, then serve its **parent** folder so the address
matches GitHub Pages (`/tools/`):

```powershell
git clone https://github.com/USACE-WRISES/tools.git D:\Code\Work\usace-wrises\tools
cd D:\Code\Work\usace-wrises
python -m http.server 8000
```

Open http://localhost:8000/tools/. (Opening `index.html` directly from disk does not work because
browsers block loading the JSON file from `file://` addresses.)

## Find new resources and check links

```bash
python scripts/discover_resources.py
```

The script never changes the catalog. It writes `reports/discovery-report.md` with:

- **New repositories:** public repositories in the organization that are neither in the catalog nor in
  `data/repo-review.json`, with their description, homepage, Pages site, latest release and candidate
  links from the README.
- **Changes since the last review:** repositories with new commits or releases since `lastReviewed`
  in `data/repo-review.json`, repositories that were archived, and homepages or Pages sites the
  catalog does not link.
- **Problems:** catalog entries that point to repositories that were renamed, deleted or made private.
- **Link check:** every link in the catalog and the page, grouped as broken, could not be verified
  automatically, redirected to another site, and OK. DOIs and handles are verified through their
  registries. Some sites block automated checks; check those in a browser.

To act on the report, add a resource for each new repository worth listing, or record a decision in
`data/repo-review.json` (`"excluded"` or `"pending"` with a reason), then set `lastReviewed` to
today's date. Use `"included"` with `"ignore": ["pages"]` or `["homepage"]` to silence a finding you
have reviewed. Update `docs/RESOURCE_INVENTORY.md` as well.

Useful options: `--validate-only` (offline check of the JSON files), `--skip-links`,
`--extra-url URL` (check a link before adding it), `--output PATH`. Without a token the GitHub API
allows 60 requests per hour, which is enough for one run; set `GITHUB_TOKEN` for more.

The **Check resources** workflow runs the same script on every change to `data/`, `scripts/` or the
pages, every Monday, and on demand (Actions tab → Check resources → Run workflow). It fails when a
link is broken or a new repository needs review. GitHub emails a failed scheduled run to the person
who last changed the workflow's schedule, and pauses scheduled workflows in repositories with no
activity for 60 days; re-enable it from the Actions tab if that happens.

## Deploy

1. **One-time setup (repository admin):** Settings → Pages → Build and deployment → Source:
   **GitHub Actions**.
2. Merge changes into `main`. The **Deploy to GitHub Pages** workflow validates the catalog, copies the
   site files into `_site/` and publishes them. Pull requests and other branches run the build only.

Notes:

- Only the files listed in the workflow's "Assemble the site" step are published. If you add a new
  folder or file that the page needs, add it there.
- `404.html` uses absolute `/tools/...` addresses because GitHub Pages serves it for missing pages at
  any depth. If the repository is renamed, update those addresses.
- GitHub Pages caches files for up to 10 minutes, so a change can take a few minutes to appear.
- No custom domain or redirects are used.

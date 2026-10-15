# Resource inventory

**Verified:** 2026-10-15 · **Organization:** [USACE-WRISES](https://github.com/USACE-WRISES) ·
**Public repositories examined:** 28 · **Directory entries:** 35 in 6 categories

This document records what was reviewed to build the directory, what is listed, and why some
repositories are not. The directory itself is driven by [`data/resources.json`](../data/resources.json);
decisions for repositories that are not listed live in [`data/repo-review.json`](../data/repo-review.json).
Re-run `python scripts/discover_resources.py` to compare this inventory with the organization today.

## How the review was done

- **Repositories:** all 28 public repositories in the organization. Each was examined through its README, file tree, Pages configuration (workflows, `docs/` folders,
  `gh-pages` branches, build configs), package metadata and release tags.
- **Earlier catalog:** every entry in the team's single-page catalog,
  [WRISES Models](https://usace-wrises.github.io/WRISES.Models/) (May 2025), was carried over. Entries
  without a GitHub repository use the catalog's text and links.
- **Link verification:** `scripts/discover_resources.py` ran in GitHub Actions
  ([Check resources](https://github.com/USACE-WRISES/tools/actions/workflows/check-resources.yml)) on
  2026-10-15. It requested every link from a GitHub-hosted runner, verified DOIs and handles through
  their registries, and verified GitHub links through the GitHub API (repository exists and is public,
  release or release asset exists, file exists, issues enabled). Redirect pages (for example the STAF
  short links) were followed to their targets. The environment used to build the site could not reach
  GitHub Pages or the GitHub API directly, so all live checks ran in GitHub Actions.
- **Only verified links are displayed.** Links that were broken, led to sign-in pages, or could not be
  confirmed are listed under [Links not displayed](#links-not-displayed).

## Summary

| | Count |
|---|---|
| Public repositories examined | 28 |
| Repositories linked from the directory | 22 |
| Repositories not listed | 6 |
| Directory entries backed by an organization repository | 23 |
| Directory entries from the earlier catalog without an organization repository | 12 |

**Categories:** Stream & Riparian Assessment (9) · Ecological Modeling (8) · Hydrologic & Hydraulic
Modeling (8) · Planning & Decision Support (3) · Data & GIS (3) · Training & Technical Resources (4).

## Organization repositories

"Listed" means the repository is linked from at least one directory entry.

| Repository | What it provides | Directory entry | Category | Listed |
|---|---|---|---|---|
| [DamRemovalCostModel](https://github.com/USACE-WRISES/DamRemovalCostModel) | R Shiny source of the Dam Removal Cost Estimator; its deployment record points to the wrises.shinyapps.io app | Dam Removal Cost Estimator | Planning & Decision Support | Yes |
| [DamRemovalCostUS](https://github.com/USACE-WRISES/DamRemovalCostUS) | R Markdown code for a revised dam removal cost model applied to dams nationwide (NID); no README | Dam Removal Cost Estimator ("Nationwide cost model code") | Planning & Decision Support | Yes |
| [ecorest-pkg-update](https://github.com/USACE-WRISES/ecorest-pkg-update) | Development repository of the ecorest R package (CRAN) | ecorest ("Package source") | Ecological Modeling | Yes |
| [ecorest-webapp](https://github.com/USACE-WRISES/ecorest-webapp) | Shiny web app for HSI modeling and CEICA with ecorest | ecorest ("Web app source"; app on wrises.shinyapps.io) | Ecological Modeling | Yes |
| [ecorest.documentation](https://github.com/USACE-WRISES/ecorest.documentation) | Preliminary model documentation report (GitHub Pages) | ecorest ("Preliminary documentation") | Ecological Modeling | Yes |
| [GitHub_Basic_Skills](https://github.com/USACE-WRISES/GitHub_Basic_Skills) | Practice repository for the GitHub tutorial exercises | — | — | No: not a standalone resource |
| [GitHub_Workflow_Tutorial_Webpage](https://github.com/USACE-WRISES/GitHub_Workflow_Tutorial_Webpage) | Quarto tutorial book (GitHub Pages), releases v1.0–v1.1, Zenodo DOI | GitHub Workflow Tutorials | Training & Technical Resources | Yes |
| [hype-app](https://github.com/USACE-WRISES/hype-app) | Public home of HYPE: Windows installers (latest v1.4.1), example projects, changelog, issue tracker; license terms pending | HYPE ★ | Hydrologic & Hydraulic Modeling | Yes |
| [hype-tool](https://github.com/USACE-WRISES/hype-tool) | HyporheicTools: Python CLI and ArcGIS Pro toolbox for MODFLOW 6 / MODPATH 7 hyporheic workflows ("Alpha") | HyporheicTools | Hydrologic & Hydraulic Modeling | Yes |
| [HyporheicFloPy](https://github.com/USACE-WRISES/HyporheicFloPy) | Notebooks coupling HEC-RAS output with FloPy; the earlier catalog's "Hyporheic Modeling Library" | Hyporheic Modeling Library | Hydrologic & Hydraulic Modeling | Yes (repository only; its Pages site of case-specific rendered notebooks is not linked) |
| [ITEK_Vault](https://github.com/USACE-WRISES/ITEK_Vault) | Locally installed retrieval-augmented language model for ITEK literature; installation guide (GitHub Pages); Zenodo DOI | ITEK Vault | Training & Technical Resources | Yes |
| [resst](https://github.com/USACE-WRISES/resst) | RESST web application (GitHub Pages) and GIS data release (`data-latest`) | RESST ★ | Data & GIS | Yes |
| [resst-dev](https://github.com/USACE-WRISES/resst-dev) | Archived development copy of RESST | — | — | No: archived, superseded by `resst` |
| [rgsm_hydraulic](https://github.com/USACE-WRISES/rgsm_hydraulic) | R and Stan research code (releases v1.0-review, v2.0), Shiny app reached through the repository's Pages address, walkthrough | RGSM Population Tool | Ecological Modeling | Yes |
| [RiverEngineeringResources](https://github.com/USACE-WRISES/RiverEngineeringResources) | Web catalog of river engineering references and stream assessment methods (GitHub Pages) | River Engineering Resources | Training & Technical Resources | Yes |
| [RiverEngineeringResourcesDB](https://github.com/USACE-WRISES/RiverEngineeringResourcesDB) | CSV tables behind River Engineering Resources (GitHub Pages download page) | River Engineering Resources Database | Data & GIS | Yes |
| [riverweed](https://github.com/USACE-WRISES/riverweed) | R package of macrophyte growth models | riverweed | Ecological Modeling | Yes |
| [staf](https://github.com/USACE-WRISES/staf) | Stream Tiered Assessment Framework: documentation site, EASI, SFARI and DEEP web apps (short links on the site), spreadsheet calculators, StreamCurves Desktop releases | STAF ★, EASI, SFARI, DEEP, StreamCurves Desktop | Stream & Riparian Assessment | Yes |
| [terrain-to-stl](https://github.com/USACE-WRISES/terrain-to-stl) | Browser converter and viewer (GitHub Pages) and Windows portable release (v0.1.1) | Terrain to STL | Data & GIS | Yes |
| [tools](https://github.com/USACE-WRISES/tools) | This directory | — | — | No: this site |
| [UtoyDecisions](https://github.com/USACE-WRISES/UtoyDecisions) | Online decision-support report for the Utoy Creek study (GitHub Pages) | Utoy Creek Decision Support | Planning & Decision Support | Yes |
| [UtoyEcoMod](https://github.com/USACE-WRISES/UtoyEcoMod) | Ecological modeling report for Utoy Creek | — | — | No: describes itself as a preliminary working version for internal use |
| [USACE-WRISES.github.io](https://github.com/USACE-WRISES/USACE-WRISES.github.io) | Organization root site (2022 team website) | — | — | No: team website, not a tool or technical resource |
| [USACE.EcoMod.Training](https://github.com/USACE-WRISES/USACE.EcoMod.Training) | Bookdown training site on R for ecological modeling (GitHub Pages) | Using R for Ecological Modeling in USACE | Training & Technical Resources | Yes |
| [WARM](https://github.com/USACE-WRISES/WARM) | Shiny source of the Web App for Riparian Models (GPL-3); includes the SMURF calculator | WARM; SMURF ("Calculator in WARM") | Stream & Riparian Assessment | Yes |
| [WRISES.Models](https://github.com/USACE-WRISES/WRISES.Models) | Earlier single-page catalog of WRISES models (May 2025, GitHub Pages) | — (credited in About) | — | No: superseded by this directory; all of its entries are included |
| [WUCT](https://github.com/USACE-WRISES/WUCT) | R function and model report for watershed connectivity; nationally certified as a USACE planning model in October 2018 | WUCT | Ecological Modeling | Yes |
| [xs-calc](https://github.com/USACE-WRISES/xs-calc) | Single-page 1D cross-section hydraulics calculator (GitHub Pages) | Cross-Section Calculator | Hydrologic & Hydraulic Modeling | Yes |

## Entries from the earlier catalog without an organization repository

| Entry | Category | Links displayed |
|---|---|---|
| GSI Toolbox (Geospatial Suitability Indices Toolbox) | Ecological Modeling | Toolbox (DOI 10.21079/11681/41881); user's guide ERDC/EL SR-22-4 (handle 11681/45128) |
| REFI (Riparian Ecological Functions Index) | Stream & Riparian Assessment | Utoy Creek application article (DOI 10.3390/land14030449); EMRRP webinars page |
| PCEM (Proctor Creek Ecological Model) | Ecological Modeling | Phase 1 and Phase 2 reports (DOIs 10.21079/11681/29514, 10.21079/11681/29515) |
| NYBEM (New York Bight Ecological Model) | Ecological Modeling | Online model documentation (mvr-gis.github.io); nybem R package (MVR-GIS on GitHub) |
| THREM (Tidal Habitats and Resilience Evaluation Model) | Ecological Modeling | Paper (DOI 10.1142/9789811275135_0195) |
| SMURF (Simple Model for Urban Riparian Function) | Stream & Riparian Assessment | Calculator in WARM (code available on request from WRISES, per the earlier catalog) |
| QHEILS (Qualitative Habitat Evaluation Index for Louisville Streams) | Stream & Riparian Assessment | Technical note with R script (DOI 10.21079/11681/48759) |
| HYDROCAL (Hydraulic Roughness Calculator) | Hydrologic & Hydraulic Modeling | Web app (wrises.shinyapps.io); CRAN package; technical note (handle 11681/2034) |
| RHA (Rapid Hydraulic Assessment) | Hydrologic & Hydraulic Modeling | Technical note (handle 11681/4038) |
| eRAMS Flow Analysis | Hydrologic & Hydraulic Modeling | eRAMS flow analysis tools and the eRAMS platform (Colorado State University) |
| LSRI (Life Safety Risk Indicator) | Hydrologic & Hydraulic Modeling | Public Planning Community Toolbox webinar page |
| EngrEcon | Planning & Decision Support | Web app (wrises.shinyapps.io); CRAN package |

The earlier catalog also lists ecorest, WARM, WUCT, the Rio Grande Silvery Minnow tool, riverweed,
the Hyporheic Modeling Library, the Dam Removal Cost Estimator, the Utoy Creek models and the R
training; those entries are backed by organization repositories and appear in the table above.

## Links not displayed

| Link (source) | Result on 2026-10-15 | Action |
|---|---|---|
| SEDHYD 2023 program page for the Hyporheic Modeling Library paper (earlier catalog) | HTTP 404; no replacement found | Omitted |
| RHA-Trap and RHA-Cross web tools on cw-environment.erdc.dren.mil (earlier catalog) | Redirect to an error page | Omitted; the technical note is linked |
| RHA-Trap and RHA-Cross on cw-environment.usace.army.mil (2022 team website) | Host no longer resolves | Omitted |
| LSRI application homepage (earlier catalog) | Sign-in required | Omitted; noted on the card |
| Beargrass Creek feasibility study page on lrd.usace.army.mil (earlier catalog, for SMURF) | HTTP 403 to automated checks; could not be confirmed another way | Omitted |
| GSI Toolbox user's guide download URL on ERDC Knowledge Core (earlier catalog) | Bot-protection page | Replaced with the report's handle |
| WARM web-app repository named in the earlier catalog | Not publicly accessible | Replaced with the public WARM repository |
| Rio Grande Silvery Minnow app on wrises.shinyapps.io (earlier catalog) | Not checked | The repository's own Pages address, which redirects to the current deployment, is used instead |

## Verification log

Results of the [Check resources run on 2026-10-15](https://github.com/USACE-WRISES/tools/actions/runs/38741454060)
for every link shown on the site: 84 distinct links, all OK, no redirects to other sites, nothing
broken or unverified. "Redirect page" means a short link that forwards to an application; the
forwarding target was checked too. Later runs are listed under the repository's Actions tab.

| Entry | Link | Result |
|---|---|---|
| STAF | <https://usace-wrises.github.io/staf/> | HTTP 200, “Stream Tiered Assessment Framework” |
| STAF | <https://usace-wrises.github.io/staf/tools/> | HTTP 200, “Apply STAF” |
| STAF | <https://usace-wrises.github.io/staf/tier-selector/> | HTTP 200, “Tier Selector” |
| STAF | <https://github.com/USACE-WRISES/staf> | Public repository |
| EASI | <https://usace-wrises.github.io/staf/easi/> | Redirect page to Posit Connect Cloud; target responds |
| EASI | <https://usace-wrises.github.io/staf/tools/#easi> | HTTP 200, “Apply STAF” |
| EASI | <https://usace-wrises.github.io/staf/walkthroughs/easi/> | HTTP 200, “EASI Walkthrough” |
| EASI | <https://github.com/USACE-WRISES/staf> | Public repository |
| SFARI | <https://usace-wrises.github.io/staf/sfari/> | Redirect page to Posit Connect Cloud; target responds |
| SFARI | <https://usace-wrises.github.io/staf/tools/#sfari> | HTTP 200, “Apply STAF” |
| SFARI | <https://github.com/USACE-WRISES/staf> | Public repository |
| DEEP | <https://usace-wrises.github.io/staf/deep/> | Redirect page to Posit Connect Cloud; target responds |
| DEEP | <https://usace-wrises.github.io/staf/tools/#deep> | HTTP 200, “Apply STAF” |
| DEEP | <https://github.com/USACE-WRISES/staf> | Public repository |
| StreamCurves Desktop | <https://github.com/USACE-WRISES/staf/releases/latest> | Latest release streamcurves-v1.0.0 |
| StreamCurves Desktop | <https://github.com/USACE-WRISES/staf> | Public repository |
| WARM | <https://wrises.shinyapps.io/warm/> | HTTP 200, “WARM” |
| WARM | <https://doi.org/10.21079/11681/47706> | DOI registered; resolves to https://hdl.handle.net/11681/47706 |
| WARM | <https://doi.org/10.1061/9780784485163.024> | DOI registered; resolves to https://ascelibrary.org/doi/10.1061/9780784485163.024 |
| WARM | <https://github.com/USACE-WRISES/WARM> | Public repository |
| REFI | <https://doi.org/10.3390/land14030449> | DOI registered; resolves to https://www.mdpi.com/2073-445X/14/3/449 |
| REFI | <https://emrrp.el.erdc.dren.mil/webinars.html> | HTTP 200, “Webinars” |
| SMURF | <https://wrises.shinyapps.io/warm/> | HTTP 200, “WARM” |
| QHEILS | <https://doi.org/10.21079/11681/48759> | DOI registered; resolves to https://hdl.handle.net/11681/48759 |
| ecorest | <https://wrises.shinyapps.io/ecorest-webapp/> | HTTP 200, “ecorest” |
| ecorest | <https://CRAN.R-project.org/package=ecorest> | HTTP 200, “CRAN: Package ecorest” (redirects within the same site) |
| ecorest | <https://usace-wrises.github.io/ecorest.documentation/> | HTTP 200, “ecorest: Generic Platform for Index-Based Modeling” |
| ecorest | <https://github.com/USACE-WRISES/ecorest-pkg-update> | Public repository |
| ecorest | <https://github.com/USACE-WRISES/ecorest-webapp> | Public repository |
| GSI Toolbox | <https://doi.org/10.21079/11681/41881> | DOI registered; resolves to https://hdl.handle.net/11681/41881 |
| GSI Toolbox | <https://hdl.handle.net/11681/45128> | Handle registered; resolves to https://erdc-library.erdc.dren.mil/handle/11681/45128 |
| WUCT | <https://github.com/USACE-WRISES/WUCT/blob/main/Instructions/README.md> | 'Instructions/README.md' found on main |
| WUCT | <https://github.com/USACE-WRISES/WUCT> | Public repository |
| WUCT | <https://doi.org/10.1890/12-1564.1> | DOI registered; resolves to https://esajournals.onlinelibrary.wiley.com/doi/10.1890/12-1564.1 |
| PCEM | <https://doi.org/10.21079/11681/29514> | DOI registered; resolves to http://hdl.handle.net/11681/29514 |
| PCEM | <https://doi.org/10.21079/11681/29515> | DOI registered; resolves to http://hdl.handle.net/11681/29515 |
| NYBEM | <https://mvr-gis.github.io/NYBEM-Report/> | HTTP 200, “New York Bight Ecological Model (NYBEM), Version 1.0.0” |
| NYBEM | <https://github.com/MVR-GIS/nybem> | Public repository |
| THREM | <https://doi.org/10.1142/9789811275135_0195> | DOI registered; resolves to https://www.worldscientific.com/doi/10.1142/9789811275135_0195 |
| RGSM Population Tool | <https://usace-wrises.github.io/rgsm_hydraulic/> | Redirect page to Posit Connect Cloud; target responds |
| RGSM Population Tool | <https://usace-wrises.github.io/rgsm_hydraulic/walkthrough/> | HTTP 200, “walkthrough” |
| RGSM Population Tool | <https://github.com/USACE-WRISES/rgsm_hydraulic> | Public repository |
| RGSM Population Tool | <https://doi.org/10.1002/ecs2.4240> | DOI registered; resolves to https://esajournals.onlinelibrary.wiley.com/doi/10.1002/ecs2.4240 |
| riverweed | <https://github.com/USACE-WRISES/riverweed> | Public repository |
| HYPE | <https://github.com/USACE-WRISES/hype-app/releases/latest> | Latest release v1.4.1 |
| HYPE | <https://github.com/USACE-WRISES/hype-app> | Public repository |
| HYPE | <https://github.com/USACE-WRISES/hype-app/issues> | Issues enabled |
| HyporheicTools | <https://github.com/USACE-WRISES/hype-tool> | Public repository |
| Hyporheic Modeling Library | <https://github.com/USACE-WRISES/HyporheicFloPy> | Public repository |
| HYDROCAL | <https://wrises.shinyapps.io/hydrocal/> | HTTP 200, “HYDROCAL” |
| HYDROCAL | <https://CRAN.R-project.org/package=HYDROCAL> | HTTP 200, “CRAN: Package HYDROCAL” (redirects within the same site) |
| HYDROCAL | <https://hdl.handle.net/11681/2034> | Handle registered; resolves to https://erdc-library.erdc.dren.mil/handle/11681/2034 |
| RHA | <https://hdl.handle.net/11681/4038> | Handle registered; resolves to https://erdc-library.erdc.dren.mil/handle/11681/4038 |
| Cross-Section Calculator | <https://usace-wrises.github.io/xs-calc/> | HTTP 200, “1D Cross-Section Hydraulics Calculator” |
| Cross-Section Calculator | <https://github.com/USACE-WRISES/xs-calc> | Public repository |
| eRAMS Flow Analysis | <https://erams.com/flowanalysis> | HTTP 200, “eRAMS” (redirects within the same site) |
| eRAMS Flow Analysis | <https://erams.com/catena/> | HTTP 200, “Home - Catena Analytics” |
| LSRI | <https://planning.erdc.dren.mil/toolbox/resources.cfm?Id=0&WId=700&Option=Planning%20Webinars> | HTTP 200, “Planning Community Toolbox: Training Resources” |
| EngrEcon | <https://wrises.shinyapps.io/engrecon-webapp/> | HTTP 200, “EngrEcon Analysis” |
| EngrEcon | <https://CRAN.R-project.org/package=EngrEcon> | HTTP 200, “CRAN: Package EngrEcon” (redirects within the same site) |
| Dam Removal Cost Estimator | <https://wrises.shinyapps.io/DamRemovalCostPredictiveModel/> | HTTP 200, “Dam Removal Cost EstimatorInput parametersInput parametersInput parame” |
| Dam Removal Cost Estimator | <https://doi.org/10.3389/fevo.2023.1215471> | DOI registered; resolves to https://www.frontiersin.org/articles/10.3389/fevo.2023.1215471/full |
| Dam Removal Cost Estimator | <https://www.usgs.gov/publications/dam-removal-cost-databases-and-drivers> | HTTP 200, “Dam removal cost databases and drivers” |
| Dam Removal Cost Estimator | <https://github.com/USACE-WRISES/DamRemovalCostModel> | Public repository |
| Dam Removal Cost Estimator | <https://github.com/USACE-WRISES/DamRemovalCostUS> | Public repository |
| Utoy Creek Decision Support | <https://usace-wrises.github.io/UtoyDecisions/> | HTTP 200, “Socioeconomic Analysis” |
| Utoy Creek Decision Support | <https://github.com/USACE-WRISES/UtoyDecisions> | Public repository |
| RESST | <https://usace-wrises.github.io/resst/> | HTTP 200, “Reservoir Sustainable Sediment Tool (RESST)” |
| RESST | <https://github.com/USACE-WRISES/resst/releases/tag/data-latest> | Release 'data-latest' found |
| RESST | <https://github.com/USACE-WRISES/resst> | Public repository |
| River Engineering Resources Database | <https://usace-wrises.github.io/RiverEngineeringResourcesDB/> | HTTP 200, “River Engineering Resources Database” |
| River Engineering Resources Database | <https://github.com/USACE-WRISES/RiverEngineeringResourcesDB> | Public repository |
| Terrain to STL | <https://usace-wrises.github.io/terrain-to-stl/> | HTTP 200, “Terrain to STL” |
| Terrain to STL | <https://github.com/USACE-WRISES/terrain-to-stl/releases/latest/download/terrain-to-stl-desktop-windows-x64.zip> | Asset 'terrain-to-stl-desktop-windows-x64.zip' found in the latest release |
| Terrain to STL | <https://github.com/USACE-WRISES/terrain-to-stl> | Public repository |
| Using R for Ecological Modeling in USACE | <https://usace-wrises.github.io/USACE.EcoMod.Training/> | HTTP 200, “Using R for ecological modeling in USACE restoration planning” |
| Using R for Ecological Modeling in USACE | <https://github.com/USACE-WRISES/USACE.EcoMod.Training> | Public repository |
| GitHub Workflow Tutorials | <https://usace-wrises.github.io/GitHub_Workflow_Tutorial_Webpage/> | HTTP 200, “GitHub Skill Building Tutorials for Students & Researchers” |
| GitHub Workflow Tutorials | <https://doi.org/10.5281/zenodo.15717297> | DOI registered; resolves to https://zenodo.org/doi/10.5281/zenodo.15717297 |
| GitHub Workflow Tutorials | <https://github.com/USACE-WRISES/GitHub_Workflow_Tutorial_Webpage> | Public repository |
| River Engineering Resources | <https://usace-wrises.github.io/RiverEngineeringResources/> | HTTP 200, “River Engineering Resources” |
| River Engineering Resources | <https://usace-wrises.github.io/RiverEngineeringResourcesDB/> | HTTP 200, “River Engineering Resources Database” |
| River Engineering Resources | <https://github.com/USACE-WRISES/RiverEngineeringResources> | Public repository |
| ITEK Vault | <https://usace-wrises.github.io/ITEK_Vault/> | HTTP 200, “ITEK Vault Installation and Use Guide” |
| ITEK Vault | <https://doi.org/10.5281/zenodo.18436869> | DOI registered; resolves to https://zenodo.org/doi/10.5281/zenodo.18436869 |
| ITEK Vault | <https://github.com/USACE-WRISES/ITEK_Vault> | Public repository |
| Site pages | <https://github.com/USACE-WRISES> | HTTP 200, “USACE-WRISES” |
| Site pages | <https://github.com/USACE-WRISES/tools> | Public repository |
| Site pages | <https://github.com/USACE-WRISES/tools/issues> | Issues enabled |
| Site pages | <https://usace-wrises.github.io/WRISES.Models/> | HTTP 200, “WRISES Models” |

## Notes

- **Hosting outside GitHub.** EASI, SFARI and DEEP open through short links on the STAF site
  (`/staf/easi/`, `/staf/sfari/`, `/staf/deep/`), which the STAF repository maintains in
  `docs/_data/apps.yml`; on 2026-10-15 they redirected to the STAF app on Posit Connect Cloud. The
  ecorest, WARM, HYDROCAL, EngrEcon and Dam Removal Cost Estimator apps are hosted on
  wrises.shinyapps.io; all responded (HTTP 200, or 202 while an app was starting).
- **Statuses** shown on cards come from each resource's own documentation: HyporheicTools is "Alpha"
  (package metadata); EASI is a "screening tool, not a regulatory determination"; the SFARI calculator is
  a draft pending Eco-PCX certification; DEEP regional assessments are Draft or Preliminary; HYPE's license
  terms are pending. Review statuses from the earlier catalog are shown as "as of May 2025".
- **GitHub Pages for this site** was not yet enabled on 2026-10-15 (Settings → Pages → Source: GitHub
  Actions).

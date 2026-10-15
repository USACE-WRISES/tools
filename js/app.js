// WRISES Tools & Resources
// Renders the directory from data/resources.json. To add or change a resource, edit that file;
// nothing here needs to change. Content is inserted as text (never as HTML).

const CATALOG_URL = "data/resources.json";
const ALL = "all";
const MAX_VISIBLE_TAGS = 4;
const STATUS_DELAY_MS = 400;
const URL_DELAY_MS = 300;
const SVG_NS = "http://www.w3.org/2000/svg";

// Link types: the label shown when a link has no "label" of its own, its icon, and whether it
// may be the card's main (filled) button when it is listed first.
const LINK_TYPES = {
  app: { label: "Launch tool", icon: "i-launch", primary: true },
  download: { label: "Download", icon: "i-download", primary: true },
  documentation: { label: "Documentation", icon: "i-book", primary: true },
  dataset: { label: "Dataset", icon: "i-database", primary: true },
  repository: { label: "Repository", icon: "i-code", primary: true },
  publication: { label: "Publication", icon: "i-file", primary: false },
  reference: { label: "More information", icon: "i-link", primary: false },
};

const state = { query: "", category: ALL };
const dom = {};
const filterChips = new Map();
let catalog = null;
let statusTimer = 0;
let urlTimer = 0;

init();

async function init() {
  dom.form = document.getElementById("search-form");
  dom.input = document.getElementById("search-input");
  dom.status = document.getElementById("result-status");
  dom.filters = document.getElementById("filters");
  dom.filterOptions = document.getElementById("filter-options");
  dom.results = document.getElementById("results");
  dom.empty = document.getElementById("empty-state");
  dom.clear = document.getElementById("clear-filters");
  dom.dateWrap = document.getElementById("catalog-date-wrap");
  dom.date = document.getElementById("catalog-date");

  readUrlState();
  dom.input.value = state.query;
  dom.results.replaceChildren(el("p", { className: "loading" }, "Loading resources…"));
  bindEvents();

  try {
    catalog = await loadCatalog();
  } catch (error) {
    console.error("The resource catalog could not be loaded.", error);
    showLoadError();
    return;
  }

  // Fall back to "All" when the address names a category that does not exist or has no resources.
  if (state.category !== ALL && !catalog.resources.some((resource) => resource.category === state.category)) {
    state.category = ALL;
  }
  buildFilters();
  renderCatalogDate();
  render({ immediate: true });
}

// ---------------------------------------------------------------------------------------------
// Data

async function loadCatalog() {
  const response = await fetch(CATALOG_URL, { cache: "no-cache" });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} for ${CATALOG_URL}`);
  }
  const data = await response.json();

  const categories = (Array.isArray(data.categories) ? data.categories : [])
    .filter((category) => category && isText(category.id) && isText(category.name))
    .map((category) => ({
      id: category.id,
      name: category.name.trim(),
      description: isText(category.description) ? category.description.trim() : "",
    }));
  const categoryNames = new Map(categories.map((category) => [category.id, category.name]));

  const resources = [];
  for (const item of Array.isArray(data.resources) ? data.resources : []) {
    if (!item || !isText(item.id) || !isText(item.name) || !isText(item.description)) {
      console.warn("Skipping a catalog entry without an id, name or description.", item);
      continue;
    }
    let category = item.category;
    if (!categoryNames.has(category)) {
      console.warn(`"${item.id}" uses an unknown category "${category}"; it is listed under "Other".`);
      category = "other";
      if (!categoryNames.has("other")) {
        categories.push({ id: "other", name: "Other", description: "" });
        categoryNames.set("other", "Other");
      }
    }
    resources.push(normalizeResource(item, category, categoryNames.get(category)));
  }
  return { updated: isText(data.updated) ? data.updated : "", categories, resources };
}

function normalizeResource(item, category, categoryName) {
  const tags = (Array.isArray(item.tags) ? item.tags : []).filter(isText).map((tag) => tag.trim());
  const links = (Array.isArray(item.links) ? item.links : [])
    .map((link) => {
      const type = link && LINK_TYPES[link.type] ? link.type : null;
      const url = link ? safeUrl(link.url) : null;
      if (!type || !url) {
        return null;
      }
      return { type, url, label: isText(link.label) ? link.label.trim() : LINK_TYPES[type].label };
    })
    .filter(Boolean);
  // Launch links come first; everything else keeps the order given in the catalog.
  const ordered = [...links.filter((link) => link.type === "app"), ...links.filter((link) => link.type !== "app")];

  const resource = {
    id: item.id,
    name: item.name.trim(),
    fullName: isText(item.fullName) ? item.fullName.trim() : "",
    description: item.description.trim(),
    category,
    type: isText(item.type) ? item.type.trim() : "",
    status: isText(item.status) ? item.status.trim() : "",
    note: isText(item.note) ? item.note.trim() : "",
    tags,
    links: ordered,
  };
  resource.searchText = ` ${normalize(
    [resource.name, resource.fullName, resource.description, resource.type, resource.status, categoryName, ...tags].join(" "),
  )} `;
  return resource;
}

function isText(value) {
  return typeof value === "string" && value.trim() !== "";
}

function safeUrl(value) {
  if (!isText(value)) {
    return null;
  }
  try {
    const url = new URL(value.trim(), document.baseURI);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------------------------
// Search and filters

function normalize(text) {
  return String(text)
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function tokenize(query) {
  const normalized = normalize(query);
  return normalized ? normalized.split(" ") : [];
}

// Every word of the query must appear. One-letter words must match a whole word ("r" finds
// "R package", not "river"); two-letter words must start a word; longer words can match anywhere.
function matchesQuery(resource, tokens) {
  return tokens.every((token) => {
    if (token.length === 1) {
      return resource.searchText.includes(` ${token} `);
    }
    return resource.searchText.includes(token.length === 2 ? ` ${token}` : token);
  });
}

function bindEvents() {
  dom.input.addEventListener("input", () => {
    state.query = dom.input.value;
    if (catalog) {
      render();
    }
  });
  dom.input.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && dom.input.value !== "") {
      event.preventDefault();
      dom.input.value = "";
      state.query = "";
      if (catalog) {
        render();
      }
    }
  });
  dom.form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (window.matchMedia("(pointer: coarse)").matches) {
      dom.input.blur();
    }
  });
  dom.filterOptions.addEventListener("change", (event) => {
    if (event.target instanceof HTMLInputElement && event.target.name === "category") {
      state.category = event.target.value;
      render();
    }
  });
  dom.clear.addEventListener("click", () => {
    state.query = "";
    state.category = ALL;
    dom.input.value = "";
    const allOption = filterChips.get(ALL);
    if (allOption) {
      allOption.input.checked = true;
    }
    render({ immediate: true });
    dom.input.focus();
  });
}

function buildFilters() {
  const options = [
    { id: ALL, name: "All" },
    ...catalog.categories.filter((category) => catalog.resources.some((r) => r.category === category.id)),
  ];
  filterChips.clear();
  const chips = options.map((option) => {
    const input = el("input", { type: "radio", name: "category", value: option.id, className: "filter-input" });
    input.checked = option.id === state.category;
    const count = el("span", { className: "filter-count" });
    const chip = el("label", { className: "filter-chip" }, [
      input,
      el("span", { className: "filter-text" }, [option.name, " ", count]),
    ]);
    filterChips.set(option.id, { chip, input, count });
    return chip;
  });
  dom.filterOptions.replaceChildren(...chips);
  dom.filters.hidden = false;
}

// ---------------------------------------------------------------------------------------------
// Rendering

function render({ immediate = false } = {}) {
  const tokens = tokenize(state.query);
  const matching = catalog.resources.filter((resource) => matchesQuery(resource, tokens));

  for (const [id, { chip, count }] of filterChips) {
    const n = id === ALL ? matching.length : matching.filter((resource) => resource.category === id).length;
    count.textContent = String(n);
    chip.classList.toggle("is-empty", n === 0);
  }

  const visible = state.category === ALL ? matching : matching.filter((r) => r.category === state.category);
  const groups = catalog.categories
    .map((category) => ({ category, items: visible.filter((resource) => resource.category === category.id) }))
    .filter((group) => group.items.length > 0)
    .map(({ category, items }) => renderGroup(category, items));

  dom.results.replaceChildren(...groups);
  dom.results.hidden = visible.length === 0;
  dom.empty.hidden = visible.length > 0;

  updateStatus(statusMessage(visible.length, tokens.length > 0), immediate);
  scheduleUrlUpdate();
}

function renderGroup(category, items) {
  const headingId = `category-${category.id}`;
  return el("section", { className: "category-group", "aria-labelledby": headingId }, [
    el("div", { className: "group-head" }, [
      el("h3", { className: "group-title", id: headingId }, [
        category.name,
        el("span", { className: "group-count" }, [
          String(items.length),
          el("span", { className: "visually-hidden" }, items.length === 1 ? " resource" : " resources"),
        ]),
      ]),
      category.description ? el("p", { className: "group-description" }, category.description) : null,
    ]),
    el("div", { className: "card-grid" }, items.map((resource) => createCard(resource))),
  ]);
}

function createCard(resource) {
  const meta = el("p", { className: "card-meta" }, [
    resource.type ? el("span", { className: "card-type" }, resource.type) : null,
    resource.status ? el("span", { className: "badge" }, resource.status) : null,
  ]);

  const actions = resource.links.length
    ? el(
        "div",
        { className: "card-actions" },
        resource.links.map((link, index) =>
          el(
            "a",
            {
              className: index === 0 && LINK_TYPES[link.type].primary ? "button" : "action-link",
              href: link.url,
              target: "_blank",
              rel: "noopener",
            },
            [
              icon(LINK_TYPES[link.type].icon),
              link.label,
              el("span", { className: "visually-hidden" }, `: ${resource.name} (opens in a new tab)`),
            ],
          ),
        ),
      )
    : null;

  return el("article", { className: "card" }, [
    meta.childNodes.length ? meta : null,
    el("h4", { className: "card-title" }, resource.name),
    resource.fullName ? el("p", { className: "card-subtitle" }, resource.fullName) : null,
    el("p", { className: "card-description" }, resource.description),
    resource.note ? el("p", { className: "card-note" }, [icon("i-info"), el("span", {}, resource.note)]) : null,
    resource.tags.length
      ? el(
          "ul",
          { className: "tag-list", "aria-label": "Tags" },
          resource.tags.slice(0, MAX_VISIBLE_TAGS).map((tag) => el("li", { className: "tag" }, tag)),
        )
      : null,
    actions,
  ]);
}

function statusMessage(count, hasQuery) {
  const noun = count === 1 ? "resource" : "resources";
  if (!hasQuery && state.category === ALL) {
    const categories = new Set(catalog.resources.map((resource) => resource.category)).size;
    return `${count} ${noun} in ${categories} ${categories === 1 ? "category" : "categories"}`;
  }
  let message = `${count} ${noun}`;
  if (hasQuery) {
    message += ` matching “${state.query.trim()}”`;
  }
  if (state.category !== ALL) {
    const category = catalog.categories.find((item) => item.id === state.category);
    message += ` in ${category ? category.name : state.category}`;
  }
  return message;
}

function updateStatus(message, immediate) {
  clearTimeout(statusTimer);
  if (immediate) {
    dom.status.textContent = message;
  } else {
    statusTimer = setTimeout(() => {
      dom.status.textContent = message;
    }, STATUS_DELAY_MS);
  }
}

function renderCatalogDate() {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(catalog.updated);
  if (!match) {
    return;
  }
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  dom.date.dateTime = catalog.updated;
  dom.date.textContent = date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
  dom.dateWrap.hidden = false;
}

function showLoadError() {
  dom.results.replaceChildren(
    el("div", { className: "notice notice-error", role: "alert" }, [
      el("p", {}, "The resource catalog could not be loaded."),
      el("p", {}, [
        "Please reload the page, or browse the ",
        el("a", { href: "https://github.com/USACE-WRISES", target: "_blank", rel: "noopener" }, [
          "WRISES GitHub organization",
          el("span", { className: "visually-hidden" }, " (opens in a new tab)"),
        ]),
        " directly.",
      ]),
    ]),
  );
  dom.status.textContent = "";
  dom.filters.hidden = true;
}

// ---------------------------------------------------------------------------------------------
// URL state (?q=…&category=…) so a filtered view can be bookmarked or shared

function readUrlState() {
  const params = new URLSearchParams(window.location.search);
  state.query = (params.get("q") || "").slice(0, 200);
  state.category = params.get("category") || ALL;
}

function scheduleUrlUpdate() {
  clearTimeout(urlTimer);
  urlTimer = setTimeout(() => {
    const params = new URLSearchParams();
    if (state.query.trim()) {
      params.set("q", state.query.trim());
    }
    if (state.category !== ALL) {
      params.set("category", state.category);
    }
    const search = params.toString();
    const url = `${window.location.pathname}${search ? `?${search}` : ""}${window.location.hash}`;
    try {
      window.history.replaceState(null, "", url);
    } catch {
      // Some browsers limit how often the URL can change; the page works without it.
    }
  }, URL_DELAY_MS);
}

// ---------------------------------------------------------------------------------------------
// DOM helpers

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === null || value === undefined || value === false) {
      continue;
    }
    if (key === "className") {
      node.className = value;
    } else {
      node.setAttribute(key, value === true ? "" : String(value));
    }
  }
  for (const child of [].concat(children)) {
    if (child === null || child === undefined || child === false) {
      continue;
    }
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function icon(id) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const use = document.createElementNS(SVG_NS, "use");
  use.setAttribute("href", `#${id}`);
  svg.append(use);
  return svg;
}

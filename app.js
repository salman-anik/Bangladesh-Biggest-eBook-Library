(() => {
  "use strict";

  const BATCH_SIZE = 36;
  const ROOT_DRIVE_URL = "https://drive.google.com/drive/folders/1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq";
  const STORAGE_SAVED_KEY = "bd_ebook_saved_v1";
  const STORAGE_THEME_KEY = "bd_ebook_theme_v1";
  const STORAGE_VIEW_KEY = "bd_ebook_view_v1";

  const state = {
    raw: null,
    books: [],
    filtered: [],
    renderedCount: 0,
    tree: [],
    selectedCat: "",
    selectedSub: "",
    query: "",
    format: "",
    language: "",
    sort: "covers",
    coversOnly: false,
    folderQuery: "",
    discoverManualHidden: false,
    viewMode: localStorage.getItem(STORAGE_VIEW_KEY) || "grid",
    expandedNodes: new Set(),
    savedIds: new Set(loadSavedIds()),
    activeModalBook: null,
  };

  const els = {};
  let scrollObserver = null;

  function $(id) {
    return document.getElementById(id);
  }

  function loadSavedIds() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_SAVED_KEY) || "[]");
      return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
    } catch {
      return [];
    }
  }

  function persistSavedIds() {
    try {
      localStorage.setItem(STORAGE_SAVED_KEY, JSON.stringify([...state.savedIds]));
    } catch {
      // Ignore storage errors
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatSize(bytes) {
    const n = Number(bytes) || 0;
    if (n <= 0) return "—";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let val = n;
    for (let i = 0; i < units.length; i++) {
      if (val < 1000 || i === units.length - 1) {
        return (i <= 1 ? Math.round(val) : val.toFixed(2)) + " " + units[i];
      }
      val /= 1000;
    }
    return n + " B";
  }

  function showToast(message) {
    const container = els.toastContainer;
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 2600);
  }

  function initTheme() {
    applyTheme(localStorage.getItem(STORAGE_THEME_KEY) || "dark");
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    if (els.themeIcon) {
      els.themeIcon.textContent = theme === "dark" ? "◐" : "◑";
    }
    try {
      localStorage.setItem(STORAGE_THEME_KEY, theme);
    } catch {
      // Ignore
    }
  }

  function applyViewMode(mode) {
    state.viewMode = mode === "list" ? "list" : "grid";
    els.booksGrid.classList.toggle("list-view", state.viewMode === "list");
    els.gridViewBtn.classList.toggle("active", state.viewMode === "grid");
    els.listViewBtn.classList.toggle("active", state.viewMode === "list");
    try {
      localStorage.setItem(STORAGE_VIEW_KEY, state.viewMode);
    } catch {
      // Ignore
    }
  }

  function inflateCatalog(data) {
    const { cats = [], subs = [], langs = [], fmts = [], books = [] } = data;
    return books.map((row, idx) => {
      const fid = row[0] || "";
      const title = row[1] || "Untitled";
      const author = row[2] || "Unknown";
      const cat = cats[row[3]] || "Other";
      const sub = subs[row[4]] || "";
      const lang = langs[row[5]] || "Unknown";
      const fmt = fmts[row[6]] || "PDF";
      const size = Number(row[7]) || 0;
      const coverId = row[8] || "";
      const series = row[9] || "";
      return {
        idx,
        id: fid,
        title,
        author,
        cat,
        sub,
        lang,
        fmt,
        size,
        coverId,
        series,
        searchBlob: `${title} ${author} ${cat} ${sub} ${series} ${fmt}`.toLowerCase(),
      };
    });
  }

  /* ================= LIBRARY INTELLIGENCE DASHBOARD ================= */

  function renderDashboard(data, books) {
    const total = data.total || books.length;
    const totalBytes = data.total_bytes || 0;
    const coversCount = data.covers_count || books.filter((b) => b.coverId).length;
    const coverPct = total ? (coversCount / total) * 100 : 0;

    els.dashboardUpdatedAt.textContent = data.generated_at ? `SYNC ${data.generated_at}` : "LIVE ARCHIVE";
    els.kpiTotalBooks.textContent = total.toLocaleString();
    els.kpiTotalSize.textContent = formatSize(totalBytes);
    els.kpiCoversPct.textContent = `${coverPct.toFixed(1)}%`;
    els.kpiCoversBar.style.width = `${Math.min(100, coverPct)}%`;
    els.kpiCoversCount.textContent = `${coversCount.toLocaleString()} books with cover art`;
    els.kpiAuthors.textContent = `${(data.authors_count || 0).toLocaleString()}+`;
    els.kpiSubcats.textContent = String((data.subs || []).filter(Boolean).length);

    const catCounts = new Map();
    const eduTopCounts = new Map();
    const fmtCounts = new Map();
    const langCounts = new Map();

    for (const b of books) {
      catCounts.set(b.cat, (catCounts.get(b.cat) || 0) + 1);
      if (b.cat === "Education & Textbooks") {
        const top = (b.sub || "Other").split("/")[0];
        eduTopCounts.set(top, (eduTopCounts.get(top) || 0) + 1);
      }
      fmtCounts.set(b.fmt, (fmtCounts.get(b.fmt) || 0) + 1);
      langCounts.set(b.lang, (langCounts.get(b.lang) || 0) + 1);
    }

    els.kpiEduCount.textContent = (catCounts.get("Education & Textbooks") || 0).toLocaleString();

    renderBarChart(
      els.chartCategories,
      [...catCounts.entries()].sort((a, b) => b[1] - a[1]),
      (label) => {
        selectFolder(label, "");
        scrollToCatalog();
      }
    );

    renderBarChart(
      els.chartEducation,
      [...eduTopCounts.entries()].sort((a, b) => b[1] - a[1]),
      (label) => {
        selectFolder("Education & Textbooks", label);
        scrollToCatalog();
      }
    );

    renderFormatsDonut(fmtCounts, total);

    const topLangs = [...langCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
    renderBarChart(els.chartLanguages, topLangs, (label) => {
      state.language = label;
      els.languageFilter.value = label;
      resetScrollAndRender();
      scrollToCatalog();
    });
  }

  function renderBarChart(container, entries, onClick) {
    if (!container) return;
    container.innerHTML = "";
    const maxVal = entries.length ? entries[0][1] : 1;
    const frag = document.createDocumentFragment();
    for (const [label, count] of entries) {
      const pct = Math.max(2, (count / maxVal) * 100);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "bar-row";
      btn.innerHTML = `
        <span class="bar-label" title="${escapeHtml(label)}">${escapeHtml(label)}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${pct.toFixed(1)}%"></span></span>
        <span class="bar-val">${count.toLocaleString()}</span>
      `;
      btn.addEventListener("click", () => onClick(label));
      frag.appendChild(btn);
    }
    container.appendChild(frag);
  }

  function renderFormatsDonut(fmtCounts, total) {
    const svg = els.chartFormatsSvg;
    const legend = els.chartFormatsLegend;
    if (!svg || !legend) return;

    const sorted = [...fmtCounts.entries()].sort((a, b) => b[1] - a[1]);
    const top4 = sorted.slice(0, 4);
    const otherCnt = sorted.slice(4).reduce((s, x) => s + x[1], 0);
    const slices = otherCnt > 0 ? [...top4, ["Other Formats", otherCnt]] : top4;
    const opacities = [1.0, 0.65, 0.42, 0.25, 0.14];

    const r = 44;
    const circ = 2 * Math.PI * r;
    let offset = 0;

    let svgHtml = `<circle cx="60" cy="60" r="${r}" fill="none" stroke="var(--surface-2)" stroke-width="14"/>`;
    slices.forEach(([fmt, count], idx) => {
      const len = total > 0 ? (count / total) * circ : 0;
      const op = opacities[idx] ?? 0.2;
      svgHtml += `<circle cx="60" cy="60" r="${r}" fill="none" stroke="var(--ink)" stroke-opacity="${op}" stroke-width="14" stroke-dasharray="${len.toFixed(2)} ${(circ - len).toFixed(2)}" stroke-dashoffset="${(-offset).toFixed(2)}" transform="rotate(-90 60 60)"/>`;
      offset += len;
    });
    svgHtml += `<text x="60" y="57" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="800" font-family="JetBrains Mono, monospace">${sorted.length}</text>`;
    svgHtml += `<text x="60" y="70" text-anchor="middle" fill="var(--muted)" font-size="7" font-family="JetBrains Mono, monospace">FORMATS</text>`;
    svg.innerHTML = svgHtml;

    legend.innerHTML = "";
    slices.forEach(([fmt, count], idx) => {
      const pct = total > 0 ? ((count / total) * 100).toFixed(1) : "0.0";
      const op = opacities[idx] ?? 0.2;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "legend-row";
      btn.innerHTML = `
        <span class="legend-left">
          <span class="legend-swatch" style="background:var(--ink);opacity:${op}"></span>
          <span>${escapeHtml(fmt)}</span>
        </span>
        <span class="mono-muted">${count.toLocaleString()} (${pct}%)</span>
      `;
      if (fmt !== "Other Formats") {
        btn.addEventListener("click", () => {
          state.format = fmt;
          els.formatFilter.value = fmt;
          resetScrollAndRender();
          scrollToCatalog();
        });
      }
      legend.appendChild(btn);
    });
  }

  /* ================= CURATED SCROLL & DISCOVER RAILS ================= */

  function renderDiscoveryRails(books) {
    const container = els.discoverRails;
    if (!container) return;

    const covered = books.filter((b) => b.coverId);
    const pool = covered.length > 50 ? covered : books;

    const specs = [
      {
        title: "Education & Textbooks Spotlight",
        items: pool.filter((b) => b.cat === "Education & Textbooks" && !b.sub.startsWith("Madrasa/Qawmi")).slice(0, 14),
      },
      {
        title: "University, CS & Open Textbooks",
        items: pool.filter((b) => b.sub.startsWith("University Education")).slice(0, 14),
      },
      {
        title: "Bangla Literature & Classics",
        items: pool.filter((b) => b.cat === "Bangla Books").slice(0, 14),
      },
      {
        title: "Visual Maps, Reference & Question Banks",
        items: books
          .filter((b) =>
            ["JPG", "JPEG", "PNG"].includes(b.fmt) ||
            b.sub.startsWith("Academic Resources") ||
            b.cat === "Reference & Research"
          )
          .slice(0, 14),
      },
    ].filter((s) => s.items.length > 0);

    container.innerHTML = "";
    const frag = document.createDocumentFragment();
    specs.forEach((spec, sIdx) => {
      const block = document.createElement("div");
      block.className = "rail-block";

      const head = document.createElement("div");
      head.className = "rail-head";
      head.innerHTML = `<h3 class="rail-title">${escapeHtml(spec.title)}</h3>`;

      const ctrls = document.createElement("div");
      ctrls.className = "rail-controls";
      const prev = document.createElement("button");
      prev.type = "button";
      prev.className = "bw-btn bw-btn-icon";
      prev.textContent = "‹";
      prev.setAttribute("aria-label", `Scroll ${spec.title} left`);
      const next = document.createElement("button");
      next.type = "button";
      next.className = "bw-btn bw-btn-icon";
      next.textContent = "›";
      next.setAttribute("aria-label", `Scroll ${spec.title} right`);
      ctrls.appendChild(prev);
      ctrls.appendChild(next);
      head.appendChild(ctrls);

      const track = document.createElement("div");
      track.className = "rail-track";
      track.id = `railTrack_${sIdx}`;
      for (const b of spec.items) {
        track.appendChild(createBookCard(b));
      }

      prev.addEventListener("click", () => track.scrollBy({ left: -560, behavior: "smooth" }));
      next.addEventListener("click", () => track.scrollBy({ left: 560, behavior: "smooth" }));

      block.appendChild(head);
      block.appendChild(track);
      frag.appendChild(block);
    });
    container.appendChild(frag);
  }

  function updateDiscoverVisibility(hasActiveFilter) {
    const hide = hasActiveFilter || state.discoverManualHidden;
    els.discoverRails.classList.toggle("hidden", hide);
    els.toggleDiscoverBtn.textContent = hide ? "Show Shelves" : "Hide Shelves";
    if (hasActiveFilter && !state.discoverManualHidden) {
      els.discoverSection.classList.add("hidden");
    } else {
      els.discoverSection.classList.remove("hidden");
    }
  }

  /* ================= QUICK CATEGORY CHIPS & DRIVE TREE ================= */

  function renderQuickChips(cats) {
    const container = els.quickChips;
    if (!container) return;
    container.innerHTML = "";
    const items = ["All", ...cats.filter((c) => c && c !== "Library Management")];
    for (const name of items) {
      const isAll = name === "All";
      const active = isAll ? !state.selectedCat : state.selectedCat === name && !state.selectedSub;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip-btn" + (active ? " active" : "");
      btn.textContent = name;
      btn.addEventListener("click", () => {
        if (isAll) {
          selectFolder("", "");
        } else {
          selectFolder(name, "");
        }
      });
      container.appendChild(btn);
    }
  }

  function buildFolderTree(books, canonicalCats) {
    const rootMap = new Map();
    function ensureRoot(cat) {
      if (!rootMap.has(cat)) {
        rootMap.set(cat, { name: cat, cat, sub: "", pathKey: cat, count: 0, children: new Map() });
      }
      return rootMap.get(cat);
    }
    for (const c of canonicalCats) {
      if (c && c !== "Library Management") ensureRoot(c);
    }
    for (const book of books) {
      const root = ensureRoot(book.cat);
      root.count++;
      if (!book.sub) continue;
      const parts = book.sub.split("/").filter(Boolean);
      let curr = root;
      let accSub = "";
      for (const part of parts) {
        accSub = accSub ? `${accSub}/${part}` : part;
        if (!curr.children.has(part)) {
          curr.children.set(part, {
            name: part,
            cat: book.cat,
            sub: accSub,
            pathKey: `${book.cat}:::${accSub}`,
            count: 0,
            children: new Map(),
          });
        }
        curr = curr.children.get(part);
        curr.count++;
      }
    }
    function toSortedArray(map, preserveOrder = false) {
      const arr = Array.from(map.values());
      if (!preserveOrder) {
        arr.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" }));
      }
      return arr.map((node) => ({ ...node, children: toSortedArray(node.children, false) }));
    }
    return toSortedArray(rootMap, true).filter((r) => r.count > 0);
  }

  function filterTreeNodes(nodes, q) {
    if (!q) return nodes;
    const lower = q.toLowerCase();
    const result = [];
    for (const node of nodes) {
      const filteredChildren = filterTreeNodes(node.children, lower);
      const selfMatches = node.name.toLowerCase().includes(lower);
      if (selfMatches || filteredChildren.length > 0) {
        result.push({
          ...node,
          children: selfMatches && filteredChildren.length === 0 ? node.children : filteredChildren,
          forceExpand: filteredChildren.length > 0,
        });
      }
    }
    return result;
  }

  function renderFolderTree() {
    const visibleTree = filterTreeNodes(state.tree, state.folderQuery.trim());
    const frag = document.createDocumentFragment();
    els.allBooksBtn.classList.toggle("active", !state.selectedCat && !state.selectedSub);

    function renderNodes(nodes, container) {
      for (const node of nodes) {
        const group = document.createElement("div");
        group.className = "tree-group";

        const hasChildren = node.children && node.children.length > 0;
        const isExpanded = node.forceExpand || state.expandedNodes.has(node.pathKey);
        const isActive = state.selectedCat === node.cat && state.selectedSub === node.sub;

        const row = document.createElement("div");
        row.className = "tree-row" + (isActive ? " active" : "");

        const chevron = document.createElement("button");
        chevron.type = "button";
        chevron.className = "tree-chevron" + (hasChildren ? (isExpanded ? " expanded" : "") : " leaf-spacer");
        chevron.textContent = "▶";
        if (hasChildren) {
          chevron.addEventListener("click", (e) => {
            e.stopPropagation();
            if (state.expandedNodes.has(node.pathKey)) state.expandedNodes.delete(node.pathKey);
            else state.expandedNodes.add(node.pathKey);
            renderFolderTree();
          });
        }

        const label = document.createElement("span");
        label.className = "tree-label";
        label.textContent = node.name;
        label.title = `${node.name} (${node.count.toLocaleString()})`;

        const chip = document.createElement("span");
        chip.className = "mono-chip";
        chip.textContent = node.count.toLocaleString();

        row.appendChild(chevron);
        row.appendChild(label);
        row.appendChild(chip);

        row.addEventListener("click", () => {
          selectFolder(node.cat, node.sub);
          if (hasChildren) state.expandedNodes.add(node.pathKey);
          closeMobileSidebar();
        });

        group.appendChild(row);
        if (hasChildren && isExpanded) {
          const childWrap = document.createElement("div");
          childWrap.className = "tree-children";
          renderNodes(node.children, childWrap);
          group.appendChild(childWrap);
        }
        container.appendChild(group);
      }
    }

    renderNodes(visibleTree, frag);
    els.folderTree.innerHTML = "";
    els.folderTree.appendChild(frag);
  }

  function expandAncestors(cat, sub) {
    if (!cat) return;
    state.expandedNodes.add(cat);
    if (!sub) return;
    const parts = sub.split("/").filter(Boolean);
    let acc = "";
    for (const p of parts) {
      acc = acc ? `${acc}/${p}` : p;
      state.expandedNodes.add(`${cat}:::${acc}`);
    }
  }

  function selectFolder(cat, sub) {
    state.selectedCat = cat || "";
    state.selectedSub = sub || "";
    expandAncestors(state.selectedCat, state.selectedSub);
    renderFolderTree();
    renderQuickChips((state.raw && state.raw.cats) || []);
    resetScrollAndRender();
  }

  function populateDropdowns(books) {
    const fmtCounts = new Map();
    const langCounts = new Map();
    for (const b of books) {
      fmtCounts.set(b.fmt, (fmtCounts.get(b.fmt) || 0) + 1);
      langCounts.set(b.lang, (langCounts.get(b.lang) || 0) + 1);
    }

    const sortedFmts = [...fmtCounts.entries()].sort((a, b) => b[1] - a[1]);
    for (const [fmt, cnt] of sortedFmts) {
      const opt = document.createElement("option");
      opt.value = fmt;
      opt.textContent = `${fmt} (${cnt.toLocaleString()})`;
      els.formatFilter.appendChild(opt);
    }

    const sortedLangs = [...langCounts.entries()].sort((a, b) => b[1] - a[1]);
    for (const [lang, cnt] of sortedLangs) {
      const opt = document.createElement("option");
      opt.value = lang;
      opt.textContent = `${lang} (${cnt.toLocaleString()})`;
      els.languageFilter.appendChild(opt);
    }
  }

  function readUrlParams() {
    const params = new URLSearchParams(window.location.search);
    state.query = params.get("q") || "";
    state.selectedCat = params.get("category") || "";
    state.selectedSub = params.get("sub") || "";
    state.format = params.get("fmt") || "";
    state.language = params.get("lang") || "";
    state.coversOnly = params.get("covers") === "1";
    state.sort = params.get("sort") || "covers";

    els.searchInput.value = state.query;
    els.formatFilter.value = state.format;
    els.languageFilter.value = state.language;
    els.coversOnlyToggle.checked = state.coversOnly;
    els.sortSelect.value = state.sort;
    expandAncestors(state.selectedCat, state.selectedSub);
  }

  function syncUrlParams() {
    const params = new URLSearchParams();
    if (state.query.trim()) params.set("q", state.query.trim());
    if (state.selectedCat) params.set("category", state.selectedCat);
    if (state.selectedSub) params.set("sub", state.selectedSub);
    if (state.format) params.set("fmt", state.format);
    if (state.language) params.set("lang", state.language);
    if (state.coversOnly) params.set("covers", "1");
    if (state.sort && state.sort !== "covers") params.set("sort", state.sort);

    const qs = params.toString();
    window.history.replaceState(null, "", qs ? `${window.location.pathname}?${qs}` : window.location.pathname);
  }

  function renderBreadcrumbs() {
    const frag = document.createDocumentFragment();
    const homeBtn = document.createElement("button");
    homeBtn.type = "button";
    homeBtn.className = "crumb-btn";
    homeBtn.textContent = "All Resources";
    homeBtn.addEventListener("click", () => selectFolder("", ""));
    frag.appendChild(homeBtn);

    if (state.selectedCat) {
      frag.appendChild(document.createTextNode(" › "));
      if (!state.selectedSub) {
        const span = document.createElement("span");
        span.textContent = state.selectedCat;
        frag.appendChild(span);
      } else {
        const catBtn = document.createElement("button");
        catBtn.type = "button";
        catBtn.className = "crumb-btn";
        catBtn.textContent = state.selectedCat;
        catBtn.addEventListener("click", () => selectFolder(state.selectedCat, ""));
        frag.appendChild(catBtn);

        const parts = state.selectedSub.split("/").filter(Boolean);
        let acc = "";
        parts.forEach((p, idx) => {
          frag.appendChild(document.createTextNode(" › "));
          acc = acc ? `${acc}/${p}` : p;
          if (idx === parts.length - 1) {
            const span = document.createElement("span");
            span.textContent = p;
            frag.appendChild(span);
          } else {
            const targetSub = acc;
            const subBtn = document.createElement("button");
            subBtn.type = "button";
            subBtn.className = "crumb-btn";
            subBtn.textContent = p;
            subBtn.addEventListener("click", () => selectFolder(state.selectedCat, targetSub));
            frag.appendChild(subBtn);
          }
        });
      }
    }

    els.breadcrumbTrail.innerHTML = "";
    els.breadcrumbTrail.appendChild(frag);

    const roots = (state.raw && state.raw.drive_roots) || {};
    const rootDriveId = state.selectedCat ? roots[state.selectedCat] : "";
    els.openDriveFolderBtn.href = rootDriveId
      ? `https://drive.google.com/drive/folders/${rootDriveId}`
      : ROOT_DRIVE_URL;
    els.openDriveFolderBtn.textContent = state.selectedCat
      ? `Open ${state.selectedCat} ↗`
      : "Open Drive Root ↗";
  }

  /* ================= INFINITE SCROLL FILTERING & RENDERING ================= */

  function resetScrollAndRender() {
    const terms = state.query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const hasActiveFilter = Boolean(
      terms.length || state.selectedCat || state.selectedSub || state.format || state.language || state.coversOnly
    );

    els.clearSearchBtn.classList.toggle("hidden", !state.query);
    els.resetFiltersBtn.classList.toggle("hidden", !hasActiveFilter);
    updateDiscoverVisibility(hasActiveFilter);

    const out = [];
    for (const book of state.books) {
      if (state.selectedCat && book.cat !== state.selectedCat) continue;
      if (state.selectedSub) {
        if (book.sub !== state.selectedSub && !book.sub.startsWith(state.selectedSub + "/")) {
          continue;
        }
      }
      if (state.format && book.fmt !== state.format) continue;
      if (state.language && book.lang !== state.language) continue;
      if (state.coversOnly && !book.coverId) continue;

      if (terms.length) {
        let matched = true;
        for (const t of terms) {
          if (!book.searchBlob.includes(t)) {
            matched = false;
            break;
          }
        }
        if (!matched) continue;
      }
      out.push(book);
    }

    if (state.sort === "covers") {
      out.sort((a, b) => {
        const ca = a.coverId ? 1 : 0;
        const cb = b.coverId ? 1 : 0;
        if (ca !== cb) return cb - ca;
        return a.title.localeCompare(b.title, undefined, { sensitivity: "base" });
      });
    } else if (state.sort === "title") {
      out.sort((a, b) => a.title.localeCompare(b.title, undefined, { sensitivity: "base" }));
    } else if (state.sort === "size_desc") {
      out.sort((a, b) => b.size - a.size);
    } else if (state.sort === "size_asc") {
      out.sort((a, b) => a.size - b.size);
    }

    state.filtered = out;
    state.renderedCount = 0;

    syncUrlParams();
    renderBreadcrumbs();
    renderQuickChips((state.raw && state.raw.cats) || []);

    els.booksGrid.innerHTML = "";
    const total = state.filtered.length;
    els.resultCount.textContent = `${total.toLocaleString()} item${total === 1 ? "" : "s"}`;

    if (total === 0) {
      els.booksGrid.classList.add("hidden");
      els.emptyState.classList.remove("hidden");
      els.scrollFooter.classList.add("hidden");
      return;
    }

    els.emptyState.classList.add("hidden");
    els.booksGrid.classList.remove("hidden");
    appendNextBatch();
  }

  function appendNextBatch() {
    const total = state.filtered.length;
    if (state.renderedCount >= total) {
      updateScrollFooter();
      return;
    }

    const nextEnd = Math.min(total, state.renderedCount + BATCH_SIZE);
    const slice = state.filtered.slice(state.renderedCount, nextEnd);
    const frag = document.createDocumentFragment();
    for (const book of slice) {
      frag.appendChild(createBookCard(book));
    }
    els.booksGrid.appendChild(frag);
    state.renderedCount = nextEnd;
    updateScrollFooter();
  }

  function updateScrollFooter() {
    const total = state.filtered.length;
    if (total === 0) {
      els.scrollFooter.classList.add("hidden");
      return;
    }
    els.scrollFooter.classList.remove("hidden");
    els.scrollProgressText.textContent = `Showing ${state.renderedCount.toLocaleString()} of ${total.toLocaleString()} resources`;
    els.loadMoreBtn.classList.toggle("hidden", state.renderedCount >= total);
  }

  function createBookCard(book) {
    const card = document.createElement("article");
    card.className = "book-card";

    const isSaved = state.savedIds.has(book.id);
    const downloadUrl = `https://drive.google.com/uc?export=download&id=${encodeURIComponent(book.id)}`;
    const leafSub = book.sub ? book.sub.split("/").pop() : book.cat;

    const coverBox = document.createElement("div");
    coverBox.className = "cover-box";
    coverBox.innerHTML = `
      <div class="cover-fallback">
        <span class="fallback-cat">${escapeHtml(leafSub)}</span>
        <div class="fallback-title">${escapeHtml(book.title)}</div>
        <span class="fallback-author">${escapeHtml(book.author)}</span>
      </div>
      <span class="format-badge">${escapeHtml(book.fmt)}</span>
    `;

    const isImageDirect = ["JPG", "JPEG", "PNG"].includes(book.fmt.toUpperCase());
    const thumbId = book.coverId || (isImageDirect ? book.id : "");

    if (thumbId) {
      const img = document.createElement("img");
      img.alt = `${book.title} cover`;
      img.loading = "lazy";
      img.decoding = "async";
      img.referrerPolicy = "no-referrer";
      img.src = `https://drive.google.com/thumbnail?id=${encodeURIComponent(thumbId)}&sz=w400`;
      img.addEventListener("error", () => {
        if (!img.dataset.fallbackTried) {
          img.dataset.fallbackTried = "1";
          img.src = `https://lh3.googleusercontent.com/d/${encodeURIComponent(thumbId)}=w400`;
        } else {
          img.remove();
        }
      });
      coverBox.appendChild(img);
    }

    const likeBtn = document.createElement("button");
    likeBtn.type = "button";
    likeBtn.className = "card-like-btn" + (isSaved ? " saved" : "");
    likeBtn.title = isSaved ? "Remove from Saved" : "Save Book";
    likeBtn.textContent = isSaved ? "♥" : "♡";
    likeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleSaveBook(book);
      const nowSaved = state.savedIds.has(book.id);
      likeBtn.classList.toggle("saved", nowSaved);
      likeBtn.textContent = nowSaved ? "♥" : "♡";
    });
    coverBox.appendChild(likeBtn);
    coverBox.addEventListener("click", () => openReaderModal(book));

    const body = document.createElement("div");
    body.className = "card-body";

    const infoCol = document.createElement("div");
    infoCol.className = "card-info-col";

    const titleEl = document.createElement("h3");
    titleEl.className = "book-title";
    titleEl.textContent = book.title;
    titleEl.title = book.title;
    titleEl.addEventListener("click", () => openReaderModal(book));

    const authorEl = document.createElement("div");
    authorEl.className = "book-author";
    authorEl.textContent = book.author;
    authorEl.title = book.author;

    const metaRow = document.createElement("div");
    metaRow.className = "book-meta-row";
    metaRow.innerHTML = `
      <span class="cat-tag" title="${escapeHtml(book.cat + (book.sub ? " / " + book.sub : ""))}">${escapeHtml(leafSub)}</span>
      <span>${escapeHtml(formatSize(book.size))}</span>
    `;

    infoCol.appendChild(titleEl);
    infoCol.appendChild(authorEl);
    infoCol.appendChild(metaRow);

    const actions = document.createElement("div");
    actions.className = "card-actions";

    const readBtn = document.createElement("button");
    readBtn.type = "button";
    readBtn.className = "btn-read";
    readBtn.textContent = "Read";
    readBtn.addEventListener("click", () => openReaderModal(book));

    const dlLink = document.createElement("a");
    dlLink.className = "btn-download";
    dlLink.href = downloadUrl;
    dlLink.target = "_blank";
    dlLink.rel = "noopener noreferrer";
    dlLink.textContent = "⬇ Download";
    dlLink.addEventListener("click", () => {
      showToast(`Download started: ${book.title}`);
    });

    actions.appendChild(readBtn);
    actions.appendChild(dlLink);
    body.appendChild(infoCol);
    body.appendChild(actions);

    card.appendChild(coverBox);
    card.appendChild(body);
    return card;
  }

  /* ================= MODAL, SAVED DRAWER & INTERACTIONS ================= */

  function toggleSaveBook(book) {
    if (!book || !book.id) return;
    if (state.savedIds.has(book.id)) {
      state.savedIds.delete(book.id);
      showToast("Removed from Saved Books");
    } else {
      state.savedIds.add(book.id);
      showToast("Saved to Reading List");
    }
    persistSavedIds();
    updateSavedUI();
  }

  function updateSavedUI() {
    const count = state.savedIds.size;
    els.savedCountBadge.textContent = String(count);
    els.drawerSavedCount.textContent = String(count);
    if (state.activeModalBook) {
      const saved = state.savedIds.has(state.activeModalBook.id);
      els.modalSaveBtn.textContent = saved ? "♥ Saved" : "♡ Save";
    }
    if (!els.savedDrawer.classList.contains("hidden")) {
      renderSavedDrawer();
    }
  }

  function renderSavedDrawer() {
    const container = els.savedList;
    container.innerHTML = "";
    if (state.savedIds.size === 0) {
      container.innerHTML = '<div class="mono-muted" style="padding:1rem;text-align:center;">No saved books yet. Click ♡ on any cover card to bookmark it here.</div>';
      return;
    }

    const byId = new Map(state.books.map((b) => [b.id, b]));
    const frag = document.createDocumentFragment();
    for (const id of state.savedIds) {
      const book = byId.get(id);
      if (!book) continue;
      const item = document.createElement("div");
      item.className = "saved-item";
      const dlUrl = `https://drive.google.com/uc?export=download&id=${encodeURIComponent(book.id)}`;
      item.innerHTML = `
        <div>
          <div class="saved-item-title">${escapeHtml(book.title)}</div>
          <div class="saved-item-sub">${escapeHtml(book.author)} · ${escapeHtml(book.fmt)} · ${escapeHtml(formatSize(book.size))}</div>
        </div>
      `;

      const act = document.createElement("div");
      act.className = "saved-item-actions";

      const readBtn = document.createElement("button");
      readBtn.type = "button";
      readBtn.className = "btn-read";
      readBtn.textContent = "Read";
      readBtn.addEventListener("click", () => {
        closeSavedDrawer();
        openReaderModal(book);
      });

      const dlBtn = document.createElement("a");
      dlBtn.className = "btn-download";
      dlBtn.href = dlUrl;
      dlBtn.target = "_blank";
      dlBtn.rel = "noopener noreferrer";
      dlBtn.textContent = "⬇ Download";

      const rmBtn = document.createElement("button");
      rmBtn.type = "button";
      rmBtn.className = "bw-btn";
      rmBtn.textContent = "Remove";
      rmBtn.style.marginLeft = "auto";
      rmBtn.addEventListener("click", () => {
        toggleSaveBook(book);
      });

      act.appendChild(readBtn);
      act.appendChild(dlBtn);
      act.appendChild(rmBtn);
      item.appendChild(act);
      frag.appendChild(item);
    }
    container.appendChild(frag);
  }

  function openReaderModal(book) {
    state.activeModalBook = book;
    const previewUrl = `https://drive.google.com/file/d/${encodeURIComponent(book.id)}/preview`;
    const viewUrl = `https://drive.google.com/file/d/${encodeURIComponent(book.id)}/view`;
    const dlUrl = `https://drive.google.com/uc?export=download&id=${encodeURIComponent(book.id)}`;

    els.modalTitle.textContent = book.title;
    els.modalMeta.textContent = `${book.author} · ${book.cat}${book.sub ? " / " + book.sub : ""} · ${book.fmt} · ${formatSize(book.size)}`;
    els.modalDownloadBtn.href = dlUrl;
    els.modalDriveBtn.href = viewUrl;

    const saved = state.savedIds.has(book.id);
    els.modalSaveBtn.textContent = saved ? "♥ Saved" : "♡ Save";

    els.readerSpinner.classList.remove("hidden");
    els.readerIframe.src = previewUrl;
    els.readerModal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
    setTimeout(() => els.readerSpinner.classList.add("hidden"), 5000);
  }

  function closeReaderModal() {
    els.readerModal.classList.add("hidden");
    els.readerIframe.src = "about:blank";
    state.activeModalBook = null;
    document.body.style.overflow = "";
  }

  function openSavedDrawer() {
    els.savedDrawer.classList.remove("hidden");
    els.sidebarBackdrop.classList.remove("hidden");
    renderSavedDrawer();
  }

  function closeSavedDrawer() {
    els.savedDrawer.classList.add("hidden");
    if (!els.folderSidebar.classList.contains("open")) {
      els.sidebarBackdrop.classList.add("hidden");
    }
  }

  function openMobileSidebar() {
    if (window.innerWidth > 960) {
      const collapsed = els.appShell.classList.toggle("sidebar-collapsed");
      els.folderSidebar.classList.toggle("hidden", collapsed);
      return;
    }
    els.folderSidebar.classList.add("open");
    els.sidebarBackdrop.classList.remove("hidden");
  }

  function closeMobileSidebar() {
    els.folderSidebar.classList.remove("open");
    if (els.savedDrawer.classList.contains("hidden")) {
      els.sidebarBackdrop.classList.add("hidden");
    }
  }

  function scrollToCatalog() {
    els.searchInput.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function resetAllFilters() {
    state.selectedCat = "";
    state.selectedSub = "";
    state.query = "";
    state.format = "";
    state.language = "";
    state.coversOnly = false;
    state.sort = "covers";

    els.searchInput.value = "";
    els.formatFilter.value = "";
    els.languageFilter.value = "";
    els.coversOnlyToggle.checked = false;
    els.sortSelect.value = "covers";

    renderFolderTree();
    renderQuickChips((state.raw && state.raw.cats) || []);
    resetScrollAndRender();
  }

  function wireEvents() {
    let searchTimer = null;
    els.searchInput.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        state.query = els.searchInput.value;
        resetScrollAndRender();
      }, 140);
    });

    els.clearSearchBtn.addEventListener("click", () => {
      state.query = "";
      els.searchInput.value = "";
      resetScrollAndRender();
      els.searchInput.focus();
    });

    els.formatFilter.addEventListener("change", () => {
      state.format = els.formatFilter.value;
      resetScrollAndRender();
    });

    els.languageFilter.addEventListener("change", () => {
      state.language = els.languageFilter.value;
      resetScrollAndRender();
    });

    els.sortSelect.addEventListener("change", () => {
      state.sort = els.sortSelect.value;
      resetScrollAndRender();
    });

    els.coversOnlyToggle.addEventListener("change", () => {
      state.coversOnly = els.coversOnlyToggle.checked;
      resetScrollAndRender();
    });

    els.gridViewBtn.addEventListener("click", () => applyViewMode("grid"));
    els.listViewBtn.addEventListener("click", () => applyViewMode("list"));
    els.resetFiltersBtn.addEventListener("click", resetAllFilters);
    els.emptyResetBtn.addEventListener("click", resetAllFilters);

    els.allBooksBtn.addEventListener("click", () => {
      selectFolder("", "");
      closeMobileSidebar();
    });

    els.folderSearchInput.addEventListener("input", () => {
      state.folderQuery = els.folderSearchInput.value;
      renderFolderTree();
    });

    els.toggleDashboardBtn.addEventListener("click", () => {
      els.analyticsDashboard.classList.toggle("hidden");
    });

    els.toggleDiscoverBtn.addEventListener("click", () => {
      state.discoverManualHidden = !state.discoverManualHidden;
      updateDiscoverVisibility(false);
    });

    els.kpiEduBtn.addEventListener("click", () => {
      selectFolder("Education & Textbooks", "");
      scrollToCatalog();
    });

    els.surpriseMeBtn.addEventListener("click", () => {
      const pool = state.filtered.length ? state.filtered : state.books;
      if (!pool.length) return;
      const pick = pool[Math.floor(Math.random() * pool.length)];
      showToast(`Discovered: ${pick.title}`);
      openReaderModal(pick);
    });

    els.themeToggleBtn.addEventListener("click", () => {
      const curr = document.documentElement.getAttribute("data-theme") || "dark";
      applyTheme(curr === "dark" ? "light" : "dark");
    });

    els.loadMoreBtn.addEventListener("click", appendNextBatch);

    els.backToTopBtn.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

    window.addEventListener(
      "scroll",
      () => {
        els.backToTopBtn.classList.toggle("hidden", window.scrollY < 500);
      },
      { passive: true }
    );

    if ("IntersectionObserver" in window) {
      scrollObserver = new IntersectionObserver(
        (entries) => {
          if (entries.some((e) => e.isIntersecting) && state.renderedCount < state.filtered.length) {
            appendNextBatch();
          }
        },
        { rootMargin: "320px 0px" }
      );
      scrollObserver.observe(els.scrollSentinel);
    }

    els.mobileMenuBtn.addEventListener("click", openMobileSidebar);
    els.closeSidebarBtn.addEventListener("click", closeMobileSidebar);
    els.openSavedBtn.addEventListener("click", openSavedDrawer);
    els.closeSavedBtn.addEventListener("click", closeSavedDrawer);
    els.sidebarBackdrop.addEventListener("click", () => {
      closeMobileSidebar();
      closeSavedDrawer();
    });

    els.clearSavedBtn.addEventListener("click", () => {
      if (state.savedIds.size === 0) return;
      state.savedIds.clear();
      persistSavedIds();
      updateSavedUI();
      showToast("Cleared all saved books");
    });

    els.modalCloseBtn.addEventListener("click", closeReaderModal);
    els.modalBackdrop.addEventListener("click", closeReaderModal);
    els.readerIframe.addEventListener("load", () => {
      els.readerSpinner.classList.add("hidden");
    });

    els.modalSaveBtn.addEventListener("click", () => {
      if (!state.activeModalBook) return;
      toggleSaveBook(state.activeModalBook);
    });

    els.modalDownloadBtn.addEventListener("click", () => {
      if (state.activeModalBook) showToast(`Download started: ${state.activeModalBook.title}`);
    });

    els.modalCopyBtn.addEventListener("click", async () => {
      if (!state.activeModalBook) return;
      const url = `https://drive.google.com/file/d/${encodeURIComponent(state.activeModalBook.id)}/view`;
      try {
        await navigator.clipboard.writeText(url);
        showToast("Drive link copied");
      } catch {
        showToast(url);
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (!els.readerModal.classList.contains("hidden")) closeReaderModal();
        else if (!els.savedDrawer.classList.contains("hidden")) closeSavedDrawer();
        else if (els.folderSidebar.classList.contains("open")) closeMobileSidebar();
      } else if (
        e.key === "/" &&
        document.activeElement &&
        !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)
      ) {
        e.preventDefault();
        els.searchInput.focus();
      }
    });
  }

  async function init() {
    [
      "mobileMenuBtn", "closeSidebarBtn", "folderSidebar", "sidebarBackdrop",
      "toggleDashboardBtn", "analyticsDashboard", "dashboardUpdatedAt",
      "kpiTotalBooks", "kpiTotalSize", "kpiCoversPct", "kpiCoversBar", "kpiCoversCount",
      "kpiEduBtn", "kpiEduCount", "kpiAuthors", "kpiSubcats",
      "chartCategories", "chartEducation", "chartFormatsSvg", "chartFormatsLegend", "chartLanguages",
      "discoverSection", "discoverRails", "toggleDiscoverBtn", "surpriseMeBtn", "quickChips",
      "openSavedBtn", "savedCountBadge", "savedDrawer", "drawerSavedCount",
      "clearSavedBtn", "closeSavedBtn", "savedList",
      "themeToggleBtn", "themeIcon",
      "allBooksBtn", "allBooksCount", "folderSearchInput", "folderTree",
      "searchInput", "clearSearchBtn", "formatFilter", "languageFilter",
      "sortSelect", "coversOnlyToggle", "gridViewBtn", "listViewBtn", "resetFiltersBtn",
      "breadcrumbTrail", "resultCount", "openDriveFolderBtn",
      "loadingState", "booksGrid", "emptyState", "emptyResetBtn",
      "scrollFooter", "scrollProgressText", "loadMoreBtn", "scrollSentinel", "backToTopBtn",
      "readerModal", "modalBackdrop", "modalTitle", "modalMeta",
      "modalSaveBtn", "modalDownloadBtn", "modalDriveBtn", "modalCopyBtn",
      "modalCloseBtn", "readerSpinner", "readerIframe", "toastContainer"
    ].forEach((id) => {
      els[id] = $(id);
    });
    els.appShell = document.querySelector(".app-shell");

    initTheme();
    applyViewMode(state.viewMode);
    wireEvents();
    updateSavedUI();

    try {
      const resp = await fetch("books.json");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      state.raw = data;
      state.books = inflateCatalog(data);

      els.allBooksCount.textContent = (data.total || state.books.length).toLocaleString();
      renderDashboard(data, state.books);
      renderDiscoveryRails(state.books);

      state.tree = buildFolderTree(state.books, data.cats || []);
      populateDropdowns(state.books);
      readUrlParams();
      renderQuickChips(data.cats || []);
      renderFolderTree();

      els.loadingState.classList.add("hidden");
      resetScrollAndRender();
    } catch (err) {
      els.loadingState.classList.add("hidden");
      els.resultCount.textContent = "Failed to load catalog";
      els.emptyState.classList.remove("hidden");
      els.emptyState.querySelector("h3").textContent = "Unable to load books.json";
      els.emptyState.querySelector("p").textContent = String(err);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();

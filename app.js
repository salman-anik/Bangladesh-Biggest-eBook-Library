(() => {
  "use strict";

  const PAGE_SIZE = 48;
  const ROOT_DRIVE_URL = "https://drive.google.com/drive/folders/1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq";
  const STORAGE_SAVED_KEY = "bd_ebook_saved_v1";
  const STORAGE_THEME_KEY = "bd_ebook_theme_v1";
  const STORAGE_VIEW_KEY = "bd_ebook_view_v1";

  const state = {
    raw: null,
    books: [],
    filtered: [],
    tree: [],
    selectedCat: "",
    selectedSub: "",
    query: "",
    format: "",
    language: "",
    sort: "covers",
    coversOnly: false,
    folderQuery: "",
    viewMode: localStorage.getItem(STORAGE_VIEW_KEY) || "grid",
    page: 1,
    expandedNodes: new Set(),
    savedIds: new Set(loadSavedIds()),
    activeModalBook: null,
  };

  const els = {};

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
      // Ignore storage quota errors
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
    setTimeout(() => {
      toast.remove();
    }, 2600);
  }

  function initTheme() {
    const saved = localStorage.getItem(STORAGE_THEME_KEY) || "dark";
    applyTheme(saved);
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    if (els.themeIcon) {
      els.themeIcon.textContent = theme === "dark" ? "☀️" : "🌙";
    }
    try {
      localStorage.setItem(STORAGE_THEME_KEY, theme);
    } catch {
      // Ignore
    }
  }

  function applyViewMode(mode) {
    state.viewMode = mode === "list" ? "list" : "grid";
    if (els.booksGrid) {
      els.booksGrid.classList.toggle("list-view", state.viewMode === "list");
    }
    if (els.gridViewBtn && els.listViewBtn) {
      els.gridViewBtn.classList.toggle("active", state.viewMode === "grid");
      els.listViewBtn.classList.toggle("active", state.viewMode === "list");
    }
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
        searchBlob: `${title} ${author} ${cat} ${sub} ${series}`.toLowerCase(),
      };
    });
  }

  function buildFolderTree(books, canonicalCats) {
    const rootMap = new Map();

    function ensureRoot(cat) {
      if (!rootMap.has(cat)) {
        rootMap.set(cat, {
          name: cat,
          cat,
          sub: "",
          pathKey: cat,
          count: 0,
          children: new Map(),
        });
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
        arr.sort((a, b) =>
          a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" })
        );
      }
      return arr.map((node) => ({
        ...node,
        children: toSortedArray(node.children, false),
      }));
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

    const isAllSelected = !state.selectedCat && !state.selectedSub;
    els.allBooksBtn.classList.toggle("active", isAllSelected);

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
        chevron.className = "tree-chevron" +
          (hasChildren ? (isExpanded ? " expanded" : "") : " leaf-spacer");
        chevron.textContent = "▶";
        chevron.setAttribute("aria-label", hasChildren ? "Toggle subfolder" : "");
        if (hasChildren) {
          chevron.addEventListener("click", (e) => {
            e.stopPropagation();
            if (state.expandedNodes.has(node.pathKey)) {
              state.expandedNodes.delete(node.pathKey);
            } else {
              state.expandedNodes.add(node.pathKey);
            }
            renderFolderTree();
          });
        }

        const label = document.createElement("span");
        label.className = "tree-label";
        label.textContent = node.name;
        label.title = `${node.name} (${node.count.toLocaleString()} books)`;

        const chip = document.createElement("span");
        chip.className = "count-chip";
        chip.textContent = node.count.toLocaleString();

        row.appendChild(chevron);
        row.appendChild(label);
        row.appendChild(chip);

        row.addEventListener("click", () => {
          selectFolder(node.cat, node.sub);
          if (hasChildren) {
            state.expandedNodes.add(node.pathKey);
          }
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
    state.page = 1;
    expandAncestors(state.selectedCat, state.selectedSub);
    renderFolderTree();
    applyFiltersAndRender();
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
    const q = params.get("q") || "";
    const cat = params.get("category") || "";
    const sub = params.get("sub") || "";
    const fmt = params.get("fmt") || "";
    const lang = params.get("lang") || "";
    const covers = params.get("covers") === "1";
    const sort = params.get("sort") || "covers";

    state.query = q;
    state.selectedCat = cat;
    state.selectedSub = sub;
    state.format = fmt;
    state.language = lang;
    state.coversOnly = covers;
    state.sort = sort;

    els.searchInput.value = q;
    els.formatFilter.value = fmt;
    els.languageFilter.value = lang;
    els.coversOnlyToggle.checked = covers;
    els.sortSelect.value = sort;
    expandAncestors(cat, sub);
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
    const newUrl = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
    window.history.replaceState(null, "", newUrl);
  }

  function renderBreadcrumbs() {
    const frag = document.createDocumentFragment();
    const homeBtn = document.createElement("button");
    homeBtn.type = "button";
    homeBtn.className = "crumb-btn";
    homeBtn.textContent = "All Books";
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
      ? `📂 Open ${state.selectedCat} in Drive`
      : "📂 Open Root in Drive";
  }

  function applyFiltersAndRender() {
    const terms = state.query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const hasActiveFilter = Boolean(
      terms.length || state.selectedCat || state.selectedSub || state.format || state.language || state.coversOnly
    );

    els.clearSearchBtn.classList.toggle("hidden", !state.query);
    els.resetFiltersBtn.classList.toggle("hidden", !hasActiveFilter);

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
    const totalPages = Math.max(1, Math.ceil(out.length / PAGE_SIZE));
    if (state.page > totalPages) state.page = totalPages;

    syncUrlParams();
    renderBreadcrumbs();
    renderResults();
    renderPagination(totalPages);
  }

  function renderResults() {
    const total = state.filtered.length;
    els.resultCount.textContent = `${total.toLocaleString()} book${total === 1 ? "" : "s"}`;

    if (total === 0) {
      els.booksGrid.classList.add("hidden");
      els.emptyState.classList.remove("hidden");
      els.paginationBar.classList.add("hidden");
      return;
    }

    els.emptyState.classList.add("hidden");
    els.booksGrid.classList.remove("hidden");

    const start = (state.page - 1) * PAGE_SIZE;
    const slice = state.filtered.slice(start, start + PAGE_SIZE);
    const frag = document.createDocumentFragment();

    for (const book of slice) {
      frag.appendChild(createBookCard(book));
    }

    els.booksGrid.innerHTML = "";
    els.booksGrid.appendChild(frag);
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

    if (book.coverId) {
      const img = document.createElement("img");
      img.alt = `${book.title} cover`;
      img.loading = "lazy";
      img.decoding = "async";
      img.referrerPolicy = "no-referrer";
      img.style.position = "relative";
      img.style.zIndex = "1";
      img.src = `https://drive.google.com/thumbnail?id=${encodeURIComponent(book.coverId)}&sz=w400`;
      img.addEventListener("error", () => {
        if (!img.dataset.fallbackTried) {
          img.dataset.fallbackTried = "1";
          img.src = `https://lh3.googleusercontent.com/d/${encodeURIComponent(book.coverId)}=w400`;
        } else {
          img.remove();
        }
      });
      coverBox.appendChild(img);
    }

    const likeBtn = document.createElement("button");
    likeBtn.type = "button";
    likeBtn.className = "card-like-btn" + (isSaved ? " saved" : "");
    likeBtn.style.zIndex = "2";
    likeBtn.title = isSaved ? "Remove from Saved" : "Save / Like Book";
    likeBtn.textContent = isSaved ? "❤️" : "🤍";
    likeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleSaveBook(book);
      const nowSaved = state.savedIds.has(book.id);
      likeBtn.classList.toggle("saved", nowSaved);
      likeBtn.textContent = nowSaved ? "❤️" : "🤍";
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
    readBtn.innerHTML = "📖 Read";
    readBtn.addEventListener("click", () => openReaderModal(book));

    const dlLink = document.createElement("a");
    dlLink.className = "btn-download";
    dlLink.href = downloadUrl;
    dlLink.target = "_blank";
    dlLink.rel = "noopener noreferrer";
    dlLink.innerHTML = "⬇️ Download";
    dlLink.addEventListener("click", () => {
      showToast(`Starting download: ${book.title}`);
    });

    actions.appendChild(readBtn);
    actions.appendChild(dlLink);

    body.appendChild(infoCol);
    body.appendChild(actions);

    card.appendChild(coverBox);
    card.appendChild(body);
    return card;
  }

  function renderPagination(totalPages) {
    if (totalPages <= 1) {
      els.paginationBar.classList.add("hidden");
      return;
    }
    els.paginationBar.classList.remove("hidden");
    const frag = document.createDocumentFragment();

    function addBtn(label, targetPage, disabled = false, active = false) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "page-btn" + (active ? " active" : "");
      btn.textContent = label;
      btn.disabled = disabled;
      if (!disabled && !active) {
        btn.addEventListener("click", () => {
          state.page = targetPage;
          renderResults();
          renderPagination(totalPages);
          window.scrollTo({ top: 0, behavior: "smooth" });
        });
      }
      frag.appendChild(btn);
    }

    addBtn("« First", 1, state.page === 1);
    addBtn("‹ Prev", Math.max(1, state.page - 1), state.page === 1);

    const windowSize = 2;
    const startP = Math.max(1, state.page - windowSize);
    const endP = Math.min(totalPages, state.page + windowSize);

    if (startP > 1) {
      addBtn("1", 1);
      if (startP > 2) {
        const span = document.createElement("span");
        span.textContent = "…";
        frag.appendChild(span);
      }
    }

    for (let p = startP; p <= endP; p++) {
      addBtn(String(p), p, false, p === state.page);
    }

    if (endP < totalPages) {
      if (endP < totalPages - 1) {
        const span = document.createElement("span");
        span.textContent = "…";
        frag.appendChild(span);
      }
      addBtn(String(totalPages), totalPages);
    }

    addBtn("Next ›", Math.min(totalPages, state.page + 1), state.page === totalPages);
    addBtn("Last »", totalPages, state.page === totalPages);

    els.paginationBar.innerHTML = "";
    els.paginationBar.appendChild(frag);
  }

  function toggleSaveBook(book) {
    if (!book || !book.id) return;
    if (state.savedIds.has(book.id)) {
      state.savedIds.delete(book.id);
      showToast("Removed from Saved Books");
    } else {
      state.savedIds.add(book.id);
      showToast("Saved to Reading List ❤️");
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
      els.modalSaveBtn.textContent = saved ? "❤️ Saved" : "🤍 Save";
    }

    if (!els.savedDrawer.classList.contains("hidden")) {
      renderSavedDrawer();
    }
  }

  function renderSavedDrawer() {
    const container = els.savedList;
    container.innerHTML = "";

    if (state.savedIds.size === 0) {
      container.innerHTML = '<div class="saved-item-sub" style="padding:1rem;text-align:center;">No saved books yet. Click ❤️ on any book cover to save it here.</div>';
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
        <div class="saved-item-top">
          <div>
            <div class="saved-item-title">${escapeHtml(book.title)}</div>
            <div class="saved-item-sub">${escapeHtml(book.author)} · ${escapeHtml(book.fmt)} · ${escapeHtml(formatSize(book.size))}</div>
          </div>
        </div>
      `;

      const act = document.createElement("div");
      act.className = "saved-item-actions";

      const readBtn = document.createElement("button");
      readBtn.type = "button";
      readBtn.className = "btn-read";
      readBtn.textContent = "📖 Read";
      readBtn.addEventListener("click", () => {
        closeSavedDrawer();
        openReaderModal(book);
      });

      const dlBtn = document.createElement("a");
      dlBtn.className = "btn-download";
      dlBtn.href = dlUrl;
      dlBtn.target = "_blank";
      dlBtn.rel = "noopener noreferrer";
      dlBtn.textContent = "⬇️ Download";

      const rmBtn = document.createElement("button");
      rmBtn.type = "button";
      rmBtn.className = "btn-text";
      rmBtn.textContent = "Remove";
      rmBtn.style.marginLeft = "auto";
      rmBtn.addEventListener("click", () => {
        toggleSaveBook(book);
        renderResults();
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
    els.modalSaveBtn.textContent = saved ? "❤️ Saved" : "🤍 Save";

    els.readerSpinner.classList.remove("hidden");
    els.readerIframe.src = previewUrl;
    els.readerModal.classList.remove("hidden");
    document.body.style.overflow = "hidden";

    setTimeout(() => {
      els.readerSpinner.classList.add("hidden");
    }, 5500);
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
    els.folderSidebar.classList.add("open");
    els.sidebarBackdrop.classList.remove("hidden");
  }

  function closeMobileSidebar() {
    els.folderSidebar.classList.remove("open");
    if (els.savedDrawer.classList.contains("hidden")) {
      els.sidebarBackdrop.classList.add("hidden");
    }
  }

  function resetAllFilters() {
    state.selectedCat = "";
    state.selectedSub = "";
    state.query = "";
    state.format = "";
    state.language = "";
    state.coversOnly = false;
    state.sort = "covers";
    state.page = 1;

    els.searchInput.value = "";
    els.formatFilter.value = "";
    els.languageFilter.value = "";
    els.coversOnlyToggle.checked = false;
    els.sortSelect.value = "covers";

    renderFolderTree();
    applyFiltersAndRender();
  }

  function wireEvents() {
    let searchTimer = null;
    els.searchInput.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        state.query = els.searchInput.value;
        state.page = 1;
        applyFiltersAndRender();
      }, 140);
    });

    els.clearSearchBtn.addEventListener("click", () => {
      state.query = "";
      els.searchInput.value = "";
      state.page = 1;
      applyFiltersAndRender();
      els.searchInput.focus();
    });

    els.formatFilter.addEventListener("change", () => {
      state.format = els.formatFilter.value;
      state.page = 1;
      applyFiltersAndRender();
    });

    els.languageFilter.addEventListener("change", () => {
      state.language = els.languageFilter.value;
      state.page = 1;
      applyFiltersAndRender();
    });

    els.sortSelect.addEventListener("change", () => {
      state.sort = els.sortSelect.value;
      state.page = 1;
      applyFiltersAndRender();
    });

    els.coversOnlyToggle.addEventListener("change", () => {
      state.coversOnly = els.coversOnlyToggle.checked;
      state.page = 1;
      applyFiltersAndRender();
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

    els.themeToggleBtn.addEventListener("click", () => {
      const curr = document.documentElement.getAttribute("data-theme") || "dark";
      applyTheme(curr === "dark" ? "light" : "dark");
    });

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
      renderResults();
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
      renderResults();
    });

    els.modalDownloadBtn.addEventListener("click", () => {
      if (state.activeModalBook) {
        showToast(`Starting download: ${state.activeModalBook.title}`);
      }
    });

    els.modalCopyBtn.addEventListener("click", async () => {
      if (!state.activeModalBook) return;
      const url = `https://drive.google.com/file/d/${encodeURIComponent(state.activeModalBook.id)}/view`;
      try {
        await navigator.clipboard.writeText(url);
        showToast("Drive link copied to clipboard");
      } catch {
        showToast("Link: " + url);
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (!els.readerModal.classList.contains("hidden")) {
          closeReaderModal();
        } else if (!els.savedDrawer.classList.contains("hidden")) {
          closeSavedDrawer();
        } else if (els.folderSidebar.classList.contains("open")) {
          closeMobileSidebar();
        }
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
      "openSavedBtn", "savedCountBadge", "savedDrawer", "drawerSavedCount",
      "clearSavedBtn", "closeSavedBtn", "savedList",
      "themeToggleBtn", "themeIcon",
      "statBooks", "statSize", "statCovers", "statFolders", "statAuthors",
      "allBooksBtn", "allBooksCount", "folderSearchInput", "folderTree",
      "searchInput", "clearSearchBtn", "formatFilter", "languageFilter",
      "sortSelect", "coversOnlyToggle", "gridViewBtn", "listViewBtn", "resetFiltersBtn",
      "breadcrumbTrail", "resultCount", "openDriveFolderBtn",
      "loadingState", "booksGrid", "emptyState", "emptyResetBtn", "paginationBar",
      "readerModal", "modalBackdrop", "modalTitle", "modalMeta",
      "modalSaveBtn", "modalDownloadBtn", "modalDriveBtn", "modalCopyBtn",
      "modalCloseBtn", "readerSpinner", "readerIframe", "toastContainer"
    ].forEach((id) => {
      els[id] = $(id);
    });

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

      els.statBooks.textContent = (data.total || state.books.length).toLocaleString();
      els.allBooksCount.textContent = (data.total || state.books.length).toLocaleString();
      els.statSize.textContent = formatSize(data.total_bytes || 0);
      els.statCovers.textContent = (data.covers_count || 0).toLocaleString();
      els.statFolders.textContent = String(Object.keys(data.drive_roots || {}).length || 9);
      els.statAuthors.textContent = `${(data.authors_count || 0).toLocaleString()}+`;

      state.tree = buildFolderTree(state.books, data.cats || []);
      populateDropdowns(state.books);
      readUrlParams();
      renderFolderTree();
      els.loadingState.classList.add("hidden");
      applyFiltersAndRender();
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

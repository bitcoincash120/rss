const scheduleEl = document.getElementById("schedule");
const scheduleHint = document.getElementById("schedule-hint");
const form = document.getElementById("import-form");
const importBtn = document.getElementById("import-btn");
const statusEl = document.getElementById("status");
const bodyEl = document.getElementById("import-body");
const selectAll = document.getElementById("select-all");
const logEl = document.getElementById("import-log");
const progressEl = document.getElementById("progress");
const progressFill = progressEl ? progressEl.querySelector("span") : null;
const styleEl = document.getElementById("style");
const previewDialog = document.getElementById("import-preview");
const previewBody = document.getElementById("import-preview-body");

let ideas = [];
let busy = false;
let openPreviewRow = 0;
let previewRun = 0;

const STYLE_KEY = "import-style";
const randomEl = document.getElementById("random-style");
const STYLE_CODES = styleEl ? [...styleEl.options].map((option) => option.value) : ["blue"];
const randomOn = () => Boolean(randomEl && randomEl.checked);
const baseStyle = () => (styleEl && styleEl.value) || "blue";
const pickRandomStyle = () => STYLE_CODES[Math.floor(Math.random() * STYLE_CODES.length)] || "blue";
const styleFor = (idea) => (randomOn() ? (idea && idea.randomStyle) || baseStyle() : baseStyle());
const currentStyle = baseStyle;

const assignRandomStyles = () => {
  ideas.forEach((idea) => {
    idea.randomStyle = pickRandomStyle();
  });
};

const paintStyleBadges = () => {
  document.querySelectorAll("#import-body tr[data-row]").forEach((tr) => {
    const badge = tr.querySelector("[data-style-badge]");
    if (!badge) return;
    const idea = ideaByRow(tr.dataset.row);
    badge.hidden = !randomOn();
    badge.textContent = randomOn() ? styleFor(idea) : "";
  });
};

const escapeHtml = (value) =>
  String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const hooppyTokenValue = () =>
  ((window.hooppyTokenStore && window.hooppyTokenStore.read()) || "").trim();

const siteBase = () => {
  const dir = location.pathname.replace(/[^/]+$/, "") || "/";
  return `${location.origin}${dir}`.replace(/\/$/, "");
};

const setStatus = (text, kind) => {
  if (!statusEl) return;
  statusEl.textContent = text;
  statusEl.className = `status${kind ? " " + kind : ""}`;
};

const setScheduleHint = (text, kind) => {
  if (!scheduleHint) return;
  scheduleHint.textContent = text;
  scheduleHint.classList.toggle("err", kind === "err");
};

const postsCountLabel = (count) => {
  const n = Number(count) || 0;
  const n10 = n % 10;
  const n100 = n % 100;
  if (n10 === 1 && n100 !== 11) return `${n} пост`;
  if (n10 >= 2 && n10 <= 4 && (n100 < 12 || n100 > 14)) return `${n} поста`;
  return `${n} постов`;
};

const selectedBoxes = () => [...document.querySelectorAll('#import-body input[name="row"]:checked')];

const syncUi = () => {
  const boxes = [...document.querySelectorAll('#import-body input[name="row"]')];
  const selected = selectedBoxes();
  if (selectAll) {
    selectAll.checked = Boolean(boxes.length) && boxes.every((box) => box.checked);
    selectAll.indeterminate = boxes.some((box) => box.checked) && !selectAll.checked;
  }
  if (importBtn) {
    importBtn.disabled = busy || !scheduleEl.value || !selected.length;
  }
  if (styleEl) styleEl.disabled = busy || randomOn();
  if (randomEl) randomEl.disabled = busy;
};

const appendLog = (text, kind) => {
  if (!logEl) return;
  logEl.hidden = false;
  const line = document.createElement("div");
  if (kind) line.className = kind;
  line.textContent = text;
  logEl.appendChild(line);
  logEl.scrollTop = logEl.scrollHeight;
};

const setProgress = (index, total) => {
  if (!progressEl || !progressFill) return;
  progressEl.hidden = false;
  progressEl.classList.add("is-on");
  const pct = total ? Math.round((index / total) * 100) : 0;
  progressFill.style.width = `${pct}%`;
};

const bindCarousel = (stage) => {
  const slides = [...stage.querySelectorAll("img")];
  if (slides.length < 2) return;
  let i = 0;
  const count = stage.querySelector("[data-count]");
  const show = (next) => {
    i = (next + slides.length) % slides.length;
    slides.forEach((img, idx) => img.classList.toggle("is-on", idx === i));
    if (count) count.textContent = String(i + 1);
  };
  stage.querySelectorAll("[data-dir]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      show(i + Number(btn.dataset.dir));
    });
  });
  stage.querySelectorAll("[data-go]").forEach((dot) => {
    dot.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      show(Number(dot.dataset.go));
    });
  });
};

const ideaByRow = (row) => ideas.find((item) => Number(item.row) === Number(row));

const carouselMarkup = (images, title) => {
  if (!images.length) return '<p class="hint">Карточки ещё собираются…</p>';
  const nav =
    images.length > 1
      ? `<button type="button" class="nav prev" data-dir="-1" aria-label="Предыдущая карточка">‹</button>
         <button type="button" class="nav next" data-dir="1" aria-label="Следующая карточка">›</button>
         <div class="dots">${images
           .map(
             (_, idx) =>
               `<button type="button" class="dot${idx === 0 ? " is-on" : ""}" data-go="${idx}" aria-label="Карточка ${idx + 1}"></button>`
           )
           .join("")}</div>
         <p class="count"><span data-count>1</span> / ${images.length}</p>`
      : "";
  const slides = images
    .map(
      (src, idx) =>
        `<img${idx === 0 ? ' class="is-on"' : ""} src="${escapeHtml(src)}" alt="${escapeHtml(title)}">`
    )
    .join("");
  return `<div class="stage" data-carousel>${slides}${nav}</div>`;
};

const fillPreviewDialog = (idea, images) => {
  if (!previewBody) return;
  previewBody.innerHTML = `
    <tr><th>Заголовок</th><td>${escapeHtml(idea.title)}</td></tr>
    <tr><th>Карточки</th><td>${carouselMarkup(images || [], idea.title)}</td></tr>
  `;
  const stage = previewBody.querySelector("[data-carousel]");
  if (stage) bindCarousel(stage);
};

const closePreview = () => {
  openPreviewRow = 0;
  if (previewDialog && previewDialog.open) previewDialog.close();
};

const openPreview = async (row) => {
  const idea = ideaByRow(row);
  if (!idea || !previewDialog || typeof previewDialog.showModal !== "function") return;
  openPreviewRow = Number(idea.row);
  fillPreviewDialog(idea, idea.imagesStyle === styleFor(idea) ? idea.images || [] : []);
  if (!previewDialog.open) previewDialog.showModal();
  const style = styleFor(idea);
  if (idea.images && idea.imagesStyle === style) return;
  fillPreviewDialog(idea, []);
  try {
    const res = await fetch(
      `api/import/preview?row=${idea.row}&style=${encodeURIComponent(style)}`,
      { cache: "no-store" }
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Не собрались карточки");
    idea.images = data.images || [];
    idea.imagesStyle = style;
    paintPreview(idea.row, idea.images);
    if (openPreviewRow === Number(idea.row)) fillPreviewDialog(idea, idea.images);
  } catch (error) {
    if (openPreviewRow === Number(idea.row) && previewBody) {
      previewBody.innerHTML = `<tr><th>Ошибка</th><td>${escapeHtml(error.message || "Не собрались карточки")}</td></tr>`;
    }
  }
};

const bindRow = (tr, idea) => {
  tr.tabIndex = 0;
  tr.setAttribute("role", "button");
  const open = () => openPreview(idea.row);
  tr.addEventListener("click", (event) => {
    if (event.target.closest("[data-stop], input, button, a, label.check")) return;
    open();
  });
  tr.addEventListener("keydown", (event) => {
    if (event.target.closest("input, button, a")) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      open();
    }
  });
};

const rowHtml = (idea, index) => {
  const title = idea.title || "";
  const slides = Number(idea.slides) || 1;
  const tr = document.createElement("tr");
  tr.className = "row";
  tr.dataset.row = String(idea.row);
  tr.innerHTML = `
    <td class="col-check" data-stop>
      <label class="check">
        <input type="checkbox" name="row" value="${idea.row}" aria-label="Выбрать ${escapeHtml(title)}" checked>
      </label>
    </td>
    <td class="col-num">${index}</td>
    <td class="col-thumb"><div class="import-ph" data-preview>Карточки…</div></td>
    <td class="col-title">${escapeHtml(title)} <code class="style-badge" data-style-badge hidden></code></td>
    <td class="col-count">${slides}</td>
    <td class="col-num">${idea.row}</td>
  `;
  const box = tr.querySelector('input[name="row"]');
  box.addEventListener("click", (event) => event.stopPropagation());
  box.addEventListener("change", syncUi);
  bindRow(tr, idea);
  return tr;
};

const fillTable = (list) => {
  bodyEl.innerHTML = "";
  if (!list.length) {
    bodyEl.innerHTML = '<tr><td colspan="6">Нет черновиков в Google Таблице. Добавьте строки со статусом не «импортирован».</td></tr>';
    syncUi();
    return;
  }
  list.forEach((idea, index) => bodyEl.appendChild(rowHtml(idea, index + 1)));
  if (selectAll) selectAll.checked = true;
  syncUi();
};

const paintPreview = (row, images) => {
  const cell = document.querySelector(`tr[data-row="${row}"] .col-thumb`);
  if (!cell) return;
  if (!images.length) {
    cell.innerHTML = '<div class="import-ph">Нет карточек</div>';
    return;
  }
  const nav =
    images.length > 1
      ? `<button type="button" class="nav prev" data-dir="-1" aria-label="Предыдущая">‹</button>
         <button type="button" class="nav next" data-dir="1" aria-label="Следующая">›</button>
         <p class="count"><span data-count>1</span> / ${images.length}</p>`
      : "";
  const stage = document.createElement("div");
  stage.className = "import-stage";
  stage.setAttribute("data-carousel", "");
  stage.innerHTML =
    images
      .map(
        (src, idx) =>
          `<img${idx === 0 ? ' class="is-on"' : ""} src="${src}" alt="">`
      )
      .join("") + nav;
  cell.innerHTML = "";
  cell.appendChild(stage);
  bindCarousel(stage);
};

const placeholderHtml = (text) => `<div class="import-ph">${escapeHtml(text)}</div>`;

const loadPreviews = async (list) => {
  const run = ++previewRun;
  paintStyleBadges();
  list.forEach((idea) => {
    const cell = document.querySelector(`tr[data-row="${idea.row}"] .col-thumb`);
    if (cell && idea.imagesStyle !== styleFor(idea)) cell.innerHTML = placeholderHtml("Карточки…");
  });
  for (const idea of list) {
    if (run !== previewRun) return;
    const style = styleFor(idea);
    if (idea.imagesStyle === style && idea.images) {
      paintPreview(idea.row, idea.images);
      continue;
    }
    try {
      const res = await fetch(
        `api/import/preview?row=${idea.row}&style=${encodeURIComponent(style)}`,
        { cache: "no-store" }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "Не собрались карточки");
      if (run !== previewRun) return;
      idea.images = data.images || [];
      idea.imagesStyle = style;
      paintPreview(idea.row, idea.images);
    } catch (error) {
      if (run !== previewRun) return;
      const cell = document.querySelector(`tr[data-row="${idea.row}"] .col-thumb`);
      if (cell) cell.innerHTML = placeholderHtml(error.message || "Нет карточек");
    }
  }
};

const fillSchedules = (list) => {
  scheduleEl.innerHTML = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = list.length ? "Выберите расписание" : "Нет расписаний";
  scheduleEl.appendChild(empty);
  list.forEach((item) => {
    const option = document.createElement("option");
    option.value = String(item.id);
    option.textContent = `${item.name} — ${item.state_label} · ${postsCountLabel(item.posts_count)}`;
    scheduleEl.appendChild(option);
  });
  scheduleEl.value = "";
  syncUi();
};

const loadSchedules = async () => {
  const secret = hooppyTokenValue();
  try {
    const res = await fetch("api/hooppy/schedules", {
      cache: "no-store",
      headers: secret ? { "X-Hooppy-Token": secret } : {},
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Не удалось загрузить расписания");
    fillSchedules(data.schedules || []);
    setScheduleHint(
      (data.schedules || []).length
        ? `Подтянуто расписаний: ${(data.schedules || []).length}. Выберите одно, затем импортируйте.`
        : "В кабинете Hooppy пока нет расписаний."
    );
  } catch (error) {
    fillSchedules([]);
    setScheduleHint(error.message || "Не удалось прочитать расписания Hooppy.", "err");
  }
};

const loadIdeas = async () => {
  const res = await fetch("api/ideas", { cache: "no-store" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Не удалось прочитать Google Таблицу");
  ideas = data.ideas || [];
  if (randomOn()) assignRandomStyles();
  fillTable(ideas);
  setStatus(
    ideas.length
      ? `Черновиков в таблице: ${ideas.length}. Все выбраны. Собираю превью карточек…`
      : "Нет черновиков в Google Таблице."
  );
  await loadPreviews(ideas);
  if (ideas.length) {
    setStatus(`Черновиков в таблице: ${ideas.length}. Все выбраны.`);
  }
};

const readNdjson = async (res, onEvent) => {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop();
    for (const line of lines) {
      if (!line.trim()) continue;
      onEvent(JSON.parse(line));
    }
  }
  if (buf.trim()) onEvent(JSON.parse(buf));
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const rows = selectedBoxes().map((box) => Number(box.value));
  const scheduleId = scheduleEl.value ? Number(scheduleEl.value) : 0;
  if (!scheduleId) {
    setStatus("Выберите расписание Hooppy.", "err");
    return;
  }
  if (!rows.length) {
    setStatus("Выберите хотя бы один пост.", "err");
    return;
  }
  busy = true;
  syncUi();
  logEl.hidden = false;
  logEl.textContent = "";
  setProgress(0, rows.length);
  setStatus("Начинаю импорт…");
  const headers = { "Content-Type": "application/json" };
  const secret = hooppyTokenValue();
  if (secret) headers["X-Hooppy-Token"] = secret;
  const option = scheduleEl.selectedOptions[0];
  const scheduleName = option ? option.textContent.replace(/\s+[—–-].*$/, "").trim() : "";
  try {
    const res = await fetch("api/import", {
      method: "POST",
      headers,
      body: JSON.stringify({
        schedule_id: scheduleId,
        schedule_name: scheduleName,
        rows,
        origin: siteBase(),
        style: baseStyle(),
        random_style: randomOn(),
        styles: Object.fromEntries(
          rows.map((row) => [String(row), styleFor(ideaByRow(row))])
        ),
      }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || "Импорт не принят");
    }
    await readNdjson(res, (event) => {
      if (event.message) {
        appendLog(event.message, event.ok === false ? "err" : event.ok ? "ok" : "");
      }
      if (event.event === "progress" || event.event === "item") {
        setProgress(event.index || 0, event.total || rows.length);
        setStatus(event.message || "Импорт…");
      }
      if (event.event === "item" && event.ok) {
        document.querySelector(`tr[data-row="${event.row}"]`)?.remove();
        ideas = ideas.filter((idea) => idea.row !== event.row);
      }
      if (event.event === "done") {
        setProgress(event.total || rows.length, event.total || rows.length);
        setStatus(event.message || "Импорт закончен.", event.fail ? "err" : "ok");
      }
    });
    syncUi();
  } catch (error) {
    appendLog(error.message || "Импорт оборвался.", "err");
    setStatus(error.message || "Импорт оборвался.", "err");
  } finally {
    busy = false;
    syncUi();
  }
});

if (selectAll) {
  selectAll.addEventListener("change", () => {
    document.querySelectorAll('#import-body input[name="row"]').forEach((box) => {
      box.checked = selectAll.checked;
    });
    syncUi();
  });
}

if (scheduleEl) {
  scheduleEl.addEventListener("change", syncUi);
}

if (styleEl) {
  const styleCode = document.getElementById("style-code");
  const showStyleCode = () => {
    if (styleCode) styleCode.textContent = randomOn() ? "случайный" : styleEl.value;
  };
  const saved = localStorage.getItem(STYLE_KEY);
  if (saved && [...styleEl.options].some((option) => option.value === saved)) styleEl.value = saved;
  showStyleCode();
  styleEl.addEventListener("change", () => {
    localStorage.setItem(STYLE_KEY, styleEl.value);
    showStyleCode();
    if (ideas.length) {
      setStatus(`Тема ${styleEl.value}: пересобираю карточки…`);
      loadPreviews(ideas).then(() => {
        if (!busy) setStatus(`Черновиков в таблице: ${ideas.length}. Все выбраны.`);
      });
    }
  });
}

if (randomEl) {
  randomEl.addEventListener("change", () => {
    if (randomOn()) assignRandomStyles();
    const styleCode = document.getElementById("style-code");
    if (styleCode) styleCode.textContent = randomOn() ? "случайный" : baseStyle();
    syncUi();
    paintStyleBadges();
    if (ideas.length) {
      setStatus(
        randomOn()
          ? "Случайный стиль: каждому посту выпал свой. Пересобираю карточки…"
          : `Тема ${baseStyle()}: пересобираю карточки…`
      );
      loadPreviews(ideas).then(() => {
        if (!busy) setStatus(`Черновиков в таблице: ${ideas.length}. Все выбраны.`);
      });
    }
  });
}

if (previewDialog) {
  previewDialog.querySelector("[data-close]")?.addEventListener("click", closePreview);
  previewDialog.addEventListener("click", (event) => {
    if (event.target === previewDialog) closePreview();
  });
  previewDialog.addEventListener("close", () => {
    openPreviewRow = 0;
  });
}

setStatus("Загружаю Google Таблицу…");
const ready = window.hooppyTokenStore ? window.hooppyTokenStore.hydrate() : Promise.resolve("");
ready.finally(() => {
  loadSchedules();
  loadIdeas().catch((error) => {
    fillTable([]);
    setStatus(error.message || "Не удалось прочитать Google Таблицу.", "err");
  });
});

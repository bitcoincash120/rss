const SHEET = {
  id: "19ZlYXpbgZ8lvlkniXU-BoxVuLewfFX0xh-nX97DN2VI",
  gid: "0",
  url: "https://docs.google.com/spreadsheets/d/19ZlYXpbgZ8lvlkniXU-BoxVuLewfFX0xh-nX97DN2VI/edit?gid=0#gid=0",
};

const DEFAULT_CARD_COUNT = 10;
const TITLE_KEYS = ["заголовок", "title", "headline", "тема", "name"];
const TEXT_KEYS = ["текст", "text", "описание", "анонс", "description", "body"];
const SLIDE_KEYS = ["карточки", "slides", "фото", "photos", "slide"];
const STATUS_KEYS = ["статус", "status", "state"];
const IMPORTED_MARKS = new Set(["импортирован", "imported", "готово", "published", "опубликован"]);
const CARD_HEADER = /^(карточка|card|текст|slide)\s*(\d+)$/i;

const siteBase = () => {
  const dir = location.pathname.replace(/[^/]+$/, "") || "/";
  return `${location.origin}${dir}`.replace(/\/$/, "");
};
window.SHEET_WEBHOOK =
  window.SHEET_WEBHOOK ||
  "https://script.google.com/macros/s/AKfycbz4rHUVVCe3imLSysN1EaQAxT5bm-WEVr9wwR6B9rN926tLP07wrCj8dKMFyxJ_UbDb/exec";

let ideas = [];
let currentIdea = null;
let cardCount = DEFAULT_CARD_COUNT;

const form = document.getElementById("post-form");
const title = document.getElementById("title");
const cardRows = document.getElementById("card-rows");
const token = document.getElementById("token");
const statusEl = document.getElementById("status");
const mocks = document.getElementById("mocks");
const markdownEl = document.getElementById("markdown");
const publishedAt = document.getElementById("published-at");
const randomBtn = document.getElementById("random");
const styleEl = document.getElementById("style");

const repoFromLocation = () => {
  const host = location.hostname;
  if (host.endsWith(".github.io")) {
    const parts = location.pathname.split("/").filter(Boolean);
    return { owner: host.split(".")[0], repo: parts[0] || "rss" };
  }
  return { owner: "bitcoincash120", repo: "rss" };
};

const isLocal = () => location.hostname === "127.0.0.1" || location.hostname === "localhost";

const styleValue = () => {
  const value = styleEl && styleEl.value;
  return value === "paper" || value === "studio" ? value : "night";
};

const MONTHS_RU = [
  "января",
  "февраля",
  "марта",
  "апреля",
  "мая",
  "июня",
  "июля",
  "августа",
  "сентября",
  "октября",
  "ноября",
  "декабря",
];

const nowIso = () => new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00");

const formatDatetimeRu = (iso) => {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "";
  const local = new Date(parsed.getTime() + 4 * 60 * 60 * 1000);
  const hours = String(local.getUTCHours()).padStart(2, "0");
  const minutes = String(local.getUTCMinutes()).padStart(2, "0");
  return `${local.getUTCDate()} ${MONTHS_RU[local.getUTCMonth()]} ${local.getUTCFullYear()}, ${hours}:${minutes}`;
};

const cardInputs = () => [...cardRows.querySelectorAll("textarea[data-card]")];

const cardValues = () => cardInputs().map((input) => input.value.trim());

const filledCards = () => cardValues().filter(Boolean);

const slidesValue = () => Math.max(1, filledCards().length);

const descriptionValue = () => filledCards()[0] || "";

const markdown = () => {
  const cards = filledCards();
  const slides = cards.length;
  const parts = [`---\ndate: ${nowIso()}\nslides: ${slides}\nstyle: ${styleValue()}\n---\n\n# ${title.value.trim()}\n`];
  cards.forEach((text, index) => {
    parts.push(`\n## ${index + 1}\n\n${text}\n`);
  });
  return parts.join("");
};

const mockKind = (index) => {
  if (index === 1) return "hero";
  if (index === 2) return "quote";
  return "compact";
};

const mockCard = (kind, kicker, heading, body, index, total) => {
  const headingTag = kind === "hero" ? `<h1>${escapeHtml(heading)}</h1>` : "";
  const bodyTag = body ? `<p>${escapeHtml(body)}</p>` : "";
  return `<div class="mock-wrap"><article class="mock ${kind} ${styleValue()}">
    <div class="when">${escapeHtml(kicker)}</div>
    ${headingTag}
    ${bodyTag}
    <div class="num">Карточка ${index} из ${total}</div>
  </article></div>`;
};

const escapeHtml = (value) =>
  value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const renderCardRows = (count, values = []) => {
  cardCount = Math.max(DEFAULT_CARD_COUNT, Number(count) || DEFAULT_CARD_COUNT);
  const current = cardValues();
  const copy = values.length ? values : current;
  cardRows.innerHTML = Array.from({ length: cardCount }, (_, index) => {
    const n = index + 1;
    const text = escapeHtml(copy[index] || "");
    return `<tr>
      <th><label for="card${n}">Карточка ${n}</label></th>
      <td><textarea id="card${n}" name="card${n}" data-card="${n}" rows="3" maxlength="280" placeholder="Текст карточки ${n}"${n === 1 ? " required" : ""}>${text}</textarea></td>
    </tr>`;
  }).join("");
};

const renderPreview = () => {
  const heading = title.value.trim() || "Заголовок появится здесь";
  const cards = cardValues();
  const filled = cards.filter(Boolean);
  const total = Math.max(1, filled.length);
  const iso = nowIso();
  const when = formatDatetimeRu(iso);
  const shown = filled.length ? filled : [""];
  mocks.innerHTML = shown
    .map((text, index) => {
      const n = index + 1;
      const kind = mockKind(n);
      const body = text || (n === 1 ? "" : `Текст карточки ${n} появится здесь.`);
      return mockCard(kind, when, heading, body, n, total);
    })
    .join("");
  markdownEl.textContent = markdown();
  if (publishedAt) {
    publishedAt.dateTime = iso;
    publishedAt.textContent = when;
  }
};

const setStatus = (text, kind) => {
  statusEl.textContent = text;
  statusEl.className = `status${kind ? " " + kind : ""}`;
};

const cellText = (cell) => {
  if (!cell) return "";
  const value = cell.f != null ? cell.f : cell.v;
  return value == null ? "" : String(value).trim();
};

const colIndex = (labels, keys, fallback) => {
  const index = labels.findIndex((label) => {
    const name = String(label || "").trim().toLowerCase();
    return keys.some((key) => name === key || name.startsWith(`${key} `) || name.startsWith(`${key}\n`));
  });
  return index >= 0 ? index : fallback;
};

const cardColumns = (labels) => {
  const found = [];
  labels.forEach((label, index) => {
    const name = String(label || "").trim().toLowerCase();
    const match = name.match(CARD_HEADER) || name.replace(/\s+/g, "").match(/^(карточка|card|текст|slide)(\d+)$/i);
    if (match) found.push({ number: Number(match[2]), index });
  });
  found.sort((a, b) => a.number - b.number);
  return found;
};

const isImported = (status) => IMPORTED_MARKS.has(String(status || "").trim().toLowerCase());

const valueAt = (values, index) =>
  index >= 0 && index < values.length ? String(values[index] || "").trim() : "";

const rowIdea = (values, cols, row) => {
  const heading = valueAt(values, cols.title);
  const legacy = valueAt(values, cols.text);
  const byNumber = {};
  cols.cards.forEach(({ number, index }) => {
    byNumber[number] = valueAt(values, index);
  });
  const highest = cols.cards.reduce((max, item) => Math.max(max, item.number), 0);
  const listed = [];
  for (let n = 1; n <= highest; n += 1) listed.push(byNumber[n] || "");
  while (listed.length && !listed[listed.length - 1]) listed.pop();
  const cards = listed.filter(Boolean);
  if (!cards.length && legacy) cards.push(legacy);
  const body = cards[0] || legacy;
  if (!heading || !body) return null;
  if (TITLE_KEYS.includes(heading.toLowerCase())) return null;
  if (isImported(valueAt(values, cols.status))) return null;
  const idea = { title: heading, description: body, cards, row };
  const raw = valueAt(values, cols.slide);
  const listedSlides = Number(raw);
  idea.slides = Math.max(1, cards.length || (Number.isFinite(listedSlides) ? listedSlides : 1));
  return idea;
};

const parseGvizTable = (table) => {
  const labels = (table.cols || []).map((col) => String(col.label || "").trim().toLowerCase());
  const cols = {
    title: colIndex(labels, TITLE_KEYS, 2),
    text: colIndex(labels, TEXT_KEYS, -1),
    slide: colIndex(labels, SLIDE_KEYS, -1),
    status: colIndex(labels, STATUS_KEYS, 0),
    cards: cardColumns(labels),
  };
  return (table.rows || [])
    .map((row, index) => rowIdea((row.c || []).map(cellText), cols, index + 2))
    .filter(Boolean);
};

const loadSheetJsonp = () =>
  new Promise((resolve, reject) => {
    const name = `__sheet${Date.now()}`;
    const timer = setTimeout(() => {
      cleanup();
      reject(new Error("Таблица не ответила"));
    }, 8000);
    const cleanup = () => {
      clearTimeout(timer);
      delete window[name];
      script.remove();
    };
    window[name] = (payload) => {
      cleanup();
      if (!payload || payload.status !== "ok") {
        reject(new Error("Не удалось прочитать таблицу"));
        return;
      }
      resolve(parseGvizTable(payload.table || {}));
    };
    const script = document.createElement("script");
    script.src = `https://docs.google.com/spreadsheets/d/${SHEET.id}/gviz/tq?gid=${SHEET.gid}&headers=1&tqx=${encodeURIComponent(`out:json;responseHandler:${name}`)}&_=${Date.now()}`;
    script.onerror = () => {
      cleanup();
      reject(new Error("Нет доступа к Google Таблице"));
    };
    document.head.appendChild(script);
  });

const loadSheetLocal = async () => {
  const res = await fetch("api/ideas", { cache: "no-store" });
  if (!res.ok) throw new Error("local sheet");
  const data = await res.json();
  if (!Array.isArray(data.ideas)) throw new Error("local sheet");
  return data.ideas.filter((idea) => !idea.imported);
};

const loadIdeas = async () => {
  try {
    const fromApi = await loadSheetLocal();
    ideas = fromApi;
    return;
  } catch (_error) {
    /* GitHub Pages has no local API; try the sheet directly. */
  }
  ideas = await loadSheetJsonp();
};

const applyIdea = (idea) => {
  const copy = (idea.cards || []).filter(Boolean);
  title.value = idea.title;
  renderCardRows(Math.max(DEFAULT_CARD_COUNT, copy.length), copy);
  renderPreview();
};

const clearIdea = () => {
  currentIdea = null;
  title.value = "";
  renderCardRows(DEFAULT_CARD_COUNT, []);
  renderPreview();
};

const pickRandom = () => {
  if (!ideas.length) {
    clearIdea();
    setStatus("Нет черновиков в Google Таблице. Добавьте строки со статусом не «импортирован».", "err");
    return;
  }
  let pool = ideas;
  if (currentIdea && ideas.length > 1) {
    pool = ideas.filter((idea) => idea.row !== currentIdea.row);
    if (!pool.length) pool = ideas;
  }
  currentIdea = pool[Math.floor(Math.random() * pool.length)];
  applyIdea(currentIdea);
  setStatus(`Случайный пост из Google Таблицы, строка ${currentIdea.row} (${ideas.length} доступно).`);
};

const fillRandom = async () => {
  randomBtn.disabled = true;
  setStatus("Загружаю Google Таблицу…");
  try {
    await loadIdeas();
    pickRandom();
  } catch (error) {
    ideas = [];
    clearIdea();
    setStatus(error.message || "Не удалось прочитать Google Таблицу.", "err");
  } finally {
    randomBtn.disabled = false;
  }
};

const utf8ToBase64 = (text) => {
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary);
};

const publicPostUrl = (postId) => `${siteBase()}/#${postId}`;

const markSheetRow = async (row, url) => {
  if (!row) return { ok: false, error: "no row" };
  if (isLocal()) {
    const res = await fetch("api/ideas/imported", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ row, url, status: "импортирован" }),
    });
    return res.json().catch(() => ({ ok: false }));
  }
  const webhook = window.SHEET_WEBHOOK;
  if (!webhook) return { ok: false, error: "no webhook" };
  return new Promise((resolve) => {
    const name = `__mark${Date.now()}`;
    const timer = setTimeout(() => {
      cleanup();
      resolve({ ok: false, error: "timeout" });
    }, 10000);
    const cleanup = () => {
      clearTimeout(timer);
      delete window[name];
      script.remove();
    };
    window[name] = (payload) => {
      cleanup();
      resolve(payload || { ok: true });
    };
    const script = document.createElement("script");
    const params = new URLSearchParams({
      row: String(row),
      url,
      status: "импортирован",
      callback: name,
    });
    script.src = `${webhook}${webhook.includes("?") ? "&" : "?"}${params}`;
    script.onerror = () => {
      cleanup();
      resolve({ ok: false, error: "webhook" });
    };
    document.head.appendChild(script);
  });
};

const createLocal = async (payload) => {
  const res = await fetch("api/posts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || "Локальный сервер не принял пост");
  }
  return data;
};

const nextGitHubId = async (headers) => {
  const { owner, repo } = repoFromLocation();
  const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/posts`, { headers });
  if (!res.ok) {
    throw new Error("Не удалось прочитать папку posts");
  }
  const files = await res.json();
  let max = 0;
  for (const file of files) {
    const match = /^post-(\d+)\.md$/.exec(file.name || "");
    if (match) max = Math.max(max, Number(match[1]));
  }
  return `post-${String(max + 1).padStart(2, "0")}`;
};

const createOnGitHub = async (payload, secret) => {
  const { owner, repo } = repoFromLocation();
  const headers = {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${secret}`,
  };
  const id = await nextGitHubId(headers);
  const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/posts/${id}.md`, {
    method: "PUT",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({
      message: `Add ${id} from the generator page.`,
      content: utf8ToBase64(markdown()),
      branch: "main",
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.message || "GitHub не принял файл");
  }
  return { id, url: `./#${id}` };
};

form.addEventListener("input", renderPreview);
form.addEventListener("change", renderPreview);
randomBtn.addEventListener("click", fillRandom);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    title: title.value.trim(),
    description: descriptionValue(),
    cards: filledCards(),
    slides: slidesValue(),
    date: nowIso(),
    row: currentIdea && currentIdea.row,
    origin: siteBase(),
    style: styleValue(),
  };
  if (!payload.title || !payload.description) {
    setStatus("Заполните заголовок и текст карточек.", "err");
    return;
  }
  const submit = form.querySelector('button[type="submit"]');
  submit.disabled = true;
  setStatus("Создаю пост…");
  try {
    let created;
    try {
      created = await createLocal(payload);
    } catch (_localError) {
      const secret = token.value.trim();
      if (!secret) {
        throw new Error(
          "Локальный сервер недоступен. Запустите python3 serve.py или вставьте токен GitHub."
        );
      }
      created = await createOnGitHub(payload, secret);
      const marked = await markSheetRow(payload.row, publicPostUrl(created.id));
      if (marked && marked.ok) {
        ideas = ideas.filter((idea) => idea.row !== payload.row);
        currentIdea = null;
      }
      setStatus(
        `Файл ${created.id}.md записан. Карточки появятся после сборки GitHub Pages.`,
        "ok"
      );
      return;
    }
    if (!created.sheet_marked && payload.row) {
      const marked = await markSheetRow(payload.row, publicPostUrl(created.id));
      created.sheet_marked = Boolean(marked && marked.ok);
      created.sheet_error = marked && marked.error;
    }
    if (created.sheet_marked) {
      ideas = ideas.filter((idea) => idea.row !== payload.row);
      currentIdea = null;
    }
    const sheetNote = created.sheet_marked
      ? " Строка в таблице помечена как импортированная."
      : created.sheet_error
        ? ` Пост создан, но таблица не обновилась: ${created.sheet_error}`
        : " Пост создан, но статус в таблице не обновился.";
    setStatus(`Готово: ${created.id}. Карточки уже в ленте.${sheetNote}`, created.sheet_marked ? "ok" : "err");
    if (created.sheet_marked) {
      location.href = created.url || "./";
    }
  } catch (error) {
    setStatus(error.message || "Не получилось создать пост.", "err");
  } finally {
    submit.disabled = false;
  }
});

token.value = sessionStorage.getItem("gh-token") || "";
token.addEventListener("input", () => {
  const value = token.value.trim();
  if (value) sessionStorage.setItem("gh-token", value);
  else sessionStorage.removeItem("gh-token");
});

renderCardRows(DEFAULT_CARD_COUNT);
fillRandom();

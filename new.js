const IDEAS = [
  ["В метро начали продавать билеты с запахом свежего хлеба", "Контролёры говорят, что безбилетников теперь выдаёт аппетит. Кассы просят не облизывать QR-код."],
  ["Фонари на набережной научились шептать комплименты", "Прохожие останавливаются на третьем столбе и краснеют. Городские службы уточняют: это не реклама, а вежливость."],
  ["В зоопарке пингвин открыл шахматный кружок", "Первый турнир завершился ничьей и ведром рыбы. Дети утверждают, что ферзь у него холодный."],
  ["Почтовый голубь доставил открытку раньше, чем её написали", "Адресат ещё выбирал марку, а птица уже ждала на подоконнике. Почта рассматривает это как новый тариф."],
  ["В парке зацвела скамейка и зовёт присесть на варенье", "Садовники спорят, поливать её или намазывать тосты. Вечером вокруг собираются осы и романтики."],
  ["Часы на площади начали отставать специально, чтобы все успевали", "Мэр благодарит механизм за эмпатию. Пассажиры электричек просят распространить опыт на вокзал."],
  ["Найден зонтик, который возвращает вчерашнюю хорошую погоду", "Под куполом снова светит то утро, когда вы не забыли ключи. Метеорологи просят не раскрывать его в июле."],
  ["Коты двора подписали договор о тишине после десяти", "Мыши получили час форума, но обязаны ходить на цыпочках. Дворник заверяет документ лапкой."],
  ["В булочной появился круассан, который рассказывает сказки", "Если отломить рожок, слышно про дракона из корицы. Очередь просит историю без изюма."],
  ["Река в центре города потекла вспять, чтобы вернуть уток", "Утки были на экскурсии и заблудились у моста. Лодочники уже продают билеты «туда и сразу обратно»."],
  ["Музей выдал посетителям носки, чтобы картины не мёрзли", "Экскурсовод шепчет: особенно зябнет натюрморт с селёдкой. Гардероб теперь пахнет маслом и шерстью."],
  ["На чердаке завелась луна размером с блюдце", "Она всходит из коробки с проводами и просит не включать люстру. Соседи уже делают фото для календаря."],
  ["Самокат научился выбирать самый поэтичный маршрут", "Он сворачивает к фонтанам и читает таблички вслух. Пассажир добирается дольше, зато с рифмой."],
  ["В лифте появился этаж, которого нет на кнопках", "Двери открываются в комнату с запахом какао и старых карт. Консьерж просит не опаздывать вниз."],
  ["Скворцы сложили на проводах слово «доброе утро»", "Автобус №12 теперь отправляется только после прочтения. Водитель кивает птицам, как коллегам."],
];

const SHEET = {
  id: "19ZlYXpbgZ8lvlkniXU-BoxVuLewfFX0xh-nX97DN2VI",
  gid: "0",
  url: "https://docs.google.com/spreadsheets/d/19ZlYXpbgZ8lvlkniXU-BoxVuLewfFX0xh-nX97DN2VI/edit?gid=0#gid=0",
};

const TITLE_KEYS = ["заголовок", "title", "headline", "тема", "name"];
const TEXT_KEYS = ["текст", "text", "описание", "анонс", "description", "body"];
const SLIDE_KEYS = ["карточки", "slides", "фото", "photos", "slide"];

let ideas = IDEAS.map(([title, description]) => ({ title, description }));
let ideaSource = "local";

const form = document.getElementById("post-form");
const title = document.getElementById("title");
const description = document.getElementById("description");
const token = document.getElementById("token");
const statusEl = document.getElementById("status");
const mocks = document.getElementById("mocks");
const markdownEl = document.getElementById("markdown");
const publishedAt = document.getElementById("published-at");
const randomBtn = document.getElementById("random");

const repoFromLocation = () => {
  const host = location.hostname;
  if (host.endsWith(".github.io")) {
    const parts = location.pathname.split("/").filter(Boolean);
    return { owner: host.split(".")[0], repo: parts[0] || "rss" };
  }
  return { owner: "bitcoincash120", repo: "rss" };
};

const slidesValue = () => {
  const checked = form.querySelector('input[name="slides"]:checked');
  return Number(checked ? checked.value : 3);
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

const markdown = () => {
  const slides = slidesValue();
  return `---\ndate: ${nowIso()}\nslides: ${slides}\n---\n\n# ${title.value.trim()}\n\n${description.value.trim()}\n`;
};

const mockCard = (kind, kicker, heading, body, index, total) => {
  const headingTag = kind === "quote" ? "" : `<h1>${escapeHtml(heading)}</h1>`;
  const bodyTag = kind === "hero" ? "" : `<p>${escapeHtml(body)}</p>`;
  return `<div class="mock-wrap"><article class="mock ${kind}">
    <h2>${escapeHtml(kicker)}</h2>
    ${headingTag}
    ${bodyTag}
    <h3>Карточка ${index} из ${total}</h3>
  </article></div>`;
};

const escapeHtml = (value) =>
  value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const renderPreview = () => {
  const heading = title.value.trim() || "Заголовок появится здесь";
  const body = description.value.trim() || "Текст анонса появится здесь.";
  const total = slidesValue();
  const iso = nowIso();
  const when = formatDatetimeRu(iso);
  const cards = [
    mockCard("hero", when, heading, body, 1, total),
    mockCard("quote", when, heading, body, 2, total),
  ];
  if (total >= 3) {
    cards.push(mockCard("compact", when, heading, body, 3, total));
  }
  mocks.innerHTML = cards.join("");
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
  const index = labels.findIndex((label) => keys.includes(label));
  return index >= 0 ? index : fallback;
};

const rowIdea = (values, titleI, textI, slideI) => {
  const heading = (values[titleI] || "").trim();
  const body = (values[textI] || "").trim();
  if (!heading || !body) return null;
  if (TITLE_KEYS.includes(heading.toLowerCase()) || TEXT_KEYS.includes(body.toLowerCase())) {
    return null;
  }
  const idea = { title: heading, description: body };
  const raw = String(values[slideI] || "").trim();
  if (raw === "2" || raw === "3") idea.slides = Number(raw);
  return idea;
};

const parseGvizTable = (table) => {
  const labels = (table.cols || []).map((col) => String(col.label || "").trim().toLowerCase());
  const titleI = colIndex(labels, TITLE_KEYS, 0);
  const textI = colIndex(labels, TEXT_KEYS, 1);
  const slideI = colIndex(labels, SLIDE_KEYS, 2);
  return (table.rows || [])
    .map((row) => rowIdea((row.c || []).map(cellText), titleI, textI, slideI))
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
    script.src = `https://docs.google.com/spreadsheets/d/${SHEET.id}/gviz/tq?gid=${SHEET.gid}&tqx=${encodeURIComponent(`out:json;responseHandler:${name}`)}`;
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
  return data.ideas;
};

const loadIdeas = async () => {
  try {
    const fromApi = await loadSheetLocal();
    if (fromApi.length) {
      ideas = fromApi;
      ideaSource = "sheet";
      return;
    }
  } catch (_error) {
    /* GitHub Pages has no local API; try the sheet directly. */
  }
  const fromSheet = await loadSheetJsonp();
  if (fromSheet.length) {
    ideas = fromSheet;
    ideaSource = "sheet";
  }
};

const fillRandom = () => {
  if (!ideas.length) {
    setStatus("Нет черновиков: добавьте строки в Google Таблицу.", "err");
    return;
  }
  const idea = ideas[Math.floor(Math.random() * ideas.length)];
  title.value = idea.title;
  description.value = idea.description;
  const two = form.querySelector('input[name="slides"][value="2"]');
  const three = form.querySelector('input[name="slides"][value="3"]');
  if (idea.slides === 2) two.checked = true;
  else if (idea.slides === 3) three.checked = true;
  else (Math.random() < 0.4 ? two : three).checked = true;
  renderPreview();
  if (ideaSource === "sheet") {
    setStatus(`Случайный пост из Google Таблицы (${ideas.length}). Можно править и создавать.`);
  } else {
    setStatus("Таблица пустая или недоступна, взят запасной список. Добавьте строки: Заголовок, Текст, Карточки.");
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
    description: description.value.trim(),
    slides: slidesValue(),
    date: nowIso(),
  };
  if (!payload.title || !payload.description) {
    setStatus("Заполните заголовок и текст.", "err");
    return;
  }
  const submit = form.querySelector('button[type="submit"]');
  submit.disabled = true;
  setStatus("Создаю пост…");
  try {
    try {
      const created = await createLocal(payload);
      setStatus(`Готово: ${created.id}. Карточки уже в ленте.`, "ok");
      location.href = created.url || "./";
      return;
    } catch (localError) {
      const secret = token.value.trim();
      if (!secret) {
        throw new Error(
          "Локальный сервер недоступен. Запустите python3 serve.py или вставьте токен GitHub."
        );
      }
      const created = await createOnGitHub(payload, secret);
      setStatus(
        `Файл ${created.id}.md записан. Карточки появятся после сборки GitHub Pages.`,
        "ok"
      );
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

setStatus("Загружаю Google Таблицу…");
loadIdeas()
  .catch(() => {
    ideaSource = "local";
  })
  .finally(() => {
    fillRandom();
  });

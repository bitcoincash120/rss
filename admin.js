const form = document.getElementById("admin-form");
const generateRss = document.getElementById("generate-rss");
const token = document.getElementById("token");
const hooppyToken = document.getElementById("hooppy-token");
const statusEl = document.getElementById("status");

const isLocal = () => location.hostname === "127.0.0.1" || location.hostname === "localhost";

const repoFromLocation = () => {
  const host = location.hostname;
  if (host.endsWith(".github.io")) {
    const parts = location.pathname.split("/").filter(Boolean);
    return { owner: host.split(".")[0], repo: parts[0] || "rss" };
  }
  return { owner: "bitcoincash120", repo: "rss" };
};

const utf8ToBase64 = (text) => {
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary);
};

const setStatus = (text, kind) => {
  statusEl.textContent = text;
  statusEl.classList.toggle("ok", kind === "ok");
  statusEl.classList.toggle("err", kind === "err");
};

const settingsPayload = () => ({ generate_rss: Boolean(generateRss.checked) });

const applySettings = (data) => {
  generateRss.checked = Boolean(data && data.generate_rss);
};

const loadLocal = async () => {
  const res = await fetch("api/settings", { cache: "no-store" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || "Не удалось прочитать настройки");
  }
  return data.settings || data;
};

const loadFile = async () => {
  const res = await fetch("site_settings.json", { cache: "no-store" });
  if (!res.ok) return { generate_rss: false };
  return res.json();
};

const saveLocal = async (settings) => {
  const res = await fetch("api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || "Локальный сервер не сохранил настройки");
  }
  return data.settings || settings;
};

const saveOnGitHub = async (settings, secret) => {
  const { owner, repo } = repoFromLocation();
  const headers = {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${secret}`,
  };
  const path = `https://api.github.com/repos/${owner}/${repo}/contents/site_settings.json`;
  let sha;
  const existing = await fetch(path, { headers });
  if (existing.ok) {
    const current = await existing.json();
    sha = current.sha;
  }
  const res = await fetch(path, {
    method: "PUT",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({
      message: settings.generate_rss ? "Enable RSS generation." : "Disable RSS generation.",
      content: utf8ToBase64(JSON.stringify(settings, null, 2) + "\n"),
      branch: "main",
      ...(sha ? { sha } : {}),
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.message || "GitHub не принял файл настроек");
  }
  return settings;
};

const loadSettings = async () => {
  try {
    applySettings(await loadLocal());
  } catch (_error) {
    applySettings(await loadFile());
  }
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const settings = settingsPayload();
  const submit = form.querySelector('button[type="submit"]');
  submit.disabled = true;
  setStatus("Сохраняю настройки…");
  try {
    try {
      applySettings(await saveLocal(settings));
      if (isLocal()) {
        await fetch("api/hooppy/token", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: (hooppyToken && hooppyToken.value.trim()) || "" }),
        }).catch(() => ({}));
      }
      setStatus(
        settings.generate_rss
          ? "RSS включён. Файл будет собираться при публикации и создании постов."
          : "RSS выключен. Файл больше не собирается.",
        "ok"
      );
    } catch (_localError) {
      if (!isLocal()) {
        const secret = token.value.trim();
        if (!secret) {
          throw new Error(
            "Локальный сервер недоступен. Запустите python3 serve.py или вставьте токен GitHub."
          );
        }
        applySettings(await saveOnGitHub(settings, secret));
        setStatus(
          settings.generate_rss
            ? "Настройка записана. RSS появится после сборки GitHub Pages."
            : "Настройка записана. RSS отключится после сборки GitHub Pages.",
          "ok"
        );
      } else {
        throw _localError;
      }
    }
    document.querySelectorAll("[data-rss]").forEach((el) => {
      el.hidden = !settings.generate_rss;
    });
  } catch (error) {
    setStatus(error.message || "Не получилось сохранить настройки.", "err");
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

if (hooppyToken) {
  hooppyToken.value = sessionStorage.getItem("hooppy-token") || "";
  hooppyToken.addEventListener("input", () => {
    const value = hooppyToken.value.trim();
    if (value) sessionStorage.setItem("hooppy-token", value);
    else sessionStorage.removeItem("hooppy-token");
  });
}

loadSettings();

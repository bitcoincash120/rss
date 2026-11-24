const crcTable = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let crc = n;
    for (let k = 0; k < 8; k += 1) crc = crc & 1 ? 0xedb88320 ^ (crc >>> 1) : crc >>> 1;
    table[n] = crc;
  }
  return table;
})();

const crc32 = (bytes) => {
  let crc = 0xffffffff;
  for (let i = 0; i < bytes.length; i += 1) {
    crc = crcTable[(crc ^ bytes[i]) & 255] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
};

const concatBytes = (chunks) => {
  const out = new Uint8Array(chunks.reduce((sum, chunk) => sum + chunk.length, 0));
  let offset = 0;
  chunks.forEach((chunk) => {
    out.set(chunk, offset);
    offset += chunk.length;
  });
  return out;
};

const u16 = (value) => new Uint8Array([value & 255, (value >>> 8) & 255]);
const u32 = (value) =>
  new Uint8Array([value & 255, (value >>> 8) & 255, (value >>> 16) & 255, (value >>> 24) & 255]);

const zipBlob = (files) => {
  const encode = new TextEncoder();
  const locals = [];
  const centrals = [];
  let offset = 0;
  files.forEach((file) => {
    const name = encode.encode(file.name);
    const data = file.data;
    const crc = crc32(data);
    const local = concatBytes([
      u32(0x04034b50),
      u16(20),
      u16(0),
      u16(0),
      u16(0),
      u16(0),
      u32(crc),
      u32(data.length),
      u32(data.length),
      u16(name.length),
      u16(0),
      name,
      data,
    ]);
    locals.push(local);
    centrals.push(
      concatBytes([
        u32(0x02014b50),
        u16(20),
        u16(20),
        u16(0),
        u16(0),
        u16(0),
        u16(0),
        u32(crc),
        u32(data.length),
        u32(data.length),
        u16(name.length),
        u16(0),
        u16(0),
        u16(0),
        u16(0),
        u32(0),
        u32(offset),
        name,
      ])
    );
    offset += local.length;
  });
  const center = concatBytes(centrals);
  const end = concatBytes([
    u32(0x06054b50),
    u16(0),
    u16(0),
    u16(files.length),
    u16(files.length),
    u32(center.length),
    u32(offset),
    u16(0),
  ]);
  return new Blob([concatBytes([...locals, center, end])], { type: "application/zip" });
};

const saveBlob = (blob, filename) => {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
};

const downloadZip = async (paths, filename) => {
  const files = [];
  for (const path of paths) {
    const res = await fetch(path);
    if (!res.ok) throw new Error("Не удалось скачать " + path);
    files.push({
      name: path.split("/").pop(),
      data: new Uint8Array(await res.arrayBuffer()),
    });
  }
  if (!files.length) throw new Error("Нет картинок для скачивания");
  saveBlob(zipBlob(files), filename);
};

const setBusy = (button, busy, idleText) => {
  button.disabled = busy;
  button.textContent = busy ? "Собираю архив…" : idleText;
};

const openPreview = (id) => {
  const dialog = document.getElementById(id);
  if (dialog && typeof dialog.showModal === "function") {
    dialog.showModal();
    history.replaceState(null, "", "#" + id);
  }
};

const closePreview = (dialog) => {
  dialog.close();
  if (location.hash.slice(1) === dialog.id) history.replaceState(null, "", location.pathname);
};

document.querySelectorAll("[data-open]").forEach((row) => {
  const open = () => openPreview(row.dataset.open);
  row.addEventListener("click", (event) => {
    if (event.target.closest("[data-stop], input, button, a, label.check")) return;
    open();
  });
  row.addEventListener("keydown", (event) => {
    if (event.target.closest("input, button, a")) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      open();
    }
  });
});

document.querySelectorAll("dialog.preview").forEach((dialog) => {
  dialog.querySelector("[data-close]")?.addEventListener("click", () => closePreview(dialog));
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closePreview(dialog);
  });
});

if (location.hash) openPreview(location.hash.slice(1));

document.querySelectorAll("[data-carousel]").forEach((stage) => {
  const slides = [...stage.querySelectorAll("img")];
  const dots = [...stage.querySelectorAll("[data-go]")];
  const count = stage.querySelector("[data-count]");
  if (slides.length < 2) return;
  let i = 0;
  const show = (next) => {
    i = (next + slides.length) % slides.length;
    slides.forEach((img, idx) => img.classList.toggle("is-on", idx === i));
    dots.forEach((dot, idx) => dot.classList.toggle("is-on", idx === i));
    if (count) count.textContent = String(i + 1);
  };
  show(0);
  stage.querySelectorAll("[data-dir]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.stopPropagation();
      show(i + Number(btn.dataset.dir));
    });
  });
  dots.forEach((dot) => {
    dot.addEventListener("click", (event) => {
      event.stopPropagation();
      show(Number(dot.dataset.go));
    });
  });
});

const allImages = [...new Set(
  [...document.querySelectorAll("[data-zip]")]
    .flatMap((btn) => (btn.dataset.zip || "").split(",").filter(Boolean))
    .map((name) => (name.startsWith("images/") ? name : "images/" + name))
)];

const downloadAll = document.getElementById("download-all");
if (downloadAll && !allImages.length) {
  downloadAll.hidden = true;
} else if (downloadAll) {
  downloadAll.addEventListener("click", async () => {
    const idle = downloadAll.textContent;
    setBusy(downloadAll, true, idle);
    try {
      await downloadZip(allImages, "rss-cards.zip");
    } catch (error) {
      downloadAll.textContent = error.message || "Не получилось скачать";
      setTimeout(() => {
        downloadAll.disabled = false;
        downloadAll.textContent = idle;
      }, 2400);
      return;
    }
    setBusy(downloadAll, false, idle);
  });
}

document.querySelectorAll("[data-zip]").forEach((button) => {
  button.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();
    const idle = button.textContent;
    const names = (button.dataset.zip || "")
      .split(",")
      .filter(Boolean)
      .map((name) => (name.startsWith("images/") ? name : "images/" + name));
    setBusy(button, true, idle);
    try {
      await downloadZip(names, (button.dataset.zipName || "cards") + ".zip");
    } catch (error) {
      button.textContent = error.message || "Не получилось скачать";
      setTimeout(() => setBusy(button, false, idle), 2400);
      return;
    }
    setBusy(button, false, idle);
  });
});

const POST_ID_RE = /^post-\d+$/;
const deleteBtn = document.getElementById("delete-selected");
const deleteStatus = document.getElementById("delete-status");
const selectAll = document.getElementById("select-all");
const postChecks = () => [...document.querySelectorAll('.feed tbody input[name="post"]')];

const isLocalHost = () => location.hostname === "127.0.0.1" || location.hostname === "localhost";

const repoFromLocation = () => {
  const host = location.hostname;
  if (host.endsWith(".github.io")) {
    const parts = location.pathname.split("/").filter(Boolean);
    return { owner: host.split(".")[0], repo: parts[0] || "rss" };
  }
  return { owner: "bitcoincash120", repo: "rss" };
};

const selectedPosts = () =>
  postChecks()
    .filter((box) => box.checked)
    .map((box) => {
      const row = box.closest("tr");
      return {
        id: box.value,
        images: String(row && row.dataset.images ? row.dataset.images : "")
          .split(",")
          .map((name) => name.trim())
          .filter(Boolean),
      };
    })
    .filter((item) => POST_ID_RE.test(item.id));

const syncDeleteUi = () => {
  const selected = selectedPosts();
  const boxes = postChecks();
  if (deleteBtn) deleteBtn.disabled = !selected.length;
  if (selectAll) {
    selectAll.checked = Boolean(boxes.length) && boxes.every((box) => box.checked);
    selectAll.indeterminate = boxes.some((box) => box.checked) && !selectAll.checked;
  }
};

const setDeleteStatus = (text, kind) => {
  if (!deleteStatus) return;
  deleteStatus.textContent = text;
  deleteStatus.classList.toggle("ok", kind === "ok");
  deleteStatus.classList.toggle("err", kind === "err");
};

const deleteLocal = async (ids) => {
  const res = await fetch("api/posts/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || "Локальный сервер не удалил посты");
  }
  return data;
};

const githubHeaders = (secret) => ({
  Accept: "application/vnd.github+json",
  Authorization: `Bearer ${secret}`,
});

const deleteGitHubFile = async (headers, path) => {
  const { owner, repo } = repoFromLocation();
  const url = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;
  const existing = await fetch(url, { headers });
  if (existing.status === 404) return;
  if (!existing.ok) {
    const data = await existing.json().catch(() => ({}));
    throw new Error(data.message || `Не удалось прочитать ${path}`);
  }
  const current = await existing.json();
  const res = await fetch(url, {
    method: "DELETE",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({
      message: `Delete ${path} from the feed.`,
      sha: current.sha,
      branch: "main",
    }),
  });
  if (res.status === 404) return;
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.message || `GitHub не удалил ${path}`);
  }
};

const deleteOnGitHub = async (posts, secret) => {
  const headers = githubHeaders(secret);
  for (const post of posts) {
    await deleteGitHubFile(headers, `posts/${post.id}.md`);
    const names = post.images.length ? post.images : [`${post.id}.jpg`];
    for (const name of names) {
      const file = name.startsWith("images/") ? name : `images/${name}`;
      await deleteGitHubFile(headers, file);
    }
  }
};

if (selectAll) {
  selectAll.addEventListener("click", (event) => event.stopPropagation());
  selectAll.addEventListener("change", () => {
    postChecks().forEach((box) => {
      box.checked = selectAll.checked;
    });
    syncDeleteUi();
  });
}

postChecks().forEach((box) => {
  box.addEventListener("click", (event) => event.stopPropagation());
  box.addEventListener("change", syncDeleteUi);
});

if (deleteBtn) {
  deleteBtn.addEventListener("click", async (event) => {
    event.preventDefault();
    const posts = selectedPosts();
    if (!posts.length) return;
    const confirmed = window.confirm(
      `Удалить выбранные посты и их картинки? Строки в Google Таблице не изменятся.`
    );
    if (!confirmed) return;
    deleteBtn.disabled = true;
    setDeleteStatus("Удаляю посты и картинки…");
    const ids = posts.map((post) => post.id);
    try {
      try {
        await deleteLocal(ids);
        setDeleteStatus("Посты и картинки удалены. Таблица не менялась.", "ok");
        location.reload();
        return;
      } catch (localError) {
        if (isLocalHost()) throw localError;
        const secret = (sessionStorage.getItem("gh-token") || "").trim();
        if (!secret) {
          throw new Error(
            "Локальный сервер недоступен. Запустите python3 serve.py или сохраните токен в админке."
          );
        }
        await deleteOnGitHub(posts, secret);
        posts.forEach((post) => {
          document.querySelector(`tr[data-open="${post.id}"]`)?.remove();
        });
        syncDeleteUi();
        setDeleteStatus(
          "Посты и картинки удалены из репозитория. Лента обновится после сборки GitHub Pages. Таблица не менялась.",
          "ok"
        );
      }
    } catch (error) {
      setDeleteStatus(error.message || "Не получилось удалить посты.", "err");
      syncDeleteUi();
    }
  });
}

syncDeleteUi();

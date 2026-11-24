(() => {
  const KEY = "hooppy-token";

  const read = () =>
    (localStorage.getItem(KEY) || sessionStorage.getItem(KEY) || "").trim();

  const write = (value) => {
    const text = String(value || "").trim();
    if (!text) return;
    localStorage.setItem(KEY, text);
    sessionStorage.setItem(KEY, text);
  };

  const hydrate = async () => {
    const local = read();
    if (local) {
      write(local);
      return local;
    }
    try {
      const res = await fetch("api/hooppy/token", { cache: "no-store" });
      const data = await res.json().catch(() => ({}));
      const token = String((data && data.token) || "").trim();
      if (token) write(token);
      return token;
    } catch (_error) {
      return "";
    }
  };

  window.hooppyTokenStore = { read, write, hydrate };
})();

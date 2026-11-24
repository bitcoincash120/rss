(() => {
  const apply = (enabled) => {
    document.querySelectorAll("[data-rss]").forEach((el) => {
      el.hidden = !enabled;
    });
  };
  apply(false);
  fetch("site_settings.json", { cache: "no-store" })
    .then((res) => (res.ok ? res.json() : { generate_rss: false }))
    .then((data) => apply(Boolean(data && data.generate_rss)))
    .catch(() => apply(false));
})();

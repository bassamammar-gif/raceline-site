(() => {
  const grid = document.getElementById("gallery-grid");
  if (!grid || !window.RLM_GALLERY) return;

  const version = window.RLM_GALLERY_VERSION || 1;

  window.RLM_GALLERY.forEach((photo) => {
    const item = document.createElement("div");
    item.className = "gallery__item";
    item.setAttribute("data-media-reveal", "");
    item.innerHTML = `<img src="${photo.image}?v=${version}" alt="${photo.alt}" width="${photo.width}" height="${photo.height}" loading="lazy" />`;
    grid.appendChild(item);
  });
})();

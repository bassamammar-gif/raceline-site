(() => {
  const grid = document.getElementById("instagram-grid");
  if (!grid || !window.RLM_INSTAGRAM_POSTS) return;

  window.RLM_INSTAGRAM_POSTS.forEach((post, i) => {
    const item = document.createElement("a");
    item.className = "gallery__item gallery__item--link";
    item.href = post.permalink;
    item.target = "_blank";
    item.rel = "noopener";
    item.setAttribute("aria-label", `View post ${i + 1} on Instagram`);
    item.setAttribute("data-media-reveal", "");
    item.innerHTML = `<img src="${post.image}" alt="Race Line Motorsports Instagram post ${i + 1}" width="800" height="1000" loading="lazy" />`;
    grid.appendChild(item);
  });

  document.querySelectorAll("[data-instagram-handle]").forEach((el) => {
    el.textContent = window.RLM_INSTAGRAM_HANDLE;
  });
  document.querySelectorAll("[data-instagram-url]").forEach((el) => {
    el.setAttribute("href", window.RLM_INSTAGRAM_URL);
  });
})();

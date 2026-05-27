/* ZenCV — UI interactions (powered by Clyra) */

(() => {
  // ----------------------------------------------------------
  // Theme toggle (persisted)
  // ----------------------------------------------------------
  const themeKey = "arp-theme";
  const html = document.documentElement;
  const saved = localStorage.getItem(themeKey);
  if (saved === "dark" || (!saved && window.matchMedia?.("(prefers-color-scheme: dark)").matches)) {
    html.setAttribute("data-theme", "dark");
  }

  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-theme-toggle]");
    if (!t) return;
    const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
    if (next === "dark") html.setAttribute("data-theme", "dark");
    else html.removeAttribute("data-theme");
    localStorage.setItem(themeKey, next);
  });

  // ----------------------------------------------------------
  // Sticky nav: hide on scroll-down, reveal on scroll-up
  // ----------------------------------------------------------
  const nav = document.querySelector(".app-navbar");
  let lastY = 0;
  if (nav) {
    window.addEventListener("scroll", () => {
      const y = window.scrollY;
      if (y > 80 && y > lastY) nav.classList.add("nav-hidden");
      else nav.classList.remove("nav-hidden");
      lastY = y;
    }, { passive: true });
  }

  // ----------------------------------------------------------
  // Mark active nav link based on current path
  // ----------------------------------------------------------
  const path = location.pathname.replace(/\/$/, "");
  document.querySelectorAll(".app-navbar .nav-link").forEach((a) => {
    const href = a.getAttribute("href")?.replace(/\/$/, "");
    if (!href) return;
    if (href === path || (href !== "" && path.startsWith(href))) {
      a.classList.add("active");
    }
  });

  // ----------------------------------------------------------
  // Reveal-on-scroll
  // ----------------------------------------------------------
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add("in");
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });

  document.querySelectorAll(".reveal").forEach((el) => io.observe(el));

  // ----------------------------------------------------------
  // Animated count-up on numbers with data-count
  // ----------------------------------------------------------
  function countUp(el) {
    const target = parseInt(el.dataset.count, 10);
    if (isNaN(target)) return;
    const dur = 1400;
    const start = performance.now();
    function step(t) {
      const p = Math.min(1, (t - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased);
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  const countIO = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        countUp(e.target);
        countIO.unobserve(e.target);
      }
    });
  }, { threshold: 0.4 });

  document.querySelectorAll("[data-count]").forEach((el) => countIO.observe(el));

  // ----------------------------------------------------------
  // Animate score ring from 0 → target on load
  // ----------------------------------------------------------
  document.querySelectorAll(".score-ring[data-score]").forEach((ring) => {
    const target = parseFloat(ring.dataset.score);
    if (isNaN(target)) return;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        ring.style.setProperty("--score", target);
      });
    });
  });

  // ----------------------------------------------------------
  // Animate progress bars
  // ----------------------------------------------------------
  const pbIO = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add("animate");
        pbIO.unobserve(e.target);
      }
    });
  }, { threshold: 0.3 });

  document.querySelectorAll(".progress-bar[data-target]").forEach((bar) => {
    bar.style.setProperty("--target-width", bar.dataset.target + "%");
    pbIO.observe(bar);
  });

  // ----------------------------------------------------------
  // Drag & drop upload dropzone
  // ----------------------------------------------------------
  document.querySelectorAll(".upload-dropzone").forEach((zone) => {
    const input = zone.querySelector("input[type='file']");
    const badge = zone.querySelector("[data-file-name]");
    const hint  = zone.querySelector("[data-default-hint]");
    if (!input) return;

    ["dragenter", "dragover"].forEach((ev) =>
      zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("dragover"); })
    );
    ["dragleave", "drop"].forEach((ev) =>
      zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("dragover"); })
    );
    zone.addEventListener("drop", (e) => {
      if (e.dataTransfer?.files?.length) {
        input.files = e.dataTransfer.files;
        updateFileLabel();
      }
    });

    input.addEventListener("change", updateFileLabel);

    function updateFileLabel() {
      if (input.files?.length && badge) {
        badge.textContent = input.files[0].name;
        badge.classList.remove("d-none");
        if (hint) hint.classList.add("d-none");
      }
    }
  });

  // ----------------------------------------------------------
  // Button ripple coords
  // ----------------------------------------------------------
  document.addEventListener("pointermove", (e) => {
    const btn = e.target.closest(".btn");
    if (!btn) return;
    const r = btn.getBoundingClientRect();
    btn.style.setProperty("--mx", ((e.clientX - r.left) / r.width * 100) + "%");
    btn.style.setProperty("--my", ((e.clientY - r.top)  / r.height * 100) + "%");
  });

  // ----------------------------------------------------------
  // Copy-to-clipboard for code snippets
  // ----------------------------------------------------------
  document.querySelectorAll(".api-snippet").forEach((snip) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-btn";
    btn.textContent = "Copy";
    btn.addEventListener("click", async () => {
      const code = snip.querySelector("code")?.textContent ?? "";
      try {
        await navigator.clipboard.writeText(code);
        btn.textContent = "Copied!";
        btn.classList.add("copied");
        setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("copied"); }, 1600);
      } catch {
        btn.textContent = "Press Ctrl+C";
      }
    });
    snip.appendChild(btn);
  });

  // ----------------------------------------------------------
  // Smooth remove for repeat-row elements (builder)
  // ----------------------------------------------------------
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".remove-row");
    if (!btn) return;
    const row = btn.closest(".repeat-row");
    if (!row) return;
    row.classList.add("removing");
    setTimeout(() => row.remove(), 240);
  });
})();

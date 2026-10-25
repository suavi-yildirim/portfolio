/* Project filters, picture lightbox and language memory.  No dependencies. */
(function () {
  "use strict";

  // ------------------------------------------------ remember the language
  document.querySelectorAll("[data-set-lang]").forEach(function (a) {
    a.addEventListener("click", function () {
      try { localStorage.setItem("lang", a.dataset.setLang); } catch (e) { /* private mode */ }
    });
  });

  // ------------------------------------------------------ project filters
  var grid = document.getElementById("project-grid");
  if (grid) {
    var buttons = document.querySelectorAll(".filter");
    var cards = grid.querySelectorAll(".card");
    var apply = function (key) {
      var known = false;
      buttons.forEach(function (b) {
        var on = b.dataset.filter === key;
        known = known || on;
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      if (!known) { key = "all"; buttons[0].setAttribute("aria-pressed", "true"); }
      cards.forEach(function (c) {
        c.hidden = key !== "all" && c.dataset.cats.split(" ").indexOf(key) < 0;
      });
    };
    buttons.forEach(function (b) {
      b.addEventListener("click", function () {
        var key = b.dataset.filter;
        apply(key);
        history.replaceState(null, "", key === "all" ? location.pathname : "#" + key);
      });
    });
    apply(location.hash.slice(1) || "all");
    window.addEventListener("hashchange", function () { apply(location.hash.slice(1) || "all"); });
  }

  // ------------------------------------------------------------ lightbox
  var links = Array.prototype.slice.call(document.querySelectorAll("a.zoom"));
  if (!links.length) return;
  var lang = document.body.dataset.lang;
  var box = document.createElement("div");
  box.className = "lightbox";
  box.hidden = true;
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-modal", "true");
  box.innerHTML =
    '<button class="lb-close" type="button" aria-label="' + (lang === "de" ? "Schließen" : "Close") + '">×</button>' +
    '<button class="lb-prev" type="button" aria-label="' + (lang === "de" ? "Zurück" : "Previous") + '">‹</button>' +
    '<img alt=""><p></p>' +
    '<button class="lb-next" type="button" aria-label="' + (lang === "de" ? "Weiter" : "Next") + '">›</button>';
  document.body.appendChild(box);
  var img = box.querySelector("img"), cap = box.querySelector("p"), current = 0, opener = null;

  function show(i) {
    current = (i + links.length) % links.length;
    var a = links[current];
    img.src = a.href;
    img.alt = a.querySelector("img").alt;
    cap.textContent = a.dataset.caption || "";
  }
  function close() {
    box.hidden = true;
    document.body.style.overflow = "";
    if (opener) opener.focus();
  }
  links.forEach(function (a, i) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      opener = a;
      show(i);
      box.hidden = false;
      document.body.style.overflow = "hidden";
      box.querySelector(".lb-close").focus();
    });
  });
  box.querySelector(".lb-close").addEventListener("click", close);
  box.querySelector(".lb-prev").addEventListener("click", function () { show(current - 1); });
  box.querySelector(".lb-next").addEventListener("click", function () { show(current + 1); });
  box.addEventListener("click", function (e) { if (e.target === box) close(); });
  document.addEventListener("keydown", function (e) {
    if (box.hidden) return;
    if (e.key === "Escape") close();
    if (e.key === "ArrowLeft") show(current - 1);
    if (e.key === "ArrowRight") show(current + 1);
  });
  if (links.length < 2) {
    box.querySelector(".lb-prev").hidden = true;
    box.querySelector(".lb-next").hidden = true;
  }
})();

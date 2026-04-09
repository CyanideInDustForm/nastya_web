// static/app.js

function showToast(text, variant="info") {
  const container = document.querySelector(".toast-container");
  if (!container) return;

  const el = document.createElement("div");
  el.className = `toast align-items-center text-bg-${variant}`;
  el.setAttribute("role", "alert");
  el.setAttribute("aria-live", "assertive");
  el.setAttribute("aria-atomic", "true");
  el.dataset.bsDelay = "5000";

  el.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${text}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto"
              data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  container.appendChild(el);
  const t = new bootstrap.Toast(el);
  t.show();
  el.addEventListener("hidden.bs.toast", () => el.remove());
}

document.addEventListener("DOMContentLoaded", () => {
  // server flash toasts
  document.querySelectorAll(".toast").forEach((el) => new bootstrap.Toast(el).show());

  // bootstrap validation
  document.querySelectorAll(".needs-validation").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add("was-validated");
    });
  });

  async function submitModal(formId, url, selectId, modalId) {
    const form = document.getElementById(formId);
    if (!form) return;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(form);

      try {
        const res = await fetch(url, { method: "POST", body: fd });
        const data = await res.json();

        if (!res.ok || !data.ok) throw new Error(data.error || "Ошибка");

        const sel = document.getElementById(selectId);
        const opt = document.createElement("option");
        opt.value = data.id;
        opt.textContent = data.label;
        opt.selected = true;
        sel.appendChild(opt);

        bootstrap.Modal.getInstance(document.getElementById(modalId)).hide();
        form.reset();
        showToast("Добавлено и выбрано.", "success");
      } catch (err) {
        showToast(`Ошибка: ${err.message}`, "danger");
      }
    });
  }

  // cascade: reader -> books in loans
  const cascadeReader = document.getElementById("cascadeReader");
  const cascadeBook = document.getElementById("cascadeBook");

  if (cascadeReader && cascadeBook) {
    cascadeReader.addEventListener("change", async () => {
      cascadeBook.innerHTML = `<option value="">(загрузка...)</option>`;
      const rid = cascadeReader.value;

      if (!rid) {
        cascadeBook.innerHTML = `<option value="">(сначала выберите читателя)</option>`;
        return;
      }

      try {
        const res = await fetch(`/api/options/books-by-reader?reader_id=${encodeURIComponent(rid)}`);
        const data = await res.json();

        if (!res.ok || !data.ok) throw new Error(data.error || "Ошибка");

        cascadeBook.innerHTML = `<option value="">(любая)</option>`;
        if (!data.items.length) {
          cascadeBook.innerHTML = `<option value="">(нет выдач)</option>`;
          return;
        }

        for (const item of data.items) {
          const opt = document.createElement("option");
          opt.value = item.value;
          opt.textContent = item.label;
          cascadeBook.appendChild(opt);
        }
      } catch (err) {
        cascadeBook.innerHTML = `<option value="">(ошибка)</option>`;
        showToast(`Ошибка каскада: ${err.message}`, "danger");
      }
    });
  }
});

// ---------- AJAX-поиск для search.html ----------
document.addEventListener("DOMContentLoaded", () => {
  const searchForm = document.querySelector("form#searchOne"); // форма mode=one
  const resultsContainer = document.getElementById("results"); // контейнер для таблицы

  if (!searchForm || !resultsContainer) return;

  const debounce = (fn, delay) => {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn(...args), delay);
    };
  };

  const fetchResults = async () => {
    const params = new URLSearchParams(new FormData(searchForm));
    params.set("mode", "one");

    try {
      const res = await fetch(`/search?${params.toString()}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const html = await res.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");
      const newTable = doc.getElementById("results");
      if (newTable) {
        resultsContainer.innerHTML = newTable.innerHTML;
      }
    } catch (err) {
      showToast(`Ошибка поиска: ${err.message}`, "danger");
    }
  };

  // Авто-запуск при вводе
  searchForm.querySelectorAll("input, select").forEach(el => {
    el.addEventListener("input", debounce(fetchResults, 400));
    el.addEventListener("change", debounce(fetchResults, 400));
  });
});
/* global chrome */
/* global CONFIG */

const PAGE_PATTERNS = {
  classlist: /classlist\.d2l/,
  assignments: /folders_manage\.d2l/,
  groups: /group_list\.d2l/,
  quizzes: /quizzes_manage\.d2l/,
  rubrics: /rubrics\/list\.d2l/,
  submissions: /folder_submissions_users\.d2l/,
};

/**
 * Detect the Brightspace page type from a URL string.
 * @param {string} url
 * @returns {string|null} page type key or null
 */
function detectPageType(url) {
  for (const [type, pattern] of Object.entries(PAGE_PATTERNS)) {
    if (pattern.test(url)) return type;
  }
  return null;
}

/**
 * Convert an array of objects to a TSV string (header + data rows).
 * @param {Array<Object>} rows
 * @returns {string}
 */
function tableToTSV(rows) {
  if (!rows.length) return "";
  const keys = Object.keys(rows[0]);
  const header = keys.join("\t");
  const lines = rows.map((r) => keys.map((k) => String(r[k] ?? "")).join("\t"));
  return [header, ...lines].join("\n");
}

// ── UI helpers ──────────────────────────────────────────────────────────────

const $status = document.getElementById("status");
const $controls = document.getElementById("controls");
const $formatSelect = document.getElementById("format-select");
const $extractBtn = document.getElementById("extract-btn");
const $loader = document.getElementById("loader");
const $error = document.getElementById("error");
const $resultInfo = document.getElementById("result-info");
const $result = document.getElementById("result");

function showError(msg) {
  $error.textContent = msg;
  $error.style.display = "block";
  $loader.classList.remove("active");
}

function clearError() {
  $error.style.display = "none";
  $error.textContent = "";
}

function showLoader() {
  $loader.classList.add("active");
  clearError();
  $resultInfo.style.display = "none";
  $result.style.display = "none";
}

function hideLoader() {
  $loader.classList.remove("active");
}

// ── Rendering ───────────────────────────────────────────────────────────────

const PAGE_TYPE_LABELS = {
  classlist: "Classlist",
  assignments: "Assignments",
  groups: "Groups",
  quizzes: "Quizzes",
  rubrics: "Rubrics",
  submissions: "Submissions",
};

const ITEM_LABELS = {
  classlist: "students",
  assignments: "assignments",
  groups: "groups",
  quizzes: "quizzes",
  rubrics: "rubrics",
};

function renderTable(rows) {
  if (!rows.length) return;
  const keys = Object.keys(rows[0]);
  let html = "<table><thead><tr>";
  for (const k of keys) html += `<th>${k}</th>`;
  html += "</tr></thead><tbody>";
  for (const row of rows) {
    html += "<tr>";
    for (const k of keys) html += `<td>${row[k] ?? ""}</td>`;
    html += "</tr>";
  }
  html += "</tbody></table>";
  html += `<button class="copy-btn" id="copy-btn">Copy as TSV</button>`;
  $result.innerHTML = html;
  $result.style.display = "block";

  document.getElementById("copy-btn").addEventListener("click", () => {
    const tsv = tableToTSV(rows);
    navigator.clipboard.writeText(tsv).then(() => {
      document.getElementById("copy-btn").textContent = "Copied!";
      setTimeout(() => {
        document.getElementById("copy-btn").textContent = "Copy as TSV";
      }, 1500);
    });
  });
}

// ── API communication ───────────────────────────────────────────────────────

async function getApiBaseUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get("apiBaseUrl", (data) => {
      resolve(data.apiBaseUrl || CONFIG.DEFAULT_API_URL);
    });
  });
}

async function capturePageHtml(tabId) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    files: ["content.js"],
  });
  if (!results || !results[0] || !results[0].result) {
    throw new Error(
      "Could not read page content. The page may contain cross-origin frames."
    );
  }
  return results[0].result;
}

async function sendToApi(baseUrl, pageType, html, format) {
  const isSubmissions = pageType === "submissions";
  const endpoint = isSubmissions ? "/api/extract" : `/api/${pageType}`;
  const url = new URL(endpoint, baseUrl);
  if (isSubmissions && format) url.searchParams.set("format", format);

  const resp = await fetch(url.toString(), {
    method: "POST",
    headers: { "Content-Type": "text/html" },
    body: html,
  });

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      if (body.detail) detail = body.detail;
    } catch { /* ignore parse errors */ }
    throw new Error(detail);
  }

  const ct = resp.headers.get("content-type") || "";
  if (ct.includes("application/pdf")) {
    return { type: "pdf", data: await resp.blob() };
  }
  if (ct.includes("text/markdown")) {
    return { type: "markdown", data: await resp.text() };
  }
  return { type: "json", data: await resp.json() };
}

// ── Main flow ───────────────────────────────────────────────────────────────

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url) {
    $status.innerHTML = `<span class="unsupported">Cannot access this page.</span>`;
    return;
  }

  const pageType = detectPageType(tab.url);
  if (!pageType) {
    $status.innerHTML = `<span class="unsupported">This is not a supported Brightspace page.</span>`;
    return;
  }

  $status.textContent = `Detected: ${PAGE_TYPE_LABELS[pageType] || pageType}`;
  $controls.style.display = "flex";

  if (pageType === "submissions") {
    $formatSelect.style.display = "inline-block";
  }

  $extractBtn.addEventListener("click", async () => {
    $extractBtn.disabled = true;
    showLoader();

    try {
      const html = await capturePageHtml(tab.id);
      const baseUrl = await getApiBaseUrl();
      const format = pageType === "submissions" ? $formatSelect.value : null;
      const result = await sendToApi(baseUrl, pageType, html, format);

      hideLoader();

      if (result.type === "pdf") {
        const blobUrl = URL.createObjectURL(result.data);
        const a = document.createElement("a");
        a.href = blobUrl;
        a.download = "feedback.pdf";
        a.click();
        URL.revokeObjectURL(blobUrl);
        $resultInfo.textContent = "PDF downloaded.";
        $resultInfo.style.display = "block";
      } else if (result.type === "markdown") {
        $resultInfo.textContent = "Markdown received.";
        $resultInfo.style.display = "block";
        $result.innerHTML = `<pre style="white-space:pre-wrap;font-size:12px;max-height:300px;overflow:auto;">${result.data}</pre>`;
        $result.style.display = "block";
      } else {
        // JSON array — render as table
        const rows = result.data;
        const label = ITEM_LABELS[pageType] || "items";
        $resultInfo.textContent = `${rows.length} ${label} found`;
        $resultInfo.style.display = "block";
        renderTable(rows);
      }
    } catch (err) {
      hideLoader();
      showError(err.message);
    } finally {
      $extractBtn.disabled = false;
    }
  });
}

init();

// Export for testing (ignored in browser context)
if (typeof module !== "undefined") {
  module.exports = { detectPageType, tableToTSV, PAGE_PATTERNS };
}

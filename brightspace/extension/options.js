/* global chrome */
/* global CONFIG */

const $apiUrl = document.getElementById("api-url");
const $saveBtn = document.getElementById("save-btn");
const $saved = document.getElementById("saved");

// Load current setting
chrome.storage.local.get("apiBaseUrl", (data) => {
  $apiUrl.value = data.apiBaseUrl || CONFIG.DEFAULT_API_URL;
});

$saveBtn.addEventListener("click", () => {
  const url = $apiUrl.value.trim() || CONFIG.DEFAULT_API_URL;
  chrome.storage.local.set({ apiBaseUrl: url }, () => {
    $saved.style.display = "block";
    setTimeout(() => {
      $saved.style.display = "none";
    }, 2000);
  });
});

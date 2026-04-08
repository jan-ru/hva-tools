// Content script injected via chrome.scripting.executeScript.
// Returns the full page HTML so the popup can send it to the API.
(() => document.documentElement.outerHTML)();

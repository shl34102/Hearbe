const HEARBE_APP_URL = "http://localhost:5173/A/store";

function buildHearbeUrl(targetUrl) {
  const encoded = encodeURIComponent(targetUrl || "");
  return `${HEARBE_APP_URL}?url=${encoded}&autoshare=1`;
}

chrome.runtime.onMessage.addListener((message, sender) => {
  if (!message || message.type !== "OPEN_HEARBE") {
    return;
  }

  const targetUrl = message.url || (sender.tab && sender.tab.url) || "";
  chrome.tabs.create({ url: buildHearbeUrl(targetUrl) });
});

(() => {
  if (window.__hearbeShareInjected) {
    return;
  }
  window.__hearbeShareInjected = true;

  const button = document.createElement("button");
  button.className = "hearbe-share-btn";
  button.type = "button";
  button.textContent = "HearBe 공유";

  const showToast = (message) => {
    const toast = document.createElement("div");
    toast.className = "hearbe-share-toast";
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 1800);
  };

  button.addEventListener("click", () => {
    try {
      chrome.runtime.sendMessage({
        type: "OPEN_HEARBE",
        url: window.location.href
      });
      showToast("HearBe 앱을 새 탭으로 열었어요.");
    } catch (e) {
      console.error("HearBe extension error:", e);
    }
  });

  document.documentElement.appendChild(button);
})();

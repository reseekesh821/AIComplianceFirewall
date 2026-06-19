function refreshIcons() {
  if (window.lucide) window.lucide.createIcons();
}

document.addEventListener("DOMContentLoaded", refreshIcons);
document.body.addEventListener("htmx:afterSwap", refreshIcons);

function copyText(text, el) {
  navigator.clipboard.writeText(text).then(() => {
    const label = el.querySelector("[data-copy-label]") || el;
    const prev = label.textContent;
    label.textContent = "Copied";
    setTimeout(() => { label.textContent = prev; }, 1500);
  });
}

function closeModal() {
  const root = document.getElementById("modal-root");
  if (root) root.innerHTML = "";
}

function fillPrompt(text) {
  const input = document.getElementById("prompt-input");
  if (input) {
    input.value = text;
    input.focus();
  }
}

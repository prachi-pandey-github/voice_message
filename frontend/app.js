const $ = (id) => document.getElementById(id);
const form = $("generate-form");
const fileInput = $("voice-file");
const uploadZone = $("upload-zone");
const messageInput = $("message");
const loadingMessages = [
  "Warming up the studio...",
  "Learning the voice's rhythm...",
  "Adding a personal touch...",
  "Putting the finishing touches on...",
];
let loadingTimer;
let objectUrl;

function showStatus(type, text) {
  const status = $("message-status");
  status.className = `status show ${type}`;
  status.textContent = text;
}

function setLoading(isLoading) {
  $("result-body").hidden = isLoading;
  $("loading-state").hidden = !isLoading;
  $("generate-button").disabled = isLoading;
  $("result-pill").textContent = isLoading ? "Creating your audio" : "Waiting for you";
  if (!isLoading) {
    clearInterval(loadingTimer);
    return;
  }
  let index = 0;
  $("loading-text").textContent = loadingMessages[index];
  loadingTimer = setInterval(() => {
    index = (index + 1) % loadingMessages.length;
    $("loading-text").textContent = loadingMessages[index];
  }, 2100);
}

function updateFileName() {
  const file = fileInput.files[0];
  $("file-name").textContent = file ? file.name : "Drop an audio file here";
  uploadZone.classList.toggle("selected", Boolean(file));
}

messageInput.addEventListener("input", () => {
  $("character-count").textContent = `${messageInput.value.length.toLocaleString()} / 2,000`;
});
messageInput.dispatchEvent(new Event("input"));
fileInput.addEventListener("change", updateFileName);
["dragenter", "dragover"].forEach((eventName) => uploadZone.addEventListener(eventName, (event) => {
  event.preventDefault();
  uploadZone.classList.add("dragging");
}));
["dragleave", "drop"].forEach((eventName) => uploadZone.addEventListener(eventName, (event) => {
  event.preventDefault();
  uploadZone.classList.remove("dragging");
}));
uploadZone.addEventListener("drop", (event) => {
  const [file] = event.dataTransfer.files;
  if (file && file.type.startsWith("audio/")) {
    const transfer = new DataTransfer();
    transfer.items.add(file);
    fileInput.files = transfer.files;
    updateFileName();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file) {
    showStatus("error", "Please choose a reference voice recording.");
    return;
  }
  setLoading(true);
  $("message-status").className = "status";
  $("audio-result").replaceChildren();
  const body = new FormData();
  body.append("file", file);
  body.append("language", $("voice-language").value);
  body.append("first_name", $("first-name").value);
  body.append("message", messageInput.value);
  body.append("language_code", $("message-language").value);
  try {
    const response = await fetch("/generate", { method: "POST", body });
    if (!response.ok) {
      let detail = "Audio generation failed.";
      try { detail = (await response.json()).detail || detail; } catch (error) { /* Non-JSON upstream response. */ }
      throw new Error(detail);
    }
    const audioBlob = await response.blob();
    if (!audioBlob.size) throw new Error("The server returned an empty audio file.");
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = URL.createObjectURL(new Blob([audioBlob], { type: "audio/mpeg" }));
    const player = document.createElement("audio");
    player.controls = true;
    player.src = objectUrl;
    const download = document.createElement("a");
    download.className = "download-button";
    download.download = `${$("first-name").value.trim().toLowerCase().replace(/\s+/g, "-") || "echo"}-echo.mp3`;
    download.href = objectUrl;
    download.textContent = "Download MP3";
    $("audio-result").append(player, download);
    $("result-pill").textContent = "Ready to listen";
    $("result-pill").classList.add("ready");
    showStatus("success", "Your personalized voice message is ready.");
  } catch (error) {
    showStatus("error", error.message);
  } finally {
    setLoading(false);
    $("generate-button").querySelector("span").textContent = "Generate voice message";
  }
});

import base64
import binascii
import os
import re
import uuid
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel


SARVAM_CREATE_VOICE_URL = "https://api.sarvam.ai/voices/create"
SARVAM_CLONE_URL = "https://api.sarvam.ai/voices/clone"
MAX_REFERENCE_AUDIO_BYTES = 50 * 1024 * 1024
DEFAULT_LANGUAGE_CODE = "en-IN"
VOICE_PROFILE_NAME = "CEO voice"
FIXED_MESSAGE = (
    "Hello {{first_name}}, I would like to personally thank you for your "
    "contribution to our organization."
)
MESSAGES_DIR = Path(__file__).with_name("messages")

load_dotenv(dotenv_path=Path(__file__).with_name(".env"), override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "messages")

app = FastAPI(
    title="Echo Voice API",
    description="Create personalized CEO voice messages with Sarvam AI Instant Voice Cloning.",
    version="1.0.0",
)

UI_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Echo | CEO Voice Messages</title>
  <style>
    :root { font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #101828; background: #f7f8fc; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; }
    .shell { max-width: 1080px; margin: 0 auto; padding: 42px 22px 64px; }
    .brand { font-size: 34px; font-weight: 800; letter-spacing: -.05em; }
    .subtitle { color: #667085; margin: 6px 0 28px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    .card { background: #fff; border: 1px solid #eaecf0; border-radius: 16px; padding: 24px; box-shadow: 0 2px 8px #1018280a; }
    h2 { font-size: 18px; margin: 0 0 18px; }
    label { display: block; font-size: 13px; font-weight: 650; color: #344054; margin: 16px 0 7px; }
    input, textarea, select { width: 100%; border: 1px solid #d0d5dd; border-radius: 9px; padding: 11px 12px; color: #101828; background: #fff; font: inherit; }
    textarea { min-height: 150px; resize: vertical; }
    input:focus, textarea:focus, select:focus { outline: 3px solid #dbeafe; border-color: #2563eb; }
    button { width: 100%; border: 0; border-radius: 9px; padding: 12px 16px; margin-top: 18px; color: #fff; background: #155eef; font: inherit; font-weight: 700; cursor: pointer; }
    button.secondary { background: #0f766e; }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .hint { color: #667085; font-size: 13px; line-height: 1.5; }
    .status { display: none; border-radius: 9px; padding: 11px 12px; margin-top: 16px; font-size: 13px; line-height: 1.45; }
    .status.show { display: block; }
    .status.info { color: #194185; background: #eff8ff; border: 1px solid #b2ddff; }
    .status.error { color: #912018; background: #fef3f2; border: 1px solid #fecdca; }
    .status.success { color: #05603a; background: #ecfdf3; border: 1px solid #abefc6; }
    audio { width: 100%; margin-top: 18px; }
    .download-button { display: inline-block; width: auto; background: #155eef; color: #fff; font-size: 14px; font-weight: 700; margin-top: 14px; text-decoration: none; }
    .download-button:hover { background: #004eeb; }
    .badge { display: inline-block; color: #175cd3; background: #eff8ff; border-radius: 999px; padding: 5px 9px; font-size: 12px; font-weight: 700; }
    @media (max-width: 760px) { .grid { grid-template-columns: 1fr; } .shell { padding-top: 28px; } }
  </style>
</head>
<body>
  <main class="shell">
    <div class="brand">Echo</div>
    <div class="subtitle">Create a personal message in your CEO's cloned voice.</div>
    <div class="grid">
      <section class="card">
        <h2>Create personalized audio</h2>
        <span class="badge">Sarvam Instant Voice Cloning</span>
        <p class="hint">Upload a clear 10–15 second recording. The voice is cloned and the message is generated in one request. Only use a voice you have permission to clone.</p>
        <form id="generate-form">
          <label for="voice-language">Reference language</label>
          <select id="voice-language">
            <option value="en-IN">English (India)</option>
            <option value="hi-IN">Hindi</option>
            <option value="mr-IN">Marathi</option>
            <option value="ta-IN">Tamil</option>
            <option value="te-IN">Telugu</option>
          </select>
          <label for="voice-file">CEO reference recording</label>
          <input id="voice-file" type="file" accept="audio/*" required>
          <label for="first-name">Employee first name</label>
          <input id="first-name" placeholder="e.g. Ananya" required>
          <label>Message the agent will speak</label>
          <p class="hint">Hello {{first_name}}, I would like to personally thank you for your contribution to our organization.</p>
          <label for="message-language">Message language</label>
          <select id="message-language">
            <option value="en-IN">English (India)</option>
            <option value="hi-IN">Hindi</option>
            <option value="mr-IN">Marathi</option>
            <option value="ta-IN">Tamil</option>
            <option value="te-IN">Telugu</option>
          </select>
          <button id="generate-button" class="secondary">Clone voice and generate audio</button>
        </form>
        <div id="message-status" class="status"></div>
        <div id="audio-result"></div>
      </section>
    </div>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);
    function show(id, type, text) {
      const el = $(id); el.className = "status show " + type; el.textContent = text;
    }
    $("generate-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = $("generate-button"); button.disabled = true; button.textContent = "Cloning and generating...";
      show("message-status", "info", "Cloning the CEO voice and generating the personalized message...");
      const body = new FormData();
      body.append("file", $("voice-file").files[0]);
      body.append("language", $("voice-language").value);
      body.append("first_name", $("first-name").value);
      body.append("language_code", $("message-language").value);
      try {
        const response = await fetch("/generate", { method: "POST", body });
        if (!response.ok) {
          const result = await response.json(); throw new Error(result.detail || "Audio generation failed.");
        }
        const audioBlob = await response.blob();
        if (!audioBlob.size) throw new Error("The server returned an empty audio file.");
        const audioUrl = URL.createObjectURL(new Blob([audioBlob], { type: "audio/mpeg" }));
        $("audio-result").innerHTML = "";
        const player = document.createElement("audio");
        player.controls = true;
        player.preload = "auto";
        player.src = audioUrl;
        const download = document.createElement("a");
        download.className = "download-button";
        download.download = $("first-name").value.trim().toLowerCase().replace(/\\s+/g, "-") + "-echo.mp3";
        download.href = audioUrl;
        download.textContent = "Download generated output";
        $("audio-result").append(player, download);
        player.load();
        show("message-status", "success", "CEO voice cloned and personalized audio is ready.");
      } catch (error) {
        show("message-status", "error", error.message);
      } finally {
        button.disabled = false; button.textContent = "Clone voice and generate audio";
      }
    });
  </script>
</body>
</html>
"""


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    detail: str


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def user_interface() -> HTMLResponse:
    return HTMLResponse(content=UI_HTML)


def sarvam_api_key(request_key: str | None) -> str:
    api_key = os.getenv("SARVAM_API_KEY", "").strip() or (request_key or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Sarvam API key is not configured. Set SARVAM_API_KEY or send X-Sarvam-API-Key.",
        )
    return api_key


def sarvam_error(response: requests.Response) -> HTTPException:
    detail = response.text[:500].strip() or "No error details were returned."
    status_code = 502 if response.status_code >= 500 else response.status_code
    return HTTPException(
        status_code=status_code,
        detail=f"Sarvam API returned HTTP {response.status_code}: {detail}",
    )


def decode_audio(result: dict) -> bytes:
    audio_base64 = result.get("audio_b64") or result.get("audio")
    if not isinstance(audio_base64, str) or not audio_base64:
        raise ValueError("Missing audio data in Sarvam response.")
    return base64.b64decode(audio_base64)


def save_message_audio(audio: bytes, employee_name: str) -> Path:
    MESSAGES_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", employee_name.strip()).strip("-_").lower()
    safe_name = safe_name or "employee"
    output_path = MESSAGES_DIR / f"{safe_name}-echo-{uuid.uuid4().hex[:8]}.mp3"
    output_path.write_bytes(audio)
    return output_path


def message_cache_path(employee_name: str) -> str:
    safe_name = re.sub(
        r"[^a-zA-Z0-9_-]+", "-", employee_name.strip()
    ).strip("-_").lower()
    return f"{safe_name or 'employee'}.mp3"


def supabase_headers() -> dict[str, str]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {}
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }


def get_cached_audio(employee_name: str) -> bytes | None:
    headers = supabase_headers()
    if not headers:
        return None
    object_path = quote(message_cache_path(employee_name), safe="")
    response = requests.get(
        f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{object_path}",
        headers=headers,
        timeout=30,
    )
    if response.status_code == 404:
        return None
    if response.status_code == 400:
        try:
            error_body = response.json()
        except ValueError:
            error_body = {}
        if (
            error_body.get("code") == "NoSuchKey"
            or error_body.get("error") == "not_found"
            or str(error_body.get("statusCode")) == "404"
        ):
            return None
    if not response.ok:
        raise RuntimeError(
            f"Supabase cache lookup failed with HTTP {response.status_code}: "
            f"{response.text[:300]}"
        )
    if not response.content:
        raise RuntimeError("Supabase returned an empty cached audio file.")
    return response.content


def cache_audio(employee_name: str, audio: bytes) -> None:
    headers = supabase_headers()
    if not headers:
        return
    object_path = quote(message_cache_path(employee_name), safe="")
    upload_headers = {
        **headers,
        "Content-Type": "audio/mpeg",
        "x-upsert": "false",
    }
    response = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{object_path}",
        headers=upload_headers,
        data=audio,
        timeout=30,
    )
    if response.status_code in (200, 201):
        return
    if response.status_code == 409:
        return
    raise RuntimeError(
        f"Supabase cache upload failed with HTTP {response.status_code}: "
        f"{response.text[:300]}"
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post(
    "/generate",
    response_class=Response,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def generate_personalized_audio(
    file: Annotated[UploadFile, File(description="A clear 10–15 second CEO recording.")],
    first_name: Annotated[str, Form(min_length=1, max_length=100)],
    language: Annotated[str, Form()] = DEFAULT_LANGUAGE_CODE,
    language_code: Annotated[str, Form()] = DEFAULT_LANGUAGE_CODE,
    x_sarvam_api_key: Annotated[str | None, Header()] = None,
) -> Response:
    first_name = first_name.strip()
    personalized_message = FIXED_MESSAGE.replace("{{first_name}}", first_name)
    try:
        cached_audio = get_cached_audio(first_name)
    except (requests.RequestException, RuntimeError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    if cached_audio is not None:
        return Response(
            content=cached_audio,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": 'inline; filename="personalized-ceo-message.mp3"',
                "X-Audio-Cache": "HIT",
                "Cache-Control": "no-store",
            },
        )
    api_key = sarvam_api_key(x_sarvam_api_key)

    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="The reference audio file is empty.")
    if len(audio) > MAX_REFERENCE_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="Reference audio must be smaller than 50 MB.")

    try:
        voice_response = requests.post(
            SARVAM_CREATE_VOICE_URL,
            headers={"api-subscription-key": api_key},
            data={"name": VOICE_PROFILE_NAME, "language": language},
            files={"file": (file.filename or "reference-audio", audio, file.content_type)},
            timeout=60,
        )
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail=f"Could not reach Sarvam: {error}") from error
    if not voice_response.ok:
        raise sarvam_error(voice_response)

    try:
        voice_id = voice_response.json()["data"]["voice_id"]
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(
            status_code=502,
            detail="Sarvam returned an unexpected voice creation response.",
        ) from error

    try:
        response = requests.post(
            SARVAM_CLONE_URL,
            headers={"api-subscription-key": api_key},
            files={
                "voice_id": (None, voice_id),
                "text": (None, personalized_message),
                "language_code": (None, language_code),
                "output_audio_codec": (None, "mp3"),
                "speech_sample_rate": (None, "24000"),
            },
            timeout=60,
        )
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail=f"Could not reach Sarvam: {error}") from error
    if not response.ok:
        raise sarvam_error(response)

    try:
        audio = decode_audio(response.json())
    except (ValueError, TypeError, KeyError, binascii.Error) as error:
        raise HTTPException(
            status_code=502,
            detail="Sarvam returned an unexpected cloned audio response.",
        ) from error
    if not audio:
        raise HTTPException(status_code=502, detail="Sarvam returned an empty audio response.")
    try:
        save_message_audio(audio, first_name)
        cache_audio(first_name, audio)
    except (OSError, requests.RequestException, RuntimeError) as error:
        raise HTTPException(
            status_code=500,
            detail=f"Audio was generated but could not be cached: {error}",
        ) from error
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": 'inline; filename="personalized-ceo-message.mp3"',
            "X-Audio-Cache": "MISS",
            "Cache-Control": "no-store",
        },
    )

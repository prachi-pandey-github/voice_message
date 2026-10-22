import base64
import os
from typing import Any

import requests
import streamlit as st


SARVAM_CREATE_VOICE_URL = "https://api.sarvam.ai/voices/create"
SARVAM_CLONE_URL = "https://api.sarvam.ai/voices/clone"
DEFAULT_MESSAGE = (
    "Hello {{first_name}}, I would like to personally thank you for your "
    "contribution to our organization."
)
VOICE_PROFILE_NAME = "CEO voice"
LANGUAGES = {
    "English (India)": "en-IN",
    "Hindi": "hi-IN",
    "Hinglish": "hi-IN",
    "Marathi": "mr-IN",
    "Tamil": "ta-IN",
    "Telugu": "te-IN",
    "Kannada": "kn-IN",
    "Bengali": "bn-IN",
    "Gujarati": "gu-IN",
    "Malayalam": "ml-IN",
    "Punjabi": "pa-IN",
    "Odia": "od-IN",
}


def personalize_message(template: str, first_name: str) -> str:
    return template.replace("{{first_name}}", first_name)


def _api_error(response: requests.Response) -> str:
    detail = response.text[:500].strip() or "No error details were returned."
    return f"Sarvam API returned HTTP {response.status_code}: {detail}"


def create_cloned_voice(
    reference_audio: Any, api_key: str, voice_name: str, language_code: str
) -> tuple[str, str]:
    audio_bytes = reference_audio.getvalue()
    if len(audio_bytes) > 50 * 1024 * 1024:
        raise ValueError("The reference audio must be smaller than 50 MB.")

    response = requests.post(
        SARVAM_CREATE_VOICE_URL,
        headers={"api-subscription-key": api_key},
        data={"name": voice_name, "language": language_code},
        files={
            "file": (
                getattr(reference_audio, "name", "ceo-reference.wav"),
                audio_bytes,
                getattr(reference_audio, "type", "audio/wav"),
            )
        },
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(_api_error(response))

    try:
        result = response.json()
        voice_id = result["data"]["voice_id"]
        reference_text = result["data"].get("reference_text", "")
        return voice_id, reference_text
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeError("Sarvam returned an unexpected voice creation response.") from error


def synthesize_speech(
    text: str, api_key: str, voice_id: str, language_code: str
) -> bytes:
    response = requests.post(
        SARVAM_CLONE_URL,
        headers={"api-subscription-key": api_key},
        files={
            "voice_id": (None, voice_id),
            "text": (None, text),
            "language_code": (None, language_code),
        },
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(_api_error(response))

    try:
        result = response.json()
        audio_base64 = result.get("audio_b64") or result["audio"]
        return base64.b64decode(audio_base64)
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeError("Sarvam returned an unexpected cloned audio response.") from error


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #f7f8fc; }
        [data-testid="stMain"] h1,
        [data-testid="stMain"] h2,
        [data-testid="stMain"] h3,
        [data-testid="stMain"] h4,
        [data-testid="stMain"] p,
        [data-testid="stMain"] label,
        [data-testid="stMain"] small,
        [data-testid="stMain"] span,
        [data-testid="stMain"] [data-testid="stMarkdownContainer"] {
            color: #101828;
        }
        [data-testid="stMain"] .stCaption,
        [data-testid="stMain"] [data-testid="stCaptionContainer"] {
            color: #667085 !important;
        }
        [data-testid="stSidebar"] { background: #111827; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stCaption,
        [data-testid="stSidebar"] .stAlert p,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
            color: #f9fafb !important;
        }
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea,
        [data-testid="stSidebar"] [data-baseweb="select"] *,
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
            color: #101828 !important;
        }
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] span {
            color: #475467 !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] > div {
            background: #ffffff !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] [role="combobox"],
        [data-testid="stSidebar"] [data-baseweb="select"] [role="combobox"] * {
            color: #101828 !important;
        }
        [data-testid="stSidebar"] [data-baseweb="popover"],
        [data-testid="stSidebar"] [role="listbox"],
        [data-testid="stSidebar"] [role="option"] {
            background: #ffffff !important;
            color: #101828 !important;
        }
        [data-testid="stSidebar"] [data-baseweb="popover"] *,
        [data-testid="stSidebar"] [role="listbox"] *,
        [data-testid="stSidebar"] [role="option"] * {
            color: #101828 !important;
        }
        [data-testid="stSidebar"] [data-testid="stAlert"] p,
        [data-testid="stSidebar"] [data-testid="stAlert"] span {
            color: #344054 !important;
        }
        [data-testid="stSidebar"] .stButton button p,
        [data-testid="stSidebar"] .stButton button span {
            color: #ffffff !important;
        }
        [data-testid="stTextArea"] textarea,
        [data-testid="stTextInput"] input,
        [data-testid="stFileUploaderDropzone"] {
            color: #101828 !important;
            background: #ffffff !important;
            caret-color: #101828 !important;
            pointer-events: auto !important;
            user-select: text !important;
        }
        [data-testid="stTextArea"] textarea {
            display: block !important;
            min-height: 160px !important;
            cursor: text !important;
        }
        [data-testid="stTextArea"] textarea::placeholder,
        [data-testid="stTextInput"] input::placeholder {
            color: #667085 !important;
            opacity: 1 !important;
        }
        [data-testid="stWidgetLabel"] p,
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] span {
            color: #344054 !important;
        }
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
            color: #f9fafb !important;
        }
        [data-testid="stAlert"] p,
        [data-testid="stAlert"] li,
        [data-testid="stAlert"] span {
            color: #344054 !important;
        }
        .stButton button p,
        .stButton button span,
        .stButton button[kind="primary"] p,
        .stButton button[kind="primary"] span {
            color: #ffffff !important;
        }
        .stButton button[kind="secondary"] p,
        .stButton button[kind="secondary"] span,
        .stDownloadButton button p,
        .stDownloadButton button span {
            color: #344054 !important;
        }
        .brand { font-size: 2rem; font-weight: 800; letter-spacing: -0.04em; color: #111827; }
        .subtitle { color: #667085; margin-top: -0.7rem; margin-bottom: 1.5rem; }
        .metric-card {
            background: white; border: 1px solid #eaecf0; border-radius: 14px;
            padding: 1rem 1.2rem; box-shadow: 0 1px 2px rgba(16,24,40,.04);
        }
        .metric-label { color: #667085; font-size: .82rem; }
        .metric-value { color: #101828; font-size: 1.6rem; font-weight: 700; }
        .notice {
            background: #eef4ff; border: 1px solid #c7d7fe; border-radius: 10px;
            padding: .8rem 1rem; color: #194185; font-size: .9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="Echo | CEO voice messages",
        page_icon="🔊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()

    if "generated_audio" not in st.session_state:
        st.session_state.generated_audio = {}
    if "voice_id" not in st.session_state:
        st.session_state.voice_id = ""
    if "message_template" not in st.session_state:
        st.session_state.message_template = DEFAULT_MESSAGE

    with st.sidebar:
        st.markdown("## 🔊 Echo")
        st.caption("Personal messages, in the CEO's voice")
        st.divider()
        st.markdown("### Clone the CEO's voice")
        env_key = os.getenv("SARVAM_API_KEY", "")
        api_key = st.text_input(
            "Sarvam API key",
            value=env_key,
            type="password",
            help="Use SARVAM_API_KEY in your environment for production deployments.",
        )
        reference_audio = st.file_uploader(
            "CEO reference recording",
            type=["wav", "mp3", "m4a", "ogg", "webm"],
            help="Use a clear 10–15 second recording of the CEO speaking. Maximum 50 MB.",
        )
        consent = st.checkbox(
            "I confirm I have the CEO's permission to clone and use this voice.",
            help="Voice cloning must only be used with the speaker's authorization.",
        )
        clone_voice = st.button(
            "Create CEO voice",
            type="primary",
            use_container_width=True,
            disabled=not (api_key and reference_audio and consent),
        )
        if clone_voice:
            with st.spinner("Creating the CEO voice profile..."):
                try:
                    voice_id, reference_text = create_cloned_voice(
                        reference_audio,
                        api_key,
                        VOICE_PROFILE_NAME,
                        LANGUAGES["English (India)"],
                    )
                    st.session_state.voice_id = voice_id
                    st.session_state.generated_audio = {}
                    st.success(f"Voice created: {voice_id}")
                    if reference_text:
                        st.caption(f"Reference transcript: {reference_text}")
                except (requests.RequestException, RuntimeError, ValueError) as error:
                    st.error(f"Could not create voice: {error}")
        if st.session_state.voice_id:
            st.success(f"Active cloned voice: `{st.session_state.voice_id}`")
        else:
            st.info("Upload a reference clip and create the CEO voice to begin.")
        language_name = st.selectbox("Message language", list(LANGUAGES))
        st.divider()
        st.caption("The reference clip is sent to Sarvam to create a saved voice ID. Use only an authorized voice.")

    st.markdown('<div class="brand">Echo</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Create a personal thank-you message for every employee.</div>',
        unsafe_allow_html=True,
    )

    first_name = st.text_input(
        "Employee first name",
        placeholder="Enter the employee's first name",
        help="This name replaces {{first_name}} in the spoken message.",
    ).strip()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Employee</div><div class="metric-value">{first_name or "Not set"}</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Messages generated</div><div class="metric-value">{len(st.session_state.generated_audio)}</div></div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Active voice</div><div class="metric-value" style="font-size:1.15rem">{"Cloned CEO" if st.session_state.voice_id else "Not set"}</div></div>',
            unsafe_allow_html=True,
        )

    st.write("")
    editor_col, preview_col = st.columns([1.05, 0.95], gap="large")
    with editor_col:
        st.subheader("Message the agent should speak")
        template = st.text_area(
            "Message template",
            key="message_template",
            height=160,
            help="Use {{first_name}} where the employee's first name should be inserted.",
        ).strip()
        st.caption(f"{len(template)} characters · Generated using the cloned CEO voice")

    with preview_col:
        st.subheader("Live preview")
        st.markdown(
            f'<div class="notice">This is how the message will sound for <strong>{first_name or "the employee"}</strong>.</div>',
            unsafe_allow_html=True,
        )
        preview_text = personalize_message(template, first_name or "{{first_name}}")
        st.write("")
        st.info(f"“{preview_text}”")
        generate_preview = st.button(
            f"Generate preview for {first_name or 'employee'}",
            type="primary",
            use_container_width=True,
            disabled=not api_key or not st.session_state.voice_id or not first_name or "{{first_name}}" not in template,
        )
        if generate_preview:
            with st.spinner("Creating the preview..."):
                try:
                    st.session_state.generated_audio[first_name] = synthesize_speech(
                        preview_text,
                        api_key,
                        st.session_state.voice_id,
                        LANGUAGES[language_name],
                    )
                except (requests.RequestException, RuntimeError) as error:
                    st.error(f"Could not generate audio: {error}")
        if first_name in st.session_state.generated_audio:
            audio = st.session_state.generated_audio[first_name]
            st.audio(audio, format="audio/wav")
            st.download_button(
                "Download preview",
                audio,
                file_name=f"{first_name.lower()}-echo.wav",
                mime="audio/wav",
                use_container_width=True,
            )

    if first_name in st.session_state.generated_audio:
        st.subheader("Ready to share")
        st.caption("Your personalized audio message is ready.")
        audio = st.session_state.generated_audio[first_name]
        st.audio(audio, format="audio/wav")
        st.download_button(
            f"Download {first_name}'s audio",
            audio,
            file_name=f"{first_name.lower()}-echo.wav",
            mime="audio/wav",
            key=f"download-{first_name}",
        )

    if not api_key:
        st.warning("Add your Sarvam API key in the sidebar to generate audio.")
    elif not st.session_state.voice_id:
        st.warning("Upload an authorized CEO reference recording and create the cloned voice first.")
    elif not first_name:
        st.warning("Enter an employee first name before generating audio.")
    st.caption("This demo generates audio on demand. Add your authenticated email provider and storage layer before sending messages in production.")


if __name__ == "__main__":
    main()
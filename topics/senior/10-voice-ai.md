# Module 10: Voice AI & Real-time Systems — Đáp án phỏng vấn

> **Lưu ý:** Đây là GAP area. Nắm vững kiến trúc, các trade-offs, và code examples để trả lời tự tin. Không cần deep expertise nhưng cần hiểu rõ "how it fits together".

---

## 1. Voicebot Architecture

### Q: Giải thích end-to-end architecture của một voicebot?

**Trả lời mẫu:**

```
===== VOICEBOT END-TO-END ARCHITECTURE =====

User speaks
    │
    ▼
[Microphone / Phone]
    │  Raw audio (PCM 16kHz, 16-bit)
    ▼
[VAD - Voice Activity Detection]  ←── Silero VAD / WebRTC VAD
    │  Detects speech start/end
    │  Handles barge-in (user interrupts bot)
    ▼
[STT - Speech-to-Text]  ←── Deepgram / Whisper / AssemblyAI
    │  Audio chunks → text (streaming)
    │  ~200-400ms latency
    ▼
[Context Manager]
    │  Conversation history
    │  Entity tracking (user name, preferences)
    ▼
[LLM - Language Model]  ←── GPT-4o / GPT-4o-mini / Claude
    │  Text → Response text (streaming)
    │  ~300-800ms TTFT (Time to First Token)
    ▼
[TTS - Text-to-Speech]  ←── ElevenLabs / OpenAI TTS / Google
    │  Text chunks → audio (streaming by sentence)
    │  ~100-300ms latency
    ▼
[Audio Playback / Phone]
    │
    ▼
User hears response
    
===== LATENCY BUDGET =====

Target: < 2 seconds end-to-end

Component          Min    Typical    Max
─────────────────────────────────────────
VAD detection      10ms    20ms      50ms
STT transcription  150ms  300ms     500ms
Network round-trip  20ms   50ms     100ms
LLM TTFT           200ms  500ms     900ms
TTS first chunk     80ms  200ms     350ms
─────────────────────────────────────────
TOTAL              460ms  1070ms    1900ms

Key optimization: Start TTS as soon as first LLM sentence arrives,
don't wait for complete response.
```

**Latency budget explanation for interview:**

```python
# Latency breakdown visualization
latency_budget = {
    "STT": {
        "range_ms": (150, 400),
        "notes": "Streaming STT giảm latency vs batch",
        "key_metric": "Latency to first word"
    },
    "LLM_TTFT": {
        "range_ms": (200, 800),
        "notes": "TTFT = Time to First Token, quan trọng hơn total latency",
        "key_metric": "Time to First Token (TTFT)"
    },
    "TTS": {
        "range_ms": (80, 300),
        "notes": "Stream by sentence, không đợi full response",
        "key_metric": "Latency to first audio byte"
    },
    "target_total_ms": 2000,
    "ideal_total_ms": 1000  # Sub-1s cho premium experience
}

# Component selection based on latency
component_options = {
    "STT": {
        "fastest": "Deepgram Nova-2 (streaming)",
        "best_accuracy": "AssemblyAI Universal-2",
        "cheapest": "Whisper large-v3 (self-hosted)",
        "balanced": "Deepgram Nova-2"
    },
    "LLM": {
        "fastest": "GPT-4o-mini (~200ms TTFT)",
        "smartest": "GPT-4o (~500ms TTFT)",
        "cheapest": "GPT-4o-mini",
        "balanced": "GPT-4o-mini for most turns, GPT-4o for complex"
    },
    "TTS": {
        "best_voice": "ElevenLabs (highest quality)",
        "fastest": "OpenAI TTS-1 (optimized for speed)",
        "cheapest": "Google Cloud TTS",
        "balanced": "OpenAI TTS-1"
    }
}
```

---

## 2. Speech-to-Text (STT)

### Q: So sánh Whisper, Deepgram, AssemblyAI. Khi nào dùng cái nào?

**Trả lời mẫu:**

| Feature | OpenAI Whisper | Deepgram Nova-2 | AssemblyAI Universal-2 |
|---------|---------------|-----------------|----------------------|
| **Type** | Batch (API) / Streaming (self-hosted) | Streaming + Batch | Streaming + Batch |
| **WER (English)** | ~3-5% | ~2-3% | ~2-3% |
| **Latency** | 500ms-2s (API) | 200-300ms (streaming) | 300-500ms |
| **Real-time** | Self-hosted only | Yes (WebSocket) | Yes (WebSocket) |
| **Word timestamps** | Yes | Yes | Yes |
| **Speaker diarization** | No | Yes ($) | Yes |
| **Custom vocab** | No | Yes | Yes |
| **Cost** | $0.006/min | $0.0059/min | $0.0065/min |
| **Vietnamese support** | Good | Limited | Limited |
| **Self-hosted** | Yes | No | No |

**WER (Word Error Rate):** Tỉ lệ lỗi = (substitutions + deletions + insertions) / total words. Lower is better. Whisper ~3% = trong 100 từ, có 3 từ sai.

```python
# === Deepgram Streaming STT ===
import asyncio
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

async def transcribe_audio_stream(audio_stream_generator):
    """
    Real-time streaming STT với Deepgram
    audio_stream_generator: async generator yielding audio chunks (bytes)
    """
    deepgram = DeepgramClient(api_key="your-deepgram-key")
    
    transcript_parts = []
    final_transcript = asyncio.Event()
    
    # Create live transcription connection
    connection = deepgram.listen.asynclive.v("1")
    
    # Event handlers
    async def on_message(self, result, **kwargs):
        """Called for each transcription result"""
        sentence = result.channel.alternatives[0].transcript
        
        if result.is_final:
            # Final: high confidence, end of utterance
            transcript_parts.append(sentence)
            print(f"[FINAL] {sentence}")
        else:
            # Interim: real-time partial results
            print(f"[INTERIM] {sentence}", end="\r")
    
    async def on_utterance_end(self, utterance_end, **kwargs):
        """Called when user stops speaking"""
        full_transcript = " ".join(transcript_parts)
        print(f"\n[UTTERANCE END] Complete: {full_transcript}")
        final_transcript.set()
    
    async def on_error(self, error, **kwargs):
        print(f"STT Error: {error}")
    
    connection.on(LiveTranscriptionEvents.Transcript, on_message)
    connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
    connection.on(LiveTranscriptionEvents.Error, on_error)
    
    # Connection options
    options = LiveOptions(
        model="nova-2",
        language="en-US",
        encoding="linear16",
        channels=1,
        sample_rate=16000,
        interim_results=True,       # Get partial results
        utterance_end_ms=1000,      # 1s silence = utterance end
        vad_events=True,            # Voice activity detection
        endpointing=500,            # ms of silence before finalization
        smart_format=True,          # Punctuation, capitalization
        punctuate=True,
        diarize=False,              # Speaker diarization (costs more)
        keywords=["FastAPI", "Temporal", "LangChain:2"],  # Boost keywords
    )
    
    # Start connection
    await connection.start(options)
    
    # Stream audio chunks
    async for audio_chunk in audio_stream_generator:
        connection.send(audio_chunk)
    
    # Wait for final transcript
    await asyncio.wait_for(final_transcript.wait(), timeout=10.0)
    await connection.finish()
    
    return " ".join(transcript_parts)

# Usage example
async def example_usage():
    async def mock_audio_generator():
        """Simulate audio chunks from microphone"""
        import wave
        with wave.open("input.wav", "rb") as f:
            chunk_size = 8000  # 0.5 seconds at 16kHz
            while True:
                data = f.readframes(chunk_size)
                if not data:
                    break
                yield data
                await asyncio.sleep(0.5)
    
    transcript = await transcribe_audio_stream(mock_audio_generator())
    print(f"Final transcript: {transcript}")
```

---

## 3. Voice Activity Detection (VAD)

### Q: VAD là gì? Tại sao cần và hoạt động thế nào?

**Trả lời mẫu:**

VAD (Voice Activity Detection) phát hiện khi nào người dùng đang nói và khi nào im lặng. Cần thiết để:

1. **Segment audio**: Chỉ gửi speech frames đến STT, không gửi silence
2. **End-of-utterance detection**: Biết khi người dùng nói xong → trigger LLM
3. **Barge-in handling**: Phát hiện người dùng ngắt lời bot đang nói

```python
import numpy as np
import torch
import asyncio
from typing import AsyncGenerator

# === Silero VAD (ML-based, more accurate) ===
class SileroVAD:
    def __init__(self, threshold: float = 0.5, sampling_rate: int = 16000):
        # Load model
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False
        )
        self.get_speech_timestamps = utils[0]
        self.threshold = threshold
        self.sampling_rate = sampling_rate
        self.model.eval()
    
    def is_speech(self, audio_chunk: bytes) -> tuple[bool, float]:
        """
        Returns (is_speech, confidence_score)
        audio_chunk: PCM 16-bit, 16kHz
        """
        # Convert bytes to numpy array
        audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        # Get VAD probability
        tensor = torch.FloatTensor(audio_float32)
        
        with torch.no_grad():
            speech_prob = self.model(tensor, self.sampling_rate).item()
        
        return speech_prob > self.threshold, speech_prob
    
    def reset_states(self):
        """Reset between utterances"""
        self.model.reset_states()


# === End-of-Utterance Detection ===
class UtteranceDetector:
    def __init__(
        self,
        vad: SileroVAD,
        silence_duration_ms: int = 700,   # 700ms silence = end of utterance
        min_speech_ms: int = 200,          # Minimum speech to be valid
        sampling_rate: int = 16000
    ):
        self.vad = vad
        self.silence_threshold_frames = (silence_duration_ms * sampling_rate) // (1000 * 512)
        self.min_speech_frames = (min_speech_ms * sampling_rate) // (1000 * 512)
        
        self.speech_frames = 0
        self.silence_frames = 0
        self.is_speaking = False
        self.audio_buffer = bytearray()
    
    def process_chunk(self, audio_chunk: bytes) -> dict:
        """
        Process audio chunk, return state
        Returns: {"state": "speaking"|"silence"|"utterance_end", "audio": bytes|None}
        """
        is_speech, confidence = self.vad.is_speech(audio_chunk)
        
        if is_speech:
            self.speech_frames += 1
            self.silence_frames = 0
            self.is_speaking = True
            self.audio_buffer.extend(audio_chunk)
            return {"state": "speaking", "audio": None, "confidence": confidence}
        else:
            self.silence_frames += 1
            
            if self.is_speaking:
                self.audio_buffer.extend(audio_chunk)  # Include trailing silence
                
                # Check if utterance is complete
                if (self.silence_frames >= self.silence_threshold_frames and
                        self.speech_frames >= self.min_speech_frames):
                    
                    # Utterance complete!
                    utterance_audio = bytes(self.audio_buffer)
                    self._reset()
                    
                    return {
                        "state": "utterance_end",
                        "audio": utterance_audio,
                        "confidence": confidence
                    }
            
            return {"state": "silence", "audio": None, "confidence": confidence}
    
    def _reset(self):
        self.speech_frames = 0
        self.silence_frames = 0
        self.is_speaking = False
        self.audio_buffer = bytearray()
        self.vad.reset_states()


# === Barge-in Handler ===
class BargeinHandler:
    """Detects when user interrupts bot speech"""
    
    def __init__(self, vad: SileroVAD, bot_speaking: asyncio.Event):
        self.vad = vad
        self.bot_speaking = bot_speaking
        self.consecutive_speech_frames = 0
        self.barge_in_threshold = 3  # 3 consecutive speech frames = barge-in
    
    def check_barge_in(self, audio_chunk: bytes) -> bool:
        """Returns True if user is interrupting"""
        if not self.bot_speaking.is_set():
            return False
        
        is_speech, confidence = self.vad.is_speech(audio_chunk)
        
        if is_speech and confidence > 0.7:
            self.consecutive_speech_frames += 1
        else:
            self.consecutive_speech_frames = 0
        
        if self.consecutive_speech_frames >= self.barge_in_threshold:
            self.consecutive_speech_frames = 0
            return True
        
        return False
```

---

## 4. Text-to-Speech (TTS)

### Q: Implement streaming TTS với ElevenLabs và OpenAI?

**Trả lời mẫu:**

```python
import asyncio
import aiohttp
from openai import AsyncOpenAI
from elevenlabs.client import AsyncElevenLabs
from elevenlabs import VoiceSettings
import re

openai_client = AsyncOpenAI()
elevenlabs_client = AsyncElevenLabs(api_key="your-elevenlabs-key")

# === OpenAI TTS Streaming ===
async def openai_tts_stream(text: str) -> AsyncGenerator[bytes, None]:
    """
    Stream audio from OpenAI TTS
    Returns: async generator of audio bytes (MP3)
    """
    async with openai_client.audio.speech.with_streaming_response.create(
        model="tts-1",           # tts-1: faster, tts-1-hd: higher quality
        voice="alloy",           # alloy, echo, fable, onyx, nova, shimmer
        input=text,
        response_format="opus",  # Opus: best for real-time streaming
        speed=1.0
    ) as response:
        async for chunk in response.iter_bytes(chunk_size=4096):
            yield chunk

# === ElevenLabs Streaming (Higher quality) ===
async def elevenlabs_tts_stream(
    text: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
) -> AsyncGenerator[bytes, None]:
    """
    Stream audio from ElevenLabs
    Returns: async generator of audio bytes (MP3)
    """
    audio_stream = elevenlabs_client.text_to_speech.stream(
        text=text,
        voice_id=voice_id,
        voice_settings=VoiceSettings(
            stability=0.71,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True
        ),
        model_id="eleven_turbo_v2",  # Turbo: lower latency
        output_format="mp3_44100_128"
    )
    
    async for chunk in audio_stream:
        if isinstance(chunk, bytes):
            yield chunk

# === Key Optimization: Sentence-level streaming ===
async def llm_to_tts_pipeline(user_message: str) -> AsyncGenerator[bytes, None]:
    """
    Pipeline: LLM → sentence chunking → TTS streaming
    
    Key insight: Don't wait for full LLM response.
    Stream LLM output → split by sentence → TTS each sentence immediately.
    This reduces perceived latency significantly.
    """
    sentence_buffer = ""
    sentence_enders = re.compile(r'[.!?。！？]')
    
    # Stream from LLM
    async for chunk in await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_message}],
        stream=True,
        max_tokens=500
    ):
        if not chunk.choices or not chunk.choices[0].delta.content:
            continue
        
        token = chunk.choices[0].delta.content
        sentence_buffer += token
        
        # Check if we have a complete sentence
        if sentence_enders.search(token):
            sentence = sentence_buffer.strip()
            sentence_buffer = ""
            
            if len(sentence) > 10:  # Skip very short fragments
                # Stream TTS for this sentence immediately
                async for audio_chunk in openai_tts_stream(sentence):
                    yield audio_chunk
    
    # Handle remaining text
    if sentence_buffer.strip() and len(sentence_buffer.strip()) > 5:
        async for audio_chunk in openai_tts_stream(sentence_buffer.strip()):
            yield audio_chunk

# === Caching Common Phrases ===
import hashlib
import aiofiles
from pathlib import Path

class TTSCache:
    """Cache TTS audio for common phrases to reduce latency"""
    
    def __init__(self, cache_dir: str = "/tmp/tts_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        # Pre-warm common phrases
        self.common_phrases = [
            "Xin chào! Tôi có thể giúp gì cho bạn?",
            "Vui lòng chờ một moment.",
            "Tôi không hiểu, bạn có thể nói lại không?",
            "Cảm ơn bạn đã gọi!",
            "Để tôi kiểm tra thông tin cho bạn..."
        ]
    
    def _cache_key(self, text: str, voice: str) -> str:
        return hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
    
    async def get_or_generate(self, text: str, voice: str = "alloy") -> bytes:
        cache_key = self._cache_key(text, voice)
        cache_file = self.cache_dir / f"{cache_key}.opus"
        
        if cache_file.exists():
            async with aiofiles.open(cache_file, "rb") as f:
                return await f.read()
        
        # Generate and cache
        audio_chunks = []
        async for chunk in openai_tts_stream(text):
            audio_chunks.append(chunk)
        
        audio_data = b"".join(audio_chunks)
        
        async with aiofiles.open(cache_file, "wb") as f:
            await f.write(audio_data)
        
        return audio_data
    
    async def prewarm(self):
        """Pre-generate common phrases at startup"""
        tasks = [
            self.get_or_generate(phrase)
            for phrase in self.common_phrases
        ]
        await asyncio.gather(*tasks)
        print(f"TTS cache warmed with {len(self.common_phrases)} phrases")
```

---

## 5. Real-time Systems

### Q: WebSocket vs WebRTC vs SSE - khi nào dùng cái nào?

**Trả lời mẫu:**

| Feature | SSE | WebSocket | WebRTC |
|---------|-----|-----------|--------|
| **Direction** | Server → Client only | Bidirectional | Bidirectional (P2P) |
| **Protocol** | HTTP/1.1, HTTP/2 | WS (TCP) | UDP (DTLS/SRTP) |
| **Latency** | ~100-300ms | ~50-150ms | ~20-100ms |
| **Audio/Video** | Không phù hợp | Possible but suboptimal | Designed for this |
| **Browser support** | Native EventSource API | WebSocket API | RTCPeerConnection |
| **Load balancing** | Easy (stateless HTTP) | Sticky sessions needed | Complex (TURN/STUN) |
| **Firewall friendly** | Yes (port 80/443) | Usually yes | Sometimes blocked |
| **Use case** | LLM token streaming, notifications | Chat, voice assistant | Video calls, phone |
| **Complexity** | Low | Medium | High |

```python
# === FastAPI WebSocket cho Voice Assistant ===
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import asyncio
import json
import base64

app = FastAPI()

class VoiceAssistantSession:
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.utterance_detector = UtteranceDetector(SileroVAD())
        self.bot_speaking = asyncio.Event()
        self.barge_in_handler = BargeinHandler(SileroVAD(), self.bot_speaking)
        self.conversation_history = []
        self.current_tts_task = None
    
    async def send_audio(self, audio_bytes: bytes):
        """Send audio to client"""
        encoded = base64.b64encode(audio_bytes).decode()
        await self.websocket.send_json({
            "type": "audio",
            "data": encoded,
            "format": "opus"
        })
    
    async def send_transcript(self, text: str, is_final: bool = False):
        """Send transcript update to client"""
        await self.websocket.send_json({
            "type": "transcript",
            "text": text,
            "is_final": is_final
        })

@app.websocket("/voice/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = VoiceAssistantSession(websocket, session_id)
    
    # Send ready signal
    await websocket.send_json({"type": "ready", "session_id": session_id})
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive()
            
            if data["type"] == "websocket.receive":
                if "bytes" in data:
                    # Audio chunk received
                    audio_chunk = data["bytes"]
                    await handle_audio_chunk(session, audio_chunk)
                
                elif "text" in data:
                    message = json.loads(data["text"])
                    await handle_control_message(session, message)
    
    except WebSocketDisconnect:
        print(f"Session {session_id} disconnected")
    except Exception as e:
        print(f"Session {session_id} error: {e}")
        await websocket.close()

async def handle_audio_chunk(session: VoiceAssistantSession, audio_chunk: bytes):
    """Process incoming audio chunk"""
    
    # Check for barge-in
    if session.barge_in_handler.check_barge_in(audio_chunk):
        # User interrupted bot
        if session.current_tts_task:
            session.current_tts_task.cancel()
        session.bot_speaking.clear()
        await session.websocket.send_json({"type": "barge_in"})
    
    # VAD processing
    result = session.utterance_detector.process_chunk(audio_chunk)
    
    if result["state"] == "utterance_end" and result["audio"]:
        # User finished speaking → process utterance
        asyncio.create_task(
            process_utterance(session, result["audio"])
        )

async def process_utterance(session: VoiceAssistantSession, audio: bytes):
    """Full pipeline: audio → STT → LLM → TTS"""
    
    # 1. STT
    transcript = await transcribe_audio_stream(iter([audio]))
    await session.send_transcript(transcript, is_final=True)
    
    # 2. Update conversation history
    session.conversation_history.append({
        "role": "user",
        "content": transcript
    })
    
    # 3. LLM + TTS pipeline
    session.bot_speaking.set()
    
    async def tts_task():
        async for audio_chunk in llm_to_tts_pipeline_with_history(
            session.conversation_history
        ):
            if session.websocket.client_state == WebSocketState.CONNECTED:
                await session.send_audio(audio_chunk)
        session.bot_speaking.clear()
    
    session.current_tts_task = asyncio.create_task(tts_task())

async def handle_control_message(session: VoiceAssistantSession, message: dict):
    """Handle control messages (mute, settings, etc.)"""
    msg_type = message.get("type")
    
    if msg_type == "mute":
        session.utterance_detector._reset()
    elif msg_type == "settings":
        # Update session settings
        pass

async def llm_to_tts_pipeline_with_history(history: list) -> AsyncGenerator[bytes, None]:
    """LLM with conversation history → TTS stream"""
    messages = [
        {"role": "system", "content": "You are a helpful voice assistant. Keep responses concise."},
        *history
    ]
    
    sentence_buffer = ""
    sentence_enders = re.compile(r'[.!?。！？]')
    
    async for chunk in await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=True,
        max_tokens=300  # Keep voice responses short
    ):
        if not chunk.choices or not chunk.choices[0].delta.content:
            continue
        
        token = chunk.choices[0].delta.content
        sentence_buffer += token
        
        if sentence_enders.search(token):
            sentence = sentence_buffer.strip()
            sentence_buffer = ""
            if len(sentence) > 10:
                async for audio_chunk in openai_tts_stream(sentence):
                    yield audio_chunk
    
    if sentence_buffer.strip():
        async for audio_chunk in openai_tts_stream(sentence_buffer.strip()):
            yield audio_chunk
```

#### Audio Format Comparison

```python
# Audio format trade-offs
audio_formats = {
    "PCM (Raw)": {
        "bitrate": "256 kbps (16kHz, 16-bit)",
        "latency": "Lowest",
        "quality": "Perfect (lossless)",
        "use_case": "Internal processing, STT input",
        "note": "No compression overhead"
    },
    "MP3": {
        "bitrate": "32-320 kbps",
        "latency": "Medium (codec delay ~100ms)",
        "quality": "Good",
        "use_case": "Pre-recorded audio, podcast",
        "note": "Not ideal for real-time streaming"
    },
    "Opus": {
        "bitrate": "6-510 kbps (typically 32-64kbps)",
        "latency": "~5-20ms (very low)",
        "quality": "Excellent",
        "use_case": "BEST for real-time voice streaming",
        "note": "Designed for real-time comms, used in WebRTC, Discord, Zoom"
    },
    "AAC": {
        "bitrate": "16-320 kbps",
        "latency": "Low",
        "quality": "Very good",
        "use_case": "iOS/macOS, Apple ecosystem",
        "note": "Good compression but more CPU"
    }
}

# Recommendation for voicebot
recommended_pipeline = {
    "capture": "PCM (16kHz, 16-bit, mono)",
    "STT_input": "PCM or WebM/Opus",
    "TTS_output": "Opus (for WebSocket streaming)",
    "storage": "MP3 or Opus",
    "phone_calls": "μ-law (G.711) or PCMA for Twilio"
}
```

#### Backpressure Handling

```python
import asyncio
from asyncio import Queue

async def audio_pipeline_with_backpressure(
    audio_input_stream,
    websocket: WebSocket,
    max_queue_size: int = 10
):
    """
    Handle backpressure: nếu client không consume fast enough,
    drop old audio chunks thay vì buffer mãi (prevent lag buildup)
    """
    audio_queue = Queue(maxsize=max_queue_size)
    
    async def producer():
        """Generate TTS audio"""
        async for audio_chunk in llm_to_tts_pipeline("Hello world"):
            try:
                # Non-blocking put, drop if full (drop oldest strategy)
                if audio_queue.full():
                    audio_queue.get_nowait()  # Drop oldest chunk
                audio_queue.put_nowait(audio_chunk)
            except asyncio.QueueFull:
                pass  # Drop chunk if still full
    
    async def consumer():
        """Send to WebSocket"""
        while True:
            try:
                # Wait max 1 second for next chunk
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
                
                if chunk is None:  # Sentinel value
                    break
                
                await websocket.send_bytes(chunk)
                audio_queue.task_done()
            
            except asyncio.TimeoutError:
                # No audio for 1 second - check if done
                if audio_queue.empty():
                    break
    
    # Run producer and consumer concurrently
    await asyncio.gather(producer(), consumer())
```

---

## 6. Latency Optimization for Voice

### Q: Các kỹ thuật tối ưu latency cho voice AI?

**Trả lời mẫu:**

```
LATENCY OPTIMIZATION STRATEGIES:

1. Sentence Streaming Pipeline (biggest impact)
   
   WITHOUT optimization:
   LLM generates full response (2-3s) → TTS converts (0.5s) → Play
   Total: 2.5-3.5s
   
   WITH sentence streaming:
   LLM generates sentence 1 (0.3s) → TTS converts (0.2s) → Play
   Perceived latency: 0.5s ← user hears first words quickly
   
2. Parallel Processing
   
   LLM stream: [sent1][sent2][sent3][sent4]
   TTS queue:       [tts1][tts2][tts3]
   Audio output:        [play1][play2][play3]
   
   TTS converts sent N+1 while sent N is playing.
```

```python
import asyncio
from asyncio import Queue

async def optimized_voice_pipeline(
    conversation_history: list,
    audio_output_queue: Queue
):
    """
    Optimized pipeline với parallel LLM + TTS processing
    
    Architecture:
    LLM streaming → sentence queue → TTS workers (parallel) → audio queue
    """
    sentence_queue = Queue(maxsize=5)
    
    # === LLM Producer: stream tokens, emit sentences ===
    async def llm_producer():
        sentence_buffer = ""
        sentence_enders = re.compile(r'(?<=[.!?。！？])\s')
        
        async for chunk in await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_history,
            stream=True,
            temperature=0.7,
            max_tokens=400
        ):
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if not delta:
                continue
            
            sentence_buffer += delta
            
            # Split on sentence boundaries
            parts = sentence_enders.split(sentence_buffer, maxsplit=1)
            if len(parts) > 1:
                sentence = parts[0].strip()
                sentence_buffer = parts[1]
                
                if len(sentence) > 8:
                    await sentence_queue.put(sentence)
        
        # Flush remaining
        if sentence_buffer.strip():
            await sentence_queue.put(sentence_buffer.strip())
        
        await sentence_queue.put(None)  # Sentinel
    
    # === TTS Consumer: convert sentences to audio ===
    async def tts_consumer():
        while True:
            sentence = await sentence_queue.get()
            
            if sentence is None:
                await audio_output_queue.put(None)  # Signal done
                break
            
            # Convert to audio
            async for audio_chunk in openai_tts_stream(sentence):
                await audio_output_queue.put(audio_chunk)
    
    # Run both concurrently
    await asyncio.gather(
        llm_producer(),
        tts_consumer()
    )

# === Model Selection Strategy ===
async def smart_model_selection(
    user_input: str,
    conversation_history: list,
    latency_budget_ms: int = 2000
) -> str:
    """
    Choose model based on task complexity and latency budget
    """
    # Quick heuristic: use fast model for simple queries
    simple_patterns = [
        r'\b(hi|hello|hey|thanks|bye|yes|no|ok|okay)\b',
        r'^.{1,20}$',  # Very short inputs
        r'\b(what time|what day|current|today)\b'
    ]
    
    is_simple = any(
        re.search(pattern, user_input.lower())
        for pattern in simple_patterns
    )
    
    if is_simple or latency_budget_ms < 1500:
        model = "gpt-4o-mini"  # ~200ms TTFT
    else:
        model = "gpt-4o"       # ~500ms TTFT, better for complex tasks
    
    return model

# === Common Phrases Cache ===
COMMON_PHRASES_AUDIO = {}  # Preloaded at startup

async def preload_common_phrases():
    """Preload TTS for frequent phrases to serve instantly"""
    phrases = {
        "greeting": "Hi! How can I help you today?",
        "thinking": "Let me think about that for a moment.",
        "clarify": "Could you please repeat that?",
        "goodbye": "Goodbye! Have a great day!",
        "wait": "Please hold on while I look that up.",
        "error": "I'm sorry, I encountered an issue. Please try again."
    }
    
    cache = TTSCache()
    for key, phrase in phrases.items():
        audio = await cache.get_or_generate(phrase)
        COMMON_PHRASES_AUDIO[key] = audio
    
    print(f"Preloaded {len(COMMON_PHRASES_AUDIO)} common phrases")

async def get_phrase_audio(phrase_key: str) -> bytes:
    """Serve cached phrase instantly, ~0ms latency"""
    return COMMON_PHRASES_AUDIO.get(phrase_key, b"")
```

---

## 7. Production Platforms

### Q: LiveKit, Daily.co, Twilio - so sánh và khi nào dùng?

**Trả lời mẫu:**

| Feature | LiveKit | Daily.co | Twilio |
|---------|---------|----------|--------|
| **Type** | Open-source WebRTC | WebRTC SaaS | Communications PaaS |
| **Self-hosting** | Yes | No | No |
| **AI Pipeline** | Built-in livekit-agents | Manual | Twilio Voice + AI |
| **Phone calls** | No (WebRTC only) | No | Yes (PSTN, SIP) |
| **Video** | Yes | Yes | Yes |
| **Pricing** | Free (self-host) / $0.002/min | $0.004/min | $0.013/min (voice) |
| **Latency** | ~50-100ms | ~50-100ms | ~100-200ms |
| **Best for** | AI voice agents (web/mobile) | Web video apps | Phone/SMS automation |

```python
# === LiveKit Agents: Production Voice AI Pipeline ===
# livekit-agents provides built-in VAD → STT → LLM → TTS pipeline

from livekit import agents
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.agents.llm import ChatContext, ChatMessage
from livekit.plugins import openai as lk_openai
from livekit.plugins import deepgram, silero

async def entrypoint(ctx: JobContext):
    """Main entrypoint for LiveKit voice agent"""
    
    # Define initial context
    initial_ctx = ChatContext().append(
        role="system",
        text=(
            "You are a helpful voice assistant. "
            "Keep your responses concise - this is a voice conversation. "
            "Respond in the same language as the user."
        )
    )
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Create voice pipeline agent
    # LiveKit handles: VAD → STT → LLM → TTS automatically
    agent = VoicePipelineAgent(
        vad=silero.VAD.load(),           # Silero VAD
        stt=deepgram.STT(                # Deepgram STT
            model="nova-2",
            language="en-US",
            interim_results=True,
        ),
        llm=lk_openai.LLM(              # OpenAI LLM
            model="gpt-4o-mini",
            temperature=0.7
        ),
        tts=lk_openai.TTS(              # OpenAI TTS
            model="tts-1",
            voice="alloy"
        ),
        chat_ctx=initial_ctx,
        
        # Interruption handling
        allow_interruptions=True,
        interrupt_speech_duration=0.5,   # 500ms speech to interrupt
        interrupt_min_words=3,           # Min 3 words to trigger interrupt
        
        # Timing
        min_endpointing_delay=0.5,       # Min silence before responding
        max_endpointing_delay=6.0,       # Max wait for speech to end
    )
    
    agent.start(ctx.room)
    
    # Send initial greeting
    await agent.say("Hello! How can I help you today?", allow_interruptions=True)

# Run the agent
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(entrypoint_fnc=entrypoint)
    )
```

```python
# === Twilio for Phone Calls ===
# Use case: customer support bot, IVR replacement

from fastapi import FastAPI, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather, Say, Connect, Stream
from twilio.rest import Client as TwilioClient

app = FastAPI()
twilio_client = TwilioClient("ACCOUNT_SID", "AUTH_TOKEN")

@app.post("/twilio/incoming-call")
async def handle_incoming_call(request: Request):
    """TwiML response for incoming calls"""
    response = VoiceResponse()
    
    # Option 1: Simple TTS + gather (no streaming)
    gather = Gather(
        input="speech",
        speech_timeout="auto",
        action="/twilio/process-speech",
        speech_model="phone_call"
    )
    gather.say(
        "Hello! How can I help you today?",
        voice="Polly.Joanna",  # Amazon Polly TTS
        language="en-US"
    )
    response.append(gather)
    
    return Response(content=str(response), media_type="application/xml")

@app.post("/twilio/process-speech")
async def process_speech(request: Request):
    """Process speech input from Twilio"""
    form_data = await request.form()
    speech_result = form_data.get("SpeechResult", "")
    confidence = float(form_data.get("Confidence", 0))
    
    # Low confidence → ask to repeat
    if confidence < 0.5:
        response = VoiceResponse()
        response.say("I didn't catch that. Could you please repeat?")
        response.redirect("/twilio/incoming-call")
        return Response(content=str(response), media_type="application/xml")
    
    # Process with LLM
    llm_response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": speech_result}],
        max_tokens=200
    )
    
    reply_text = llm_response.choices[0].message.content
    
    response = VoiceResponse()
    response.say(reply_text, voice="Polly.Joanna")
    response.redirect("/twilio/incoming-call")  # Loop for continued conversation
    
    return Response(content=str(response), media_type="application/xml")

# Option 2: Twilio Media Streams (WebSocket, for real-time processing)
@app.post("/twilio/stream-call")
async def stream_call(request: Request):
    """Use Media Streams for real-time audio processing"""
    response = VoiceResponse()
    connect = Connect()
    connect.stream(url="wss://your-server.com/twilio/audio-stream")
    response.append(connect)
    return Response(content=str(response), media_type="application/xml")

@app.websocket("/twilio/audio-stream")
async def twilio_audio_stream(websocket: WebSocket):
    """Handle Twilio Media Stream WebSocket"""
    await websocket.accept()
    
    # Twilio sends audio as μ-law (G.711) 8kHz - need to convert
    # Each message is JSON with base64-encoded audio
    
    async for message in websocket.iter_text():
        data = json.loads(message)
        
        if data.get("event") == "media":
            # Decode μ-law audio
            audio_payload = base64.b64decode(data["media"]["payload"])
            
            # Convert μ-law 8kHz → PCM 16kHz for Deepgram
            # (requires audioop or similar library)
            pcm_audio = convert_mulaw_to_pcm(audio_payload)
            
            # Process with VAD → STT → LLM → TTS pipeline
            # ... same as WebSocket example above
```

---

## Quick Reference: Interview Q&A

**Q: "Latency target cho voice AI là bao nhiêu?"**
- Target: < 2 giây end-to-end từ lúc user nói xong đến lúc nghe response đầu tiên
- Ideal: < 1 giây cho premium experience
- Breakdown: STT ~300ms + LLM TTFT ~500ms + TTS first chunk ~200ms = ~1000ms
- Key optimization: sentence streaming để TTS bắt đầu ngay khi có câu đầu tiên từ LLM

**Q: "Barge-in là gì và handle thế nào?"**
- Barge-in: user ngắt lời bot đang nói (như conversation thực)
- Detect: VAD liên tục monitor input kể cả khi bot đang nói
- Handle: cancel ongoing TTS task, stop audio playback, process new user input
- Threshold: thường cần 3+ consecutive speech frames (~150ms) để tránh false positives

**Q: "Deepgram vs Whisper cho production?"**
- Deepgram: real-time streaming API, thấp latency, word timestamps, diarization. Dùng cho production voice assistant
- Whisper: batch processing, tốt cho audio files, có thể self-host, tốt cho Vietnamese
- Recommendation: Deepgram cho real-time latency requirements, Whisper cho cost-sensitive hoặc offline

**Q: "Audio format nào tốt nhất cho WebSocket streaming?"**
- Opus: designed cho real-time, ~20ms latency, excellent compression (32-64kbps cho voice)
- PCM: raw, lossless, dùng internally giữa components
- MP3: không phù hợp cho streaming (codec delay)
- Recommendation: Opus cho WebSocket transport, PCM cho internal processing

**Q: "Làm sao test voice AI?"**
- Unit test: mock STT/TTS, test LLM logic với text
- Integration test: pre-recorded audio files qua pipeline
- Metrics: WER (transcription accuracy), end-to-end latency, task completion rate
- Load test: simulate concurrent calls với tools như Artillery/Locust

---

*File này được tạo: 2026-05-20 | Dành cho: Senior AI Engineer Interview Prep — Voice AI Gap Area*

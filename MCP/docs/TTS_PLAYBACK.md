# TTS Playback System

AI 서버에서 생성된 TTS 음성을 MCP 클라이언트에서 재생하는 시스템 문서.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI Server                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  User Speech → ASR → LLM → response.text → TTSService → TTS Chunks          │
│                                                    │                         │
│                                          Google Cloud TTS                    │
│                                          (Chirp3 HD, 24kHz)                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ WebSocket (tts_chunk)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MCP Client                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  WSClient._handle_tts_chunk()                                                │
│         │                                                                    │
│         │ publish(TTS_AUDIO_RECEIVED)                                        │
│         ▼                                                                    │
│  AudioPlayer._on_tts_audio_received()                                        │
│         │                                                                    │
│         │ queue.put(audio_bytes)                                             │
│         ▼                                                                    │
│  AudioPlayer._playback_loop() [Background Thread]                            │
│         │                                                                    │
│         │ pyaudio.write(audio_bytes)                                         │
│         ▼                                                                    │
│  Speaker Output                                                              │
│         │                                                                    │
│         │ publish(TTS_PLAYBACK_FINISHED)                                     │
│         ▼                                                                    │
│  UIManager._on_playback_finished()                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### AI Server Side

| Component | File | Description |
|-----------|------|-------------|
| TTSService | `AI/services/tts/service.py` | Google Cloud TTS Chirp3 HD 음성 합성 |
| WebSocketHandler | `AI/api/websocket.py` | TTS 청크를 클라이언트로 전송 |

### MCP Client Side

| Component | File | Description |
|-----------|------|-------------|
| WSClient | `MCP/network/ws_client.py` | TTS 청크 수신 및 이벤트 발행 |
| AudioPlayer | `MCP/audio/player.py` | PCM 오디오 재생 |

## Event Flow

```
1. [AI Server] LLM generates response.text
2. [AI Server] TTSService.synthesize_stream(text) → PCM chunks
3. [AI Server] WebSocket sends tts_chunk messages
4. [MCP Client] WSClient receives tts_chunk
5. [MCP Client] WSClient publishes TTS_AUDIO_RECEIVED event
6. [MCP Client] AudioPlayer receives event, queues audio
7. [MCP Client] AudioPlayer playback thread plays audio via pyaudio
8. [MCP Client] AudioPlayer publishes TTS_PLAYBACK_FINISHED event
```

## Audio Format

| Property | Value |
|----------|-------|
| Sample Rate | 24000 Hz |
| Channels | 1 (Mono) |
| Bit Depth | 16-bit |
| Format | PCM (Linear16) |
| Chunk Size | 4096 bytes |

## WebSocket Message Format

### tts_chunk (Server → Client)

```json
{
  "type": "tts_chunk",
  "data": {
    "audio": "hex_encoded_pcm_data",
    "is_final": false,
    "sample_rate": 24000,
    "tts_id": "a1b2c3d4e5",
    "text": "optional segment text (sent on first chunk of a segment)",
    "segment_index": 0,
    "segment_total": 5
  },
  "session_id": "uuid",
  "timestamp": "2026-01-26T12:00:00"
}
```

## Events

### TTS_AUDIO_RECEIVED

- **Publisher**: `network.ws_client`
- **Subscriber**: `audio.player.AudioPlayer`
- **Data**:
  ```python
  {
      "audio": bytes,      # PCM audio data
      "is_final": bool,    # True if last chunk for a segment
      # optional metadata (if provided by server)
      "text": str,
      "tts_id": str,
      "segment_index": int,
      "segment_total": int,
  }
  ```

### TTS_PLAYBACK_FINISHED

- **Publisher**: `audio.player.AudioPlayer`
- **Subscriber**: `ui.ui_manager.UIManager`
- **Data**: `{}`

## Configuration

### AI Server (.env)

```bash
# Google Cloud TTS
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
TTS_SAMPLE_RATE=24000
TTS_GOOGLE_VOICE=ko-KR-Chirp3-HD-Leda
```

### Available Voices (Korean)

| Voice ID | Description |
|----------|-------------|
| ko-KR-Chirp3-HD-Leda | Female, Chirp3 HD |
| ko-KR-Chirp3-HD-Aoede | Female, Chirp3 HD |
| ko-KR-Chirp3-HD-Puck | Male, Chirp3 HD |
| ko-KR-Chirp3-HD-Charon | Male, Chirp3 HD |
| ko-KR-Chirp3-HD-Kore | Female, Chirp3 HD |
| ko-KR-Chirp3-HD-Fenrir | Male, Chirp3 HD |

## TTS Trigger Points

TTS is triggered in the following scenarios:

| Location | Condition | Content |
|----------|-----------|---------|
| `_process_text_input` | `response.text` exists | LLM response (e.g., "'세지목살'를 쿠팡에서 검색합니다") |
| `_handle_mcp_result` | `products` exists | 검색 결과 안내 (e.g., "5개 상품을 찾았습니다. 첫 번째는...") |
| `_handle_mcp_result` | HTML parsing success | Product summary from HTML |
| `_handle_mcp_result` | OCR processing done | OCR summary |
| `_handle_flow_input` | Flow step prompt | Flow guidance |
| `_handle_cancel` | Cancel requested | "Cancelled" |

**Note**: Intermediate MCP results (navigate, type, click, wait) are processed silently without TTS.

## Troubleshooting

### TTS not playing

1. **Check AI Server logs**:
   ```
   Sending TTS response: '...'
   TTS completed: N chunks sent
   ```

2. **Check MCP Client logs**:
   ```
   TTS chunk queued: N bytes, final=True
   TTS playback finished
   ```

3. **Verify Google credentials**:
   ```bash
   echo $GOOGLE_APPLICATION_CREDENTIALS
   ```

### Audio quality issues

- Ensure sample rate matches (24000 Hz)
- Check output device settings
- Verify pyaudio installation: `pip install pyaudio`

### No audio output

1. Check default output device
2. Verify speaker/headphone connection
3. Check system volume

## Dependencies

### AI Server
```
google-cloud-texttospeech
```

### MCP Client
```
pyaudio
```

## File Structure

```
AI/
├── services/tts/
│   ├── service.py          # TTSService implementation
│   └── __init__.py
├── api/
│   └── websocket.py        # _send_tts_response()
└── core/
    └── config.py           # TTSConfig

MCP/
├── audio/
│   ├── player.py           # AudioPlayer implementation
│   ├── audio_manager.py    # Recording (PTT)
│   └── __init__.py
├── network/
│   └── ws_client.py        # _handle_tts_chunk()
└── main.py                 # AudioPlayer initialization
```

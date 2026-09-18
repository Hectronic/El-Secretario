# SPEC-031: Automatic Audio Compression

Status: Draft
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-17

## Problem
Currently, El Secretario records all microphone captures in raw PCM WAV format. At 16000Hz mono, WAV files consume about 115 MB for each hour of recorded audio. For power users with massive meeting history (such as the active 25 GB recordings folder), this causes high physical disk consumption and strains local system resources over time. Since human voice recordings don't require raw uncompressed PCM bandwidth, they can be highly compressed with almost zero perceptible loss in transcription (STT) accuracy.

## Proposal
Implement an automatic, background audio compression system. Immediately after a recording session is stopped and saved as WAV, the application will compress it to a high-quality mono `.mp3` or `.opus` file in a non-blocking background thread. It will then replace the file reference in the database and remove the bulky original WAV file, reducing disk usage by up to **90%** (25 GB drops to ~2.5 GB!).

### Key Highlights
- **Background Compression Thread:** Trigger non-blocking audio compression as soon as `Recorder.stop()` completes.
- **Optimized Voice Profiles:** Compress to mono `.mp3` (or `.opus`) at 32 kbps (the exact golden ratio of voice intelligibility and STT accuracy).
- **Seamless Database Swap:** Automatically update the record file path reference in the database from `.wav` to `.mp3` / `.opus` and delete the bulky WAV file cleanly.

## User Scenarios & Testing
- **Scenario:** The user records a 2-hour meeting. They stop the recording. The app saves the `.wav` file, starts transcription, and immediately launches a background thread to compress the file to `.mp3`. Within a minute, the original 230 MB WAV file is converted to a 25 MB MP3 file, freed up on disk, and referenced transparently in the databases.
- **Testing:** Create tests validating that the `.mp3`/`.opus` files are correctly compressed, check that the STT engines (faster-whisper/sherpa-onnx) can read the compressed formats successfully, and assert that the file references are updated in the database.

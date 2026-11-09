# yt-subtitle

Turn a YouTube video into a text transcript on your own computer. The tool downloads the audio, transcribes it using your NVIDIA GPU, and saves plain text and timestamped text files. No paid transcription service or API key is needed.

**Tested on Windows with an NVIDIA GeForce RTX 3090 (24 GB VRAM).** Other operating systems and GPU models have not been verified for this project. These instructions use PowerShell on Windows.

## What you need

- **An NVIDIA GPU and an up-to-date NVIDIA driver.** The GPU must support float16 inference. The currently locked cuDNN runtime requires **Turing or newer** (compute capability 7.5 or higher). For GeForce RTX cards, that means **RTX 20-series or newer**. Older GTX 10-series cards are not supported by this runtime. This is a dependency requirement, not a claim that every compatible card has been tested. See the [NVIDIA cuDNN support matrix](https://docs.nvidia.com/deeplearning/cudnn/backend/latest/reference/support-matrix.html) and [NVIDIA driver downloads](https://www.nvidia.com/Download/index.aspx).
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** to install Python and manage the project's dependencies.
- **[Node.js 22 or newer](https://nodejs.org/en/download/)**, available on your `PATH`. The YouTube downloader uses Node to handle JavaScript challenges.
- **Internet access** to download videos, dependencies, and the transcription model on its first use.

You do not need to install Python, the CUDA Toolkit, cuDNN, FFmpeg, or Deno separately. uv installs Python 3.12 and the Python dependencies: yt-dlp for downloads, faster-whisper for transcription, Hugging Face Hub for model downloads, PyAV for audio decoding, and NVIDIA CUDA 12/cuDNN 9 runtime libraries on Windows. Your NVIDIA graphics driver must already be installed.

## Set up the project

Download or clone this repository, then open PowerShell in its folder. If you just installed uv or Node, open a new terminal so they are available on `PATH`.

Check that the required tools and your graphics driver are available:

```powershell
uv --version
node --version
nvidia-smi
```

`nvidia-smi` should list your NVIDIA GPU. Then bootstrap the project:

```powershell
uv python install 3.12
uv sync --locked
```

This creates a `.venv` environment and installs the versions recorded in `uv.lock`. The NVIDIA runtime packages alone download roughly 1.3 GB, so initial setup can take a few minutes. You do not need to activate the environment manually when using `uv run`.

## Transcribe a video

From the project folder, run:

```powershell
uv run yt-subtitle "https://www.youtube.com/watch?v=VIDEO_ID"
```

Replace `VIDEO_ID` with the video's ID, or paste its full YouTube URL between the quotes. The tool processes one video at a time; playlist-only links are not supported.

The default `small` Whisper model runs on your GPU using float16. On the first run, the model downloads from Hugging Face with progress bars. Later runs reuse the cached model. Transcription also shows a progress bar and estimated time remaining. The counter measures **seconds of audio processed**, not iterations; it can pause while the next chunk is processed.

When finished, look in `transcripts/` for:

- `VIDEO_ID.txt` — the spoken words, without timestamps.
- `VIDEO_ID.timestamped.txt` — the same text with timestamps, such as `[00:00:01.250 --> 00:00:04.500] Spoken text`.

The language is detected automatically, and the transcript stays in the original language. Temporary audio is removed after processing; the model cache is kept. Existing transcripts are never overwritten. To repeat a transcription, choose a different output folder:

```powershell
uv run yt-subtitle "https://youtu.be/VIDEO_ID" --output-dir transcripts-new
```

## Useful options and troubleshooting

Specify the spoken language and use a smaller model to reduce memory use:

```powershell
uv run yt-subtitle "https://youtu.be/VIDEO_ID" --language en --model base
```

Show all command options:

```powershell
uv run yt-subtitle --help
```

GPU use is the default and intended workflow. The tool stops if GPU setup fails; it does not silently switch to CPU. An explicit `--device cpu` mode is available for troubleshooting, but it can be impractically slow for long videos.

If GPU initialization fails, check `nvidia-smi`, update your graphics driver, and rerun `uv sync --locked`. If GPU memory runs out, close other GPU-heavy applications or try `--model base`. If a download fails, check `node --version` and your internet connection.

## Development

Source code is in `src/yt_subtitle/`, and automated tests are in `tests/`. Run the tests and build a distributable package with:

```powershell
uv run pytest
uv build
```

The automated tests do not require a GPU or model downloads. Real GPU transcription has also been checked on the RTX 3090 described above.

## License

GNU General Public License v3. See [LICENSE.txt](LICENSE.txt).

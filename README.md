# Music Smart Trim

Shorten or extend a song while keeping it musical. Instead of fading or chopping
at an arbitrary point, Music Smart Trim finds the song's sections (intro, verse,
chorus, bridge, outro) and edits **whole sections at bar boundaries** — removing
a verse to shorten, or repeating the chorus to lengthen — so the result still
sounds like a deliberate edit rather than a cut-off clip.

The same engine powers two front doors: a command-line tool and a web app.

## What it does

- **Trim** by removing whole sections (a repeated verse, a bridge) — never a
  mid-phrase chop.
- **Extend** by repeating a section (the chorus first, then a verse) with
  seamless crossfades.
- **Stays musical**: cuts and loops land on downbeats, and the engine prefers
  one clean splice over several scattered ones.
- **Scores every option** on a single 0–5★ rubric and returns the top 3.

## Quick start — command line

```bash
git clone https://github.com/RitosEric/music-smart-trim.git
cd music-smart-trim

python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Trim a song down to 2 minutes
python -m src.cli --input song.mp3 --target 120

# Extend a song to 4 minutes
python -m src.cli --input song.mp3 --target 240
```

Results are written to `./output/` as ranked WAV files named after the song —
`<song> - option 1 - <score> stars.wav`, where option 1 is the best — alongside
a `summary.txt`.

### Options

| Option | Description |
|--------|-------------|
| `--input PATH` | Input audio file (required) |
| `--target SECONDS` | Target length in seconds (required) |
| `--output-dir PATH` | Output directory (default: `./output`) |
| `--protect "M:SS-M:SS"` | Protect time ranges from edits (repeatable) |
| `--auto-protect` | Keep the intro and outro intact |
| `--strict-length` | Force the result within ±15s of target (rougher, but exact) |

## Quick start — web app

Run the backend and frontend in two terminals.

**Backend** (Flask + WebSocket, port 5002) — run from the project root:

```bash
pip install -r requirements.txt -r api/requirements.txt
python -m api.app
```

**Frontend** (React, port 3000):

```bash
cd frontend
npm install
npm start
```

Open <http://localhost:3000>, drop in an audio file, choose a target length, and
download the result. Toggles let you protect the intro/outro or enforce the
strict ±15s length, and a light/dark switch lives in the top-right corner. The
interface uses a frosted "liquid glass" style and remembers your theme choice.

## How it works

1. **Analyze** — extract chroma, detect beats and downbeats, and split the song
   into labeled sections (chorus = repeated and loud, verse = repeated, bridge =
   one-off).
2. **Plan** — enumerate edits as whole-section removals (trim) or repeats
   (extend). Adjacent sections merge into one cut; plans with too many cuts are
   rejected, which is what prevents fragmented results. Every boundary snaps to
   the nearest downbeat.
3. **Score** — rate each option on one 100-point rubric (beat alignment,
   harmonic continuity, structural position, energy continuity, length), with a
   penalty for extra cuts, mapped to 0–5 stars.
4. **Render** — apply the top strategies with constant-power crossfades and write
   the ranked files.

## Requirements

- **Python 3.9+** (3.10–3.12 recommended).
- **Node 16+** for the web frontend.
- Optional: [madmom](https://github.com/CPJKU/madmom) for higher-accuracy
  downbeat detection. It needs Python ≤ 3.11; without it the engine falls back to
  a librosa beat-grouping estimate, so everything still works.

## License

MIT — see [LICENSE](LICENSE).

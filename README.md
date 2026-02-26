# Memebase

A self-hosted, web-based home for your memes. Upload, tag, search, and hoard your collection - with optional AI that names and tags them for you.

[![Tests](https://github.com/hberg539/memebase/actions/workflows/test.yml/badge.svg)](https://github.com/hberg539/memebase/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org)
[![Flask](https://img.shields.io/badge/flask-3.0+-green)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/license-MIT-orange)](LICENSE)

![Memebase](.github/assets/memebase_main.png)

## Table of contents

- [Features](#features)
- [Getting started](#getting-started)
  - [Docker (recommended)](#docker-recommended)
  - [Local development](#local-development)
- [Configuration](#configuration)
- [Hotkeys](#hotkeys)
- [Themes](#themes)
  - [Custom themes](#custom-themes)
- [Thumbnails](#thumbnails)
- [AI auto-detect](#ai-auto-detect)
  - [Setup](#setup)
  - [Usage](#usage)
  - [Supported models](#supported-models)
- [Data layout](#data-layout)
- [License](#license)

## Features

- **Upload** - Drag-and-drop, paste from clipboard, or add a URL. Supports page scraping via [gallery-dl](https://github.com/mikf/gallery-dl) ([hundreds of supported sites](https://github.com/mikf/gallery-dl/blob/master/docs/supportedsites.md))
- **Search & filter** - Full-text search with filters for extension, tag, and favorites
- **AI auto-detect** - Let a vision model generate filenames, descriptions, and tags for you
- **Bulk operations** - Select a bunch of memes at once for tagging, auto-detect, or deleting
- **Copy & download** - One click to copy a meme to your clipboard or download it
- **Themes** - Ships with built-in themes and supports custom CSS themes
- **Self-contained** - Everything lives in a single `./data` folder. Easy to back up, easy to move

**Supported formats:** PNG, JPG, JPEG, GIF, WEBP, WEBM, MP4

## Getting started

### Docker (recommended)

```bash
mkdir memebase && cd memebase
mkdir data

# Create docker-compose.yml
docker-compose up -d
```

`docker-compose.yml`:

```yaml
services:
  memebase:
    image: ghcr.io/hberg539/memebase:latest
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
```

That's it. Open [http://localhost:5000](http://localhost:5000) and start dumping memes.

### Local development

Requires [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/hberg539/memebase.git
cd memebase
uv run main.py
```

Then open [http://localhost:5000](http://localhost:5000).

## Configuration

On first run, `config.default.toml` gets copied to `./data/config.toml`. Edit that file to tweak things.

| Key | Default | What it does |
|-----|---------|--------------|
| `server.host` | `"0.0.0.0"` | Address the server listens on |
| `server.port` | `5000` | Port the server listens on |
| `server.max_upload_size` | `100` | Max upload size in MB (0 = unlimited) |
| `grid.layout` | `"grid"` | Layout mode: `"grid"` (uniform squares) or `"masonry"` (natural aspect ratios) |
| `grid.thumbnail_size` | `220` | Card width in pixels |
| `grid.per_page` | `"auto"` | Memes per page: `"auto"` (fill viewport) or a number |
| `ui.title` | `"Memebase"` | Page title and header text |
| `ui.theme` | `"midnight"` | CSS theme name (see [Themes](#themes)) |
| `thumbnails.enabled` | `true` | Generate and serve smaller thumbnails in the grid view (see [Thumbnails](#thumbnails)) |
| `thumbnails.max_size` | `440` | Max width/height in pixels (2x card size for retina) |
| `thumbnails.quality` | `80` | Output quality (1-100) |
| `thumbnails.format` | `"webp"` | Thumbnail format: `"webp"` or `"jpeg"` |
| `thumbnails.skip_types` | `["gif"]` | File extensions to skip, e.g. `["gif", "mp4"]` |
| `scrape.max_files` | `4` | Max media files to download per URL |
| `ai.enabled` | `false` | Turn the AI auto-detect feature on or off (see [AI auto-detect](#ai-auto-detect)) |
| `ai.model` | `"anthropic/claude-sonnet-4-5-20250929"` | Any LiteLLM-compatible model string (see [Supported models](#supported-models)) |
| `ai.parallel` | `3` | Max parallel requests during bulk auto-detect |
| `ai.prompt` | *(see config.toml)* | The prompt sent to the vision model - customize it to change the output style |

## Hotkeys

| Key | Where | What it does |
|-----|-------|--------------|
| `Shift` + click | Grid | Select multiple memes |
| `Escape` | Grid / Meme dialog | Clear selection or close dialog |
| `Enter` | Meme dialog | Save changes |
| `F` | Meme dialog | Toggle favorite |

## Themes

Memebase ships with a couple of built-in themes. Set `ui.theme` in `./data/config.toml` to switch, or add `?theme=` to the URL to try one out without committing:

```
http://localhost:5000/?theme=ember
```

| Theme | Look |
|-------|------|
| `midnight` | Deep navy and blue accents (default) |
| `ember` | Warm brown tones with amber and orange accents |
| `sakura` | Light cherry blossom pinks and soft rose accents |
| `matrix` | Black and phosphor green, follow the white rabbit |

### Custom themes

You can add your own themes by dropping a CSS file into `./data/themes/` and setting `ui.theme` to the filename (without `.css`):

```bash
# Example: create a custom theme called "vapor"
cp static/css/themes/midnight.css data/themes/vapor.css
# edit data/themes/vapor.css to your liking
```

Then set `ui.theme = "vapor"` in `./data/config.toml` (or just visit `?theme=vapor`).

Custom themes in `data/themes/` take priority over built-in ones with the same name, so you can override `midnight` or `ember` without touching the source.

## Thumbnails

Enabled by default. When enabled, the grid view serves small pre-generated thumbnails instead of full-resolution files - way faster page loads and less memory usage. Clicking a meme still shows the full-size original.

Set `thumbnails.enabled = true` in `./data/config.toml` and you're good to go. Thumbnails are generated on first view and cached to `data/thumbnails/`.

**Video thumbnails** require [ffmpeg](https://ffmpeg.org/) installed on the host (included in the Docker image). If ffmpeg isn't available, videos just serve at full resolution.

**Skip types**: Use `thumbnails.skip_types` to keep certain formats as-is in the grid. For example:
- `["gif"]` - keep GIFs animated instead of showing a static first frame (this is the default)
- `["mp4", "webm"]` - skip video thumbnails entirely
- `["gif", "mp4", "webm"]` - only thumbnail static images

## AI auto-detect

AI features are disabled by default. When enabled, Memebase can use a vision model to automatically generate filenames, descriptions, and tags for your memes - one at a time or in bulk.

### Setup

1. Set `ai.enabled = true` in `./data/config.toml`
2. Set `ai.model` to a [LiteLLM-compatible model string](#supported-models) (e.g. `"openai/gpt-4o"`)
3. Pass your API key as an environment variable

For Docker, create a `memebase.env` file next to `docker-compose.yml` and add `env_file` to your service:

```
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=...
# DEEPSEEK_API_KEY=...
```

```yaml
services:
  memebase:
    image: ghcr.io/hberg539/memebase:latest
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
    env_file:
      - memebase.env
```

### Usage

When AI is enabled, an **Auto** button appears in two places:

- **Meme popup** - click Auto to detect the name, description, and tags for a single meme.
- **Bulk selection** - select multiple memes, then click Auto to run AI detection across all of them.

Memes that fail during bulk auto-detect are automatically tagged with `auto-failed`, so you can filter for them later and review by hand.

You can customize the `ai.prompt` in `./data/config.toml` to fine-tune how the model names, describes, and tags your memes.

### Supported models

Memebase uses [LiteLLM](https://docs.litellm.ai/) for model routing, so pretty much any vision model works:

| Provider | Model example | Env var |
|----------|--------------|---------|
| Anthropic | `anthropic/claude-sonnet-4-5-20250929` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai/gpt-4o` | `OPENAI_API_KEY` |
| DeepSeek | `deepseek/deepseek-chat` | `DEEPSEEK_API_KEY` |
| Ollama | `ollama/llama3.2-vision` | (local, no key needed) |

Set the `model` field in `./data/config.toml` and pass the matching API key as an environment variable.

## Data layout

Everything lives in `./data`:

```
data/
  memes.db       # SQLite database
  config.toml    # Your configuration
  memes/         # Uploaded meme files
  thumbnails/    # Generated thumbnails (if enabled)
  themes/        # Custom CSS themes (optional)
```

## License

MIT

## AI-assisted development

I built this for my own personal use and as a proof of concept to find out what LLMs can do. I directed and reviewed most of the AI-generated code, but you must use this project entirely at your own risk.

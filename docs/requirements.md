# Requirements

THRESHER-Chat runs a language model on your own computer, so memory matters more than processor speed.

## Operating system

- **macOS** and **Linux** are supported by `install.sh`, which can also install Ollama for you.
- On other systems, install [Ollama](https://ollama.com/download) yourself and follow the
  [manual installation](installation.md#option-b-manual-installation).

## Software

| Software | Why it's needed | Check with |
|---|---|---|
| [conda](https://docs.conda.io/en/latest/miniconda.html) (Miniconda, Miniforge, or Anaconda) | Creates the `thresher-chat` environment with Python 3.11 | `conda --version` |
| [Ollama](https://ollama.com/download) | Runs the chat and embedding models locally | `ollama --version` |
| Git | Downloads the THRESHER source code that the assistant learns from | `git --version` |
| A web browser | Opens the web interface | |

On macOS, `install.sh` installs Ollama through [Homebrew](https://brew.sh) if Ollama is missing.
On Linux, it uses Ollama's official install script.

You don't need THRESHER itself installed. THRESHER-Chat only reads THRESHER's source folder.

## Memory and models

THRESHER-Chat uses two models, both run by Ollama:

| Model | Role | Which one |
|---|---|---|
| Chat model | Writes the answers | Chosen from your RAM (table below) |
| Embedding model | Finds the passages relevant to your question | `embeddinggemma` (always) |

`install.sh` picks the chat model from your total RAM:

| Total RAM | Chat model |
|---|---|
| Less than 24 GB | `gemma4:e4b` |
| 24 GB or more | `gemma4:12b` |

You can choose a different model with `bash install.sh --model <name>`, or later with `--model` when you start
the assistant. Larger models usually give better answers but are slower and need more memory.
Close other memory-heavy programs if answers are very slow.

## Disk space

Leave several GB free for the models. The knowledge base and conversation memory are small in comparison.

## Internet

You need internet access only to:

- install THRESHER-Chat and Ollama
- download the models
- clone the THRESHER repository

After that, THRESHER-Chat works fully offline.

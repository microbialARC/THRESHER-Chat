# Installation

Check the [requirements](requirements.md) first, then download the THRESHER-Chat source code:

```bash
git clone https://github.com/microbialARC/THRESHER-Chat.git
```

```bash
cd THRESHER-Chat
```

There are two ways to install THRESHER-Chat: the install script (recommended) or manual installation.
Run either one from the `THRESHER-Chat` folder.

## Option A: install script (recommended)

From the THRESHER-Chat source directory:

```bash
bash install.sh
```

The script:

1. Checks that conda is installed.
2. Installs Ollama if it's missing (Homebrew on macOS, the official script on Linux) and starts the Ollama
   server if it isn't running.
3. Downloads the chat model (chosen from your RAM, see [requirements](requirements.md#memory-and-models))
   and the `embeddinggemma` embedding model. Models you already have are skipped.
4. Creates a conda environment named `thresher-chat` from `thresher-chat.yml`.
5. Installs the `thresher-chat` command into that environment.

### Options

| Option | Description |
|---|---|
| `--model`, `-m NAME` | Chat model to download, e.g. `gemma4:12b`. Defaults to a model chosen from your RAM. |
| `--force`, `-f` | Reinstall THRESHER-Chat into an existing `thresher-chat` environment. |
| `--help`, `-h` | Show help, including the model the script would choose for your machine. |

If the `thresher-chat` environment already exists, the script stops unless you pass `--force`.

## Option B: manual installation

1. Install [Ollama](https://ollama.com/download) and make sure it's running:

   ```bash
   ollama serve
   ```

   If Ollama is already running as an app or service, you'll see an "address already in use" message,
   which is fine.

2. Download the models. Use `gemma4:12b` instead of `gemma4:e4b` if you have 24 GB of RAM or more:

   ```bash
   ollama pull gemma4:e4b
   ```

   ```bash
   ollama pull embeddinggemma
   ```

3. Create the conda environment and install THRESHER-Chat from the source directory:

   ```bash
   conda env create -f thresher-chat.yml
   ```

   ```bash
   conda activate thresher-chat
   ```

   ```bash
   pip install .
   ```

## Verify the installation

```bash
conda activate thresher-chat
```

```bash
thresher-chat --version
```

```bash
ollama list
```

`thresher-chat --version` prints the installed version, and `ollama list` should show your chat model and
`embeddinggemma`. Continue with the [quick start](quick_start.md).

## Updating

Get the new THRESHER-Chat source, then from its directory:

```bash
bash install.sh --force
```

or, inside the activated environment:

```bash
pip install .
```

Then [re-run ingest](usage_ingest.md#when-to-re-run-ingest) so the knowledge base includes the updated guides.

## Uninstalling

These commands permanently remove the environment, the models, and your knowledge base.
Export your [memory](user_memory.md#export-and-import) first if you want to keep it.

```bash
conda env remove -n thresher-chat
```

```bash
ollama rm gemma4:e4b embeddinggemma
```

Then delete the directory you used for `--db-dir` (for example `thresher_chat_db`).

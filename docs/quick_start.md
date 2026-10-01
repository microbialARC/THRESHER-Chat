# Quick start

This walkthrough takes you from a fresh [installation](installation.md) to your first answer.

## 1. Activate the environment

```bash
conda activate thresher-chat
```

## 2. Make sure Ollama is running

```bash
ollama list
```

If this prints an error, start Ollama (open the Ollama app, or run `ollama serve` in another terminal).

## 3. Get the THRESHER source code

THRESHER-Chat learns from THRESHER's own code and documentation, so it needs a copy of the repository:

```bash
git clone https://github.com/microbialARC/THRESHER.git
```

Keep this folder where it is. The web interface reads THRESHER's version from it.

## 4. Build the knowledge base

```bash
thresher-chat ingest --repo THRESHER --db-dir thresher_chat_db
```

This reads the repository and the guides bundled with THRESHER-Chat, then stores them in `thresher_chat_db`.
It finishes with `Indexing complete!`. You only need to do this once, and again when THRESHER or
THRESHER-Chat is updated. See [usage_ingest.md](usage_ingest.md).

## 5. Start the web interface

Use the chat model you downloaded during installation (`gemma4:e4b` or `gemma4:12b`):

```bash
thresher-chat server --db-dir thresher_chat_db --model gemma4:e4b
```

When you see `THRESHER-Chat server ready!`, open <http://127.0.0.1:5000> in your browser.

## 6. Ask your first question

1. In the sidebar, open **Response Profile** and click the profile that best describes you.
   See [response_profiles.md](response_profiles.md).
2. Type a question in the box at the bottom, for example
   *"Which THRESHER mode should I use for my first analysis?"*, and press **Enter**.
3. Read the answer and check the source files listed under it.

For more ideas, see the [example questions](example/example_questions.md). For a tour of every button,
see [web_interface.md](web_interface.md).

## 7. Stop the assistant

Press `Ctrl+C` in the terminal running the server. THRESHER-Chat unloads the models from memory as it stops.

## Next time

You only need steps 1, 2, and 5:

```bash
conda activate thresher-chat
```

```bash
thresher-chat server --db-dir thresher_chat_db --model gemma4:e4b
```

Prefer the terminal? See [usage_chat.md](usage_chat.md).

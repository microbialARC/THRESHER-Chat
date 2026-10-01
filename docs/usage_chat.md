# `thresher-chat chat`

`chat` runs THRESHER-Chat in the terminal, with no browser. It's useful on remote servers or when you want
quick answers without the web interface.

```bash
thresher-chat chat --db-dir /path/to/thresher_chat_db
```

Run [`ingest`](usage_ingest.md) first to create the knowledge base.

## Options

| Option | Required | Default | Description |
|---|---|---|---|
| `--db-dir PATH` | Yes | | Knowledge base created by `thresher-chat ingest` |
| `--model NAME` | No | Chosen from your RAM | Ollama chat model, e.g. `gemma4:e4b` or `gemma4:12b` |
| `--embed-model NAME` | No | The model recorded at ingest | Must match the model used for `ingest` |
| `--no-sources` | No | Off | Don't list the source files after each answer |
| `--debug` | No | Off | Print the retrieved passages before each answer |

## Commands inside the chat

Type a question at the `You:` prompt and press **Enter**. You can also type:

| Command | Effect |
|---|---|
| `clear` | Forget the conversation so far and start fresh |
| `quit`, `exit`, or `q` | Leave the chat |
| `Ctrl+C` or `Ctrl+D` | Leave the chat |

## Example

```
You: What does the Redo Endpoint mode do?

Assistant: ...

  Sources: modes/redo_endpoint.md [repo], thresher_overview.md [repo]
```

## Differences from the web interface

The terminal chat answers questions only. It has no response profiles, memory, file upload, or chat export.

When the best match for a question is a page from THRESHER's own `docs/` folder, the terminal chat prints the
matching passages from that page directly instead of writing a new answer.

# `thresher-chat server`

`server` starts the web interface: a local web page for asking questions, choosing a response profile,
uploading files, and managing memory. See [web_interface.md](web_interface.md) for a tour of the page.

```bash
thresher-chat server --db-dir /path/to/thresher_chat_db --model gemma4:e4b
```

Run [`ingest`](usage_ingest.md) first to create the knowledge base.

## Options

| Option | Required | Default | Description |
|---|---|---|---|
| `--db-dir PATH` | Yes | | Knowledge base created by `thresher-chat ingest` |
| `--model NAME` | Yes, in practice | | Ollama chat model, e.g. `gemma4:e4b` or `gemma4:12b`. Use one you've downloaded (`ollama list`). |
| `--embed-model NAME` | No | The model recorded at ingest | Must match the model used for `ingest`. Only set this if you know you need it. |
| `--host HOST` | No | `127.0.0.1` | Network address to listen on |
| `--port PORT` | No | `5000` | Port to listen on |

## Starting

At startup the server prints the models, the knowledge base, and where memory is stored:

```
Loading THRESHER knowledge base...
  Chat Model:     gemma4:e4b
  Embedding Model: embeddinggemma
  Database: thresher_chat_db

  User Memory:     thresher_chat_db/user_memory.sqlite3

THRESHER-Chat server ready!
Open http://127.0.0.1:5000 in your browser
```

Open the printed address in your browser. The first answer can take longer while Ollama loads the model.

<p align="center">
  <img src="images/web_interface_annotated.png" alt="THRESHER-Chat web interface" height="600">
</p>

## Stopping

Press `Ctrl+C` in the terminal. THRESHER-Chat unloads the chat and embedding models from Ollama so they
stop using memory.

## Notes

- **One user at a time.** The server keeps a single conversation. Several browser tabs share the same
  conversation and memory.
- **Port 5000 in use.** On macOS, AirPlay Receiver often uses port 5000. Choose another port:

  ```bash
  thresher-chat server --db-dir thresher_chat_db --model gemma4:e4b --port 5050
  ```

- **Access from other computers.** The default `127.0.0.1` only accepts connections from your own computer.
  `--host 0.0.0.0` makes the assistant reachable from your network. There's no login, so anyone who can reach
  it can use it and see the stored memory. Only do this on a trusted network.
- **Switching models.** You can restart with a different `--model` at any time without re-ingesting.

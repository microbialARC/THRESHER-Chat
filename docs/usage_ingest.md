# `thresher-chat ingest`

`ingest` builds the knowledge base that THRESHER-Chat answers from. It reads a local copy of the
THRESHER repository plus the guides bundled with THRESHER-Chat, splits them into passages, and stores
them in a local vector database.

```bash
thresher-chat ingest --repo /path/to/THRESHER --db-dir /path/to/thresher_chat_db
```

Ollama must be running and the embedding model must be downloaded (`ollama pull embeddinggemma`).

## Options

| Option | Required | Default | Description |
|---|---|---|---|
| `--repo PATH` | Yes | | Path to your clone of the [THRESHER repository](https://github.com/microbialARC/THRESHER) |
| `--db-dir PATH` | No | `thresher_chat_db` in the current directory | Where to store the knowledge base |
| `--embed-model NAME` | No | `embeddinggemma` | Ollama embedding model used to index the documents |

## What gets indexed

From the THRESHER repository:

- Code: `*.py`, `*.R`, `*.r`, `*.smk`, and `Snakefile*`
- Documentation: `*.md`

From THRESHER-Chat: the curated guides on THRESHER's concepts, modes, and installation.

Build and cache folders such as `.git`, `__pycache__`, `.snakemake`, `.conda`, `build`, and `dist` are skipped.

## What it creates

| File in `--db-dir` | Contents |
|---|---|
| Chroma database files | The indexed passages and their embeddings |
| `config.json` | The THRESHER repository path and the embedding model used |
| `user_memory.sqlite3` | Created later by the web interface; see [user_memory.md](user_memory.md) |

The web interface reads THRESHER's version from the repository path saved in `config.json`.
If you move or delete the THRESHER folder, the version shows as `Unknown` until you re-ingest.

> [!WARNING]
> `ingest` **deletes the entire `--db-dir` directory** before rebuilding it. This also deletes your
> conversation memory (`user_memory.sqlite3`). Before re-ingesting:
>
> - [export your memory](user_memory.md#export-and-import) from the web interface, then import it again afterwards
> - always use a dedicated directory for `--db-dir`, never a folder that holds other files

## When to re-run ingest

Re-run `ingest` when:

- **THRESHER is updated.** Pull the latest code, then re-ingest so answers match the new version:

  ```bash
  git -C /path/to/THRESHER pull
  ```

  ```bash
  thresher-chat ingest --repo /path/to/THRESHER --db-dir /path/to/thresher_chat_db
  ```

- **THRESHER-Chat is updated.** New versions may include new or corrected guides.
- **You change the embedding model.** The embedding model used to ask questions must match the one used to
  build the knowledge base.

You don't need to re-ingest to switch the chat model. Pass `--model` when you start the
[server](usage_server.md) or [terminal chat](usage_chat.md).

## Example output

```
Indexing THRESHER repository: THRESHER
Indexing guides: .../thresher_chat/guides
DataBase directory: thresher_chat_db
Embedding model: embeddinggemma

Loading documents from repository...
...
Created ... chunks total

Creating embeddings with embeddinggemma...
Vector DB stored at thresher_chat_db
Configuration saved to thresher_chat_db/config.json

Indexing complete!
```

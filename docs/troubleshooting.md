# Troubleshooting

## Installation and startup

| Problem | Likely cause | Fix |
|---|---|---|
| `thresher-chat: command not found` | The environment isn't active | `conda activate thresher-chat` |
| `install.sh` stops: environment already exists | A previous installation exists | Re-run with `bash install.sh --force` |
| `ERROR: Vector database not found` | `ingest` hasn't been run, or `--db-dir` points elsewhere | Run [`thresher-chat ingest`](usage_ingest.md), and use the same `--db-dir` for `server` or `chat` |
| `ERROR: Failed to initialise chatbot` | Ollama isn't running, or a model isn't downloaded | Start Ollama (`ollama serve` or the Ollama app), then check `ollama list` and `ollama pull` any missing model |
| Server startup shows `Chat Model: None` | `--model` wasn't given | Restart with `--model gemma4:e4b` (or the model you downloaded) |
| `Address already in use` / port 5000 busy | Another program uses port 5000 (on macOS, often AirPlay Receiver) | Add `--port 5050` and open `http://127.0.0.1:5050` |

## Web interface

| Problem | Likely cause | Fix |
|---|---|---|
| Sidebar **Status** shows `Offline`, or *Could not reach the server* | The server has stopped | Restart `thresher-chat server` and reload the page |
| The User Memory section disappears | The page couldn't reach the server when it loaded | Restart the server and reload the page |
| **THRESHER** version shows `Unknown` | The THRESHER folder was moved or deleted after ingest | [Re-ingest](usage_ingest.md) from the folder's current location |
| **Save** shows *Need more messages* | The conversation has no question and answer yet | Ask at least one question first |
| Upload fails: *File type not supported* | The file extension isn't on the [supported list](web_interface.md#uploading-files) | Save the file as `.txt`, `.csv`, or `.tsv` |
| The assistant ignores the end of an uploaded file | Only the first 15,000 characters of each file are read | Upload a smaller excerpt |

## Answers

| Problem | Likely cause | Fix |
|---|---|---|
| *"The THRESHER documentation I have access to does not cover this."* | The knowledge base has no matching information | Rephrase using THRESHER's terms, check the [THRESHER docs](https://github.com/microbialARC/THRESHER/tree/main/docs), or open an issue on the [THRESHER repository](https://github.com/microbialARC/THRESHER/issues) |
| *"I am a THRESHER-specific assistant and cannot help with that."* | The question isn't about THRESHER | This is intended. THRESHER-Chat only answers THRESHER questions. |
| Answers describe an older THRESHER version | The knowledge base was built from an older copy | Update THRESHER with `git pull`, then [re-ingest](usage_ingest.md#when-to-re-run-ingest) |
| Answers are tailored to the wrong background | Wrong response profile, or an incorrect memory tag | Pick another [profile](response_profiles.md), and mark wrong tags incorrect under **Profile Tags** |
| Answers drift or mix up topics | A long conversation with several topics | Click **Clear** to start a new conversation |
| Answers are very slow | The model is large for your machine, or memory is low | Close other programs, or restart with a smaller model such as `--model gemma4:e4b`. The first answer is always slower while the model loads. |

## Memory

| Problem | Likely cause | Fix |
|---|---|---|
| Memory is empty after re-ingesting | `ingest` deletes the whole `--db-dir`, including memory | Import your last exported JSON with **Import Json**. Next time, export before re-ingesting. |
| The assistant keeps assuming something wrong about you | An incorrect profile tag or old goal | Open **Profile Tags** or **Goals** and mark it incorrect or completed |

Still stuck? Run the terminal chat with `--debug` to see which passages the assistant retrieves:

```bash
thresher-chat chat --db-dir thresher_chat_db --debug
```

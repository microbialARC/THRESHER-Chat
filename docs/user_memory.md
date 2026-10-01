# User memory

THRESHER-Chat can remember useful context between conversations, such as your role, your research goals, and
what you've already asked about, so you don't have to repeat yourself. Memory is managed from the
**User Memory** section of the [web interface](web_interface.md#user-memory) sidebar.

Memory is stored only on your computer and is used only by THRESHER-Chat.

## What is stored

| Item | Example | How it's created |
|---|---|---|
| **Messages** | Every question and answer | Saved as you chat |
| **Session summaries** | *Discussed choosing an endpoint method for an MRSA dataset* | Written by the local model when a conversation is saved |
| **Profile tags** | *clinical microbiologist*, *S. aureus focus* | Short (1–3 word) descriptions of you inferred from your conversations |
| **Research objectives (Goals)** | *Identify transmission clusters in the NICU outbreak* | Goals inferred from your conversations |

Everything is stored in one file, `user_memory.sqlite3`, inside your `--db-dir` directory.

## When a conversation is saved

A conversation is summarized, and tags and goals are extracted from it, when you:

- click **Save**
- click **Clear** (before the new conversation starts)
- close or reload the browser tab

A conversation needs at least one question and answer to be saved. If you click **Save** too early, the button
shows *Need more messages*.

## How memory is used

With each question, the assistant also receives:

- your active profile tags
- your active goals
- summaries of your three most recent saved conversations

This context helps it tailor answers. It doesn't change the sources: answers still come only from the
THRESHER knowledge base.

## Reviewing and correcting memory

| Button | Actions |
|---|---|
| **Profile Tags** | ✗ marks a tag incorrect, so it's no longer used and won't be inferred again. ◻ reactivates it. 🗑 deletes it. |
| **Goals** | ✅ marks a goal completed, so it's no longer used. ◻ reactivates it. ✕ deletes it. |
| **History** | Read-only list of conversation summaries, with date and message count |

Correct wrong tags early. An incorrect tag such as *beginner Python* changes how every later answer is written.

## Export and import

- **Export Json** downloads everything (tags, goals, summaries, and conversations) as
  `thresher-chat-memory-<date>.json`.
- **Import Json** merges an exported file into your current memory. Items you already have aren't duplicated,
  and incorrect tags and completed goals keep their status.

Use export and import to back up your memory, move it to another computer, or keep it when you
[re-ingest](usage_ingest.md).

> [!WARNING]
> Re-running `thresher-chat ingest` with the same `--db-dir` deletes your memory. Export it first, then import it
> after ingest finishes.

## Deleting memory

**Delete All** permanently removes all tags, goals, summaries, and conversations after you confirm.
This can't be undone. Export first if you might want it back.

To remove memory without the web interface, stop the server and delete `user_memory.sqlite3` from your
`--db-dir` directory.

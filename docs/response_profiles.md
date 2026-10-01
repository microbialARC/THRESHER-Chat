# Response profiles

A response profile tells THRESHER-Chat who you are, so it can explain THRESHER at the right level and focus on
what matters to you. Choose one under **Response Profile** in the [web interface](web_interface.md#response-profile)
sidebar.

A profile changes **how** an answer is explained. It doesn't change **what** the assistant knows: every profile
answers only from THRESHER's code, documentation, and the bundled guides.

## Built-in profiles

| Profile | Sidebar description | Answers tend to |
|---|---|---|
| **Principal Investigator** | Balanced overview | Balance methods and interpretation, using standard genomic epidemiology terms |
| **Graduate Student** | Step-by-step guidance | Give step-by-step instructions with exact commands, expected outputs, and troubleshooting tips |
| **Clinician** | Clinical action items | Lead with what results mean for patient care and infection control, with few algorithm details |
| **Programmer** | Code locations & logic | Point to specific files and functions, and explain data structures, control flow, and Snakemake rules |
| **Bioinformatician** | Algorithms & pipeline design | Discuss design choices, trade-offs, pipeline architecture, and scalability |
| **Statistician** | Statistical methods & rigor | Describe methods in terms of assumptions, optimization criteria, and validation metrics |
| **IP & C Teams** | Outbreak response actions | Frame answers around routine surveillance, batch processing, and turnaround time |
| **General Audience** | Plain-language analogies | Use everyday analogies, define acronyms, and give the simple answer first |

When you select a profile, the assistant confirms it in the conversation. You can switch at any time; the new
profile applies from your next question. The terminal chat ([usage_chat.md](usage_chat.md)) doesn't use profiles.

## Adding or editing a profile

Profiles are defined in `thresher_chat/guides/user_profiles.md` in the THRESHER-Chat source. Each profile is a
numbered `###` section in this format:

```markdown
### 9. Lab Manager

**Key**: lab_manager
**Short description**: Resources & scheduling
**Prompt**:
The user is a lab manager planning THRESHER runs for their group. You are the
THRESHER assistant helping them. Do NOT adopt the user's identity. Just answer
the question directly.

Tailor your responses to this user by:
- Focusing on run time, disk space, and computing resources
- Always ground your response in the retrieved documentation. Do not invent commands or steps not found in the source material.
---
```

| Field | Rules |
|---|---|
| `### <number>. <Name>` | The heading must start with a number and a period. The name appears in the sidebar. |
| `**Key**:` | A unique identifier with no spaces |
| `**Short description**:` | The gray text under the name in the sidebar |
| `**Prompt**:` | Instructions for the assistant, starting on the next line and ending with a line containing only `---` |

Keep the "ground your response in the retrieved documentation" line so the profile doesn't encourage made-up answers.

After editing, reinstall and restart the server:

```bash
pip install .
```

```bash
thresher-chat server --db-dir thresher_chat_db --model gemma4:e4b
```

Then reload the web page. You don't need to re-ingest; this file isn't part of the knowledge base.

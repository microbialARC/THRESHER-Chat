#!/usr/bin/env python3
"""
THRESHER-Chat User Memory System (Single-User, Local)

SQLite-backed persistent memory that lives alongside the vector DB.

When the user runs:
    thresher-chat server --db-dir /path/to/DB
    thresher-chat chat   --db-dir /path/to/DB

The memory file is automatically created/loaded at:
    /path/to/DB/user_memory.sqlite3

My rationale of this design is that since this chatbot is a single-user local deployment
There will be only a single user using the system, and there is no login —
memory loads and saves automatically throughout the conversation.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime


class UserMemory:
    """Single-user memory backed by SQLite.

    Stores:
        - conversations: 
        Complete message history per session, preserving 
        the full dialogue for audit and re-summarization.

        - user_profile_tags:
        Short 1-3 word tags inferred from conversation that
        describe who the user is (e.g. 'clinical microbiologist',
        'S. aureus focus', 'beginner Python'). Tags are injected
        into prompts to help the LLM tailor responses. Users can
        reject incorrect tags, which prevents re-inference.

        - research_objectives: 
        The user's analytical goals and key questions
        driving their use of THRESHER (e.g., identifying
        transmission clusters in a specific outbreak).
        Captures what the user ultimately needs from
        the toolkit.
        
        - session_summaries: 
        LLM-generated narrative summaries of completed
        sessions, providing condensed context from prior
        interactions to inform future responses without
        requiring full conversation replay.

    The DB file lives at {db_dir}/user_memory.sqlite3 alongside the ChromaDB.
    """
    
    
    def __init__(self, db_dir, model=None, ollama_url=None):
        """Initialize memory from the same directory as the vector DB.

        Args:
            db_dir: Path to the THRESHER-Chat vector DB directory.
                    Memory file will be created at {db_dir}/user_memory.sqlite3
                    along with the ChromaDB files. This keeps all user data in one place.
        """

        # Use sqlite3.connect with check_same_thread=False to allow access from multiple threads
        # and make sqlite3.connect as self.conn for reuse across methods.

        # Store the model and ollama_url for use in summarization and other LLM calls from memory methods.
        
        self.db_dir = db_dir
        self.db_path = os.path.join(db_dir, "user_memory.sqlite3")
        self.model = model
        self.ollama_url = ollama_url
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

        # Current session
        # the session_id is used to group messages together. 
        # A new session ID is generated when the user clicks "Clear" to start a new conversation thread.
        # only takes the first 12 chars of a uuid4 for brevity, e.g. "session-9f1b2c3d4e5f"
        self.start_session()

    # Database structure initialization
    # Some of the attributes might not be used for now 
    # But I keep them as placeholders for future expansion
    # Since this will not slow down the system and allows us to easily add new features later
    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                timestamp   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_profile_tags (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tag             TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'active'
                                    CHECK (status IN ('active', 'rejected')),
                source_session  TEXT,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS research_objectives (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                objective      TEXT NOT NULL,
                status         TEXT NOT NULL DEFAULT 'active',
                source_session TEXT DEFAULT '',
                created_at     TEXT NOT NULL,
                updated_at     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_summaries (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id    TEXT NOT NULL UNIQUE,
                summary       TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                created_at    TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_conv_session
                ON conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_conv_time
                ON conversations(timestamp);
            CREATE INDEX IF NOT EXISTS idx_tags_status
                ON user_profile_tags(status);
            CREATE INDEX IF NOT EXISTS idx_objectives_status
                ON research_objectives(status);
        """)
        self.conn.commit()
    
    # ═══════════════════════════════════════════════════════════
    # ── Session Management ────────────────────────────────────
    # ═══════════════════════════════════════════════════════════
    def start_session(self):
        """Start a new session. Returns the new session ID."""
        self.session_id = f"session-{uuid.uuid4().hex[:12]}"
        return self.session_id
    
    # ═══════════════════════════════════════════════════════════
    # ── Conversation History ──────────────────────────────────
    # ═══════════════════════════════════════════════════════════
    # Stored as a sequence of messages with role (user/assistant) and timestamp.
    
    def save_message(self, role, content):
        """Save a message from the current session."""
        self.conn.execute(
            "INSERT INTO conversations (session_id, role, content, timestamp) "
            "VALUES (?, ?, ?, ?)",
            (self.session_id, role, content, datetime.now().isoformat()),
        )
        self.conn.commit()
    
    def get_session_messages(self, session_id=None):
        """Get all messages for a session (default: current)."""
        sid = session_id or self.session_id
        rows = self.conn.execute(
            "SELECT role, content, timestamp FROM conversations "
            "WHERE session_id = ? ORDER BY timestamp ASC",
            (sid,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_session_ids(self):
        """Get all session IDs, newest first."""
        rows = self.conn.execute(
            "SELECT DISTINCT session_id, MAX(timestamp) as last_msg, "
            "COUNT(*) as msg_count "
            "FROM conversations GROUP BY session_id "
            "ORDER BY last_msg DESC",
        ).fetchall()
        return [dict(r) for r in rows]

    def get_total_message_count(self):
        """Total messages across all sessions."""
        row = self.conn.execute(
            "SELECT COUNT(*) as n FROM conversations"
        ).fetchone()
        return row["n"] if row else 0
    
    # ═══════════════════════════════════════════════════════════
    # ── User Profile Tags ─────────────────────────────────────
    # ═══════════════════════════════════════════════════════════
    # Short 1-3 word tags inferred from conversations that describe
    # who the user is and what they prefer. Injected into prompts to
    # help the LLM tailor responses. Users can reject incorrect tags,
    # which prevents re-inference in future sessions.

    def add_profile_tag(self, tag):
        """Add a 1-3 word profile tag summarizing a user characteristic.

        Tags are short descriptors injected into prompts to help the LLM
        understand who the user is.
        """
        # Basic validation: non-empty, max 3 words, no special characters
        tag = tag.strip().lower()
        if not tag:
            return False
        # Enforce 1-3 word limit for conciseness in prompt injection
        if len(tag.split()) > 3:
            return False
        
        # Skip if this exact tag is already active
        existing = self.conn.execute(
            "SELECT id FROM user_profile_tags "
            "WHERE tag = ? AND status = 'active'",
            (tag,),
        ).fetchone()
        if existing:
            return False
        
        # Check if this tag was previously rejected — don't re-add it
        rejected = self.conn.execute(
            "SELECT id FROM user_profile_tags "
            "WHERE tag = ? AND status = 'rejected'",
            (tag,),
        ).fetchone()
        if rejected:
            return False
        
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO user_profile_tags "
            "(tag, status, source_session, created_at, updated_at) "
            "VALUES (?, 'active', ?, ?, ?)",
            (tag, self.session_id, now, now),
        )
        self.conn.commit()
        return True
    
    def get_profile_tags(self, status=None):
        """Get user profile tags, optionally filtered by status.

        Args:
            status: 'active', 'rejected', or None for all.
        """
        if status:
            rows = self.conn.execute(
                "SELECT id, tag, status, updated_at "
                "FROM user_profile_tags WHERE status = ? "
                "ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT id, tag, status, updated_at "
                "FROM user_profile_tags ORDER BY created_at DESC",
            ).fetchall()
        return [dict(r) for r in rows]
    
    def get_active_tags_for_prompt(self):
        """Get only active tags as a flat list of strings for prompt injection.

        Returns:
            List of tag strings, e.g. ['clinical microbiologist', 'S. aureus focus']
        """
        rows = self.conn.execute(
            "SELECT tag FROM user_profile_tags "
            "WHERE status = 'active' ORDER BY created_at ASC",
        ).fetchall()
        return [r["tag"] for r in rows]
    
    def reject_profile_tag(self, tag_id):
        """Mark a profile tag as rejected (incorrect).

        Rejected tags are kept in the DB so the system knows not to
        re-infer them in future sessions. They are excluded from
        prompt injection.

        Args:
            tag_id: Row ID of the tag.
        """
        self.conn.execute(
            "UPDATE user_profile_tags SET status = 'rejected', "
            "updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), tag_id),
        )
        self.conn.commit()
    
    def reactivate_profile_tag(self, tag_id):
        """Reactivate a previously rejected tag.

        Args:
            tag_id: Row ID of the tag.
        """
        self.conn.execute(
            "UPDATE user_profile_tags SET status = 'active', "
            "updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), tag_id),
        )
        self.conn.commit()

    
    def delete_profile_tag(self, tag_id):
        """Permanently delete a tag from the database.

        Use reject_profile_tag() instead if you want to prevent
        re-inference. This is for true removal (e.g., user export/import
        cleanup).

        Args:
            tag_id: Row ID of the tag.
        """
        self.conn.execute(
            "DELETE FROM user_profile_tags WHERE id = ?", (tag_id,)
        )
        self.conn.commit()

    def get_rejected_tags(self):
        """Get all rejected tag strings for use as a blocklist during extraction.

        Returns:
            Set of rejected tag strings.
        """
        rows = self.conn.execute(
            "SELECT tag FROM user_profile_tags WHERE status = 'rejected'",
        ).fetchall()
        return {r["tag"] for r in rows}

    # ═══════════════════════════════════════════════════════════
    # ── Research Objectives ───────────────────────────────────
    # ═══════════════════════════════════════════════════════════
    # Analytical goals inferred from conversations. Interactive —
    # users can mark objectives as completed or remove them.

    def add_objective(self, objective):
        """Record a research objective or analytical goal.

        Objective examples:
            'Identify transmission clusters in the outbreak'
            'Determine optimal phylothresholds'
        """
        # Skip exact duplicate active objectives
        existing = self.conn.execute(
            "SELECT id FROM research_objectives "
            "WHERE objective = ? AND status = 'active'",
            (objective,),
        ).fetchone()
        if existing:
            return False

        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO research_objectives "
            "(objective, status, source_session, created_at, updated_at) "
            "VALUES (?, 'active', ?, ?, ?)",
            (objective, self.session_id, now, now),
        )
        self.conn.commit()
        return True
    
    def get_objectives(self, status=None):
        """Get research objectives, optionally filtered by status.

        Args:
            status: 'active', 'completed', or None for all.
        """
        if status:
            rows = self.conn.execute(
                "SELECT id, objective, status, updated_at "
                "FROM research_objectives WHERE status = ? "
                "ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT id, objective, status, updated_at "
                "FROM research_objectives ORDER BY created_at DESC",
            ).fetchall()
        return [dict(r) for r in rows]
    

    def update_objective_status(self, obj_id, status):
        """Update the status of a research objective.

        Args:
            obj_id: Row ID of the objective.
            status: 'active', 'completed', or 'archived'.
        """
        if status not in ("active", "completed", "archived"):
            raise ValueError(f"Invalid status: {status}")
        self.conn.execute(
            "UPDATE research_objectives SET status = ?, updated_at = ? "
            "WHERE id = ?",
            (status, datetime.now().isoformat(), obj_id),
        )
        self.conn.commit()

    def remove_objective(self, obj_id):
        """Delete a research objective by ID."""
        self.conn.execute(
            "DELETE FROM research_objectives WHERE id = ?", (obj_id,)
        )
        self.conn.commit()

   
    # ═══════════════════════════════════════════════════════════
    # ── Session Summaries ─────────────────────────────────────
    # ═══════════════════════════════════════════════════════════
    # LLM-generated narrative summaries of completed sessions

    def save_summary(self, summary, session_id=None, message_count=0):
        """Store an LLM-generated narrative summary of a session."""
        sid = session_id or self.session_id
        self.conn.execute(
            "INSERT OR REPLACE INTO session_summaries "
            "(session_id, summary, message_count, created_at) "
            "VALUES (?, ?, ?, ?)",
            (sid, summary, message_count, datetime.now().isoformat()),
        )
        self.conn.commit()

    def get_summaries(self, limit=100):
        """Get most recent session summaries."""
        rows = self.conn.execute(
            "SELECT session_id, summary, message_count, created_at "
            "FROM session_summaries ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    
    
    # ═══════════════════════════════════════════════════════════
    # ── Memory Context for Prompt Injection ───────────────────
    # ═══════════════════════════════════════════════════════════

    def build_memory_context(self, max_summaries=3):
        """Build a memory block string to inject into the LLM system prompt.
        Example output:
            [USER MEMORY]
            User profile tags: clinical microbiologist, S. aureus focus, beginner Python

            Active research objectives:
            - Identify transmission clusters in the outbreak
            - Determine optimal phylothresholds

            Previous session summaries:
            - [2026-02-20] Discussed SNP phylothresholds for transmission clustering ...
            - [2026-02-18] Asked about Strain Identifier modes ...
            [END USER MEMORY]
        """

        active_tags = self.get_active_tags_for_prompt()
        objectives = self.get_objectives(status="active")
        all_summaries = self.get_summaries(limit=max_summaries)

        if not active_tags and not objectives and not all_summaries:
            return ""
        
        lines = ["[USER MEMORY]"]

        if active_tags:
            lines.append(f"User profile tags: {', '.join(active_tags)}")
            lines.append("")

        if objectives:
            lines.append("Active research objectives:")
            for o in objectives:
                lines.append(f"- {o['objective']}")
            lines.append("")

        if all_summaries:
            lines.append("Previous session summaries:")
            for summary_entry in all_summaries:
                date = summary_entry["created_at"][:10]
                lines.append(f"- [{date}] {summary_entry['summary']}")
            lines.append("")

        lines.append("[END USER MEMORY]")
        return "\n".join(lines)
    
    
    # ═══════════════════════════════════════════════════════════
    # ── Export / Import ───────────────────────────────────────
    # ═══════════════════════════════════════════════════════════

    def export_data(self):
        """Export all memory data as a JSON dict."""
        all_sessions_ids = self.get_all_session_ids()
        conversations = {}
        for session_idx in all_sessions_ids:
            sid = session_idx["session_id"]
            conversations[sid] = self.get_session_messages(sid)

        return {
            "version": "2.0",
            "exported_at": datetime.now().isoformat(),
            "profile_tags": self.get_profile_tags(),
            "research_objectives": self.get_objectives(),
            "session_summaries": self.get_summaries(limit=100),
            "conversations": conversations,
        }
    
    # Import the data from a JSON dict, replacing existing memory

    def import_data(self, data):
        """Import memory data from a previously exported JSON dict."""
        # Import profile tags
        for tag_entry in data.get("profile_tags", []):
            tag_text = tag_entry.get("tag", "")
            if not tag_text:
                continue
            added = self.add_profile_tag(tag_text)
            # Preserve rejected status if present
            if added and tag_entry.get("status") == "rejected":
                row = self.conn.execute(
                    "SELECT id FROM user_profile_tags "
                    "WHERE tag = ? ORDER BY created_at DESC LIMIT 1",
                    (tag_text.strip().lower(),),
                ).fetchone()
                if row:
                    self.reject_profile_tag(row["id"])
        
        # Import research objectives (deduplication handled by add_objective)
        for obj_entry in data.get("research_objectives", []):
            added = self.add_objective(obj_entry["objective"])
            # Preserve status if not active
            if added and obj_entry.get("status") != "active":
                row = self.conn.execute(
                    "SELECT id FROM research_objectives "
                    "WHERE objective = ? ORDER BY created_at DESC LIMIT 1",
                    (obj_entry["objective"],),
                ).fetchone()
                if row:
                    self.update_objective_status(row["id"], obj_entry["status"])

        # Import session summaries
        # Limit here means we only import summaries for the most recent 100 sessions to prevent overload
        existing_sids = {
            summary_entry["session_id"]
            for summary_entry in self.get_summaries(limit=1000)
        }

        for summary_entry in data.get("session_summaries", []):
            if summary_entry["session_id"] not in existing_sids:
                self.save_summary(
                    summary_entry["summary"],
                    summary_entry["session_id"],
                    summary_entry.get("message_count", 0),
                )
        
        # Import conversations
        for session_id, messages in data.get("conversations", {}).items():
            existing = self.get_session_messages(session_id)
            if not existing:
                for m in messages:
                    self.conn.execute(
                        "INSERT INTO conversations "
                        "(session_id, role, content, timestamp) "
                        "VALUES (?, ?, ?, ?)",
                        (
                            session_id,
                            m["role"],
                            m["content"],
                            m.get("timestamp", datetime.now().isoformat()),
                        ),
                    )
        self.conn.commit()
    
    # ═══════════════════════════════════════════════════════════
    # ── LLM Extraction (Save Session) ────────────────────────
    # ═══════════════════════════════════════════════════════════

    # Get the chat model and ollama url from the main entry point
    def summarize_current_session(self):
        """Summarize the current session using the configured Ollama model.

        Returns:
            Summary string (4-5 sentences), or None if too few messages.
            Do NOT start with phrases like "Here is a 4-5 sentence summary of the conversation:". Just return the summary content directly.
        """
        messages = self.get_session_messages()
        if len(messages) < 2:
            return None
        return _ollama_summarize(
            messages, model=self.model, ollama_url=self.ollama_url,
        )
    

    # Run all extraction (summary, profile, objectives) on the current session and save results to DB.
    def extract_and_save(self):
        """Run all extraction on the current session: summary, profile, objectives."""
        messages = self.get_session_messages()
        if len(messages) < 2:
            return {"status": "skipped", "reason": "Too few messages"}

        msg_dicts = [{"role": m["role"], "content": m["content"]} for m in messages]

        # Session summary
        summary = _ollama_summarize(
            msg_dicts, model=self.model, ollama_url=self.ollama_url,
        )
        self.save_summary(summary, message_count=len(messages))

        # User profile tags — pass rejected tags as blocklist
        rejected = self.get_rejected_tags()
        extracted_tags = _ollama_extract_profile_tags(
            msg_dicts,
            rejected_tags=rejected,
            model=self.model,
            ollama_url=self.ollama_url,
        )
        tags_added = 0
        for tag in extracted_tags:
            if self.add_profile_tag(tag):
                tags_added += 1
                
        
        # Research objectives
        objectives = _ollama_extract_objectives(
            msg_dicts, model=self.model, ollama_url=self.ollama_url,
        )
        for obj in objectives:
            self.add_objective(obj)

        return {
            "status": "ok",
            "summary": summary,
            "tags_extracted": tags_added,
            "objectives_extracted": len(objectives),
        }


    # ═══════════════════════════════════════════════════════════
    # ── Stats and Cleanup ─────────────────────────────────────
    # ═══════════════════════════════════════════════════════════
    def get_stats(self):
        """Return a dict of memory statistics."""
        sessions = self.get_all_session_ids()
        active_tags = self.get_profile_tags(status="active")
        objectives = self.get_objectives(status="active")
        summaries = self.get_summaries(limit=1000)
        return {
            "total_sessions": len(sessions),
            "total_messages": self.get_total_message_count(),
            "profile_tags": len(active_tags),
            "active_objectives": len(objectives),
            "total_summaries": len(summaries),
            "db_path": self.db_path,
        }

    def close(self):
        self.conn.close()
    


# ═══════════════════════════════════════════════════════════════
# ── Helper Functions (LLM Calls) ──────────────────────────────
# ═══════════════════════════════════════════════════════════════

def _ollama_generate(prompt, model, ollama_url):
    """Send a single prompt to Ollama and return the raw response text."""
    import requests

    response = requests.post(
        f"{ollama_url}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0},
        },
        # 5 minutes timeout for long summarization tasks
        timeout=300,  
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


# Helper functions for LLM calls (summarization, profile extraction, objective extraction)
def _parse_json_response(raw):
    """Parse a JSON array from an LLM response, handling code fences."""
    raw = raw.strip("`").strip()
    if raw.startswith("json"):
        raw = raw[4:].strip()
    return json.loads(raw)


def _ollama_summarize(messages, model, ollama_url):
    """Generate a concise narrative summary of a conversation session."""
    if not messages:
        return "Empty session."

    conv_lines = []
    # we only analyze the last 20 messages for summarization to keep the prompt size manageable
    # As this is a small local LMM
    for m in messages[-20:]:
        role = m["role"].upper()
        content = m["content"]
        conv_lines.append(f"{role}: {content}")
    conversation_text = "\n".join(conv_lines)

    prompt = (
        "Summarize the following conversation in 4-5 sentences. "
        "Focus on: what THRESHER topics were discussed, what questions the user "
        "asked, what answers were given, and any user preferences or context "
        "that would be useful to recall in future conversations."
        "Do NOT start with phrases like 'Here is a summary of the conversation'. Just return the summary content directly.\n\n"
        f"{conversation_text}\n\n"
        "Summary:"
    )

    try:
        return _ollama_generate(prompt, model, ollama_url)
    except Exception as e:
        return f"(Summary generation failed: {e})"


def _ollama_extract_profile_tags(messages, rejected_tags=None, model=None, ollama_url=None):
    """Extract 1-3 word user profile tags from conversation.

    Args:
        messages: List of {"role": str, "content": str} dicts.
        rejected_tags: Set of tag strings to exclude (user previously marked incorrect).
        model: Ollama model name.
        ollama_url: Ollama API base URL.

    Returns:
        List of tag strings, e.g. ['clinical microbiologist', 'S. aureus focus']
    """
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    if not user_msgs:
        return []
    
    # -10 to get the last 10 messages
    # which should be enough for profile extraction and keeps the prompt size manageable
    user_text = "\n".join(user_msgs[-10:])

    blocklist_text = ""
    if rejected_tags:
        blocklist_text = (
            "\n\nDo NOT extract these tags (previously marked incorrect by the user):\n"
            + ", ".join(sorted(rejected_tags))
        )

    prompt = (
        "Analyze the following user messages from a THRESHER-chat session. "
        "Extract 1-3 word profile tags that describe who this user is.\n\n"
        "Each tag must be 1 to 3 words. Tags should capture:\n"
        "- Role or expertise (e.g. 'clinical microbiologist', 'graduate student')\n"
        "- Target organism (e.g. 'S. aureus focus', 'E. coli')\n"
        "- Skill level (e.g. 'beginner Python', 'advanced bioinformatics')\n"
        "- Preferences (e.g. 'prefers concise', 'wants examples')\n"
        "- Research area (e.g. 'outbreak investigation', 'transmission analysis')\n\n"
        "Return ONLY a JSON array of tag strings. "
        "If nothing can be extracted, return []."
        f"{blocklist_text}\n\n"
        f"User messages:\n{user_text}\n\n"
        "JSON array:"
    )

    try:
        raw = _ollama_generate(prompt, model, ollama_url)
        items = _parse_json_response(raw)
        if isinstance(items, list):
            return [
                i.strip().lower()
                for i in items
                if isinstance(i, str) and i.strip() and len(i.split()) <= 3
            ]
    except (json.JSONDecodeError, Exception):
        pass

    return []



def _ollama_extract_objectives(messages, model, ollama_url):
    """Extract research objectives from conversation.

    Returns a list of objective strings.
    """
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    if not user_msgs:
        return []

    user_text = "\n".join(user_msgs[-10:])

    prompt = (
        "Analyze the following user messages from a THRESHER-chat session. "
        "Identify the user's research objectives — the analytical goals or key questions driving their use of THRESHER.\n\n"
        "Return ONLY a JSON array of objective strings. Each should be a "
        "concise statement of what the user wants to accomplish. "
        "If no objectives can be identified, return [].\n\n"
        "Examples of good objectives:\n"
        '  "Identify transmission clusters in the outbreak"\n'
        '  "Determine optimal phylothresholds"\n\n'
        f"User messages:\n{user_text}\n\n"
        "JSON array:"
    )

    try:
        raw = _ollama_generate(prompt, model, ollama_url)
        items = _parse_json_response(raw)
        if isinstance(items, list):
            return [i for i in items if isinstance(i, str) and i.strip()]
    except (json.JSONDecodeError, Exception):
        pass

    return []
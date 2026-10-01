"""Load and retrieve user profile definitions from guides/user_profiles.md."""
import os
import re

# Path to the user profiles markdown file
PROFILES_MD = os.path.join(
    os.path.dirname(__file__),
    "guides",
    "user_profiles.md",
)


def _parse_profiles(filepath):
    """Parse user_profiles.md into a dict of profile definitions.

    Returns a dict keyed by the **Key** field, e.g.:
        {"pi": {
            "label": "Principal Investigator",
            "short_desc": "Balanced technical overview",
            "prompt_prefix": "..."
        }}
    """
    profiles = {}

    if not os.path.exists(filepath):
        print(f"Warning: Profiles file not found at {filepath}")
        return profiles

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split on ### headings (profile sections)
    all_sections = re.split(r"^### \d+\.\s+", content, flags=re.MULTILINE)
    # Get rid of the first section which is the file header and instruction for users' custom profiles
    all_sections = all_sections[1:]
    for section_entry in all_sections:
        section_entry = section_entry.strip()
        if not section_entry:
            continue

        # First line is the profile name
        section_entry_lines = section_entry.split("\n", 1)
        entry_label = section_entry_lines[0].strip()
        entry_body = section_entry_lines[1].strip() if len(section_entry_lines) > 1 else ""

        # Extract key from **Key**: line
        entry_key_match = re.search(
            r"\*\*Key\*\*:\s*(.+?)(?:\n|$)", entry_body
        )
        if not entry_key_match:
            continue

        entry_key = entry_key_match.group(1).strip()

        # Extract the Short description line for sidebar buttons
        entry_short_desc_match = re.search(
            r"\*\*Short description\*\*:\s*(.+?)(?:\n|$)", entry_body
        )
        entry_short_desc = entry_short_desc_match.group(1).strip() if entry_short_desc_match else ""
        # Only send the **Prompt** to the LLM
        # The prompt text for each profile starts with **Prompt**: 
        # and ends wiht "---"
        # Extract everything after **Prompt**: up to the trailing ---
        entry_prompt_match = re.search(
            r"\*\*Prompt\*\*:\s*\n(.*?)(?:\n---|\Z)",
            entry_body,
            flags=re.DOTALL,
        )
        if not entry_prompt_match:
            continue
        entry_prompt_text = entry_prompt_match.group(1).strip()

        profiles[entry_key] = {
            "label": entry_label,
            "short_desc": entry_short_desc,
            "prompt_prefix": entry_prompt_text
        }

    return profiles


def get_profile_prompt(profile_key):
    """Return the prompt prefix for a given profile key, or empty string if unknown."""
    profiles = _parse_profiles(PROFILES_MD)
    profile = profiles.get(profile_key)
    if profile:
        return profile["prompt_prefix"]
    return ""


def get_profiles_for_frontend():
    """Return a list of profile dicts for the frontend sidebar."""
    profiles = _parse_profiles(PROFILES_MD)
    return [
        {"key": key, "label": p["label"], "short_desc": p["short_desc"]}
        for key, p in profiles.items()
    ]

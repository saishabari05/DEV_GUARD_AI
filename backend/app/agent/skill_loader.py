import os

# Controlled skills directory path
SKILLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "skills"))

ALLOWED_SKILLS = {
    "bug-investigation": "bug-investigation/SKILL.md",
    "root-cause-analysis": "root-cause-analysis/SKILL.md",
    "test-validation": "test-validation/SKILL.md",
    "incident-report": "incident-report/SKILL.md"
}

def load_skill(skill_name: str) -> str:
    """
    Safely loads the Markdown content for a named skill.
    Prevents path traversal, absolute paths, or loading unapproved skills.
    """
    if not skill_name or not isinstance(skill_name, str):
        raise ValueError("Invalid skill name provided.")

    if skill_name not in ALLOWED_SKILLS:
        raise ValueError(f"Unknown or unapproved skill: '{skill_name}'")

    relative_path = ALLOWED_SKILLS[skill_name]
    skill_file_path = os.path.abspath(os.path.join(SKILLS_DIR, relative_path))

    # Verify path remains inside SKILLS_DIR
    if os.path.commonpath([skill_file_path, SKILLS_DIR]) != SKILLS_DIR:
        raise ValueError(f"Path traversal attempt detected for skill '{skill_name}'")

    if not os.path.isfile(skill_file_path):
        raise FileNotFoundError(f"Skill file not found at {skill_file_path}")

    with open(skill_file_path, "r", encoding="utf-8") as f:
        return f.read()

def load_all_skills() -> dict:
    """Loads all allowed skills into a dictionary keyed by skill name."""
    return {name: load_skill(name) for name in ALLOWED_SKILLS}

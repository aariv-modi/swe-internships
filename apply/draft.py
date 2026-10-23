"""Draft long-answer questions with the local `claude` CLI (Claude Code, on your own subscription).

Drafts are starting points placed in the form for you to edit; nothing is submitted. They use only
facts from your profile, so they can't invent experience. Not used on pages that forbid AI help.
"""
import shutil
import subprocess

PROMPT = """You are helping a student draft an answer to one question on an internship application.
Write the answer in the first person, plain text, at most 150 words, specific and sincere.
Use ONLY facts from the profile below; never invent experience, numbers or employers. If the profile
lacks what the question needs, write a short honest answer and put [ADD DETAIL] where the student
should fill in specifics.

Question: {question}

Student profile:
{summary}
Projects: {projects}
School: {school}, {major}, graduating {grad}

Job posting (excerpt):
{job}
"""


def available() -> bool:
    return shutil.which("claude") is not None


def claude_drafter(question: str, job_context: str, profile: dict):
    if not available():
        return None
    about, edu = profile.get("about", {}), profile.get("education", {})
    prompt = PROMPT.format(question=question, summary=about.get("summary", ""),
                           projects=about.get("projects", ""), school=edu.get("school", ""),
                           major=edu.get("major", ""),
                           grad=f"{edu.get('grad_month', '')} {edu.get('grad_year', '')}",
                           job=job_context[:6000])
    try:
        out = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True,
                             timeout=180, encoding="utf-8")
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() or None

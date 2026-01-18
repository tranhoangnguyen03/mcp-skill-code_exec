from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ._data import load_json


@dataclass(frozen=True)
class InterviewEvent:
    stage: str
    date: str
    interviewer: str
    outcome: str | None = None


@dataclass(frozen=True)
class Candidate:
    id: str
    name: str
    email: str
    role: str
    stage: str
    status: str
    skills: list[str] = field(default_factory=list)
    source: str | None = None
    interview_history: list[InterviewEvent] = field(default_factory=list)


_CANDIDATES: list[Candidate] = []


def _init_if_needed():
    global _CANDIDATES
    if _CANDIDATES:
        return
    try:
        rows = load_json("recruiting/candidates.json")
        for row in rows:
            history = [
                InterviewEvent(
                    stage=h["stage"],
                    date=h["date"],
                    interviewer=h["interviewer"],
                    outcome=h.get("outcome"),
                )
                for h in row.get("interview_history", [])
            ]
            _CANDIDATES.append(
                Candidate(
                    id=row["id"],
                    name=row["name"],
                    email=row["email"],
                    role=row["role"],
                    stage=row["stage"],
                    status=row["status"],
                    skills=row.get("skills", []),
                    source=row.get("source"),
                    interview_history=history,
                )
            )
    except Exception as e:
        print(f"Warning: failed to load candidates seed data: {e}")


def list_candidates(stage: str | None = None, status: str | None = None) -> list[dict]:
    _init_if_needed()
    matches = _CANDIDATES
    if stage:
        matches = [c for c in matches if c.stage.lower() == stage.lower()]
    if status:
        matches = [c for c in matches if c.status.lower() == status.lower()]
    return [_to_dict(c) for c in matches]


def get_candidate(email_or_id: str) -> dict | None:
    _init_if_needed()
    for c in _CANDIDATES:
        if c.email.lower() == email_or_id.lower() or c.id == email_or_id:
            return _to_dict(c)
    return None


def search_candidates(query: str) -> list[dict]:
    _init_if_needed()
    q = query.strip().lower()
    if not q:
        return []
    matches = [
        c
        for c in _CANDIDATES
        if q in c.name.lower()
        or q in c.email.lower()
        or q in c.role.lower()
        or any(q in s.lower() for s in c.skills)
    ]
    return [_to_dict(c) for c in matches]


def update_candidate_stage(email: str, new_stage: str) -> dict:
    _init_if_needed()
    for idx, c in enumerate(_CANDIDATES):
        if c.email.lower() == email.lower():
            from dataclasses import replace

            updated = replace(c, stage=new_stage)
            _CANDIDATES[idx] = updated
            print(f"   [CandidateTracker] Updated {email} stage to '{new_stage}'")
            return _to_dict(updated)
    raise ValueError(f"Candidate not found: {email}")


def add_interview_log(
    email: str,
    stage: str,
    interviewer: str,
    date_str: str | None = None,
    outcome: str | None = None,
) -> dict:
    _init_if_needed()
    if not date_str:
        date_str = date.today().isoformat()

    for idx, c in enumerate(_CANDIDATES):
        if c.email.lower() == email.lower():
            from dataclasses import replace

            new_event = InterviewEvent(stage=stage, date=date_str, interviewer=interviewer, outcome=outcome)
            new_history = c.interview_history + [new_event]
            updated = replace(c, interview_history=new_history)
            _CANDIDATES[idx] = updated
            print(f"   [CandidateTracker] Added {stage} interview log for {email}")
            return _to_dict(updated)
    raise ValueError(f"Candidate not found: {email}")


def _to_dict(c: Candidate) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "role": c.role,
        "stage": c.stage,
        "status": c.status,
        "skills": c.skills,
        "source": c.source,
        "interview_history": [
            {
                "stage": h.stage,
                "date": h.date,
                "interviewer": h.interviewer,
                "outcome": h.outcome,
            }
            for h in c.interview_history
        ],
    }


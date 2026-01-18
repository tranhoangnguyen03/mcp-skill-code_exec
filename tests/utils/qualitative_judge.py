from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from .scenario_harness import Scenario, expected_logic_flow_steps


@dataclass(frozen=True)
class JudgeVerdict:
    passed: bool
    skill_ok: bool
    steps_ok: bool
    code_ok: bool
    logs_ok: bool
    response_ok: bool
    notes: list[str]


class JudgeLLM(Protocol):
    def chat(self, prompt: str, temperature: float = 0.2) -> str: ...


def build_judge_prompt(*, scenario: Scenario, run) -> str:
    expected_steps = expected_logic_flow_steps(scenario.expected_skill)
    expected_steps_text = "\n".join([f"- {s}" for s in expected_steps]) if expected_steps else "(none)"
    required_code = "\n".join([f"- {p}" for p in scenario.required_code_patterns]) or "(none)"
    required_logs = "\n".join([f"- {p}" for p in scenario.required_log_patterns]) or "(none)"
    required_response = ", ".join(scenario.required_response_keywords) or "(none)"
    expected_skill = scenario.expected_skill or "(none)"

    return (
        "You are a strict evaluator for an HR workflow agent.\n\n"
        "Return ONLY valid JSON with this schema:\n"
        "{\n"
        '  \"passed\": true|false,\n'
        '  \"skill_ok\": true|false,\n'
        '  \"steps_ok\": true|false,\n'
        '  \"code_ok\": true|false,\n'
        '  \"logs_ok\": true|false,\n'
        '  \"response_ok\": true|false,\n'
        '  \"notes\": [\"short reason\", ...]\n'
        "}\n\n"
        f"Scenario: {scenario.name}\n"
        f"Expected action: {scenario.expected_action}\n"
        f"Expected skill: {expected_skill}\n"
        f"User request: {run.user_request}\n\n"
        "Expected steps (from skill Logic Flow):\n"
        f"{expected_steps_text}\n\n"
        "Agent plan JSON:\n"
        f"{json.dumps(run.plan, indent=2, ensure_ascii=False)}\n\n"
        "Generated code:\n"
        f"{run.generated_code}\n\n"
        "Execution stdout:\n"
        f"{run.exec_stdout}\n\n"
        "Execution stderr:\n"
        f"{run.exec_stderr}\n\n"
        "Final response:\n"
        f"{run.final_response}\n\n"
        "Hard requirements:\n"
        f"- Code must match these patterns (regex):\n{required_code}\n"
        f"- Logs must match these patterns (regex):\n{required_logs}\n"
        "- For steps_ok: compare the agent plan steps to the expected steps. If they are identical,\n"
        "  steps_ok MUST be true. Otherwise steps_ok should be true when there is clear overlap.\n"
        f"- Response must mention keywords (case-insensitive, normalize whitespace): {required_response}\n"
        "- Consider casing/spacing variations as matches (e.g., 'Completed' matches 'completed';\n"
        "  'Onboard New Hires' matches 'onboard new hires').\n"
        "- response_ok should be true if the response clearly indicates the user request was completed\n"
        "  and references the expected skill or outcome, even if exact phrasing differs.\n"
    )


def parse_verdict(text: str) -> JudgeVerdict:
    data = _loads_first_json_object(text)
    return JudgeVerdict(
        passed=bool(data.get("passed")),
        skill_ok=bool(data.get("skill_ok")),
        steps_ok=bool(data.get("steps_ok")),
        code_ok=bool(data.get("code_ok")),
        logs_ok=bool(data.get("logs_ok")),
        response_ok=bool(data.get("response_ok")),
        notes=[str(x) for x in (data.get("notes") or [])],
    )


class HeuristicJudge:
    def chat(self, prompt: str, temperature: float = 0.2) -> str:
        scenario = _extract_between(prompt, "Scenario: ", "\nExpected action:").strip()
        expected_action = _extract_between(prompt, "Expected action: ", "\nExpected skill:").strip()
        expected_skill = _extract_between(prompt, "Expected skill: ", "\nUser request:").strip()
        user_request = _extract_between(prompt, "User request: ", "\n\nExpected steps").strip()
        plan_json = _extract_between(prompt, "Agent plan JSON:\n", "\n\nGenerated code:\n")
        code = _extract_between(prompt, "Generated code:\n", "\n\nExecution stdout:\n")
        stdout = _extract_between(prompt, "Execution stdout:\n", "\n\nExecution stderr:\n")
        final_response = _extract_between(prompt, "Final response:\n", "\n\nHard requirements:\n")

        try:
            plan = json.loads(plan_json)
        except json.JSONDecodeError:
            verdict = JudgeVerdict(
                passed=False,
                skill_ok=False,
                steps_ok=False,
                code_ok=False,
                logs_ok=False,
                response_ok=False,
                notes=["plan_json is not valid JSON"],
            )
            return json.dumps(verdict.__dict__, ensure_ascii=False)

        notes: list[str] = []

        if expected_action == "custom_script":
            skill_ok = plan.get("action") == "custom_script"
            if not skill_ok:
                notes.append(f"action mismatch: got={plan.get('action')} expected=custom_script")
        else:
            skill_ok = plan.get("skill_name") == expected_skill and plan.get("action") == "execute_skill"
            if not skill_ok:
                notes.append(f"skill mismatch: got={plan.get('skill_name')} expected={expected_skill}")

        expected_steps = expected_logic_flow_steps(None if expected_skill == "(none)" else expected_skill)
        actual_steps = plan.get("steps") or []
        steps_ok = True
        if expected_steps and expected_action == "execute_skill":
            overlap = set(map(str, actual_steps)).intersection(set(map(str, expected_steps)))
            steps_ok = len(overlap) >= max(1, min(3, len(expected_steps)))
            if not steps_ok:
                notes.append("plan steps do not resemble skill Logic Flow")

        required_code_patterns = _extract_list_block(prompt, "Code must match these patterns (regex):\n", "\n- Logs must match")
        code_ok = _all_patterns_match(code, required_code_patterns)
        if not code_ok:
            notes.append("generated code missing required patterns")

        required_log_patterns = _extract_list_block(prompt, "Logs must match these patterns (regex):\n", "\n- Response must mention keywords:")
        logs_ok = _all_patterns_match(stdout, required_log_patterns)
        if not logs_ok:
            notes.append("execution logs missing required patterns")

        m = re.search(r"^- Response must mention keywords.*?:\s*(.*)$", prompt, flags=re.MULTILINE)
        required_keywords = (m.group(1) if m else "").strip()
        keywords = [k.strip().lower() for k in required_keywords.split(",") if k.strip() and k.strip() != "(none)"]
        response_ok = True
        if keywords:
            response_ok = all(k in final_response.lower() for k in keywords)
            if not response_ok:
                notes.append("final response missing required keywords")

        passed = all([skill_ok, steps_ok, code_ok, logs_ok, response_ok])
        if not passed and scenario:
            notes.insert(0, f"scenario={scenario} request={user_request}")

        verdict = JudgeVerdict(
            passed=passed,
            skill_ok=skill_ok,
            steps_ok=steps_ok,
            code_ok=code_ok,
            logs_ok=logs_ok,
            response_ok=response_ok,
            notes=notes,
        )
        return json.dumps(verdict.__dict__, ensure_ascii=False)


def evaluate_with_judge(*, judge: JudgeLLM, scenario: Scenario, run) -> JudgeVerdict:
    prompt = build_judge_prompt(scenario=scenario, run=run)
    out = judge.chat(prompt, temperature=0.0)
    return parse_verdict(out)


def _all_patterns_match(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if not p:
            continue
        if re.search(p, text, flags=re.MULTILINE) is None:
            return False
    return True


def _extract_between(text: str, start: str, end: str) -> str:
    if start not in text or end not in text:
        return ""
    return text.split(start, 1)[1].split(end, 1)[0]


def _extract_after(text: str, start: str) -> str:
    if start not in text:
        return ""
    return text.split(start, 1)[1]


def _extract_list_block(text: str, start: str, end: str) -> list[str]:
    block = _extract_between(text, start, end)
    lines = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- "):
            lines.append(line[2:].strip())
        elif line and line != "(none)":
            lines.append(line)
    return lines


def _loads_first_json_object(text: str) -> dict:
    if not text or not str(text).strip():
        raise json.JSONDecodeError("empty response", text or "", 0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        s = str(text).strip()
        start = s.find("{")
        end = s.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(s[start : end + 1])

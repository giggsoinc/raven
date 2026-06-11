#!/usr/bin/env python3
"""
Raven — Architect Router

Symmetric counterpart to triage-router. Forces andie load on architecture-class
prompts so Andie cannot be skipped via description-only matching.

Rule: DECISION intent (design/plan/should-I/which/tradeoff/architecture) AND not a
symptom (those go to triage-router); build/create verbs also need multi-component
scope. Match → print [ANDIE REQUIRED] (Claude injects it as additionalContext);
else silent. Order: force (T3.1) → regex → opt-in semantic (T3.2). Local-only.
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from router_common import force_intent, semantic_fallback, log_overhead
except Exception:  # fail-soft: routing still works without the shared helper
    def force_intent(_p): return None
    def semantic_fallback(_p, _k): return False
    def log_overhead(_s, _t): return None

# ── DECISION intent — any one match triggers (a) ──────────────────────────────
DECISION = re.compile(
    r"(?:"
    r"\bdesign\b"
    r"|\bplan(?:ning)?\b"
    r"|\barchitecture\b|\barchitect(?:ural)?\b"
    r"|\bshould\s+i\b|\bshould\s+we\b"
    r"|\bwhich\s+(?:approach|option|way|stack|tool|library|framework|design|pattern)"
    r"|\bcompare\b|\bcomparison\b"
    r"|\btrade.?off\b|\bpros\s+and\s+cons\b"
    r"|\brefactor\b"
    r"|\bscaffold\b|\bbootstrap\b"
    r"|\bhow\s+do\s+i\s+(?:approach|design|architect|structure|organize|model)"
    r"|\bhow\s+should\s+i\b"
    r"|\bbest\s+way\s+to\b"
    r"|\bevaluate\b|\bassess\b"
    r"|\bbuild\s+(?:me\s+)?(?:a|an|the|new)\s+\w"
    r"|\bcreate\s+(?:a|an|the|new)\s+\w"
    r"|\bimplement\s+(?:a|an|the|new)\s+\w"
    r"|\badd\s+(?:a|an|the|new)\s+\w"
    r"|\bdecide\b|\bdecision\b"
    r"|\bstrategy\b|\bstrategic\b"
    r"|\broadmap\b"
    r"|\breview\s+(?:options|approaches|approach|design|architecture)"
    r"|\bgreenfield\b"
    r"|\bsystem\s+design\b"
    r")",
    re.IGNORECASE,
)

# ── MULTI-COMPONENT scope signals — words/patterns that imply ≥2 moving parts ──
MULTI_COMPONENT = re.compile(
    r"(?:"
    r"\bauth(?:entication|orization)?\s+(?:and|\+|with|plus)\s+\w+"
    r"|\b(?:api|frontend|backend|database|cache|queue|worker|service)\s+(?:and|\+|with|plus)\s+\w+"
    r"|\bmulti.\w+"  # multi-tenant, multi-region, multi-user, multi-service
    r"|\bdistributed\b"
    r"|\bpipeline\b|\bworkflow\b|\borchestrat(?:e|ion)\b"
    r"|\bmicroservice"
    r"|\bevent.driven\b|\bevent\s+sourc(?:e|ing)\b"
    r"|\bdata\s+model\b|\bschema\b|\bentity\s+(?:relationship|model)"
    r"|\bintegration\s+(?:between|of|with)"
    r"|\bcross.\w+"  # cross-region, cross-service, cross-team
    r"|\bend.to.end\b|\be2e\b"
    r"|\bstack\b|\barchitecture\b|\bplatform\b"
    r"|\bsystem\b.{0,30}\bsystem\b"  # mentions "system" twice
    r"|\b(?:two|three|four|five|multiple|several|many)\s+(?:services|systems|components|modules|tiers|layers)"
    r"|\bmonorepo\b|\bmono.repo\b"
    r"|\brbac\b|\bsso\b|\boauth\b"  # complex feature acronyms imply multi-component
    r"|\bobservability\b|\btelemetry\b|\bmetrics?\s+and\s+log"
    r"|\bci/cd\b|\bcicd\b|\bdeployment\s+pipeline\b"
    r")",
    re.IGNORECASE,
)

# ── SYMPTOM negation — triage-router handles these ────────────────────────────
SYMPTOM_NEGATE = re.compile(
    r"(?:"
    r"\btiming?\s*out\b|\btimed?\s*out\b|\btimeout\b"
    r"|\bfail(?:ing|ed|s|ure)?\b|\bcrash(?:ing|ed|es)?\b|\bhang(?:ing|s)?\b"
    r"|\bstuck\b|\bfrozen\b|\bunresponsive\b|\bbroken\b"
    r"|\berror\b|\bexception\b|\btraceback\b|\bstack\s*trace\b"
    r"|\bregression\b|\bused\s+to\s+\w+"
    r"|\bdoesn'?t\s+(?:work|run|fire|return|load|start)\b"
    r"|\bnot\s+(?:working|responding|loading|firing|starting)\b"
    r"|\bcan'?t\s+(?:connect|reach|access)\b"
    r"|\bwhy\s+(?:is|isn'?t|did|does|won'?t)\s+(?:my|the|this)"
    r")",
    re.IGNORECASE,
)


def classify(prompt: str) -> bool:
    """Return True if prompt is architecture-class (andie required)."""
    if not prompt or not prompt.strip():
        return False
    if SYMPTOM_NEGATE.search(prompt):
        return False  # triage-router owns this
    has_decision = bool(DECISION.search(prompt))
    has_multi    = bool(MULTI_COMPONENT.search(prompt))
    # Decision intent alone is enough for clear architecture verbs
    # (design, architecture, plan, should I, which, etc.)
    # Build/create/add need multi-component scope to qualify
    build_only = re.compile(r"^\s*(?:build|create|add|implement|scaffold|bootstrap)\s+", re.IGNORECASE)
    if build_only.match(prompt) and not has_multi:
        return False  # "build a function" — too small, let normal routing handle
    return has_decision


def main():
    """Emit [ANDIE REQUIRED] for architecture-class prompts.

    Order: explicit force (T3.1) → regex classify → opt-in semantic fallback (T3.2).
    """
    prompt = os.environ.get("PROMPT", "")
    if not prompt:
        try:
            prompt = sys.stdin.read()
        except Exception:
            return
    forced = force_intent(prompt)
    if forced == "andie-jr":
        return  # explicit andie-jr force is exclusive — triage-router owns it
    trigger = (forced == "andie") or classify(prompt)
    if not trigger and semantic_fallback(
            prompt, "asking for a design decision, architecture, or a tradeoff "
                    "between approaches across more than one component"):
        trigger = True
    if trigger:
        emission = (
            "[ANDIE REQUIRED] This prompt is architecture-class — it involves "
            "design decisions, multi-component scope, or strategic tradeoffs. "
            "MANDATORY: invoke `andie` skill BEFORE responding. Andie runs the "
            "Functional/Technical/Data triad, HITL-gates proposals, OODA loops, "
            "and hands off a crisp plan. Do not free-style the design.\n"
        )
        why = "forced via /andie" if forced == "andie" else "architecture-class prompt detected"
        # Hook JSON: additionalContext for the model, systemMessage toaster the
        # user actually sees — Raven never routes silently.
        sys.stdout.write(json.dumps({
            "systemMessage": f"🪶 Raven → andie · {why} · triad plan before code",
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": emission,
            },
        }) + "\n")
        log_overhead("architect-router", emission)


if __name__ == "__main__":
    main()

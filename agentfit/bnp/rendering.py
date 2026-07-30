"""
BNP Profile Rendering.

Shared text rendering of a BNPProfile for LLM prompts. Both the post-hoc
interpretability judge (agentfit/interpretability/prompts.py) and the
loop-testing transcript judge (agentfit/loop/prompts.py) need to describe
"what this organization actually needs" to their respective LLM calls —
this lives in one place so the two judges never drift into describing the
same BNP differently.
"""

from agentfit.bnp.schema import BNPProfile


def render_bnp_section(bnp: BNPProfile) -> str:
    """
    Render a BNP profile as a plain-text prompt section.

    Includes name/organization/domain/description, requirements (flagging
    required vs. optional), dimension weights, compliance requirements, and
    latency constraints — everything an LLM judge needs to ground its
    scoring in what the organization actually asked for, rather than
    judging the agent against some generic notion of "good."
    """
    lines = ["=== BUSINESS NEED PROFILE (BNP) ==="]
    lines.append(f"Name: {bnp.name}")
    lines.append(f"Organization: {bnp.organization}")
    lines.append(f"Domain: {bnp.domain}")
    lines.append(f"Description: {bnp.description}")
    lines.append(f"Task Complexity: {bnp.task_complexity}")

    if bnp.requirements:
        lines.append("\nRequirements:")
        for req in bnp.requirements:
            flag = "[REQUIRED]" if req.required else "[OPTIONAL]"
            rate = f" (min success rate: {req.min_success_rate})" if req.min_success_rate else ""
            lines.append(f"  - {flag} {req.capability}: {req.description}{rate}")

    if bnp.evaluation_dimensions:
        lines.append("\nDimension Weights:")
        for dw in bnp.evaluation_dimensions:
            lines.append(f"  - {dw.dimension}: weight={dw.weight}")

    if bnp.compliance_requirements:
        lines.append(f"\nCompliance: {', '.join(bnp.compliance_requirements)}")

    if bnp.max_latency_ms:
        lines.append(f"Max Latency: {bnp.max_latency_ms}ms")

    return "\n".join(lines)

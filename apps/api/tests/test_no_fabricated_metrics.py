import re
from pathlib import Path

WORKER = Path("apps/api/app/workers/worker.py")

FORBIDDEN = [
    r'"engagement_rate":\s*0\.\d+',
    r'"audience_credibility":\s*\d+',
    r'"audience_quality":\s*\d+',
    r'"country":\s*raw\.get\([^)]*,\s*"VE"\s*\)',
]


def test_worker_does_not_fabricate_metric_values():
    src = WORKER.read_text(encoding="utf-8")
    offenders = []
    for pattern in FORBIDDEN:
        for m in re.finditer(pattern, src):
            line_no = src[: m.start()].count("\n") + 1
            offenders.append(f"{WORKER}:{line_no}  {m.group()}")
    assert not offenders, (
        "Valores de métrica fabricados detectados. Regla LWFA: NULL != 0.\n"
        + "\n".join(offenders)
    )

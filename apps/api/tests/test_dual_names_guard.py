"""Dual-Names Guard Test — Regression test for FASE 1.1.

Ref: docs/AUDITORIA_LANZ_v2_1_2026-08-28.md §7.2

El plan Lanz v2.1 FASE 1.1 requiere eliminar los 8 sitios de dual-write
en search steps. Este test funciona como regression guard: cuenta las
referencias a camelCase fields en worker.py y falla si el count sube.

Canonical snake_case fields para discovery:
- follower_count, following_count, posts_count
- full_name, biography, avatar_url
- is_business, is_verified, is_private
- username, handle, pk

Canonical camelCase fields (DEBE ser removido progresivamente):
- followersCount, followingCount, postsCount
- fullName, biographyText, profilePicUrl
- isBusinessAccount, isVerified, isPrivate
- userName, uniqueId
"""

import re
import pytest


DUAL_NAME_PATTERNS = [
    r'"followersCount"',
    r'"followingCount"',
    r'"followsCount"',
    r'"postsCount"',
    r'"fullName"',
    r'"biographyText"',
    r'"profilePicUrl"',
    r'"hdProfilePicUrl"',
    r'"isBusinessAccount"',
    r'"isVerified"',
    r'"isPrivate"',
    r'"userName"',
    r'"uniqueId"',
    r'"ownerUsername"',
    r'"ownerFullName"',
    r'"videoCount"',
    r'"likeCount"',
    r'"likesCount"',
    r'"commentCount"',
    r'"commentsCount"',
    r'"shareUrl"',
    r'"videoView"',
]

WORKER_PATH = "apps/api/app/workers/worker.py"

BASELINE_COUNTS = {
    "followersCount": 24,
    "followingCount": 2,
    "followsCount": 21,
    "postsCount": 24,
    "fullName": 13,
    "biographyText": 0,
    "profilePicUrl": 28,
    "hdProfilePicUrl": 1,
    "isBusinessAccount": 21,
    "isVerified": 1,
    "isPrivate": 0,
    "userName": 0,
    "uniqueId": 1,
    "ownerUsername": 6,
    "ownerFullName": 6,
    "videoCount": 3,
    "likeCount": 0,
    "likesCount": 3,
    "commentCount": 0,
    "commentsCount": 3,
    "shareUrl": 1,
    "videoView": 1,
}


class TestDualNamesGuard:
    """Regression guard para dual-name patterns en worker.py.

    Si necesitás agregar un nuevo dual-write (compat legacy con APIs externas),
    primero remové el anterior más antiguo. Si no hay anterior para remover,
    aumentá el BASELINE_COUNTS con justificación en el PR.
    """

    def test_camelcase_field_writes_not_increasing(self):
        """El count de camelCase field writes no debe aumentar vs baseline."""
        import os

        worker_full_path = os.path.join(
            os.path.dirname(__file__), "..", "..", WORKER_PATH
        )
        with open(worker_full_path, encoding="utf-8") as f:
            content = f.read()

        violations = []
        for pattern in DUAL_NAME_PATTERNS:
            field_name = pattern.strip('"')
            matches = re.findall(pattern, content)
            baseline = BASELINE_COUNTS.get(field_name, 0)
            actual = len(matches)
            if actual > baseline:
                violations.append(
                    f"  {field_name}: {actual} (baseline={baseline}, +{actual - baseline})"
                )

        if violations:
            msg = (
                "DUAL-NAME REGRESSION: Los siguientes campos camelCase aumentaron:\n"
                + "\n".join(violations)
                + "\n\nPara agregar un nuevo dual-write, remové uno existente primero."
                + "\nSi necesitás exceptions, actualizá BASELINE_COUNTS en este test con justificación."
            )
            pytest.fail(msg)

    def test_no_new_camelcase_in_profile_assignment(self):
        """No se deben agregar nuevos patrones '"fieldName":' en profile dicts."""
        import os

        worker_full_path = os.path.join(
            os.path.dirname(__file__), "..", "..", WORKER_PATH
        )
        with open(worker_full_path, encoding="utf-8") as f:
            lines = f.readlines()

        new_patterns = []
        for i, line in enumerate(lines, 1):
            for pattern in DUAL_NAME_PATTERNS:
                field_name = pattern.strip('"')
                if re.search(pattern, line):
                    baseline = BASELINE_COUNTS.get(field_name, 0)
                    if baseline == 0:
                        new_patterns.append(f"  Line {i}: {field_name} -> {line.strip()}")

        if new_patterns:
            pytest.fail(
                "NUEVOS campos camelCase encontrados (baseline=0):\n"
                + "\n".join(new_patterns[:10])
                + "\n\nSi es legacy compat intencional, mové el baseline a 1 con justificación."
            )

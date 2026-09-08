"""Tests FIX 08-sep-2026: upload-brief 404 — ruta duplicada en el decorator.

El decorator decía "/lens/discovery/upload-brief" pero el router ya tiene
prefix="/discovery" y lens.py ya agrega "/lens" — la ruta real era
/api/v1/lens/discovery/lens/discovery/upload-brief → 404 en producción.
"""

from pathlib import Path

_SRC = Path("apps/api/app/api/v1/discovery.py").read_text(encoding="utf-8")


class TestUploadBriefRoute:
    def test_decorator_is_not_duplicated(self):
        """El decorator debe ser @router.post("/upload-brief") — sin el
        prefijo /lens/discovery duplicado."""
        assert '@router.post("/upload-brief")' in _SRC, (
            'El decorator debe ser @router.post("/upload-brief") — '
            "el router ya tiene prefix=/discovery y lens.py ya agrega /lens."
        )

    def test_decorator_does_not_duplicate_prefix(self):
        """El decorator NO debe contener /lens/discovery en el path."""
        import re

        matches = re.findall(r'@router\.post\("([^"]+)"\)', _SRC)
        upload_routes = [m for m in matches if "upload" in m]
        for route in upload_routes:
            assert route == "/upload-brief", (
                f"Decorator de upload tiene path duplicado: '{route}'. "
                f"Debe ser '/upload-brief' (sin /lens/discovery)."
            )

    def test_parse_from_document_exists(self):
        """brief_parser debe exponer parse_from_document para el endpoint."""
        parser_src = Path("packages/discovery/discovery/brief_parser.py").read_text(encoding="utf-8")
        assert "async def parse_from_document" in parser_src

    def test_frontend_calls_correct_path(self):
        """El frontend debe llamar /lens/discovery/upload-brief (sin duplicar)."""
        api_src = Path("apps/web/src/features/lens/api/lensApi.ts").read_text(encoding="utf-8")
        assert "/lens/discovery/upload-brief" in api_src, (
            "El frontend debe llamar /lens/discovery/upload-brief"
        )

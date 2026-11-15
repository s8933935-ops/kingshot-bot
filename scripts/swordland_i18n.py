#!/usr/bin/env python3
"""Schema parity checker and bundle loader for 4-language (ja/en/ar/tr) Swordland portals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LANGS = ("ja", "en", "ar", "tr")


def _compare_shape(ref: Any, tgt: Any, path: str, errors: list[str]) -> None:
    if isinstance(ref, dict):
        if not isinstance(tgt, dict):
            errors.append(f"{path}: expected dict, got {type(tgt).__name__}")
            return
        ref_keys = set(ref.keys())
        tgt_keys = set(tgt.keys())
        for missing in sorted(ref_keys - tgt_keys):
            errors.append(f"{path}.{missing}: missing key")
        for extra in sorted(tgt_keys - ref_keys):
            errors.append(f"{path}.{extra}: unexpected key")
        for k in sorted(ref_keys & tgt_keys):
            _compare_shape(ref[k], tgt[k], f"{path}.{k}", errors)
    elif isinstance(ref, list):
        if not isinstance(tgt, list):
            errors.append(f"{path}: expected list, got {type(tgt).__name__}")
            return
        if len(ref) != len(tgt):
            errors.append(f"{path}: expected len {len(ref)}, got {len(tgt)}")
            return
        for idx, (rv, tv) in enumerate(zip(ref, tgt)):
            _compare_shape(rv, tv, f"{path}[{idx}]", errors)
    elif isinstance(ref, str):
        if not isinstance(tgt, str) or not tgt.strip():
            errors.append(f"{path}: expected non-empty str")


def load_and_validate_bundles(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    """Load ja/en/ar/tr translation JSONs and enforce strict structural parity against ja."""
    bundles: dict[str, dict[str, Any]] = {}
    for lang in LANGS:
        p = paths[lang]
        bundles[lang] = json.loads(p.read_text(encoding="utf-8"))

    ref = bundles["ja"]
    all_errors: list[str] = []
    for lang in ("en", "ar", "tr"):
        errs: list[str] = []
        _compare_shape(ref, bundles[lang], lang, errs)
        all_errors.extend(errs)
    if all_errors:
        raise ValueError("i18n parity check failed:\n" + "\n".join(all_errors[:30]))
    return bundles

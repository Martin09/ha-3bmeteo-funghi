"""Keep translations, packaged files, and source dependencies in sync."""

import json
import tomllib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components/3bmeteo_funghi"


def leaves(data, prefix=""):
    return {f"{prefix}.{key}" for key, value in data.items() if not isinstance(value, dict)} | set().union(
        *(leaves(value, f"{prefix}.{key}") for key, value in data.items() if isinstance(value, dict))
    )


def test_translation_parity():
    strings = json.loads((INTEGRATION / "strings.json").read_text())
    english = json.loads((INTEGRATION / "translations/en.json").read_text())
    italian = json.loads((INTEGRATION / "translations/it.json").read_text())
    assert strings == english
    assert leaves(strings) == leaves(italian)


def test_distribution_metadata():
    manifest = json.loads((INTEGRATION / "manifest.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert manifest["version"] == project["project"]["version"]
    assert set(manifest["requirements"]) <= set(project["dependency-groups"]["dev"])
    assert (INTEGRATION / "card/3bmeteo-funghi-card.js").is_file()
    with Image.open(INTEGRATION / "brand/icon.png") as icon:
        assert icon.size == (256, 256)

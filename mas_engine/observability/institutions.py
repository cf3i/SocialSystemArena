"""Institution registry for mapping institution names to spec files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any


@dataclass(frozen=True)
class SpecEntry:
    id: str
    name: str
    name_en: str
    path: str
    description: str = ""
    description_en: str = ""


@dataclass(frozen=True)
class InstitutionEntry:
    id: str
    name: str
    name_en: str
    description: str
    description_en: str
    default_spec_id: str
    specs: tuple[SpecEntry, ...]


class InstitutionRegistry:
    """Load and resolve institution/spec mapping from YAML registry."""

    def __init__(
        self,
        registry_path: str | Path = "systems/institutions.yaml",
        workspace_root: str | Path | None = None,
    ):
        self.workspace_root = Path(workspace_root or Path.cwd()).expanduser().resolve()
        self.registry_path = self._resolve_path(Path(registry_path).expanduser())
        self._institutions: dict[str, InstitutionEntry] = {}
        self._spec_index: dict[str, tuple[InstitutionEntry, SpecEntry]] = {}
        self._load()

    def _resolve_path(self, path: Path) -> Path:
        if path.is_absolute():
            return path.resolve()
        return (self.workspace_root / path).resolve()

    def _load(self) -> None:
        self._institutions = {}
        self._spec_index = {}

        if not self.registry_path.exists():
            return

        yaml = self._yaml_module()

        raw = yaml.safe_load(self.registry_path.read_text(encoding="utf-8"))
        if raw is None:
            return
        if not isinstance(raw, dict):
            raise ValueError("institutions registry root must be object")

        rows = raw.get("institutions", [])
        if not isinstance(rows, list):
            raise ValueError("institutions field must be list")

        for idx, item in enumerate(rows):
            if not isinstance(item, dict):
                raise ValueError(f"institutions[{idx}] must be object")
            iid = str(item.get("id", "")).strip()
            name = str(item.get("name", "")).strip()
            name_en = str(item.get("name_en", "")).strip() or name
            description = str(item.get("description", "")).strip()
            description_en = str(item.get("description_en", "")).strip() or description
            if not iid or not name:
                raise ValueError(f"institutions[{idx}] requires id and name")

            specs_raw = item.get("specs", [])
            if not isinstance(specs_raw, list) or not specs_raw:
                raise ValueError(f"institutions[{idx}] must have non-empty specs")

            specs: list[SpecEntry] = []
            for jdx, s in enumerate(specs_raw):
                if not isinstance(s, dict):
                    raise ValueError(f"institutions[{idx}].specs[{jdx}] must be object")
                sid = str(s.get("id", "")).strip()
                sname = str(s.get("name", "")).strip()
                sname_en = str(s.get("name_en", "")).strip() or sname
                spath = str(s.get("path", "")).strip()
                sdesc = str(s.get("description", "")).strip()
                sdesc_en = str(s.get("description_en", "")).strip() or sdesc
                if not sid or not sname or not spath:
                    raise ValueError(
                        f"institutions[{idx}].specs[{jdx}] requires id/name/path"
                    )
                specs.append(
                    SpecEntry(
                        id=sid,
                        name=sname,
                        name_en=sname_en,
                        path=spath,
                        description=sdesc,
                        description_en=sdesc_en,
                    )
                )

            default_spec_id = str(item.get("default_spec_id", "")).strip() or specs[0].id
            if default_spec_id not in {s.id for s in specs}:
                raise ValueError(
                    f"institution '{iid}' default_spec_id '{default_spec_id}' not in specs"
                )

            inst = InstitutionEntry(
                id=iid,
                name=name,
                name_en=name_en,
                description=description,
                description_en=description_en,
                default_spec_id=default_spec_id,
                specs=tuple(specs),
            )
            if iid in self._institutions:
                raise ValueError(f"duplicate institution id: {iid}")
            self._institutions[iid] = inst

            for spec in inst.specs:
                if spec.id in self._spec_index:
                    raise ValueError(f"duplicate spec id in registry: {spec.id}")
                self._spec_index[spec.id] = (inst, spec)

    def upsert_institution_spec(
        self,
        *,
        institution_id: str,
        institution_name: str,
        institution_name_en: str = "",
        institution_description: str = "",
        institution_description_en: str = "",
        spec_id: str,
        spec_name: str,
        spec_name_en: str = "",
        spec_description: str = "",
        spec_description_en: str = "",
        spec_path: str | None = None,
        spec_text: str,
        set_default: bool = True,
    ) -> dict[str, Any]:
        iid = self._normalize_id(institution_id)
        sid = self._normalize_id(spec_id)
        iname = str(institution_name or "").strip()
        iname_en = str(institution_name_en or "").strip() or iname
        sname = str(spec_name or "").strip()
        sname_en = str(spec_name_en or "").strip() or sname
        sdesc = str(spec_description or "").strip()
        sdesc_en = str(spec_description_en or "").strip() or sdesc
        idesc = str(institution_description or "").strip()
        idesc_en = str(institution_description_en or "").strip() or idesc
        if not iid:
            raise ValueError("institution_id is required")
        if not sid:
            raise ValueError("spec_id is required")
        if not iname:
            raise ValueError("institution_name is required")
        if not sname:
            raise ValueError("spec_name is required")
        if not str(spec_text or "").strip():
            raise ValueError("spec_text is required")

        rel_spec_path = self._normalize_rel_spec_path(spec_path=spec_path, spec_id=sid)
        abs_spec_path = self._resolve_path(Path(rel_spec_path))
        if not self._is_within(abs_spec_path, self.workspace_root):
            raise ValueError("spec_path must be inside workspace")
        abs_spec_path.parent.mkdir(parents=True, exist_ok=True)
        text = str(spec_text)
        if not text.endswith("\n"):
            text += "\n"
        abs_spec_path.write_text(text, encoding="utf-8")

        raw = self._load_registry_raw_for_update()
        rows = raw["institutions"]

        # Ensure global spec-id uniqueness across institutions.
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            rid = self._normalize_id(str(row.get("id", "")))
            if rid == iid:
                continue
            for s in (row.get("specs") or []):
                if not isinstance(s, dict):
                    continue
                if self._normalize_id(str(s.get("id", ""))) == sid:
                    raise ValueError(
                        f"spec_id '{sid}' already exists under institution '{rid or idx}'"
                    )

        inst = None
        for row in rows:
            if not isinstance(row, dict):
                continue
            if self._normalize_id(str(row.get("id", ""))) == iid:
                inst = row
                break

        if inst is None:
            inst = {
                "id": iid,
                "name": iname,
                "name_en": iname_en,
                "description": idesc,
                "description_en": idesc_en,
                "default_spec_id": sid,
                "specs": [],
            }
            rows.append(inst)
        else:
            inst["id"] = iid
            inst["name"] = iname
            inst["name_en"] = iname_en
            inst["description"] = idesc
            inst["description_en"] = idesc_en

        specs_raw = inst.get("specs")
        if not isinstance(specs_raw, list):
            specs_raw = []
            inst["specs"] = specs_raw

        spec_row = None
        for s in specs_raw:
            if not isinstance(s, dict):
                continue
            if self._normalize_id(str(s.get("id", ""))) == sid:
                spec_row = s
                break

        if spec_row is None:
            spec_row = {"id": sid}
            specs_raw.append(spec_row)
        spec_row["id"] = sid
        spec_row["name"] = sname
        spec_row["name_en"] = sname_en
        spec_row["path"] = rel_spec_path
        spec_row["description"] = sdesc
        spec_row["description_en"] = sdesc_en

        valid_spec_ids = {
            self._normalize_id(str(s.get("id", "")))
            for s in specs_raw
            if isinstance(s, dict) and self._normalize_id(str(s.get("id", "")))
        }
        default_spec_id = self._normalize_id(str(inst.get("default_spec_id", "")))
        if set_default or not default_spec_id or default_spec_id not in valid_spec_ids:
            inst["default_spec_id"] = sid

        self._write_registry_raw(raw)
        self._load()
        info = self.get_spec(sid)
        return {
            "institution": self.get_institution(iid),
            "spec": info,
            "spec_path": info["spec_path"],
        }

    def list_institutions(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for inst in sorted(self._institutions.values(), key=lambda x: x.name):
            rows.append(self._institution_payload(inst, include_specs=False))
        return rows

    def get_institution(self, institution_id: str) -> dict[str, Any]:
        inst = self._institutions.get(str(institution_id).strip())
        if inst is None:
            raise KeyError(f"institution not found: {institution_id}")
        return self._institution_payload(inst, include_specs=True)

    def get_spec(self, spec_id: str) -> dict[str, Any]:
        item = self._spec_index.get(str(spec_id).strip())
        if item is None:
            raise KeyError(f"spec not found: {spec_id}")
        inst, spec = item
        path = self._resolve_path(Path(spec.path))
        return {
            "spec_id": spec.id,
            "spec_name": spec.name,
            "spec_name_en": spec.name_en,
            "spec_description": spec.description,
            "spec_description_en": spec.description_en,
            "spec_path": str(path),
            "institution_id": inst.id,
            "institution_name": inst.name,
            "institution_name_en": inst.name_en,
        }

    def resolve_spec(
        self,
        *,
        institution_id: str | None = None,
        spec_id: str | None = None,
        spec_path: str | None = None,
    ) -> dict[str, Any]:
        if spec_path:
            path = self._resolve_path(Path(spec_path).expanduser())
            return {
                "spec_path": str(path),
                "institution_id": institution_id or "",
                "spec_id": spec_id or "",
            }

        if spec_id:
            return self.get_spec(spec_id)

        if institution_id:
            inst = self._institutions.get(str(institution_id).strip())
            if inst is None:
                raise KeyError(f"institution not found: {institution_id}")
            return self.get_spec(inst.default_spec_id)

        raise ValueError("one of spec_path/spec_id/institution_id is required")

    def read_spec_text(self, spec_id: str) -> tuple[dict[str, Any], str]:
        info = self.get_spec(spec_id)
        path = Path(info["spec_path"])
        if not path.exists():
            raise FileNotFoundError(f"spec file not found: {path}")
        return info, path.read_text(encoding="utf-8")

    def _institution_payload(
        self,
        inst: InstitutionEntry,
        include_specs: bool,
    ) -> dict[str, Any]:
        out = {
            "institution_id": inst.id,
            "institution_name": inst.name,
            "institution_name_en": inst.name_en,
            "description": inst.description,
            "description_en": inst.description_en,
            "default_spec_id": inst.default_spec_id,
        }
        if include_specs:
            specs: list[dict[str, Any]] = []
            for spec in inst.specs:
                resolved = self._resolve_path(Path(spec.path))
                specs.append(
                    {
                        "spec_id": spec.id,
                        "spec_name": spec.name,
                        "spec_name_en": spec.name_en,
                        "spec_description": spec.description,
                        "spec_description_en": spec.description_en,
                        "spec_path": str(resolved),
                        "exists": resolved.exists(),
                    }
                )
            out["specs"] = specs
        return out

    def _yaml_module(self) -> Any:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError(
                "Institution registry requires PyYAML. Install with `pip install pyyaml`."
            ) from exc
        return yaml

    def _load_registry_raw_for_update(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            return {"institutions": []}
        yaml = self._yaml_module()
        raw = yaml.safe_load(self.registry_path.read_text(encoding="utf-8"))
        if raw is None:
            return {"institutions": []}
        if not isinstance(raw, dict):
            raise ValueError("institutions registry root must be object")
        rows = raw.get("institutions")
        if rows is None:
            raw["institutions"] = []
        elif not isinstance(rows, list):
            raise ValueError("institutions field must be list")
        return raw

    def _write_registry_raw(self, raw: dict[str, Any]) -> None:
        yaml = self._yaml_module()
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        text = yaml.safe_dump(raw, allow_unicode=True, sort_keys=False)
        self.registry_path.write_text(text, encoding="utf-8")

    def _normalize_id(self, raw: str) -> str:
        text = str(raw or "").strip().lower().replace("-", "_")
        text = re.sub(r"\s+", "_", text)
        text = re.sub(r"[^a-z0-9_]", "", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text

    def _normalize_rel_spec_path(self, *, spec_path: str | None, spec_id: str) -> str:
        path_raw = str(spec_path or "").strip()
        if not path_raw:
            path_raw = f"systems/{spec_id}.yaml"
        path_raw = path_raw.replace("\\", "/")
        p = Path(path_raw)
        if p.is_absolute():
            raise ValueError("spec_path must be relative")
        if p.suffix.lower() not in {".yaml", ".yml"}:
            p = p.with_suffix(".yaml")
        return str(p).replace("\\", "/")

    def _is_within(self, path: Path, root: Path) -> bool:
        root_resolved = root.resolve()
        path_resolved = path.resolve()
        return path_resolved == root_resolved or root_resolved in path_resolved.parents

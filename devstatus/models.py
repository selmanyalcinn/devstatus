from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class Artifact:
    identity: str
    name: str
    kind: str
    source: str
    version: str | None = None
    description: str = ""
    path: str | None = None
    status: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class Tool:
    id: str
    name: str
    category: tuple[str, ...]
    version: str | None = None
    version_source: str | None = None
    tags: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)
    components: list[Artifact] = field(default_factory=list)
    status: str | None = None
    hidden: bool = False
    notes: str | None = None
    detected: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": list(self.category),
            "version": self.version,
            "version_source": self.version_source,
            "tags": sorted(self.tags),
            "sources": sorted(self.sources),
            "components": [c.to_dict() for c in self.components],
            "status": self.status,
            "hidden": self.hidden,
            "notes": self.notes,
            "detected": self.detected,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Tool":
        return cls(
            id=d["id"], name=d["name"], category=tuple(d.get("category", [])),
            version=d.get("version"), version_source=d.get("version_source"),
            tags=set(d.get("tags", [])), sources=set(d.get("sources", [])),
            components=[Artifact(**c) for c in d.get("components", [])],
            status=d.get("status"), hidden=d.get("hidden", False),
            notes=d.get("notes"), detected=d.get("detected", True),
            metadata=d.get("metadata", {}),
        )

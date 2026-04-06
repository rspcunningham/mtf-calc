from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


CONFIG_DIR = Path.home() / ".parasight"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_FREQUENCIES: list[float] = [
    1000.0,
    2000.0,
    3000.0,
    5000.0,
    10000.0,
]


@dataclass(slots=True)
class AppConfig:
    frequencies: list[float] = field(default_factory=lambda: list(DEFAULT_FREQUENCIES))

    def to_dict(self) -> dict:
        return {"frequencies": self.frequencies}

    @classmethod
    def from_dict(cls, data: dict) -> AppConfig:
        freqs = data.get("frequencies", DEFAULT_FREQUENCIES)
        return cls(frequencies=[float(f) for f in freqs])


def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        return AppConfig()

    try:
        data = json.loads(CONFIG_PATH.read_text())
        return AppConfig.from_dict(data)
    except (json.JSONDecodeError, TypeError, ValueError):
        return AppConfig()


def save_config(config: AppConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config.to_dict(), indent=2) + "\n")

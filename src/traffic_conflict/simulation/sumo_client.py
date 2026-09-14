"""Gestion des exécutables et du cycle de vie TraCI, sans logique de stratégie."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import traci


def find_binary(name: str) -> str:
    suffix = ".exe" if os.name == "nt" else ""
    roots = []
    if os.environ.get("SUMO_HOME"):
        roots.append(Path(os.environ["SUMO_HOME"]))
    try:
        import sumo
        roots.append(Path(sumo.SUMO_HOME))
    except ImportError:
        pass
    for root in roots:
        candidate = root / "bin" / (name + suffix)
        if candidate.is_file():
            return str(candidate)
    candidate = shutil.which(name)
    if candidate:
        return candidate
    raise RuntimeError(f"Exécutable absent : {name}. Exécuter scripts/doctor.py.")


class SumoClient:
    def __init__(
        self,
        config_file: Path,
        seed: int,
        output_dir: Path,
        gui: bool = False,
        gui_delay: int = 0,
    ):      
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.label = "pilot_" + uuid4().hex
        self.command = [find_binary("sumo-gui" if gui else "sumo"), "-c", str(Path(config_file).resolve()),
                        "--seed", str(seed), "--no-step-log", "true", "--duration-log.disable", "true",
                        "--tripinfo-output", str(self.output_dir / "tripinfo.xml"),
                        "--tripinfo-output.write-unfinished", "true",
                        "--collision-output", str(self.output_dir / "collisions.xml"),
                        "--error-log", str(self.output_dir / "sumo_errors.log")]
        if gui:
            self.command.extend(["--start", "--quit-on-end", "false"])

            if gui_delay > 0:
                self.command.extend(["--delay", str(gui_delay)])
        self.connection = None
        self.stdout = None

    def __enter__(self):
        self.stdout = (self.output_dir / "sumo_stdout.log").open("w", encoding="utf-8")
        (self.output_dir / "command.json").write_text(json.dumps(self.command, indent=2), encoding="utf-8")
        try:
            traci.start(self.command, label=self.label, stdout=self.stdout, numRetries=5, doSwitch=False)
            self.connection = traci.getConnection(self.label)
        except BaseException:
            self.stdout.close()
            raise
        return self.connection

    def __exit__(self, *exc):
        try:
            if self.connection:
                self.connection.close()
        finally:
            if self.stdout:
                self.stdout.close()


def tool_versions() -> dict:
    return {"python": sys.version, "sumo": subprocess.check_output([find_binary("sumo"), "--version"], text=True).splitlines()[0]}

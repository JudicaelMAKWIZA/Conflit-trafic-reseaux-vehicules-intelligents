"""Diagnostic reproductible et test réel du protocole TraCI (sans scénario pilote)."""
from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def binary(name: str) -> str:
    suffix = ".exe" if os.name == "nt" else ""
    candidates = []
    if os.environ.get("SUMO_HOME"):
        candidates.append(Path(os.environ["SUMO_HOME"]) / "bin" / (name + suffix))
    try:
        import sumo
        candidates.append(Path(sumo.SUMO_HOME) / "bin" / (name + suffix))
    except ImportError:
        pass
    candidates.append(Path(sys.executable).parent / (name + suffix))
    candidates.extend([Path(p) for p in [shutil.which(name)] if p])
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    raise RuntimeError(f"{name} absent : installer requirements.txt ou définir SUMO_HOME")


def diagnose() -> dict:
    import traci
    import sumolib
    result = {"python": sys.version, "python_executable": sys.executable,
              "traci": importlib.metadata.version("traci"),
              "sumolib": importlib.metadata.version("sumolib")}
    errors = []
    for name in ("sumo", "sumo-gui", "netconvert"):
        try:
            executable = binary(name)
            result[name] = {"path": executable}
            version = subprocess.run([executable, "--version"], check=True,
                                     capture_output=True, text=True, timeout=30).stdout.splitlines()[0]
            result[name]["version"] = version
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            result.setdefault(name, {})["error"] = str(exc)
            errors.append(f"{name}: {exc}")
    try:
        import sumo
        result["SUMO_HOME"] = str(sumo.SUMO_HOME)
    except ImportError:
        result["SUMO_HOME"] = os.environ.get("SUMO_HOME")
    result["tools"] = str(Path(sumolib.__file__).parent.parent)
    if errors:
        result["gate_G0"] = "FAILED"
        result["errors"] = errors
        return result
    with tempfile.TemporaryDirectory(prefix="traffic_doctor_") as folder:
        root = Path(folder)
        (root / "n.xml").write_text('<nodes><node id="a" x="0" y="0"/><node id="b" x="100" y="0"/></nodes>')
        (root / "e.xml").write_text('<edges><edge id="ab" from="a" to="b"/></edges>')
        subprocess.run([binary("netconvert"), "-n", str(root / "n.xml"), "-e", str(root / "e.xml"),
                        "-o", str(root / "net.xml")], check=True, capture_output=True)
        traci.start([binary("sumo"), "-n", str(root / "net.xml"), "--no-step-log", "true"],
                    label="doctor", stdout=subprocess.DEVNULL)
        conn = traci.getConnection("doctor")
        try:
            result["traci_protocol"], result["traci_server"] = conn.getVersion()
            conn.simulationStep()
            result["simulation_time_s"] = conn.simulation.getTime()
            assert result["simulation_time_s"] > 0
        finally:
            conn.close()
    result["gate_G0"] = "PASSED"
    return result


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "outputs" / "doctor.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        report = diagnose()
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(0 if report["gate_G0"] == "PASSED" else 1)
    except Exception as exc:
        target.write_text(json.dumps({"gate_G0": "FAILED", "error": str(exc)}, indent=2), encoding="utf-8")
        print(f"Gate G0 FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

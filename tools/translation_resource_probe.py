"""Read-only, bounded ADB probe. Run while SubLoka is translating; no caption capture."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import time

PACKAGE = "app.subloka.caption"


def adb(*args):
    result = subprocess.run(["adb", *args], capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ADB failed")
    return result.stdout.strip()


def parse_stat(text):
    # comm is parenthesized and may contain spaces or ')' characters.
    end = text.rfind(")")
    if end < 0:
        raise ValueError("Invalid process stat")
    fields = text[end + 1:].split()  # starts at Linux proc stat field 3
    return {"minor_faults": int(fields[7]), "major_faults": int(fields[9]),
            "cpu_ticks": int(fields[11]) + int(fields[12]),
            "start_ticks": int(fields[19]), "resident_pages": int(fields[21])}


def sample(pid):
    return parse_stat(adb("exec-out", "run-as", PACKAGE, "cat", f"/proc/{pid}/stat"))


def delta(previous, current):
    if previous["start_ticks"] != current["start_ticks"]:
        raise RuntimeError("App process changed; start a new capture")
    return {key: current[key] - previous[key]
            for key in ("minor_faults", "major_faults", "cpu_ticks")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=90, choices=range(10, 301), metavar="10..300")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    output = args.output or Path.home() / "Downloads" / f"Subloka-resource-{stamp}.jsonl"
    try:
        pid = adb("shell", "pidof", PACKAGE)
        if not pid.isdigit():
            raise RuntimeError("Open SubLoka and start translation first; expected one app process")
        initial = sample(pid)  # fail before creating a file if run-as/proc access is denied
        features = [line.strip() for line in adb("shell", "cat", "/proc/cpuinfo").splitlines()
                    if line.strip().lower().startswith("features")]
        # Units remain raw if this device does not expose getconf.
        units = {}
        for name in ("CLK_TCK", "PAGESIZE"):
            try:
                value = adb("shell", "getconf", name)
                units[name] = int(value) if value.isdigit() else None
            except (RuntimeError, subprocess.TimeoutExpired):
                units[name] = None
        with output.open("x", encoding="utf-8") as stream:
            def emit(record):
                stream.write(json.dumps(record) + "\n")
                stream.flush()
            emit({"event": "start", "pid": int(pid), "cpu_features": sorted(set(features)),
                  "units": units, "requested_seconds": args.seconds,
                  "note": "Process-wide counters; faults do not identify a particular mapped file."})
            started = time.monotonic()
            previous = initial
            last = started
            emit({"event": "sample", "elapsed_seconds": 0, **initial})
            print(f"Recording up to {args.seconds}s. Keep translation active. Ctrl+C stops early.")
            try:
                while time.monotonic() - started < args.seconds:
                    time.sleep(min(2, max(0, args.seconds - (time.monotonic() - started))))
                    current = sample(pid)
                    now = time.monotonic()
                    change = delta(previous, current)
                    interval = now - last
                    record = {"event": "sample", "elapsed_seconds": round(now - started, 3),
                              "interval_seconds": round(interval, 3), **current, "delta": change}
                    if units["CLK_TCK"]:
                        record["cpu_percent_one_core"] = round(100 * change["cpu_ticks"] / units["CLK_TCK"] / interval, 2)
                    emit(record)
                    print(f"{now - started:.0f}s: major faults +{change['major_faults']}; CPU ticks +{change['cpu_ticks']}")
                    previous, last = current, now
                emit({"event": "end", "reason": "duration"})
            except KeyboardInterrupt:
                emit({"event": "end", "reason": "user_stop"})
            except (RuntimeError, ValueError, IndexError, subprocess.TimeoutExpired) as exc:
                emit({"event": "end", "reason": "capture_failed", "error_type": type(exc).__name__})
                raise
            finally:
                print(f"Capture: {output}")
    except (OSError, RuntimeError, ValueError, IndexError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f"Probe failed: {exc}\n")


if __name__ == "__main__":
    main()

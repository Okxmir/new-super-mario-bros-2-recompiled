"""Run a bounded native boot test with isolated save data."""

import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=15)
    parser.add_argument("--graphics", action="store_true")
    parser.add_argument("--screenshot", help="Frame number or frame:interval:count")
    parser.add_argument("--press", help="Frame-based button sequence for the runtime")
    parser.add_argument("--state", default="probe-userdata")
    parser.add_argument("--trace", default="")
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--log", default="boot-probe")
    args = parser.parse_args()
    for name in (args.state, args.log):
        if Path(name).name != name:
            parser.error("State and log names must be filenames")

    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    state = ROOT / "build" / args.state
    env = os.environ.copy()
    env.update(NSMB2_DATA_DIR=str(state), NSMB2_NO_DIALOG="1", NSMB2_FPS="1",
               RECOMP_TRACE=args.trace)
    if args.graphics:
        env.pop("NSMB2_HEADLESS", None)
    else:
        env["NSMB2_HEADLESS"] = "1"
    if args.cpu:
        state.mkdir(parents=True, exist_ok=True)
        (state / "settings.ini").write_text("gpu_renderer=0\n", encoding="utf-8")
    if args.press:
        env["NSMB2_PRESS"] = args.press
    if args.screenshot:
        env["NSMB2_WINDOW_SCREENSHOT"] = str(logs / f"{args.log}-") + ":" + args.screenshot
    command = [ROOT / "build/windows-Release/NewSuperMarioBros2.exe", ROOT / "extracted/NSMB2-EUR.cxi"]
    with (logs / f"{args.log}.txt").open("wb") as output:
        try:
            return subprocess.run(command, env=env, stdout=output, stderr=subprocess.STDOUT,
                                  timeout=args.seconds, creationflags=subprocess.CREATE_NO_WINDOW).returncode
        except subprocess.TimeoutExpired:
            output.write(f"\nProbe ended after {args.seconds} seconds.\n".encode())
            return 124


if __name__ == "__main__":
    raise SystemExit(main())

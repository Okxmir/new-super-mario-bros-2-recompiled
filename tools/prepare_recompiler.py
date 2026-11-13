"""Apply shared ARM discovery fixes and verified title-specific entry points."""

import argparse
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    shutil.copytree(args.upstream, args.output, dirs_exist_ok=True)
    path = args.output / "discover.rs"
    source = path.read_text(encoding="utf-8")
    original = "        Op::Udf | Op::Bkpt(_) => Flow::Stop,"
    if source.count(original) != 1:
        raise ValueError("Unexpected Clockwork source revision")
    source = source.replace(original, "        Op::Udf | Op::Bkpt(_) if !conditional => Flow::Stop,")
    path.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()

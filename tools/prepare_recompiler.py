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
    replacements = {
        "        Op::Udf | Op::Bkpt(_) => Flow::Stop,":
            "        Op::Udf | Op::Bkpt(_) if !conditional => Flow::Stop,",
        "        let (rejected_arm, rejected_thumb) = d.rejected_counts();": (
            "        // The European game passes this ARM comparator to the sort at 0x0045c90c.\n"
            "        d.add_entry(0x0039_141c, false);\n"
            "        d.run();\n"
            "        let (rejected_arm, rejected_thumb) = d.rejected_counts();"
        ),
    }
    for original, replacement in replacements.items():
        if source.count(original) != 1:
            raise ValueError("Unexpected Clockwork source revision")
        source = source.replace(original, replacement)
    path.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()

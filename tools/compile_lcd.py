"""Compile the LCD shader and embed the SPIR-V bytecode."""

import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("compiler", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("header", type=Path)
    args = parser.parse_args()
    spirv = args.header.with_suffix(".spv")
    subprocess.run(
        [str(args.compiler), "-spirv", "-T", "ps_6_0", "-E", "main", "-Fo", str(spirv), str(args.source)],
        check=True,
    )
    data = spirv.read_bytes()
    rows = ["    " + ", ".join(f"0x{x:02x}" for x in data[i:i+16]) + "," for i in range(0, len(data), 16)]
    args.header.write_text("alignas(4) static constexpr unsigned char nsmb2_lcd[] = {\n"
                           + "\n".join(rows) + "\n};\n", encoding="ascii")


if __name__ == "__main__":
    main()

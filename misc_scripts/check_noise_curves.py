import argparse
import gzip
import io
import re
from pathlib import Path

"""
Check noise curves
"""

__author__ = "Karl Wette <karl.wette@anu.edu.au>"
__copyright__ = "Copyright (C) 2025 Karl Wette"

# parse command line
parser = argparse.ArgumentParser()
parser.add_argument("filenames", type=Path, nargs="*")
args = parser.parse_args()

for filename in args.filenames:

    if (
        re.match(
            r"^(?:S|VSR|O)[1-9][1-9a-z]?-[HLVK][12]$",
            filename.parts[1],
        )
        is None
    ):
        msg = f"invalid filename {filename}"
        raise ValueError(msg)

    with gzip.open(filename, "rt", encoding="utf-8") as f:
        lines = [line.strip() for line in f]

    comment = lines.pop(0)
    header = lines.pop(0)

    if re.match(r"^# taken from https?://", comment) is None:
        msg = f"invalid filename {filename} comment '{comment}'"
        raise ValueError(msg)

    h = re.match(r"^\s*(freq)\s+((?:sqrt)?Sh)\s*$", header)
    if h is None:
        msg = f"invalid filename {filename} header '{header}'"
        raise ValueError(msg)

    with io.TextIOWrapper(
        gzip.GzipFile(filename, "wb", mtime=0), encoding="utf-8"
    ) as f:
        f.write(comment + "\n")
        f.write(h.group(1) + "\t" + h.group(2) + "\n")
        for line in lines:
            f.write("\t".join(line.split()) + "\n")

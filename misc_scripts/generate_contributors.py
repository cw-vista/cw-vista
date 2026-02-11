import re
import subprocess
import sys

"""
Generate contributor list
"""

__author__ = "Karl Wette <karl.wette@anu.edu.au>"
__copyright__ = "Copyright (C) 2025 Karl Wette"

r = subprocess.run(
    "git log --use-mailmap --full-history --no-merges HEAD | git shortlog --summary --email",
    shell=True,
    check=True,
    capture_output=True,
    encoding="utf-8",
)

contributors = []
missing_mailmap = False
for line in r.stdout.splitlines():
    m = re.fullmatch(r"\s*(\d+)\s+([^<>]+)\s+<([^>]+)>\s*", line)
    n, name, mail = m.groups()

    if "," in name and "." in name.split(",")[1]:
        contributors.append(name)
        continue

    missing_mailmap = True
    sys.stderr.write(
        f"Please add an entry to the `.mailmap` file of the form:\n\n{name}'s last name, {name}'s initials <{mail}>\n\n"
    )

if missing_mailmap:
    sys.exit(1)

with open("CONTRIBUTORS", "w", encoding="utf-8") as f:
    print("\n".join(sorted(contributors)), file=f)

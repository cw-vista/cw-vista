import re
import subprocess
import sys

"""
Generate author list
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

authors = []
missing_mailmap = False
for line in r.stdout.splitlines():
    m = re.fullmatch(r"\s*(\d+)\s+([^<>]+)\s+<([^>]+)>\s*", line)
    n, name, mail = m.groups()

    if not "," in name:
        missing_mailmap = True
        sys.stderr.write(
            f"""
Please add an entry to the `.mailmap` file of the form:

    {name}'s last name, {name}'s first names <{mail}>

"""
        )
    else:
        authors.append(name)

if missing_mailmap:
    sys.exit(1)

with open("AUTHORS", "w", encoding="utf-8") as f:
    print("\n".join(sorted(authors)), file=f)

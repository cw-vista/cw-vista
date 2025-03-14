import argparse
import json
from pathlib import Path
from string import ascii_lowercase

import cw_search_breadth
import cw_search_data_schema
import cw_search_depth
import jsonschema

"""
Validate CW search data files
"""

__author__ = "Karl Wette <karl.wette@anu.edu.au>"
__copyright__ = "Copyright (C) 2025 Karl Wette"

schema = cw_search_data_schema.get()


# parse command line
parser = argparse.ArgumentParser()
parser.add_argument("paths", type=Path, nargs="*")
args = parser.parse_args()

# get list of files to check
if any(path.suffix == ".py" for path in args.paths):
    filenames = Path("cw_search_data").glob("*.json")
else:
    filenames = args.paths

# validate files
new_filenames = {}
check_suffixes = set()
for filename in filenames:
    print(f"Validating {filename}")

    # validate JSON file contents against schema
    with open(filename, encoding="utf-8") as f:
        data = json.load(f)
    jsonschema.validate(instance=data, schema=schema)

    # compute sensitivity depths and parameter-space breadths
    for s in data["searches"]:

        # compute depth, rounded to a few significant figures
        depth = cw_search_depth.depth(s)
        s["depth"] = float(f"{depth:0.4g}")

        # compute breadth, rounded to a few significant figures
        breadth = cw_search_breadth.breadth(s)
        s["breadth"] = float(f"{breadth:0.4g}")

    # create BibTeX key
    ref = data["reference"]
    if ref == "unpublished":
        key = ref
    else:
        author = ""
        others = ""
        if "collaboration" in ref:
            for collab in ref["collaboration"]:
                if collab == "others":
                    others = "+"
                    break
                else:
                    author += collab.split(" ")[0]
        else:
            author = ref["author"][0].split(",")[0].strip()
            if len(ref["author"]) > 1:
                others = "+"
        year = str(ref["year"])
        key = author + others + year + ref["key-suffix"]
        ref["key"] = key

        check_suffixes.add((author, year))

    # create new filename consistent with BibTeX key
    new_filename = filename.with_stem(key)
    if new_filename not in new_filenames:
        new_filenames[new_filename] = filename
    else:
        msg = f"{filename} and {new_filenames[new_filename]} have the same BibTeX key: {key}"
        raise ValueError(msg)

    # write validated JSON
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent="    ", sort_keys=True)
        f.write("\n")

# rename files
for new_filename, filename in new_filenames.items():
    if new_filename != filename:
        print(f"Renaming {filename} to {new_filename}")
        filename.rename(new_filename)

# check for missing/duplicate suffixes
print("Checking for missing/duplicate suffixes")
for author, year in sorted(check_suffixes):
    suffix_used = []
    for k in ascii_lowercase:
        json_filename = Path("cw_search_data") / f"{author}{year}{k}.json"
        json_plus_filename = Path("cw_search_data") / f"{author}+{year}{k}.json"
        if json_filename.is_file() and json_plus_filename.is_file():
            msg = f"Duplicate suffixes used by {json_filename} and {json_plus_filename}"
            raise ValueError(msg)
        if json_filename.is_file():
            suffix_used.append((k, json_filename))
        elif json_plus_filename.is_file():
            suffix_used.append((k, json_plus_filename))
        else:
            suffix_used.append((k, None))
    while suffix_used[-1][1] is None:
        suffix_used.pop()
    if not all([f is not None for k, f in suffix_used]):
        missing_suffixes = "\n".join(
            [
                "    " + (f"(no file with suffix {k})" if f is None else str(f))
                for k, f in suffix_used
            ]
        )
        msg = f"Missing suffixes in the sequence:\n{missing_suffixes}"
        raise ValueError(msg)

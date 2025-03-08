import argparse
import json
from pathlib import Path

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
        key = ""
        if "collaboration" in ref:
            for collab in ref["collaboration"]:
                if collab == "others":
                    key += "+"
                    break
                else:
                    key += collab.split(" ")[0]
        else:
            key += ref["author"][0].split(",")[0].strip()
            if len(ref["author"]) > 1:
                key += "+"
        key += str(ref["year"]) + ref["key-suffix"]
        ref["key"] = key

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

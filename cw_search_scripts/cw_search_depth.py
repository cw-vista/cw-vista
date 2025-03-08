"""
Compute sensitivity depths of CW searches
"""

__author__ = "Karl Wette <karl.wette@anu.edu.au>"
__copyright__ = "Copyright (C) 2025 Karl Wette"


def depth(search):
    """Compute sensitivity depth of a CW search"""

    # always use depth if supplied

    if "depth" in search:
        return search["depth"]

from pathlib import Path

import numpy as np

"""
Compute sensitivity depths of CW searches
"""

__author__ = "Karl Wette <karl.wette@anu.edu.au>"
__copyright__ = "Copyright (C) 2025 Karl Wette"


def depth(search):
    """Compute sensitivity depth of a CW search"""

    # use given depth if it cannot be computed

    if "depth-h0" not in search:
        return search["depth"]

    # compute depth from h0 upper limit and specified noise curves

    h0 = search["depth-h0"]
    freq = search["depth-freq"]

    min_freq = freq - 0.5
    max_freq = freq + 0.5

    obs_det_sqrtSh = []
    for obs_det in search["depth-Sh-obs-det"]:

        nc_dir = Path("noise_curves") / obs_det
        nc_files = list(nc_dir.glob("*.txt.gz"))

        msg = f"noise curves found in {nc_dir}"
        if len(nc_files) == 0:
            msg = "no " + msg
            raise ValueError(msg)
        if len(nc_files) > 1:
            msg = "too many " + msg
            raise ValueError(msg)

        nc = np.genfromtxt(nc_files[0], skip_header=1, names=True)

        nc_freq = nc["freq"]
        try:
            nc_sqrtSh = np.sqrt(nc["Sh"])
        except ValueError:
            nc_sqrtSh = nc["sqrtSh"]

        ii = np.logical_and(
            min_freq <= nc_freq,
            nc_freq < max_freq,
        )
        nc_select_sqrtSh = nc_sqrtSh[ii]
        if len(nc_select_sqrtSh) < 2:
            msg = f"no enough bins in noise curve {nc_files[0]}"
            raise ValueError(msg)

        obs_det_sqrtSh.append(1.0 / np.mean(1.0 / nc_select_sqrtSh))

    sqrtSh = 1.0 / np.mean(1.0 / np.array(obs_det_sqrtSh))

    return sqrtSh / h0

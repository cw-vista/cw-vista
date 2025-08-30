from collections import defaultdict

import numpy as np
import scipy as sp

"""
Compute parameter-space breadths of CW searches
"""

__author__ = "Karl Wette <karl.wette@anu.edu.au>"
__copyright__ = "Copyright (C) 2025 Karl Wette"


def sinc(x):
    return np.sinc(x / np.pi)


def p_to_q(r, *args):
    """
    Product of max(r[p])**q - min(r[p])**q for (p, q) in *args

    See Eq. (65) of Wette 2023.

    """
    prod = 1
    for p, q in args:
        prod *= max(r[p]) ** q - min(r[p]) ** q

    return prod


def sky_breadth(*, sky, T):
    """
    Breadth of sky parameter space.

    See Eq. (67) of Wette 2023.
    """
    Omega_s = 7.27e-5  # Hz
    Omega_o = 1.99e-7  # Hz
    tau_s = 2.13e-2  # s
    tau_o = 4.99e2  # s

    prefac = (8 / 3) * np.pi**3 * tau_o**2

    sinc_half_Omega_s_T = sinc(0.5 * Omega_s * T)
    sinc_half_Omega_o_T = sinc(0.5 * Omega_o * T)
    sinc_Omega_o_T = sinc(Omega_o * T)

    fac = (
        1
        + 4 * (tau_s / tau_o) * sinc_half_Omega_s_T
        - 2 * sinc_half_Omega_o_T**2
        - sinc_Omega_o_T**2
        + 2 * sinc_half_Omega_o_T**2 * sinc_Omega_o_T
    )
    sqrtfac = np.sqrt(np.abs(fac))

    br = sky * prefac * sqrtfac

    return br, 2


def freq_breadth_fac(*, T):
    """
    Frequency parameter-space breadth factor.

    See Eq. (60) of Wette 2023.
    """

    br = max(1, np.pi * T / np.sqrt(3))

    return br, 0


def fsp_unity(*args):
    """
    Returns unity; for integrating over spindown parameter spaces.
    """

    return 1


def fsp_bound(expr, *args, **vals):
    """
    Returns a function which evaluates a spindown parameter
    space bound `expr`, using the variables defined in `vals`.
    """

    code = compile(str(expr), f"<{expr}>", "eval")
    for name in code.co_names:
        if name not in args and name not in vals:
            msg = f"'{expr}' contains unknown parameter '{name}'"
            raise ValueError(msg)

    def _fsp_bound(freq, fdot=0):
        v = vals.copy()
        v["freq"] = freq
        v["fdot"] = fdot
        return eval(code, {"__builtins__": {}}, v)

    return _fsp_bound


def fdot_breadth(*, T, r, v):
    """
    First spindown parameter-space breadth.

    Extends Eq. (63) of Wette 2023 to arbitrary parameter-space bounds.
    """

    freq_space = max(r["freq"]) - min(r["freq"])

    fdot_space, err = sp.integrate.dblquad(
        fsp_unity,
        a=min(r["freq"]),
        b=max(r["freq"]),
        gfun=fsp_bound(r["fdot"][0], "freq", **v),
        hfun=fsp_bound(r["fdot"][1], "freq", **v),
    )

    fdot_range = abs(fdot_space) / freq_space

    br = max(1, np.pi * T**2 / (6 * np.sqrt(5)) * fdot_range)

    return br, 0


def fddot_breadth(*, T, r, v):
    """
    Second spindown parameter-space breadth.

    Extends Eq. (64) of Wette 2023 to arbitrary parameter-space bounds.
    """

    fdot_space, err = sp.integrate.dblquad(
        fsp_unity,
        a=min(r["freq"]),
        b=max(r["freq"]),
        gfun=fsp_bound(r["fdot"][0], "freq", **v),
        hfun=fsp_bound(r["fdot"][1], "freq", **v),
    )

    fddot_space, err = sp.integrate.tplquad(
        fsp_unity,
        a=min(r["freq"]),
        b=max(r["freq"]),
        gfun=fsp_bound(r["fdot"][0], "freq", **v),
        hfun=fsp_bound(r["fdot"][1], "freq", **v),
        qfun=fsp_bound(r["fddot"][0], "freq", "fdot", **v),
        rfun=fsp_bound(r["fddot"][1], "freq", "fdot", **v),
    )

    fddot_range = abs(fddot_space) / abs(fdot_space)

    br = max(1, np.pi * T**3 / (60 * np.sqrt(7)) * fddot_range)

    return br, 0


def binary_known_tasc_breadth(*, T, r):
    """
    Binary orbit parameter-space breadth, in terms of projected semi-major axis,
    where time of ascension is known.

    See Eq. (69) of Wette 2023.

    """

    br = (
        -1
        * (2 / 3) ** (3 / 2)
        * np.pi**5
        * p_to_q(r, ("bin-a-sin-i", 3), ("bin-period", -2), ("bin-time-asc", 1))
        * T
    )

    return br, 3


def binary_unknown_tasc_breadth(*, T, r):
    """
    Binary orbit parameter-space breadth, in terms of projected semi-major axis,
    where time of ascension is unknown.

    See Eq. (70) of Wette 2023.

    """

    br = (
        -2
        * (2 / 3) ** (3 / 2)
        * np.pi**5
        * p_to_q(r, ("bin-a-sin-i", 3), ("bin-period", -1))
        * T
    )

    return br, 3


def binary_unknown_tasc_freq_mod_depth_breadth(*, T, r):
    """
    Binary orbit parameter-space breadth, in terms of frequency modulation depth,
    where time of ascension is unknown.

    See Eq. (71) of Wette 2023.
    """

    br = (
        (1 / 2)
        * (2 / 3) ** (3 / 2)
        * np.pi**3
        * p_to_q(r, ("bin-freq-mod-depth", 3), ("bin-period", 1))
        * T
    )

    return br, 1


def hidden_markov_model_breadth(*, Tspan, Tcoh, HMMjumps):
    """
    Conventional parameter-space breadth of a Hidden Markov model.

    See Eq. (76) of Wette 2023.
    """

    Nsegs = Tspan / Tcoh
    br = (1 / 2) * (Nsegs * HMMjumps - Nsegs - HMMjumps + 3)

    return br, 0


def breadth(search):
    """Compute parameter-space breadth of a CW search"""

    Tspan = search["time-span"]
    Tcoh = search["max-coherence-time"]
    ps = search["param-space"]

    if "num-pulsars" in ps:

        # by definition, breadth of targeted search is number of pulsars
        return ps["num-pulsars"], {}

    fsp_vals = {"yr": 365.25 * 86400}
    if "freq-space-vals" in ps:
        fsp_vals.update(ps["freq-space-vals"])

    # breadths of each range
    br = {}

    for i, r in enumerate(ps["ranges"]):

        # breadths of each parameter space component and range
        br[i] = {}

        # powers of frequency contributed by each parameter space component
        fp = {}

        br[i]["freq"], fp["freq"] = freq_breadth_fac(T=Tspan)

        if "sky-fraction" in ps:
            br[i]["sky"], fp["sky"] = sky_breadth(sky=ps["sky-fraction"], T=Tspan)

        if "fdot" in r:
            br[i]["fdot"], fp["fdot"] = fdot_breadth(T=Tspan, r=r, v=fsp_vals)

        if "fddot" in r:
            br[i]["fddot"], fp["fddot"] = fddot_breadth(T=Tspan, r=r, v=fsp_vals)

        if "bin-freq-mod-depth" in r:
            br[i]["bin"], fp["bin"] = binary_unknown_tasc_freq_mod_depth_breadth(
                T=Tspan, r=r
            )
        elif "bin-a-sin-i" in r:
            if "bin-time-asc" in r:
                br[i]["bin"], fp["bin"] = binary_known_tasc_breadth(T=Tspan, r=r)
            else:
                br[i]["bin"], fp["bin"] = binary_unknown_tasc_breadth(T=Tspan, r=r)

        if "hmm-num-jumps" in ps:
            br[i]["HMM"], fp["HMM"] = hidden_markov_model_breadth(
                Tspan=Tspan, Tcoh=Tcoh, HMMjumps=ps["hmm-num-jumps"]
            )

        fp["freq"] += 1  # for integration over frequency

        # check we have computed some breadths
        if not br[i]:
            msg = "no breadths computed"
            raise ValueError(msg)

        # compute overall power in frequency
        f_power = 0
        for k in br[i]:
            f_power += fp[k]

        # compute factor from integrating over frequency
        f_integration = p_to_q(r, ("freq", f_power)) / f_power

        # scale component breadth by contribution to total breadth [Eq. (73) of Wette 2023]
        for k in br[i]:
            br[i][k] *= f_integration ** (fp[k] / f_power)

    # integrate product of component breadths over frequency [Eq. (75) of Wette 2023]
    br_total = 0
    for i in br:
        br_total_i = 1
        for k in br[i]:
            br_total_i *= br[i][k]
        br_total += br_total_i

    # sum up component breadths over ranges
    br_comp = defaultdict(float)
    for i in br:
        for k in br[i]:
            br_comp[k] += br[i][k]

    # scale component breadth over ranges by contribution to total breadth
    br_comp_total = 1
    for k in br_comp:
        br_comp_total *= br_comp[k]
    br_comp_scale = (br_total / br_comp_total) ** (1.0 / len(br_comp))
    for k in br_comp:
        br_comp[k] *= br_comp_scale

    return br_total, br_comp

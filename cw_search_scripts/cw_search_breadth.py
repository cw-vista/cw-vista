import numpy as np

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


def fdot_breadth(*, T, r):
    """
    First spindown parameter-space breadth.

    See Eq. (63) of Wette 2023.
    """

    br = max(1, np.pi * T**2 / (6 * np.sqrt(5)) * p_to_q(r, ("fdot", 1)))

    return br, 0


def fddot_breadth(*, T, r):
    """
    Second spindown parameter-space breadth.

    See Eq. (64) of Wette 2023.
    """

    br = max(1, np.pi * T**3 / (60 * np.sqrt(7)) * p_to_q(r, ("fddot", 1)))

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
        return ps["num-pulsars"]

    br_total = 0

    for r in ps["ranges"]:

        # breadths of each parameter space component
        br = {}

        # powers of frequency contributed by each parameter space component
        fp = {}

        br["freq"], fp["freq"] = freq_breadth_fac(T=Tspan)

        if "sky-fraction" in ps:
            br["sky"], fp["sky"] = sky_breadth(sky=ps["sky-fraction"], T=Tspan)

        if "fdot" in r:
            br["fdot"], fp["fdot"] = fdot_breadth(T=Tspan, r=r)

        if "fddot" in r:
            br["fddot"], fp["fddot"] = fddot_breadth(T=Tspan, r=r)

        if "bin-freq-mod-depth" in r:
            br["bin"], fp["bin"] = binary_unknown_tasc_freq_mod_depth_breadth(
                T=Tspan, r=r
            )
        elif "bin-a-sin-i" in r:
            if "bin-time-asc" in r:
                br["bin"], fp["bin"] = binary_known_tasc_breadth(T=Tspan, r=r)
            else:
                br["bin"], fp["bin"] = binary_unknown_tasc_breadth(T=Tspan, r=r)

        if "hmm-num-jumps" in ps:
            br["HMM"], fp["HMM"] = hidden_markov_model_breadth(
                Tspan=Tspan, Tcoh=Tcoh, HMMjumps=ps["hmm-num-jumps"]
            )

        # check we have computed some breadths
        assert br

        # compute overall power in frequency
        f_power = 0
        for k in br:
            f_power += fp[k]

        # compute factor from integrating over frequency
        f_integration = p_to_q(r, ("freq", f_power + 1)) / (f_power + 1)

        # integrate product of component breadths over frequency [Eq. (75) of Wette 2023]
        br_range = f_integration
        for k in br:
            br_range *= br[k]

        # add to total breadth
        br_total += br_range

    return br_total

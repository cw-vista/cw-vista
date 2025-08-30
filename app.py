import io
import json
import re
from pathlib import Path
from textwrap import dedent, wrap
from threading import RLock

import matplotlib as mpl
import matplotlib.lines as mlines
import matplotlib.markers as mmarkers
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.text as mtext
import numpy as np
import papersize
import streamlit as st
from adjustText import adjust_text
from astropy.table import MaskedColumn, QTable
from natsort import natsorted

# to protect against non-reentrant matplotlib
_lock = RLock()

mpl.use("agg")

### configure page

page_title = "The CW Vista"
page_url = "https://cw-vista.streamlit.app/"

st.set_page_config(page_title=page_title, page_icon="icon.jpeg", layout="wide")

# vista plot show be plotted when page is first loaded
if "display-img-first-time" not in st.session_state:
    st.session_state["display-img-first-time"] = True

### get data


@st.cache_data
def get_figure_sizes():

    sizes = {}

    # add some custom sizes
    for name, size_str, scale in (
        ("beamer 4:3", "307pt x 244pt", 2),
        ("beamer 16:9", "398pt x 227pt", 2),
    ):
        size = papersize.parse_couple(size_str, "in")
        sizes[name] = tuple(float(n) * scale for n in size)

    # add a selection of standard paper sizes
    for name in ("A0", "A1", "A2", "A3", "A4", "Letter", "A5", "A6"):
        size = papersize.parse_papersize(name, "in")
        sizes[name] = tuple(float(n) for n in size)

    return sizes


figure_sizes = get_figure_sizes()


@st.cache_data
def get_data():

    # load CW search data
    refs = {}
    searches = []
    for filename in Path("cw_search_data").glob("*.json"):
        with open(filename, encoding="utf-8") as f:
            data = json.load(f)
        ref = data["reference"]
        if ref == "unpublished":
            ref_key = "This work"
        else:
            ref_key = ref["key"]
        refs[ref_key] = ref
        for search in data["searches"]:
            search["ref-key"] = search["citation"] = ref_key
            search["full-citation"] = "\n".join(
                wrap(
                    "{key}, {title}, DOI:{doi}".format(
                        key=ref_key, title=ref["title"], doi=ref["doi"]
                    ),
                    40,
                )
            )
            searches.append(search)

    # maximum year of cited papers
    max_ref_year = max(r["year"] for r in refs.values() if r != "unpublished")

    # compute log-10 depth and breadth
    for s in searches:
        for n in ("depth", "breadth"):
            s["log-" + n] = np.log10(s[n])

    # set labels
    label_by_map = {
        "Astronomical object": "astro-target",
        "Algorithm": "algorithm",
        "Algorithm (coherent)": "algorithm-coherent",
        "Algorithm (incoherent)": "algorithm-incoherent",
        "Citation": "citation",
        "Full citation": "full-citation",
    }
    with open("label_map.json", encoding="utf-8") as f:
        label_map = json.load(f)
    for k in label_by_map.values():
        if k in label_map:
            for s in searches:
                if k in s:
                    for r in label_map[k]:
                        if "replace" in r:
                            s[k] = re.sub(r["replace"], r["with"], s[k])
                        elif "key" in r and s[k] == r["key"]:
                            s[k] = r["symbol"]
                            s[k + "-label"] = r["label"]
                            s[k + "-key"] = r["key"]

    # add algorithm label
    for s in searches:
        if s["algorithm-incoherent"] == "none":
            s["algorithm"] = s["algorithm-coherent"]
        else:
            s["algorithm"] = (
                s["algorithm-incoherent"] + "-on-" + s["algorithm-coherent"]
            )

    # list unique observing runs
    obs_runs_unique = set([s["obs-run"] for s in searches])
    obs_runs = []
    for p in ("S", "VSR", "O"):
        obs_runs.extend(sorted([o for o in obs_runs_unique if o.startswith(p)]))

    # set category labels and colours
    with open("category_map.json", encoding="utf-8") as f:
        category_map = json.load(f)
    for s in searches:
        category_key = s["category"]
        s["category"] = category_map[category_key]["long-name"]
        s["category-short"] = category_map[category_key]["short-name"]
        s["colour"] = category_map[category_key]["colour"]
    categories = [v["long-name"] for v in category_map.values()]
    category_legend = {
        v["long-name"]: (v["short-name"], v["colour"]) for v in category_map.values()
    }

    # add missing astronomical target labels
    for s in searches:
        if "astro-target" not in s:
            s["astro-target"] = s["category-short"]
            s["astro-target-only"] = None
        else:
            s["astro-target-only"] = s["astro-target"]

    # set observing run markers
    initial_era_markers = {
        "S1": ">",
        "S2": "<",
        "S4": "s",
        "S5": "p",
        "S6": "h",
        "VSR1": "v",
        "VSR23": "^",
        "VSR4": "d",
    }
    advanced_era_markers = set()
    for s in searches:
        if s["obs-run"] in initial_era_markers:
            s["marker"] = initial_era_markers[s["obs-run"]]
        else:
            m = re.fullmatch(r"O([1-9])", s["obs-run"])
            n = int(m.group(1))
            if n == 1:
                s["marker"] = "."
            else:
                s["marker"] = (n, 2, 0)
            advanced_era_markers.add((s["obs-run"], s["marker"]))
    obs_run_legend = list(initial_era_markers.items()) + sorted(
        list(advanced_era_markers)
    )

    # list unique astronomical targets
    astro_targets = sorted(
        list(set([s["astro-target"] for s in searches if "astro-target" in s]))
    )

    return (
        refs,
        searches,
        {
            "max-ref-year": max_ref_year,
            "label-by-map": label_by_map,
            "obs-runs": obs_runs,
            "categories": categories,
            "astro-targets": astro_targets,
            "category-legend": category_legend,
            "obs-run-legend": obs_run_legend,
        },
    )


refs, searches, props = get_data()


@st.cache_data
def get_mrt(refs, searches):

    # output data from CW searches in a machine-readable format
    mrtable = []

    for s in searches:

        # row of machine-readable table
        mr = {
            "category": s["category"],
            "obs-run": s["obs-run"],
            "astro-target": s["astro-target-only"],
            "algorithm-coherent": s["algorithm-coherent-label"],
            "algorithm-incoherent": s["algorithm-incoherent-label"],
        }
        mr["depth"] = "{:0.3g}".format(s["depth"])
        if "depth-freq" in s:
            mr["depth-freq"] = "{:0.1f}".format(s["depth-freq"])
        else:
            mr["depth-freq"] = None
        mr["log10-breadth"] = float("{:0.3g}".format(np.log10(s["breadth"])))
        for breadth_component in ("freq", "fdot", "fddot", "sky", "bin", "HMM"):
            if s["breadth-" + breadth_component] is not None:
                mr["log10-breadth-" + breadth_component] = float(
                    "{:0.3e}".format(np.log10(s["breadth-" + breadth_component]))
                )
            else:
                mr["log10-breadth-" + breadth_component] = None
        mr["DOI"] = refs[s["ref-key"]]["doi"]

        # append row to machine-readable table
        mrtable.append(mr)

    # sort machine-readable table rows
    mrtable = natsorted(
        mrtable,
        key=lambda mr: (
            mr["category"],
            "SVO".index(mr["obs-run"][0]),
            mr["obs-run"],
            mr["depth"],
            mr["log10-breadth"],
        ),
    )

    # create machine-readable table
    machine_readable_table_spec = [
        ("category", str, "Continuous wave search category"),
        ("obs-run", str, "Most recent observing run data used"),
        ("astro-target", str, "Astrophysical object targeted, if relevant"),
        ("algorithm-coherent", str, "Coherent analysis algorithm used"),
        ("algorithm-incoherent", str, "Incoherent analysis algorithm used"),
        (
            "log10-breadth-freq",
            float,
            "Parameter-space breadth over gravitational wave frequency, if relevant",
        ),
        (
            "log10-breadth-fdot",
            float,
            "Parameter-space breadth over first frequency derivative, if relevant",
        ),
        (
            "log10-breadth-fddot",
            float,
            "Parameter-space breadth over second frequency derivative, if relevant",
        ),
        (
            "log10-breadth-sky",
            float,
            "Parameter-space breadth over the sky, if relevant",
        ),
        (
            "log10-breadth-bin",
            float,
            "Parameter-space breadth over binary system orbital parameters, if relevant",
        ),
        (
            "log10-breadth-HMM",
            float,
            "Parameter-space breadth of Hidden Markov model, if relevant",
        ),
        ("log10-breadth", float, "Total parameter-space breadth"),
        ("depth", float, "Sensitivity depth"),
        (
            "depth-freq",
            float,
            "Frequency in Hz at which sensitivity depth was evaluated",
        ),
        ("DOI", str, "Digital Object Identifier of reference"),
    ]
    machine_readable_table = QTable()
    for key, dtype, desc in machine_readable_table_spec:
        machine_readable_table[key] = MaskedColumn(
            data=[mr[key] for mr in mrtable],
            mask=[mr[key] is None for mr in mrtable],
            name=key,
            unit=None,
            dtype=dtype,
            description=desc,
        )
    mrtablestr = io.StringIO()
    machine_readable_table.write(mrtablestr, format="ascii.ecsv", delimiter=",")

    return mrtablestr.getvalue()


machine_readable_table = get_mrt(refs, searches)


@st.cache_data
def get_contributors():
    with open("CONTRIBUTORS", encoding="utf-8") as f:
        contributors = [[n.strip() for n in line.rstrip().split(",")] for line in f]

    return contributors


contributors = get_contributors()

### create page intro

contributors_str = ", ".join(f"{first} {last}" for last, first in contributors)

st.title("The CW Vista: Depth vs Breadth")
st.write(
    f"""

    **Contributors to this webpage:** {contributors_str}.

    This webpage generate *vista plots* of the sensitivity depth versus the
    parameter-space breadth of searches for continuous gravitational waves
    (CWs). They are designed to give a richer comparison between different
    searches, and the different trade-offs made between sensitivity and
    parameter space coverage. They also serve as a big-picture overview of
    efforts towards a first detection of continuous gravitational waves which
    began in the early 2000s. See [Wette
    (2023)](https://doi.org/10.1016/j.astropartphys.2023.102880) for further
    information.

    **Please contribute!** If you have published a search for continuous
    gravitational waves, please contribute your results and keep the CW vista
    up-to-date. See [this link for
    instructions](https://github.com/cw-vista/cw-vista/blob/main/README.md).

    If you use a vista plot in an academic publication, please download the
    BibTeX and cite `cwv:Wette2023`, `cwv:webapp`, and (as appropriate)
    publications for the CW searches that appear in the plot. Figures are
    licensed under a [Creative Commons CC BY 4.0
    International](https://creativecommons.org/licenses/by/4.0/) license.

    """
)

### create sidebar

icon_cntr, qr_code_cntr = st.sidebar.columns(2)
icon_cntr.image("icon.jpeg", width=100)
qr_code_cntr.image("qr-code.png", width=100)

st.sidebar.markdown("## Select CW Searches")

select_searches = searches

obs_run_cntr = st.sidebar.container()
if st.sidebar.checkbox("Select all", value=True, key="select_all_obs_run"):
    obs_runs = obs_run_cntr.pills(
        "Observing run",
        options=props["obs-runs"],
        selection_mode="multi",
        default=props["obs-runs"],
    )
else:
    obs_runs = obs_run_cntr.pills(
        "Observing run", options=props["obs-runs"], selection_mode="multi"
    )

select_searches = [s for s in select_searches if s["obs-run"] in obs_runs]

if (
    st.sidebar.pills("Select by", options=["Category", "Object"], default="Category")
    == "Category"
):

    categories_cntr = st.sidebar.container()
    if st.sidebar.checkbox("Select all", value=True, key="select_all_categories"):
        categories = categories_cntr.pills(
            "Category",
            options=props["categories"],
            selection_mode="multi",
            default=props["categories"],
        )
    else:
        categories = categories_cntr.pills(
            "Category", options=props["categories"], selection_mode="multi"
        )

    select_searches = [s for s in select_searches if s["category"] in categories]

else:

    astro_targets = st.sidebar.multiselect(
        "Astronomical object", options=props["astro-targets"]
    )

    select_searches = [
        s for s in select_searches if s.get("astro-target", None) in astro_targets
    ]

select_searches = sorted(select_searches, key=lambda s: s["log-depth"])

select_obs_runs = set([s["obs-run"] for s in select_searches])
select_categories = set([s["category"] for s in select_searches])

log_depth = np.array([s["log-depth"] for s in select_searches])
log_breadth = np.array([s["log-breadth"] for s in select_searches])

colours = [s["colour"] for s in select_searches]
markers = [s["marker"] for s in select_searches]

st.sidebar.markdown("## Plotting Options")

if select_searches:

    max_depth = max(select_searches, key=lambda s: s["log-depth"])
    max_breadth = max(select_searches, key=lambda s: s["log-breadth"])

    figure_fmt = st.sidebar.selectbox(
        "Figure format", options=["png", "eps", "pdf", "svg"]
    )

    figure_size = st.sidebar.selectbox(
        "Figure size", options=["custom"] + list(figure_sizes.keys()), index=0
    )

    if figure_size == "custom":

        default_custom_size = figure_sizes["beamer 16:9"]

        width = st.sidebar.number_input(
            "Figure width (inches)",
            min_value=1.0,
            max_value=2 * max(default_custom_size),
            value=max(default_custom_size),
            step=0.1,
        )
        height = st.sidebar.number_input(
            "Figure height (inches)",
            min_value=1.0,
            max_value=2 * min(default_custom_size),
            value=min(default_custom_size),
            step=0.1,
        )

    else:

        width = max(figure_sizes[figure_size])
        height = min(figure_sizes[figure_size])

    font_size = st.sidebar.slider("Font size", min_value=6, max_value=36, value=14)

    marker_size = st.sidebar.slider(
        "Marker size", min_value=10, max_value=500, value=100
    )

    plot_lim = {}
    for a, maxv, step in (
        ("x", max_breadth["log-breadth"], 1.0),
        ("y", max_depth["log-depth"], 0.1),
    ):
        if (
            st.sidebar.pills(
                f"{a.upper()} plot range",
                options=["automatic", "manual"],
                default="automatic",
                key=f"{a}-plot-lim",
            )
            == "automatic"
        ):
            plot_lim[a] = None
        else:
            plot_lim[a] = st.sidebar.slider(
                f"Manual {a.upper()} plot range",
                min_value=-round(0.5 * maxv, 1),
                max_value=round(1.5 * maxv, 1),
                value=(0.0, round(maxv, 1)),
                step=step,
            )

    grid_lines = {}
    for a in ("x", "y"):
        grid_lines[a] = st.sidebar.pills(
            f"{a.upper()} axis grid lines",
            options=["none", "major", "both"],
            default="major",
            key=f"{a}-axis-grid-lines",
        )

    with_horizon = st.sidebar.checkbox(
        "With horizon",
        value=True,
        help=dedent(
            """\
            The **horizon** is the line which satisfies the following properties:
            1. A line parallel to the horizon which intersects the search
               of maximum depth will also intersect the search of maximum
               breadth (and vice versa).
            2. The Y-intercept of the horizon is the maximum Y-intercept of
               any line parallel to the horizon which intersects a search.
            """
        ),
    )

    label_by = st.sidebar.selectbox(
        "Label points by",
        options=["none"] + list(props["label-by-map"].keys()),
        index=0,
    )
    with_algorithm_labels = st.sidebar.checkbox(
        "Add algorithm labels to legend",
        value=True,
        disabled=not props["label-by-map"].get(label_by, "").startswith("algorithm"),
    )

    label_font_size = st.sidebar.slider(
        "Label font size", min_value=6, max_value=24, value=8
    )

    label_background_alpha = st.sidebar.slider(
        "Label background opacity", min_value=0.0, max_value=1.0, value=0.5, step=0.1
    )

    label_background_pad = st.sidebar.slider(
        "Label background padding", min_value=0, max_value=6, value=0
    )

    legend_position = st.sidebar.selectbox(
        "Legend position",
        options=[
            "best",
            "outside",
            "upper left",
            "upper right",
            "center left",
            "center right",
            "center",
            "lower center",
            "lower left",
            "lower right",
            "right",
            "upper center",
        ],
        index=1,
    )

    legend_columns = st.sidebar.slider(
        "Legend columns", min_value=1, max_value=10, value=2
    )

    legend_font_size = st.sidebar.slider(
        "Legend font size", min_value=6, max_value=36, value=12
    )

    with_image_credit = st.sidebar.checkbox("With image credit", value=True)

### generate BibTeX


def gen_bibentry(entrytype, fields):
    s = "@" + entrytype.upper() + "{cwv:" + fields["key"] + ",\n"
    for f, v in sorted(fields.items()):
        if f.startswith("key"):
            continue
        if isinstance(v, list):
            v = " and ".join(v)
        if f.endswith("title"):
            v = "{" + v + "}"
        s += "  " + f + " = {" + str(v) + "},\n"
    s += "}\n"
    return s


bibtex = gen_bibentry(
    "article",
    {
        "key": "Wette2023",
        "title": "Searches for continuous gravitational waves from neutron stars: A twenty-year retrospective",
        "author": ["Wette, K."],
        "journal": "Astropart. Phys.",
        "volume": "153",
        "pages": "102880",
        "year": 2023,
        "doi": "10.1016/j.astropartphys.2023.102880",
    },
)
bibtex += "\n"

bibtex += gen_bibentry(
    "misc",
    {
        "key": "webapp",
        "title": page_title,
        "author": " and ".join(f"{last}, {first}" for last, first in contributors),
        "year": max(2025, props["max-ref-year"]),
        "url": page_url,
    },
)
bibtex += "\n"

select_searches_bibtex = sorted(
    [
        gen_bibentry("article", refs[k])
        for k in set([s["ref-key"] for s in select_searches])
    ]
)

bibtex += "\n".join(select_searches_bibtex)

### vista plot


# handler to create text artists for algorithm legend labels
class TextLegendHandler:
    def legend_artist(self, legend, orig_handle, fontsize, handlebox):
        x0, y0 = handlebox.xdescent, handlebox.ydescent
        w, h = handlebox.width, handlebox.height
        p = mpatches.Rectangle(
            [x0, y0],
            w,
            h,
            facecolor="none",
            edgecolor="none",
            transform=handlebox.get_transform(),
        )
        handlebox.add_artist(p)
        t = mtext.Text(
            x0 + 0.5 * w,
            y0 + 0.5 * h,
            orig_handle.get_text(),
            fontsize=label_font_size,
            ha="center",
            va="center",
            transform=handlebox.get_transform(),
        )
        handlebox.add_artist(t)
        return p


def vista_plot(toast=True, **kwargs):

    with _lock:

        mpl.rcParams.update({"font.family": "serif", "text.usetex": False})

        fig, ax = plt.subplots(figsize=(width, height))
        ax.minorticks_on()
        ax.get_xaxis().set_zorder(-50)
        ax.get_yaxis().set_zorder(-50)

        # plot depth vs breadth
        sc = ax.scatter(log_breadth, log_depth, c=colours, s=marker_size, zorder=-10)

        # set markers
        paths = []
        for m in markers:
            m_obj = mmarkers.MarkerStyle(m)
            path = m_obj.get_path().transformed(m_obj.get_transform())
            paths.append(path)
        sc.set_paths(paths)

        # plot horizon
        depth_diff = max_depth["log-depth"] - max_breadth["log-depth"]
        breadth_diff = max_depth["log-breadth"] - max_breadth["log-breadth"]
        if depth_diff == 0 and toast:
            st.toast(
                """
                **Warning:** could not plot horizon, search of
                max. depth is same as search of max. breadth
                """
            )
        if with_horizon and depth_diff != 0:
            horizon_slope = -breadth_diff / depth_diff
            horizon_origin = max(
                select_searches,
                key=lambda s: horizon_slope * s["log-depth"] + s["log-breadth"],
            )
            ax.axline(
                (horizon_origin["log-breadth"], horizon_origin["log-depth"]),
                slope=-1 / horizon_slope,
                color="black",
                linewidth=0.5,
                linestyle=":",
                zorder=-10,
            )

        # set plot limits
        if plot_lim["x"] is not None:
            ax.set_xlim(min(plot_lim["x"]), max(plot_lim["x"]))
        if plot_lim["y"] is not None:
            ax.set_ylim(min(plot_lim["y"]), max(plot_lim["y"]))

        # set grid lines
        for a in grid_lines:
            if grid_lines[a] == "none":
                ax.grid(visible=False, which="both", axis=a)
            else:
                ax.grid(
                    visible=True, which="major", axis=a, linewidth=0.5, linestyle="-"
                )
                if grid_lines[a] == "both":
                    ax.grid(
                        visible=True,
                        which="minor",
                        axis=a,
                        linewidth=0.5,
                        linestyle=":",
                    )
                else:
                    ax.grid(visible=False, which="minor", axis=a)

        # set legend
        legend_handles = []
        for category, (lbl, clr) in props["category-legend"].items():
            if category in select_categories:
                legend_handles.append(mpatches.Patch(color=clr, label=lbl))
        for obs_run, mkr in props["obs-run-legend"]:
            if obs_run in select_obs_runs:
                legend_handles.append(
                    mlines.Line2D(
                        [],
                        [],
                        color="grey",
                        marker=mkr,
                        linestyle="none",
                        markersize=legend_font_size - 2,
                        label=obs_run,
                    )
                )
        if with_horizon and depth_diff != 0:
            legend_handles.append(
                mlines.Line2D(
                    [], [], color="black", linewidth=0.5, linestyle=":", label="horiz."
                )
            )
        if with_algorithm_labels:
            label_by_key = props["label-by-map"].get(label_by, "")
            if label_by_key.startswith("algorithm"):
                if label_by_key == "algorithm":
                    with_algorithm_label_keys = (
                        "algorithm-coherent",
                        "algorithm-incoherent",
                    )
                else:
                    with_algorithm_label_keys = (label_by_key,)
                algorithm_labels = set()
                for s in select_searches:
                    for k in with_algorithm_label_keys:
                        if k in s and k + "-label" in s:
                            algorithm_labels.add(
                                (s[k + "-key"].lower(), s[k], s[k + "-label"])
                            )
                for _, symb, lbl in sorted(algorithm_labels):
                    legend_handles.append(mtext.Text(text=symb, label=lbl))
        if legend_position == "outside":
            box = ax.get_position()
            ax.set_position([box.x0, box.y0, box.width * 0.9, box.height])
            ax.legend(
                handles=legend_handles,
                handler_map={mtext.Text: TextLegendHandler()},
                ncols=legend_columns,
                columnspacing=0.5,
                framealpha=1,
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                fontsize=legend_font_size,
            )
        else:
            ax.legend(
                handles=legend_handles,
                handler_map={mtext.Text: TextLegendHandler()},
                ncols=legend_columns,
                columnspacing=0.5,
                framealpha=1,
                loc=legend_position,
                fontsize=legend_font_size,
            )

        # set axis labels
        ax.set_xlabel(r"Breadth $\log_{10} \mathcal{B}$")
        ax.set_ylabel(r"Depth $\log_{10} \mathcal{D}$")

        # set font size
        for item in (
            [ax.title, ax.xaxis.label, ax.yaxis.label]
            + ax.get_xticklabels()
            + ax.get_yticklabels()
        ):
            item.set_fontsize(font_size)

        # add image credit
        if with_image_credit:
            fig.text(
                0,
                0,
                f"Image credit: {page_url}, (C) CC BY 4.0",
                fontsize=6,
                ha="left",
                va="baseline",
                zorder=10,
            )

        # add labels
        labels = {}
        if label_by != "none":
            label_by_key = props["label-by-map"][label_by]
            for s in select_searches:
                lbl = s[label_by_key]
                if lbl not in labels:
                    labels[lbl] = {"x": [], "y": [], "text": None}
                labels[lbl]["x"].append(s["log-breadth"])
                labels[lbl]["y"].append(s["log-depth"])
        for lbl in labels:
            labels[lbl]["text"] = ax.text(
                np.mean(labels[lbl]["x"]),
                np.mean(labels[lbl]["y"]),
                lbl,
                fontsize=label_font_size,
                ha="center",
                va="center",
                bbox={
                    "facecolor": "white",
                    "alpha": label_background_alpha,
                    "edgecolor": "none",
                    "pad": label_background_pad,
                },
                zorder=-5,
                usetex=True,
            )

        # fix layout
        fig.tight_layout()

        # adjust labels and add arrows
        if labels:
            adjust_text([v["text"] for v in labels.values()])
            for v in labels.values():
                for i in range(len(v["x"])):
                    ax.add_patch(
                        mpatches.FancyArrowPatch(
                            v["text"].get_position(),
                            (v["x"][i], v["y"][i]),
                            color="grey",
                            linewidth=0.25,
                            linestyle=":",
                            zorder=-15,
                        )
                    )

        # save figure to memory
        img = io.BytesIO()
        plt.savefig(img, bbox_inches="tight", **kwargs)

        return img


if not select_searches:
    st.markdown(
        "**No CW searches have been selected! Please select searches in the sidebar.**"
    )

    # remove any old vista plots
    if "display-img" in st.session_state:
        del st.session_state["display-img"]

else:

    download_img = None

    replot_cntr = st.empty()

    download_img_cntr, download_refs_cntr = st.columns((1, 1))

    vista_plot_cntr = st.container()

    if st.session_state["display-img-first-time"] or replot_cntr.button("Replot"):

        with replot_cntr:
            with st.spinner("Working ..."):

                # store vista plot in session state, so can be displayed while changing options
                display_img = vista_plot(format="svg")
                st.session_state["display-img"] = display_img.getvalue().decode("utf-8")

                st.session_state["display-img-first-time"] = False

                # create downloadable vista plot in requested format
                if figure_fmt == "svg":
                    download_img = display_img
                else:
                    download_img = vista_plot(toast=False, format=figure_fmt, dpi=600)

    if "display-img" in st.session_state:

        # show vista plot
        vista_plot_cntr.image(st.session_state["display-img"], use_container_width=True)

        # show download buttons
        if download_img is not None:
            download_img_cntr.download_button(
                label="Download Figure",
                data=download_img,
                file_name="cw-vista." + figure_fmt,
                mime="image/" + figure_fmt,
                on_click="ignore",
            )
            download_refs_cntr.download_button(
                label="Download BibTeX",
                data=bibtex,
                file_name="cw-vista.bib",
                mime="application/x-bibtex",
                on_click="ignore",
            )

        # show statistics
        st.write(
            f"**Number of CW searches that appear in this plot:** {len(select_searches)}"
        )
        st.write(
            f"**Number of CW search publications represented in this plot:** {len(select_searches_bibtex)}"
        )

        # download data
        st.write(
            """

            **Data** used to create the vista plots may be downloaded as an
            ASCII Enhanced CSV table.

            """
        )
        st.download_button(
            label="Download ECSV",
            data=machine_readable_table,
            file_name="CW_searches_table.ecsv",
            mime="text/csv",
            on_click="ignore",
        )

        # acknowledgements
        st.write(
            """

            **Acknowledgements:** This work builds upon: [Behnke et
            al. (2015)](http://doi.org/10.1103/PhysRevD.91.064007) for the
            definition of $\\mathcal{D}$, [Dreissigacker et
            al. (2018)](https://doi.org/10.1103/PhysRevD.98.084058) for
            computing $\\mathcal{D}$ for CW searches from the initial and early
            advanced detector eras, and [Wette
            (2023)](https://doi.org/10.1016/j.astropartphys.2023.102880) for the
            definition of $\\mathcal{B}$ and the original vista plot. This
            webpage generates plots using [Matplotlib](https://matplotlib.org/),
            [adjustText](https://adjusttext.readthedocs.io/),
            [papersize](https://papersize.readthedocs.io/en/latest/) and
            [NumPy](https://numpy.org/).

            """
        )

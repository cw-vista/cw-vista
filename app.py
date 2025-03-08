import io
import json
import re
from pathlib import Path
from textwrap import dedent
from threading import RLock

import matplotlib as mpl
import matplotlib.lines as mlines
import matplotlib.markers as mmarkers
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from adjustText import adjust_text

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
    }
    with open("label_map.json", encoding="utf-8") as f:
        label_map = json.load(f)
    for k in label_by_map.values():
        if k in label_map:
            for s in searches:
                if k in s:
                    for r, v in label_map[k].items():
                        if r.startswith(r"^"):
                            s[k] = re.sub(r, v, s[k])
                        elif s[k] == r:
                            s[k] = v

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

    # set observing run markers
    initial_era_markers = {
        "S1": ">",
        "S2": "<",
        "S4": "s",
        "S5": "p",
        "S6": "h",
        "VSR1": "v",
        "VSR2": "^",
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
    (2023)](https://doi.org/10.1016/j.astropartphys.2023.102880) and references
    therein for further information.

    **Please contribute!** If you have published a search for continuous
    gravitational waves, please contribute your results and keep the CW vista
    up-to-date. See
    [here](https://github.com/cw-vista/cw-vista/blob/main/README.md) for
    instructions.

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

    width = st.sidebar.number_input(
        "Figure width (inches)", min_value=1.0, max_value=8.3, value=8.3, step=0.1
    )
    height = st.sidebar.number_input(
        "Figure height (inches)", min_value=1.0, max_value=8.3, value=3.5, step=0.1
    )

    font_size = st.sidebar.slider("Font size", min_value=6, max_value=24, value=14)

    marker_size = st.sidebar.slider(
        "Marker size", min_value=10, max_value=100, value=50
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

    label_font_size = st.sidebar.slider(
        "Label font size", min_value=6, max_value=24, value=8
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
        "Legend font size", min_value=6, max_value=24, value=12
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


def vista_plot(toast=True, **kwargs):

    with _lock:

        mpl.rcParams.update({"font.family": "serif", "text.usetex": False})

        fig, ax = plt.subplots(figsize=(width, height))
        ax.minorticks_on()

        # plot depth vs breadth
        sc = ax.scatter(log_breadth, log_depth, c=colours, s=marker_size)

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

        # set labels
        labels = []
        if label_by != "none":
            label_by_key = props["label-by-map"][label_by]
            for s in select_searches:
                if label_by_key in s:
                    labels.append(
                        ax.text(
                            s["log-breadth"],
                            s["log-depth"],
                            s[label_by_key],
                            fontsize=label_font_size,
                            ha="center",
                            va="center",
                        )
                    )

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

        if legend_position == "outside":
            box = ax.get_position()
            ax.set_position([box.x0, box.y0, box.width * 0.9, box.height])
            ax.legend(
                handles=legend_handles,
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
            )

        # fix layout
        fig.tight_layout()

        # adjust labels
        adjust_text(labels)

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

        # show statistics and authors
        st.write(
            f"**Number of CW searches that appear in this plot:** {len(select_searches)}"
        )
        st.write(
            f"**Number of CW search publications represented in this plot:** {len(select_searches_bibtex)}"
        )
        authors = set()
        collaborations = set()
        for s in select_searches:
            ref = refs[s["ref-key"]]
            if "collaboration" in ref:
                collaborations.update(ref["collaboration"])
            else:
                authors.update(ref["author"])
        st.write(
            "**CW search publication authors:** "
            + "; ".join(sorted(authors))
            + "; and "
            + ", ".join(sorted(collaborations))
            + "."
        )

        # acknowledge software
        st.write(
            """
            **Software:** Plots were generated using
            [Matplotlib](https://matplotlib.org/),
            [adjustText](https://adjusttext.readthedocs.io/), and
            [NumPy](https://numpy.org/).
            """
        )

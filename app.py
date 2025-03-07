import io
import json
import re
from pathlib import Path
from threading import RLock

import matplotlib as mpl
import matplotlib.lines as mlines
import matplotlib.markers as mmarkers
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

# to protect against non-reentrant matplotlib
_lock = RLock()

mpl.use("agg")

### configure page

page_title = "The CW Vista"
st.set_page_config(page_title=page_title, page_icon="icon.jpeg", layout="wide")

# vista plot show be plotted when page is first loaded
if not "display-img-first-time" in st.session_state:
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
        refs[ref["key"]] = ref
        for search in data["searches"]:
            search["ref-key"] = ref
            searches.append(search)

    # compute log-10 depth and breadth
    for s in searches:
        for n in ("depth", "breadth"):
            s["log-" + n] = np.log10(s[n])

    # list unique observing runs
    obs_runs_unique = set([s["obs-run"] for s in searches])
    obs_runs = []
    for p in ("S", "VSR", "O"):
        obs_runs.extend(sorted([o for o in obs_runs_unique if o.startswith(p)]))

    # set category labels and colours
    category_map = {
        "pulsar targeted": ("Pulsars (Targeted)", "PSR T", "red"),
        "pulsar narrowband": ("Pulsars (Narrowband)", "PSR NB", "orange"),
        "cco": ("Central Compact Objects", "CCO", "gold"),
        "lmxb": ("Low-Mass X-ray Binaries", "LMXB", "green"),
        "skypatch": ("Sky Patches", "SkyPatch", "blue"),
        "allsky isolated": ("All Sky (Isolated)", "AllSky 1", "indigo"),
        "allsky binary": ("All Sky (Binary)", "AllSky 2", "violet"),
    }
    for s in searches:
        s["category"], s["category-short"], s["colour"] = category_map[s["category"]]
    categories = [v[0] for v in category_map.values()]
    category_legend = {v[0]: (v[1], v[2]) for v in category_map.values()}

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
            "obs-runs": obs_runs,
            "categories": categories,
            "astro-targets": astro_targets,
            "category-legend": category_legend,
            "obs-run-legend": obs_run_legend,
        },
    )


refs, searches, props = get_data()


@st.cache_data
def get_authors():
    with open("AUTHORS", encoding="utf-8") as f:
        authors = [line.rstrip().split(",") for line in f]

    return authors


authors = get_authors()

### create page intro

st.title("The CW Vista: Depth vs Breadth")

st.write("**Authors:** " + ", ".join(f"{first} {last}" for last, first in authors))

### create sidebar

st.sidebar.image("icon.jpeg", width=100)

st.sidebar.markdown("## Select CW Searches")

select_searches = searches

obs_run_cntr = st.sidebar.container()
if st.sidebar.checkbox("Select All", value=True, key="select_all_obs_run"):
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
    if st.sidebar.checkbox("Select All", value=True, key="select_all_categories"):
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
        "Astronomical Object", options=props["astro-targets"]
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

    figure_fmt = st.sidebar.selectbox(
        "Figure format", options=["png", "eps", "pdf", "svg"]
    )

    width = st.sidebar.number_input(
        "Figure width (inches)", min_value=1.0, max_value=8.3, value=8.3, step=0.1
    )
    height = st.sidebar.number_input(
        "Figure height (inches)", min_value=1.0, max_value=8.3, value=3.5, step=0.1
    )

    font_size = st.sidebar.slider("Font size", min_value=8, max_value=24, value=16)

    marker_size = st.sidebar.slider(
        "Marker size", min_value=10, max_value=100, value=50
    )

    plot_lim = {}
    for a, maxv, step in (
        ("x", float(max(log_breadth)), 1.0),
        ("y", float(max(log_depth)), 0.1),
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

    legend_font_size = st.sidebar.slider(
        "Legend font size", min_value=8, max_value=24, value=12
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

### vista plot


def vista_plot(**kwargs):

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
                    download_img = vista_plot(format=figure_fmt, dpi=600)

    if "display-img" in st.session_state:

        # show vista plot
        vista_plot_cntr.image(st.session_state["display-img"], use_container_width=True)

        # show download buttons
        if download_img is not None:
            download_img_cntr.download_button(
                label="Download figure",
                data=download_img,
                file_name="cw-vista." + figure_fmt,
                mime="image/" + figure_fmt,
                on_click="ignore",
            )

"""Region Classification Streamlit App"""
import os
from io import BytesIO

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Region Classification",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Force grey background regardless of user's system theme
st.markdown("""
<style>
    .stApp { background-color: #c8c8c8 !important; }
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div:first-child {
        background-color: #bebebe !important;
    }
    /* Ensure readable dark text on light background */
    .stApp, .stMarkdown, .stMarkdown p, .stMarkdown h1,
    .stMarkdown h2, .stMarkdown h3, label {
        color: #1a1a1a !important;
    }
    /* White buttons with dark text */
    .stButton > button {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
        border: 1px solid #aaaaaa !important;
    }
    .stButton > button:hover {
        background-color: #f0f0f0 !important;
        border: 1px solid #888888 !important;
    }
</style>
""", unsafe_allow_html=True)

REGIONS = list(range(1, 188))
SWATCHES_DIR = "data/CT_individual_swatches_V2"
RESULTS_DIR = "data/Results_CT_local_for_app"
SKINMATCH_EXCEL = "data/SkinMatch classification.xlsx"
TOTAL = len(REGIONS)

# Image number ranges per hair tone
TONE_RANGES = {
    "LIGHT": (7, 10),   # lighter models
    "MEDIUM": (4, 7),
    "DARK": (1, 4),     # darker models
}

FAMILLE_LP_OPTIONS = [
    "", "ASH", "COOL BROWN", "COPPER", "FONDAMENTALE",
    "GOLD", "IRIDESCENT", "MOCHA", "RED/ACAJOU", "WARM BROWN",
]


# ── State ────────────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "started": False,
        "current_idx": 0,
        "responses": {},
        "fr1_history": [],
        "fr2_history": [],
        "dmi_history": [],
        "fam_val": "",
        "loaded_region": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def load_region_inputs(region):
    """Populate input keys from saved response only when the region changes."""
    if st.session_state.loaded_region == region:
        return
    saved = st.session_state.responses.get(region, {})
    st.session_state.fr1_val = saved.get("Reflet 1", "")
    st.session_state.fr2_val = saved.get("Reflet 2", "")
    st.session_state.fam_val = saved.get("famille", "")
    st.session_state.dmi_val = saved.get("dmi", "")
    st.session_state.loaded_region = region


def save_current(region):
    """Persist current form values and update suggestion histories."""
    fr1 = st.session_state.get("fr1_val", "")
    fr2 = st.session_state.get("fr2_val", "")
    fam = st.session_state.get("fam_val", "")
    dmi = st.session_state.get("dmi_val", "")
    st.session_state.responses[region] = {
        "Reflet 1": fr1,
        "Reflet 2": fr2,
        "famille": fam,
        "dmi": dmi,
    }
    for val, hist_key in [(fr1, "fr1_history"), (fr2, "fr2_history"), (dmi, "dmi_history")]:
        if val and val not in st.session_state[hist_key]:
            st.session_state[hist_key].insert(0, val)
            st.session_state[hist_key] = st.session_state[hist_key][:10]


# ── Data helpers ─────────────────────────────────────────────────────────────

@st.cache_data
def load_tone_map():
    """Return {region_number: 'LIGHT'|'MEDIUM'|'DARK'} from SkinMatch Excel."""
    df = pd.read_excel(SKINMATCH_EXCEL, sheet_name="MAJ 050626")
    return {
        int(row["Unnamed: 0"]): str(row["TONE"]).upper()
        for _, row in df.iterrows()
        if pd.notna(row.get("TONE"))
    }


def load_from_excel(file):
    """Load responses from a previously downloaded Excel and jump to first unfilled region."""
    df = pd.read_excel(file)
    responses = {}
    fr1_hist, fr2_hist = [], []

    for _, row in df.iterrows():
        try:
            region = int(row["Region"])
        except (ValueError, KeyError):
            continue
        fr1 = "" if pd.isna(row.get("Reflet 1")) else str(row["Reflet 1"]).strip()
        fr2 = "" if pd.isna(row.get("Reflet 2")) else str(row["Reflet 2"]).strip()
        fam = "" if pd.isna(row.get("Famille Lp Name")) else str(row["Famille Lp Name"]).strip()
        dmi = "" if pd.isna(row.get("DMI Name")) else str(row["DMI Name"]).strip()
        fr1 = "" if fr1 == "nan" else fr1
        fr2 = "" if fr2 == "nan" else fr2
        fam = "" if fam == "nan" else fam
        dmi = "" if dmi == "nan" else dmi

        if fr1 or fr2 or fam or dmi:
            responses[region] = {"Reflet 1": fr1, "Reflet 2": fr2, "famille": fam, "dmi": dmi}
            for val, hist in [(fr1, fr1_hist), (fr2, fr2_hist)]:
                if val and val not in hist:
                    hist.append(val)

    st.session_state.responses = responses
    st.session_state.fr1_history = fr1_hist[:10]
    st.session_state.fr2_history = fr2_hist[:10]

    filled = set(responses.keys())
    st.session_state.current_idx = 0
    for i, r in enumerate(REGIONS):
        if r not in filled:
            st.session_state.current_idx = i
            break

    st.session_state.loaded_region = None


def build_excel():
    """Build Excel bytes including the live (unsaved) values for the current region."""
    current_region = REGIONS[st.session_state.current_idx]
    live = {
        "Reflet 1": st.session_state.get("fr1_val", ""),
        "Reflet 2": st.session_state.get("fr2_val", ""),
        "famille": st.session_state.get("fam_val", ""),
        "dmi": st.session_state.get("dmi_val", ""),
    }
    rows = []
    for r in REGIONS:
        resp = live if r == current_region else st.session_state.responses.get(r, {})
        rows.append({
            "Region": r,
            "Reflet 1": resp.get("Reflet 1", ""),
            "Reflet 2": resp.get("Reflet 2", ""),
            "Famille Lp Name": resp.get("famille", ""),
            "DMI Name": resp.get("dmi", ""),
        })
    buf = BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False)
    return buf.getvalue()


def get_result_images(region, tone=None):
    region_dir = os.path.join(RESULTS_DIR, str(region))
    if not os.path.exists(region_dir):
        return []
    files = [f for f in os.listdir(region_dir) if f.endswith(".jpg")]
    all_files = sorted(files, key=lambda f: int(f.rsplit("_", 1)[-1].split(".")[0]))

    if tone and tone in TONE_RANGES:
        lo, hi = TONE_RANGES[tone]
        all_files = [
            f for f in all_files
            if lo <= int(f.rsplit("_", 1)[-1].split(".")[0]) <= hi
        ]

    return all_files


# ── UI helpers ───────────────────────────────────────────────────────────────

def suggestion_buttons(hist_key, input_key):
    history = st.session_state[hist_key]
    if not history:
        return
    st.caption("Recent — click to reuse:")
    cols = st.columns(min(len(history), 8))
    for i, val in enumerate(history[:8]):
        if cols[i].button(str(val), key=f"{input_key}_sug_{i}"):
            st.session_state[input_key] = val
            st.rerun()


def sidebar_download():
    """Download button that always reflects the current live state."""
    filled = len(st.session_state.responses)
    has_live = any([
        st.session_state.get("fr1_val", ""),
        st.session_state.get("fr2_val", ""),
        st.session_state.get("fam_val", ""),
        st.session_state.get("dmi_val", ""),
    ])
    if filled > 0 or has_live:
        st.download_button(
            "⬇ Download progress",
            data=build_excel(),
            file_name="region_classification.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.caption("Fill at least one region to enable export.")


# ── Landing page ─────────────────────────────────────────────────────────────

def show_landing():
    st.title("Region Classification")
    st.markdown("Classify all 187 hair colour regions by assigning Reflet values.")
    st.divider()

    col_fresh, col_resume = st.columns(2)

    with col_fresh:
        st.markdown("### Start fresh")
        st.markdown("Begin from Region 1 with no pre-filled data.")
        if st.button("Start", type="primary", use_container_width=True):
            st.session_state.started = True
            st.rerun()

    with col_resume:
        st.markdown("### Resume previous session")
        st.markdown("Drag and drop your previously downloaded Excel to pick up where you left off.")
        uploaded = st.file_uploader(
            "Drop Excel here",
            type=["xlsx"],
            label_visibility="collapsed",
        )
        if uploaded is not None:
            load_from_excel(uploaded)
            st.session_state.started = True
            st.rerun()


# ── Main app ─────────────────────────────────────────────────────────────────

def show_app():
    region = REGIONS[st.session_state.current_idx]
    load_region_inputs(region)
    tone_map = load_tone_map()
    tone = tone_map.get(region)

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### Progress")
        filled = len(st.session_state.responses)
        st.progress(filled / TOTAL, text=f"{filled} / {TOTAL} regions filled")

        st.markdown("### Jump to region")
        jump_idx = st.selectbox(
            "Region",
            range(TOTAL),
            index=st.session_state.current_idx,
            format_func=lambda i: f"Region {REGIONS[i]}",
            label_visibility="collapsed",
        )
        if st.button("Go", use_container_width=True):
            save_current(region)
            st.session_state.current_idx = jump_idx
            st.session_state.loaded_region = None
            st.rerun()

        unfilled = [r for r in REGIONS if r not in st.session_state.responses]
        st.markdown(f"### Regions left ({len(unfilled)})")
        if unfilled:
            left_pick = st.selectbox(
                "Regions left",
                unfilled,
                format_func=lambda r: f"Region {r}",
                label_visibility="collapsed",
            )
            if st.button("Go to region", use_container_width=True):
                save_current(region)
                st.session_state.current_idx = REGIONS.index(left_pick)
                st.session_state.loaded_region = None
                st.rerun()
        else:
            st.caption("All regions classified!")

        st.divider()
        st.markdown("### Export")
        sidebar_download()

        st.divider()
        st.markdown("### Load saved session")
        resume_file = st.file_uploader(
            "Upload Excel to overwrite current session",
            type=["xlsx"],
            label_visibility="collapsed",
        )
        if resume_file is not None:
            load_from_excel(resume_file)
            st.session_state.loaded_region = None
            st.rerun()

    # ── Header ───────────────────────────────────────────────────────────────
    header_col, tone_col = st.columns([3, 1])
    with header_col:
        st.title(f"Region {region}")
    with tone_col:
        if tone:
            st.metric("Hair tone", tone.capitalize())

    st.progress(
        st.session_state.current_idx / (TOTAL - 1),
        text=f"Region {st.session_state.current_idx + 1} of {TOTAL}",
    )

    # ── Images ───────────────────────────────────────────────────────────────
    swatch_col, sim_col = st.columns([1, 4])

    with swatch_col:
        st.markdown("**CT Swatch**")
        swatch_path = os.path.join(SWATCHES_DIR, f"CT_{region}.jpg")
        if os.path.exists(swatch_path):
            st.image(swatch_path, use_container_width=True)
        else:
            st.warning("No swatch image found.")

    with sim_col:
        st.markdown("**Result Images**")
        sim_files = get_result_images(region, tone)
        if sim_files:
            n_cols = min(len(sim_files), 5)
            img_cols = st.columns(n_cols)
            for i, fname in enumerate(sim_files):
                img_path = os.path.join(RESULTS_DIR, str(region), fname)
                caption = fname.replace(f"CT_{region}_", "").replace(".jpg", "")
                img_cols[i % n_cols].image(img_path, caption=caption, use_container_width=True)
        else:
            st.info("No result images for this region.")

    st.divider()

    # ── Inputs ───────────────────────────────────────────────────────────────
    in1, in2, in3, in4 = st.columns(4)

    with in1:
        st.markdown("**Reflet 1**")
        suggestion_buttons("fr1_history", "fr1_val")
        st.text_input("Reflet 1", key="fr1_val", label_visibility="collapsed")

    with in2:
        st.markdown("**Reflet 2**")
        suggestion_buttons("fr2_history", "fr2_val")
        st.text_input("Reflet 2", key="fr2_val", label_visibility="collapsed")

    with in3:
        st.markdown("**DMI Name**")
        suggestion_buttons("dmi_history", "dmi_val")
        st.text_input("DMI Name", key="dmi_val", label_visibility="collapsed")

    with in4:
        st.markdown("**Famille Lp Name**")
        current_fam = st.session_state.get("fam_val", "")
        fam_index = FAMILLE_LP_OPTIONS.index(current_fam) if current_fam in FAMILLE_LP_OPTIONS else 0
        selected = st.selectbox(
            "Famille Lp Name",
            FAMILLE_LP_OPTIONS,
            index=fam_index,
            label_visibility="collapsed",
        )
        st.session_state.fam_val = selected

    # ── Navigation ───────────────────────────────────────────────────────────
    st.divider()
    nav_prev, nav_next = st.columns([1, 5])

    with nav_prev:
        if st.session_state.current_idx > 0:
            if st.button("← Previous", use_container_width=True):
                save_current(region)
                st.session_state.current_idx -= 1
                st.session_state.loaded_region = None
                st.rerun()

    with nav_next:
        is_last = st.session_state.current_idx == TOTAL - 1
        next_region = REGIONS[st.session_state.current_idx + 1] if not is_last else None
        btn_label = (
            "All done — download from sidebar ✓"
            if is_last
            else f"Validate & next → Region {next_region}"
        )
        if st.button(btn_label, type="primary", use_container_width=True):
            save_current(region)
            if is_last:
                st.balloons()
                st.success("All regions completed! Download your Excel from the sidebar.")
            else:
                st.session_state.current_idx += 1
                st.session_state.loaded_region = None
                st.rerun()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    init_state()
    if not st.session_state.started:
        show_landing()
    else:
        show_app()


if __name__ == "__main__":
    main()

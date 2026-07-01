import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="US Region Label Analyzer", layout="wide")

SWATCH_DIR = Path("data/CT_individual_swatches_V2")
EXCEL_PATH = "labeled_regions_us.xlsx"
SWATCH_SIZE = 110
COLS_PER_ROW = 10


@st.cache_data
def load_data():
    df = pd.read_excel(EXCEL_PATH)
    df["Reflet 1"] = df["Reflet 1"].astype(str)
    df["Reflet 2"] = df["Reflet 2"].astype(str)
    return df


def sort_key(val: str) -> float:
    try:
        return float(val)
    except ValueError:
        return 99.0


df = load_data()

deleted_mask = (df["Reflet 1"] == "0.0") & (df["Reflet 2"] == "0.0")
df_active = df[~deleted_mask].reset_index(drop=True)
df_deleted = df[deleted_mask].reset_index(drop=True)

tab1, tab2 = st.tabs(["Labeled Regions", "Deleted Regions (0.0 / 0.0)"])

# ── TAB 1 ──────────────────────────────────────────────────────────────────
with tab1:
    st.header("Labeled Regions")
    st.caption(f"{len(df_active)} regions grouped by Reflet combination — click swatches to select, then download CSV.")

    if "selected_regions" not in st.session_state:
        st.session_state.selected_regions = set()

    # Global actions
    col_sel, col_clr, _ = st.columns([2, 2, 8])
    with col_sel:
        if st.button("Select all"):
            st.session_state.selected_regions.update(df_active["Region"].tolist())
            st.rerun()
    with col_clr:
        if st.button("Clear selection"):
            st.session_state.selected_regions.clear()
            st.rerun()

    st.divider()

    # Build sorted group order: numeric first, then "Fonda"
    groups = (
        df_active.groupby(["Reflet 1", "Reflet 2"], sort=False)
        .apply(lambda g: g)
        .reset_index(drop=True)
    )
    group_keys = (
        df_active.groupby(["Reflet 1", "Reflet 2"], sort=False)
        .size()
        .reset_index(name="n")[["Reflet 1", "Reflet 2"]]
        .values.tolist()
    )
    group_keys.sort(key=lambda k: (sort_key(k[0]), sort_key(k[1])))

    for r1, r2 in group_keys:
        subset = df_active[(df_active["Reflet 1"] == r1) & (df_active["Reflet 2"] == r2)].reset_index(drop=True)
        n = len(subset)

        # Group header
        st.markdown(
            f"<div style='background:#dde3f0;border-left:4px solid #2c6fad;padding:6px 12px;border-radius:4px;"
            f"font-weight:600;font-size:15px;margin-bottom:4px;color:#1a1a2e;'>"
            f"Reflet 1: <span style='color:#1a4f8a'>{r1}</span> &nbsp;|&nbsp; "
            f"Reflet 2: <span style='color:#1a4f8a'>{r2}</span> "
            f"<span style='font-weight:400;color:#444;font-size:13px;'>({n} region{'s' if n > 1 else ''})</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Render swatches in rows of COLS_PER_ROW
        chunk_rows = [subset.iloc[i : i + COLS_PER_ROW] for i in range(0, n, COLS_PER_ROW)]
        for chunk in chunk_rows:
            cols = st.columns(COLS_PER_ROW)
            for col, (_, row) in zip(cols, chunk.iterrows()):
                region = int(row["Region"])
                is_sel = region in st.session_state.selected_regions
                img_path = SWATCH_DIR / f"CT_{region}.jpg"
                with col:
                    if img_path.exists():
                        st.image(str(img_path), width=SWATCH_SIZE)
                    else:
                        st.markdown(
                            f"<div style='width:{SWATCH_SIZE}px;height:{SWATCH_SIZE}px;"
                            f"background:#ddd;border-radius:4px;display:flex;align-items:center;"
                            f"justify-content:center;font-size:11px;'>no img</div>",
                            unsafe_allow_html=True,
                        )
                    btn_label = f"✓ {region}" if is_sel else f"+ {region}"
                    if st.button(btn_label, key=f"sel_{region}", use_container_width=True,
                                 type="primary" if is_sel else "secondary"):
                        if is_sel:
                            st.session_state.selected_regions.discard(region)
                        else:
                            st.session_state.selected_regions.add(region)
                        st.rerun()

        st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

    st.divider()

    # Download section
    selected = sorted(st.session_state.selected_regions)
    st.subheader(f"Selected: {len(selected)} region(s)")

    if selected:
        result_df = df[df["Region"].isin(selected)][["Region", "Reflet 1", "Reflet 2"]].sort_values("Region")
        st.dataframe(result_df, use_container_width=True)
        csv_bytes = result_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
            data=csv_bytes,
            file_name="selected_regions.csv",
            mime="text/csv",
        )
    else:
        st.info("No regions selected yet. Click a region button under any swatch to select it.")

# ── TAB 2 ──────────────────────────────────────────────────────────────────
with tab2:
    st.header("Deleted Regions")
    st.caption(f"{len(df_deleted)} regions where both Reflet 1 and Reflet 2 are 0.0 — marked for deletion.")

    COLS2 = 8
    rows2 = [df_deleted.iloc[i : i + COLS2] for i in range(0, len(df_deleted), COLS2)]

    for row in rows2:
        cols = st.columns(COLS2)
        for col, (_, r) in zip(cols, row.iterrows()):
            with col:
                region = int(r["Region"])
                img_path = SWATCH_DIR / f"CT_{region}.jpg"
                if img_path.exists():
                    st.image(str(img_path), width=80)
                else:
                    st.markdown("*(no img)*")
                st.caption(f"Region {region}")

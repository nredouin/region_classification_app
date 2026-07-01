import io
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="US Region Label Analyzer", layout="wide")

SWATCH_DIR = Path("data/CT_individual_swatches_V2")
EXCEL_PATH = "labeled_regions_us.xlsx"
SWATCH_SIZE = 110
REF_SIZE = 80
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


def group_header(r1: str, r2: str, n: int):
    st.markdown(
        f"<div style='background:#dde3f0;border-left:4px solid #2c6fad;padding:6px 12px;"
        f"border-radius:4px;font-weight:600;font-size:15px;margin-bottom:4px;color:#1a1a2e;'>"
        f"Reflet 1: <span style='color:#1a4f8a'>{r1}</span> &nbsp;|&nbsp; "
        f"Reflet 2: <span style='color:#1a4f8a'>{r2}</span> "
        f"<span style='font-weight:400;color:#444;font-size:13px;'>({n} region{'s' if n > 1 else ''})</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def show_swatch(region: int, size: int):
    img_path = SWATCH_DIR / f"CT_{region}.jpg"
    if img_path.exists():
        st.image(str(img_path), width=size)
    else:
        st.markdown(
            f"<div style='width:{size}px;height:{size}px;background:#ddd;border-radius:4px;"
            f"display:flex;align-items:center;justify-content:center;font-size:11px;'>no img</div>",
            unsafe_allow_html=True,
        )


def sorted_group_keys(source_df: pd.DataFrame):
    keys = (
        source_df.groupby(["Reflet 1", "Reflet 2"], sort=False)
        .size()
        .reset_index(name="n")[["Reflet 1", "Reflet 2"]]
        .values.tolist()
    )
    keys.sort(key=lambda k: (sort_key(k[0]), sort_key(k[1])))
    return keys


# ── Data ───────────────────────────────────────────────────────────────────
df = load_data()
deleted_mask = (df["Reflet 1"] == "0.0") & (df["Reflet 2"] == "0.0")
df_active = df[~deleted_mask].reset_index(drop=True)
df_deleted = df[deleted_mask].reset_index(drop=True)

# ── Session state ──────────────────────────────────────────────────────────
if "selected_regions" not in st.session_state:
    st.session_state.selected_regions = set()   # regions to keep (Step 1)
if "region_mapping" not in st.session_state:
    st.session_state.region_mapping = {}         # {left_region: kept_region} (Step 2)

tab1, tab2, tab3 = st.tabs(["Step 1 — Select regions to keep", "Step 2 — Map remaining regions", "Deleted regions"])

# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — Select regions to keep
# ══════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("Step 1 — Select the regions you want to keep")
    st.caption(
        f"{len(df_active)} active regions grouped by Reflet combination. "
        "Select the ones to keep, then go to Step 2 to map the rest."
    )

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

    for r1, r2 in sorted_group_keys(df_active):
        subset = df_active[(df_active["Reflet 1"] == r1) & (df_active["Reflet 2"] == r2)].reset_index(drop=True)
        group_header(r1, r2, len(subset))

        for chunk_start in range(0, len(subset), COLS_PER_ROW):
            chunk = subset.iloc[chunk_start : chunk_start + COLS_PER_ROW]
            cols = st.columns(COLS_PER_ROW)
            for col, (_, row) in zip(cols, chunk.iterrows()):
                region = int(row["Region"])
                is_sel = region in st.session_state.selected_regions
                with col:
                    show_swatch(region, SWATCH_SIZE)
                    if st.button(
                        f"✓ {region}" if is_sel else f"+ {region}",
                        key=f"s1_{region}",
                        use_container_width=True,
                        type="primary" if is_sel else "secondary",
                    ):
                        if is_sel:
                            st.session_state.selected_regions.discard(region)
                        else:
                            st.session_state.selected_regions.add(region)
                        st.rerun()

        st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

    st.divider()
    kept = sorted(st.session_state.selected_regions)
    st.subheader(f"Kept so far: {len(kept)} region(s)")
    if kept:
        st.dataframe(
            df[df["Region"].isin(kept)][["Region", "Reflet 1", "Reflet 2"]].sort_values("Region"),
            use_container_width=True,
        )

# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — Map remaining regions to a kept region
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("Step 2 — Map remaining regions to their closest kept region")

    kept_set = st.session_state.selected_regions
    left_df = df_active[~df_active["Region"].isin(kept_set)].reset_index(drop=True)

    if not kept_set:
        st.warning("No regions selected yet. Go to Step 1 and select the regions you want to keep.")
    elif left_df.empty:
        st.success("All active regions are kept — nothing left to map.")
    else:
        st.caption(
            f"{len(left_df)} remaining region(s). For each one, choose which kept region "
            "with the same Reflet combination it is most similar to."
        )

        # Pre-build kept lookup: (r1,r2) → list of region ints
        kept_rows = df_active[df_active["Region"].isin(kept_set)]
        kept_by_reflet = {}
        for _, krow in kept_rows.iterrows():
            key = (krow["Reflet 1"], krow["Reflet 2"])
            kept_by_reflet.setdefault(key, []).append(int(krow["Region"]))

        for r1, r2 in sorted_group_keys(left_df):
            subset = left_df[(left_df["Reflet 1"] == r1) & (left_df["Reflet 2"] == r2)].reset_index(drop=True)
            group_header(r1, r2, len(subset))

            kept_options = kept_by_reflet.get((r1, r2), [])

            if not kept_options:
                st.warning(f"No kept region has Reflet 1={r1} / Reflet 2={r2}. These regions cannot be mapped.")
                st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)
                continue

            # Show kept reference swatches once per group
            st.markdown(
                "<div style='font-size:12px;color:#555;margin-bottom:2px;'>Kept reference regions:</div>",
                unsafe_allow_html=True,
            )
            ref_cols = st.columns(min(len(kept_options), COLS_PER_ROW))
            for col, kreg in zip(ref_cols, kept_options):
                with col:
                    show_swatch(kreg, REF_SIZE)
                    st.caption(f"Region {kreg}")

            st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)

            # One row per left region: swatch + selectbox
            for _, row in subset.iterrows():
                region = int(row["Region"])
                current = st.session_state.region_mapping.get(region)
                default_idx = kept_options.index(current) if current in kept_options else 0

                lcol, rcol = st.columns([1, 5])
                with lcol:
                    show_swatch(region, SWATCH_SIZE)
                    st.caption(f"Region {region}")
                with rcol:
                    st.markdown(
                        f"<div style='margin-top:30px;font-size:13px;color:#333;'>Most similar to:</div>",
                        unsafe_allow_html=True,
                    )
                    chosen = st.selectbox(
                        f"Region {region} → most similar kept region",
                        options=kept_options,
                        index=default_idx,
                        format_func=lambda x: f"Region {x}",
                        key=f"map_{region}",
                        label_visibility="collapsed",
                    )
                    st.session_state.region_mapping[region] = chosen

            st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

        st.divider()

        # Download Excel with two sheets
        kept_list = sorted(kept_set)
        sheet1 = df[df["Region"].isin(kept_list)][["Region", "Reflet 1", "Reflet 2"]].sort_values("Region")

        mapped_left = {r: st.session_state.region_mapping.get(r) for r in left_df["Region"].tolist()}
        mapped_left = {r: k for r, k in mapped_left.items() if k is not None}

        if mapped_left:
            sheet2_rows = []
            for left_reg, kept_reg in sorted(mapped_left.items()):
                lrow = df[df["Region"] == left_reg].iloc[0]
                sheet2_rows.append({
                    "Region": left_reg,
                    "Reflet 1": lrow["Reflet 1"],
                    "Reflet 2": lrow["Reflet 2"],
                    "Most Similar Kept Region": kept_reg,
                })
            sheet2 = pd.DataFrame(sheet2_rows)
        else:
            sheet2 = pd.DataFrame(columns=["Region", "Reflet 1", "Reflet 2", "Most Similar Kept Region"])

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            sheet1.to_excel(writer, sheet_name="Kept Regions", index=False)
            sheet2.to_excel(writer, sheet_name="Mapped Regions", index=False)
        buf.seek(0)

        unmapped = len(left_df) - len(mapped_left)
        if unmapped:
            st.info(f"{unmapped} region(s) with no kept match in same Reflet group are excluded from Sheet 2.")

        st.download_button(
            label="Download Excel (2 sheets)",
            data=buf,
            file_name="region_mapping.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — Deleted regions
# ══════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("Deleted Regions")
    st.caption(f"{len(df_deleted)} regions where both Reflet 1 and Reflet 2 are 0.0 — marked for deletion.")

    COLS3 = 10
    for chunk_start in range(0, len(df_deleted), COLS3):
        chunk = df_deleted.iloc[chunk_start : chunk_start + COLS3]
        cols = st.columns(COLS3)
        for col, (_, r) in zip(cols, chunk.iterrows()):
            region = int(r["Region"])
            with col:
                show_swatch(region, 90)
                st.caption(f"Region {region}")

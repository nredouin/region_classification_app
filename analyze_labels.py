import io
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="US Region Label Analyzer", layout="wide")

SWATCH_DIR = Path("data/CT_individual_swatches_V2")
EXCEL_PATH = "labeled_regions_us.xlsx"
SWATCH_SIZE = 100
REF_SIZE = 75
COLS_PER_ROW = 6

REFLET_OPTIONS = ["0.0", "1.0", "2.0", "3.0", "4.0", "5.0", "6.0", "7.0", "8.0", "Fonda"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def sort_key(val: str) -> float:
    try:
        return float(val)
    except ValueError:
        return 99.0


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Reflet 1"] = df["Reflet 1"].astype(str).str.strip()
    df["Reflet 2"] = df["Reflet 2"].astype(str).str.strip()
    if "DMI Name" not in df.columns:
        df["DMI Name"] = ""
    else:
        df["DMI Name"] = df["DMI Name"].fillna("").astype(str)
        df.loc[df["DMI Name"].isin(["nan", "None"]), "DMI Name"] = ""
    if "Famille Lp Name" not in df.columns:
        df["Famille Lp Name"] = ""
    else:
        df["Famille Lp Name"] = df["Famille Lp Name"].fillna("").astype(str)
        df.loc[df["Famille Lp Name"].isin(["nan", "None"]), "Famille Lp Name"] = ""
    return df


def save_df():
    st.session_state.df.to_excel(EXCEL_PATH, index=False)


def sorted_group_keys(source_df: pd.DataFrame) -> list:
    keys = (
        source_df.groupby(["Reflet 1", "Reflet 2"], sort=False)
        .size()
        .reset_index(name="n")[["Reflet 1", "Reflet 2"]]
        .values.tolist()
    )
    keys.sort(key=lambda k: (sort_key(k[0]), sort_key(k[1])))
    return keys


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


def swatch_caption(row) -> str:
    dmi = str(row.get("DMI Name", "")).strip()
    if dmi and dmi not in ("", "nan", "None"):
        return dmi
    return ""


def get_dmi_options() -> list:
    names = st.session_state.df["DMI Name"].unique()
    return sorted({str(n) for n in names if n and str(n) not in ("", "nan", "None")})


def get_group_dmi(subset: pd.DataFrame) -> str:
    """Return the DMI name shared by the group, or '—' if none/mixed."""
    vals = [v for v in subset["DMI Name"].unique() if v and v not in ("", "nan", "None")]
    return vals[0] if len(vals) == 1 else "—"


# ── Callbacks ─────────────────────────────────────────────────────────────────

def on_r1_change(region):
    new_val = st.session_state[f"r1_{region}"]
    df = st.session_state.df
    idx = df[df["Region"] == region].index[0]
    df.at[idx, "Reflet 1"] = new_val
    st.session_state.selected_regions.discard(region)
    save_df()


def on_r2_change(region):
    new_val = st.session_state[f"r2_{region}"]
    df = st.session_state.df
    idx = df[df["Region"] == region].index[0]
    df.at[idx, "Reflet 2"] = new_val
    st.session_state.selected_regions.discard(region)
    save_df()


def on_grp_dmi_change(r1, r2):
    val = st.session_state[f"grp_dmi_{r1}_{r2}"]
    if val in ("—", "✏️ New..."):
        return
    mask = (st.session_state.df["Reflet 1"] == r1) & (st.session_state.df["Reflet 2"] == r2)
    st.session_state.df.loc[mask, "DMI Name"] = val
    save_df()


def on_grp_dmi_new_change(r1, r2):
    val = st.session_state.get(f"grp_dmi_new_{r1}_{r2}", "").strip()
    if not val:
        return
    mask = (st.session_state.df["Reflet 1"] == r1) & (st.session_state.df["Reflet 2"] == r2)
    st.session_state.df.loc[mask, "DMI Name"] = val
    save_df()


# ── Session state init ────────────────────────────────────────────────────────

if "df" not in st.session_state:
    st.session_state.df = clean_df(pd.read_excel(EXCEL_PATH))
if "selected_regions" not in st.session_state:
    st.session_state.selected_regions = set()
if "region_mapping" not in st.session_state:
    st.session_state.region_mapping = {}


# ── Sidebar: import / export ──────────────────────────────────────────────────

with st.sidebar:
    st.header("Import / Export")

    uploaded = st.file_uploader("Resume from exported Excel", type=["xlsx"])
    upload_id = f"{uploaded.name}_{uploaded.size}" if uploaded is not None else None
    if uploaded is not None and st.session_state.get("_last_upload_id") != upload_id:
        st.session_state["_last_upload_id"] = upload_id
        st.session_state.df = clean_df(pd.read_excel(uploaded))
        st.session_state.selected_regions = set()
        st.session_state.region_mapping = {}
        save_df()
        st.success("File loaded — session reset.")
        st.rerun()

    st.divider()

    buf_exp = io.BytesIO()
    st.session_state.df.to_excel(buf_exp, index=False)
    buf_exp.seek(0)
    st.download_button(
        "⬇ Export current state",
        data=buf_exp,
        file_name="labeled_regions_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── Derived views ─────────────────────────────────────────────────────────────

df = st.session_state.df
deleted_mask = (df["Reflet 1"] == "0.0") & (df["Reflet 2"] == "0.0")
df_active = df[~deleted_mask].reset_index(drop=True)
df_deleted = df[deleted_mask].reset_index(drop=True)

tab1, tab2, tab3 = st.tabs(["Step 1 — Select to keep", "Step 2 — Map remaining", "Deleted regions"])


# ══ TAB 1 ════════════════════════════════════════════════════════════════════

with tab1:
    st.header("Step 1 — Select regions to keep")
    st.caption(
        f"{len(df_active)} active regions grouped by Reflet combination. "
        "Edit R1 / R2 and DMI inline — all changes auto-save. "
        "Setting R1=0.0 and R2=0.0 moves a region to Deleted and resets its selection."
    )

    ca, cb, _ = st.columns([2, 2, 8])
    with ca:
        if st.button("Select all"):
            st.session_state.selected_regions.update(df_active["Region"].tolist())
            st.rerun()
    with cb:
        if st.button("Clear selection"):
            st.session_state.selected_regions.clear()
            st.rerun()

    st.divider()

    missing_dmi = df_active[df_active["DMI Name"].isin(["", "nan", "None"]) | (df_active["DMI Name"] == "")]
    if not missing_dmi.empty:
        st.warning(
            f"{len(missing_dmi)} active region(s) have no DMI name: "
            + ", ".join(str(r) for r in sorted(missing_dmi["Region"].tolist()))
        )

    for r1, r2 in sorted_group_keys(df_active):
        subset = df_active[
            (df_active["Reflet 1"] == r1) & (df_active["Reflet 2"] == r2)
        ].reset_index(drop=True)
        n = len(subset)
        group_header(r1, r2, n)

        # ── Group-level DMI assignment ────────────────────────────────────────
        dmi_opts_grp = ["—"] + get_dmi_options() + ["✏️ New..."]
        current_grp_dmi = get_group_dmi(subset)
        grp_dmi_idx = dmi_opts_grp.index(current_grp_dmi) if current_grp_dmi in dmi_opts_grp else 0

        ga, gb, _ = st.columns([3, 3, 6])
        with ga:
            grp_dmi_sel = st.selectbox(
                "DMI for group",
                options=dmi_opts_grp,
                index=grp_dmi_idx,
                key=f"grp_dmi_{r1}_{r2}",
                label_visibility="collapsed",
                on_change=on_grp_dmi_change,
                args=(r1, r2),
            )
        with gb:
            if grp_dmi_sel == "✏️ New...":
                st.text_input(
                    "New DMI",
                    key=f"grp_dmi_new_{r1}_{r2}",
                    label_visibility="collapsed",
                    placeholder="Type new DMI name and press Enter…",
                    on_change=on_grp_dmi_new_change,
                    args=(r1, r2),
                )

        st.markdown("<div style='margin-bottom:4px;'></div>", unsafe_allow_html=True)

        # ── Swatch grid ───────────────────────────────────────────────────────
        for chunk_start in range(0, n, COLS_PER_ROW):
            chunk = subset.iloc[chunk_start : chunk_start + COLS_PER_ROW]
            cols = st.columns(COLS_PER_ROW)
            for col, (_, row) in zip(cols, chunk.iterrows()):
                region = int(row["Region"])
                is_sel = region in st.session_state.selected_regions

                cur_r1 = str(row["Reflet 1"])
                cur_r2 = str(row["Reflet 2"])
                r1_idx = REFLET_OPTIONS.index(cur_r1) if cur_r1 in REFLET_OPTIONS else 0
                r2_idx = REFLET_OPTIONS.index(cur_r2) if cur_r2 in REFLET_OPTIONS else 0

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

                    cap = swatch_caption(row)
                    if cap:
                        st.caption(cap)

                    st.selectbox("Reflet 1", REFLET_OPTIONS, index=r1_idx,
                                 key=f"r1_{region}", on_change=on_r1_change, args=(region,))
                    st.selectbox("Reflet 2", REFLET_OPTIONS, index=r2_idx,
                                 key=f"r2_{region}", on_change=on_r2_change, args=(region,))

        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

    st.divider()
    kept_list = sorted(st.session_state.selected_regions)
    st.subheader(f"Kept so far: {len(kept_list)} region(s)")
    if kept_list:
        show_cols = [c for c in ["Region", "Reflet 1", "Reflet 2", "Famille Lp Name", "DMI Name"]
                     if c in st.session_state.df.columns]
        st.dataframe(
            st.session_state.df[st.session_state.df["Region"].isin(kept_list)][show_cols]
            .sort_values("Region"),
            use_container_width=True,
        )


# ══ TAB 2 ════════════════════════════════════════════════════════════════════

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
            f"{len(left_df)} remaining region(s). For each one, pick the kept region "
            "with the same Reflet combination it resembles most."
        )

        kept_rows = df_active[df_active["Region"].isin(kept_set)]
        kept_by_reflet: dict = {}
        for _, krow in kept_rows.iterrows():
            key = (krow["Reflet 1"], krow["Reflet 2"])
            kept_by_reflet.setdefault(key, []).append(int(krow["Region"]))

        for r1, r2 in sorted_group_keys(left_df):
            subset = left_df[
                (left_df["Reflet 1"] == r1) & (left_df["Reflet 2"] == r2)
            ].reset_index(drop=True)
            group_header(r1, r2, len(subset))

            kept_options = kept_by_reflet.get((r1, r2), [])
            if not kept_options:
                st.warning(f"No kept region has Reflet 1={r1} / Reflet 2={r2}. Cannot map these regions.")
                st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)
                continue

            st.markdown(
                "<div style='font-size:12px;color:#555;margin-bottom:2px;'>Kept reference regions:</div>",
                unsafe_allow_html=True,
            )
            ref_cols = st.columns(min(len(kept_options), COLS_PER_ROW))
            for col, kreg in zip(ref_cols, kept_options):
                krow = df_active[df_active["Region"] == kreg].iloc[0]
                with col:
                    show_swatch(kreg, REF_SIZE)
                    kcap = swatch_caption(krow)
                    st.caption(f"Region {kreg}" + (f"\n{kcap}" if kcap else ""))

            st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)

            for _, row in subset.iterrows():
                region = int(row["Region"])
                current = st.session_state.region_mapping.get(region)
                default_idx = kept_options.index(current) if current in kept_options else 0

                lcol, rcol = st.columns([1, 5])
                with lcol:
                    show_swatch(region, SWATCH_SIZE)
                    cap = swatch_caption(row)
                    st.caption(f"Region {region}" + (f"\n{cap}" if cap else ""))
                with rcol:
                    st.markdown(
                        "<div style='margin-top:30px;font-size:13px;color:#333;'>Most similar to:</div>",
                        unsafe_allow_html=True,
                    )
                    chosen = st.selectbox(
                        f"Region {region}",
                        options=kept_options,
                        index=default_idx,
                        format_func=lambda x: f"Region {x}",
                        key=f"map_{region}",
                        label_visibility="collapsed",
                    )
                    st.session_state.region_mapping[region] = chosen

            st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

        st.divider()

        # Build two-sheet Excel
        kept_list2 = sorted(kept_set)
        out_cols = [c for c in ["Region", "Reflet 1", "Reflet 2", "Famille Lp Name", "DMI Name"]
                    if c in st.session_state.df.columns]
        sheet1 = (
            st.session_state.df[st.session_state.df["Region"].isin(kept_list2)][out_cols]
            .sort_values("Region")
        )

        mapped = {r: st.session_state.region_mapping.get(r) for r in left_df["Region"]}
        mapped = {r: k for r, k in mapped.items() if k is not None}

        sheet2_rows = []
        for left_reg, kept_reg in sorted(mapped.items()):
            lrow = st.session_state.df[st.session_state.df["Region"] == left_reg].iloc[0]
            entry = {
                "Region": left_reg,
                "Reflet 1": lrow["Reflet 1"],
                "Reflet 2": lrow["Reflet 2"],
                "Most Similar Kept Region": kept_reg,
            }
            if "Famille Lp Name" in lrow.index:
                entry["Famille Lp Name"] = lrow["Famille Lp Name"]
            if "DMI Name" in lrow.index:
                entry["DMI Name"] = lrow["DMI Name"]
            sheet2_rows.append(entry)

        sheet2 = pd.DataFrame(sheet2_rows) if sheet2_rows else pd.DataFrame(
            columns=["Region", "Reflet 1", "Reflet 2", "Most Similar Kept Region", "Famille Lp Name", "DMI Name"]
        )

        del_cols = [c for c in ["Region", "Reflet 1", "Reflet 2", "Famille Lp Name", "DMI Name"]
                    if c in st.session_state.df.columns]
        sheet3 = df_deleted[del_cols].sort_values("Region") if not df_deleted.empty else pd.DataFrame(columns=del_cols)

        buf2 = io.BytesIO()
        with pd.ExcelWriter(buf2, engine="openpyxl") as writer:
            sheet1.to_excel(writer, sheet_name="Kept Regions", index=False)
            sheet2.to_excel(writer, sheet_name="Mapped Regions", index=False)
            sheet3.to_excel(writer, sheet_name="Deleted Regions", index=False)
        buf2.seek(0)

        unmapped = len(left_df) - len(mapped)
        if unmapped:
            st.info(f"{unmapped} region(s) with no kept match for their Reflet group are excluded from Sheet 2.")

        st.download_button(
            "⬇ Download Excel (2 sheets)",
            data=buf2,
            file_name="region_mapping.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# ══ TAB 3 ════════════════════════════════════════════════════════════════════

with tab3:
    st.header("Deleted Regions")
    st.caption(
        f"{len(df_deleted)} regions where both Reflet 1 and Reflet 2 are 0.0. "
        "Assign new Reflet values to restore a region to the active pool."
    )

    COLS3 = COLS_PER_ROW
    for chunk_start in range(0, len(df_deleted), COLS3):
        chunk = df_deleted.iloc[chunk_start : chunk_start + COLS3]
        cols = st.columns(COLS3)
        for col, (_, r) in zip(cols, chunk.iterrows()):
            region = int(r["Region"])
            cur_r1 = str(r["Reflet 1"])
            cur_r2 = str(r["Reflet 2"])
            r1_idx = REFLET_OPTIONS.index(cur_r1) if cur_r1 in REFLET_OPTIONS else 0
            r2_idx = REFLET_OPTIONS.index(cur_r2) if cur_r2 in REFLET_OPTIONS else 0
            with col:
                show_swatch(region, 90)
                cap = swatch_caption(r)
                st.caption(f"Region {region}" + (f"\n{cap}" if cap else ""))
                st.selectbox("Reflet 1", REFLET_OPTIONS, index=r1_idx,
                             key=f"r1_{region}", on_change=on_r1_change, args=(region,))
                st.selectbox("Reflet 2", REFLET_OPTIONS, index=r2_idx,
                             key=f"r2_{region}", on_change=on_r2_change, args=(region,))

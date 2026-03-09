import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TLDR Newsletter Analytics",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── TLDR brand palette (matched from logo) ────────────────────────────────────
BLUE   = "#5BB4E5"   # T — cornflower blue
YELLOW = "#EFC040"   # L — warm gold
GREEN  = "#7DC49A"   # D — sage green
RED    = "#D97272"   # R — coral red

ACCENT_COLORS = [BLUE, YELLOW, GREEN, RED,
                 "#9B8AE0", "#5CC8B8", "#F59E0B", "#60A5FA", "#34D399", "#F87171"]

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#0D0D0D",
    plot_bgcolor="#111111",
    font_color="#E0E0E0",
    margin=dict(l=0, r=10, t=30, b=0),
    legend=dict(bgcolor="rgba(0,0,0,0)", font_size=12),
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <style>
        /* KPI metric cards */
        [data-testid="metric-container"] {{
            background: #1A1A1A;
            border: 1px solid #2a2a2a;
            border-radius: 10px;
            padding: 14px 18px;
        }}
        [data-testid="stMetricValue"] {{
            font-size: 1.85rem;
            font-weight: 700;
        }}
        [data-testid="stMetricLabel"] {{
            color: #888;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        /* Sidebar */
        [data-testid="stSidebar"] {{
            background: #111111;
        }}
        /* Expander styling */
        [data-testid="stExpander"] {{
            background: #1A1A1A;
            border: 1px solid #2a2a2a !important;
            border-radius: 8px;
            margin-bottom: 6px;
        }}
        [data-testid="stExpander"] summary {{
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.03em;
        }}
        /* Button row inside expander */
        .filter-btn button {{
            font-size: 0.72rem;
            padding: 2px 8px;
            border-radius: 4px;
        }}
        /* Checkbox items */
        [data-testid="stCheckbox"] label {{
            font-size: 0.82rem;
        }}
        hr {{
            border-color: #2a2a2a !important;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE         = Path(__file__).parent / "csv"
CSV_PATH     = BASE / "article_grain.csv"
AUTHORS_PATH = BASE / "authors.csv"


# ── Data loaders ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv(CSV_PATH)
    df["email_date"]      = pd.to_datetime(df["email_date"], utc=True, errors="coerce")
    df["published_date"]  = pd.to_datetime(df["published_date"], errors="coerce")
    df["email_date_only"] = df["email_date"].dt.date
    df["read_minutes"]    = pd.to_numeric(df["read_minutes"], errors="coerce")
    df["word_count"]      = pd.to_numeric(df["word_count"], errors="coerce")
    df["is_sponsor"]      = pd.to_numeric(df["is_sponsor"], errors="coerce").fillna(0).astype(int)
    df["year_month"]      = df["email_date"].dt.to_period("M").astype(str)
    df["author_ids_list"] = (
        df["author_ids"].fillna("")
        .apply(lambda x: [a.strip() for a in str(x).split(",") if a.strip()])
    )
    return df


@st.cache_data
def load_authors():
    a = pd.read_csv(AUTHORS_PATH)
    a = a[a["name"].notna() & ~a["name"].str.strip().isin(["please click", ""])]
    return a.sort_values("name").reset_index(drop=True)


df      = load_data()
authors = load_authors()
author_map = {str(r["id"]): r["name"] for _, r in authors.iterrows()}


# ── Checkbox filter helper ────────────────────────────────────────────────────
def checkbox_filter(label, options, key_prefix, default_checked=True):
    """
    Renders a collapsible expander with a checkbox per option plus
    Select All / Clear All buttons. Returns list of selected options.
    Falls back to all options when nothing is selected.
    """
    # Seed defaults only on first render
    for opt in options:
        sk = f"{key_prefix}__{opt}"
        if sk not in st.session_state:
            st.session_state[sk] = default_checked

    n_sel = sum(bool(st.session_state.get(f"{key_prefix}__{opt}", default_checked))
                for opt in options)

    with st.expander(f"{label}   {n_sel} / {len(options)} selected"):
        # ── Select All / Clear All buttons
        col_a, col_b = st.columns(2)
        if col_a.button("Select all", key=f"{key_prefix}__btn_all",
                        use_container_width=True):
            for opt in options:
                st.session_state[f"{key_prefix}__{opt}"] = True
        if col_b.button("Clear all", key=f"{key_prefix}__btn_clr",
                        use_container_width=True):
            for opt in options:
                st.session_state[f"{key_prefix}__{opt}"] = False

        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

        selected = []
        for opt in options:
            if st.checkbox(str(opt), key=f"{key_prefix}__{opt}"):
                selected.append(opt)

    # Empty selection = treat as "all" so the dashboard never goes blank
    return selected if selected else list(options)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f'<span style="font-size:2.4rem;font-weight:900;letter-spacing:-1px;">'
        f'<span style="color:{BLUE}">T</span>'
        f'<span style="color:{YELLOW}">L</span>'
        f'<span style="color:{GREEN}">D</span>'
        f'<span style="color:{RED}">R</span>'
        f'</span>',
        unsafe_allow_html=True,
    )
    st.caption("Newsletter Analytics")
    st.divider()

    # 1 ── Date range
    date_min = df["email_date_only"].min()
    date_max = df["email_date_only"].max()
    date_range = st.date_input(
        "Date range (email date)",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
    )

    # 2 ── Newsletter
    newsletters = sorted(df["newsletter_name"].dropna().unique())
    sel_newsletters = checkbox_filter("Newsletter", newsletters, "nl")

    # 3 ── Section
    sections = sorted(df["section_name"].dropna().unique())
    sel_sections = checkbox_filter("Section", sections, "sec")

    # 4 ── Media type
    media_types = sorted(df["media_type"].dropna().unique())
    sel_media = checkbox_filter("Media type", media_types, "mt")

    # 5 ── Authors  (additive: none selected = no author filter)
    all_author_names = authors["name"].tolist()
    sel_author_names = checkbox_filter(
        "Author", all_author_names, "auth", default_checked=False
    )
    # When all defaults are False and nothing checked → no author filter
    n_auth_checked = sum(
        bool(st.session_state.get(f"auth__{n}", False)) for n in all_author_names
    )
    author_filter_active = n_auth_checked > 0
    sel_author_ids = {k for k, v in author_map.items() if v in sel_author_names}

    st.divider()
    include_sponsors = st.checkbox("Include sponsor articles", value=True)


# ── Apply filters ─────────────────────────────────────────────────────────────
start_date, end_date = (
    (date_range[0], date_range[1]) if len(date_range) == 2 else (date_min, date_max)
)

mask = (
    df["newsletter_name"].isin(sel_newsletters)
    & df["section_name"].isin(sel_sections)
    & df["media_type"].isin(sel_media)
    & (df["email_date_only"] >= start_date)
    & (df["email_date_only"] <= end_date)
)
if not include_sponsors:
    mask &= df["is_sponsor"] == 0
if author_filter_active:
    mask &= df["author_ids_list"].apply(lambda ids: bool(set(ids) & sel_author_ids))

filtered = df[mask].copy()


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<span style="font-size:2rem;font-weight:800;">'
    f'<span style="color:{BLUE}">T</span>'
    f'<span style="color:{YELLOW}">L</span>'
    f'<span style="color:{GREEN}">D</span>'
    f'<span style="color:{RED}">R</span>'
    f' Newsletter Analytics</span>',
    unsafe_allow_html=True,
)
st.caption(f"Showing **{len(filtered):,}** articles · filtered from {len(df):,} total")

st.divider()

# ── KPI row ───────────────────────────────────────────────────────────────────
total_articles   = len(filtered)
total_issues     = filtered["issue_id"].nunique()
avg_per_issue    = round(total_articles / total_issues, 1) if total_issues else 0
sponsor_count    = int(filtered["is_sponsor"].sum())
sponsor_rate     = f"{sponsor_count / total_articles * 100:.1f}%" if total_articles else "—"
unique_sources   = filtered.loc[filtered["url_domain"].notna(), "url_domain"].nunique()
avg_read         = filtered["read_minutes"].mean()
avg_read_fmt     = f"{avg_read:.1f} min" if pd.notna(avg_read) else "—"

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("Articles",             f"{total_articles:,}")
c2.metric("Issues",               f"{total_issues:,}")
c3.metric("Avg Articles / Issue", f"{avg_per_issue:,}")
c4.metric("Sponsorship Rate",     sponsor_rate)
c5.metric("Unique Sources",       f"{unique_sources:,}")
c6.metric("Avg Read Time",        avg_read_fmt)
c7.metric("Newsletters",          f"{filtered['newsletter_name'].nunique()}")

st.divider()

# ── Row 1: Articles by newsletter + Articles over time ────────────────────────
col_l, col_r = st.columns([1, 2])

with col_l:
    st.subheader("Articles by newsletter")
    by_nl = (
        filtered.groupby("newsletter_name")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=True)
    )
    fig1 = px.bar(
        by_nl, x="count", y="newsletter_name", orientation="h",
        color="newsletter_name",
        color_discrete_sequence=ACCENT_COLORS,
        labels={"newsletter_name": "", "count": "Articles"},
    )
    fig1.update_layout(**PLOTLY_LAYOUT, showlegend=False)
    st.plotly_chart(fig1, use_container_width=True)

with col_r:
    st.subheader("Articles published over time")
    over_time = (
        filtered.groupby(["year_month", "newsletter_name"])
        .size()
        .reset_index(name="count")
    )
    fig2 = px.area(
        over_time, x="year_month", y="count", color="newsletter_name",
        color_discrete_sequence=ACCENT_COLORS,
        labels={"year_month": "Month", "count": "Articles", "newsletter_name": "Newsletter"},
    )
    fig2.update_xaxes(tickangle=-45)
    fig2.update_layout(**PLOTLY_LAYOUT)
    st.plotly_chart(fig2, use_container_width=True)

# ── Row 2: Section breakdown + Media type ────────────────────────────────────
col_l2, col_r2 = st.columns(2)

with col_l2:
    st.subheader("By section")
    by_section = (
        filtered.groupby("section_name")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(15)
    )
    fig3 = px.bar(
        by_section, x="section_name", y="count",
        color="section_name",
        color_discrete_sequence=ACCENT_COLORS,
        labels={"section_name": "", "count": "Articles"},
    )
    fig3.update_xaxes(tickangle=-40)
    fig3.update_layout(**PLOTLY_LAYOUT, showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

with col_r2:
    st.subheader("By media type")

    by_media_raw = (
        filtered.groupby("media_type")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    total_media = by_media_raw["count"].sum()
    by_media_raw["pct"] = by_media_raw["count"] / total_media * 100 if total_media else 0

    # Group slices under 3% into "Other"
    major = by_media_raw[by_media_raw["pct"] >= 3.0].copy()
    minor = by_media_raw[by_media_raw["pct"] < 3.0]
    if len(minor):
        other = pd.DataFrame([{
            "media_type": "Other",
            "count": minor["count"].sum(),
            "pct":   minor["pct"].sum(),
        }])
        by_media = pd.concat([major, other], ignore_index=True)
    else:
        by_media = major

    fig4 = px.pie(
        by_media, names="media_type", values="count",
        hole=0.45,
        color_discrete_sequence=ACCENT_COLORS,
    )
    fig4.update_traces(
        textposition="inside",
        textinfo="label+percent",
        textfont_color="#0D0D0D",
        textfont_size=12,
    )
    fig4.update_layout(
        **PLOTLY_LAYOUT,
        uniformtext_minsize=11,
        uniformtext_mode="hide",   # hide labels that can't fit inside their slice
    )
    st.plotly_chart(fig4, use_container_width=True)

# ── Row 3: Top domains + Day of week ─────────────────────────────────────────
col_l3, col_r3 = st.columns(2)

with col_l3:
    st.subheader("Top source domains")
    top_domains = (
        filtered[filtered["url_domain"].notna() & (filtered["is_sponsor"] == 0)]
        .groupby("url_domain")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(15)
    )
    fig5 = px.bar(
        top_domains, x="count", y="url_domain", orientation="h",
        color="count",
        color_continuous_scale=[[0, "#112233"], [1, BLUE]],
        labels={"url_domain": "", "count": "Articles"},
    )
    # Highest result at the top
    fig5.update_layout(
        **PLOTLY_LAYOUT,
        coloraxis_showscale=False,
        yaxis={"categoryorder": "total ascending"},
    )
    st.plotly_chart(fig5, use_container_width=True)

with col_r3:
    st.subheader("Publishing by day of week")
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    by_day = (
        filtered.groupby("day_of_week")
        .size()
        .reindex(day_order)
        .reset_index(name="count")
    )
    fig6 = px.bar(
        by_day, x="day_of_week", y="count",
        color="count",
        color_continuous_scale=[[0, "#2A1515"], [1, RED]],
        labels={"day_of_week": "", "count": "Articles"},
    )
    fig6.update_layout(**PLOTLY_LAYOUT, coloraxis_showscale=False)
    st.plotly_chart(fig6, use_container_width=True)

# ── Sponsorship rate over time ────────────────────────────────────────────────
st.subheader("Sponsorship rate over time")
spon_time = (
    filtered.groupby("year_month")
    .agg(total=("is_sponsor", "count"), sponsors=("is_sponsor", "sum"))
    .reset_index()
)
spon_time["rate"] = spon_time["sponsors"] / spon_time["total"] * 100

fig7 = px.line(
    spon_time, x="year_month", y="rate",
    labels={"year_month": "Month", "rate": "Sponsorship rate (%)"},
    color_discrete_sequence=[YELLOW],
)
fig7.update_traces(line_width=2, fill="tozeroy",
                   fillcolor=f"rgba(239,192,64,0.10)")
fig7.update_xaxes(tickangle=-45)
fig7.update_layout(**PLOTLY_LAYOUT)
st.plotly_chart(fig7, use_container_width=True)

# ── Article browser ───────────────────────────────────────────────────────────
st.divider()
st.subheader("Article browser")

search = st.text_input("Search titles / descriptions", placeholder="Type to filter…")

display_cols = [
    "email_date_only", "newsletter_name", "section_name",
    "title", "description", "media_type", "read_minutes",
    "is_sponsor", "url",
]
view = filtered[display_cols].copy()
view["email_date_only"] = view["email_date_only"].astype(str)

if search:
    s_mask = (
        view["title"].str.contains(search, case=False, na=False)
        | view["description"].str.contains(search, case=False, na=False)
    )
    view = view[s_mask]

st.caption(f"{len(view):,} articles")
st.dataframe(
    view.sort_values("email_date_only", ascending=False).reset_index(drop=True),
    use_container_width=True,
    height=480,
    column_config={
        "email_date_only": "Date",
        "newsletter_name": "Newsletter",
        "section_name":    "Section",
        "media_type":      "Type",
        "read_minutes":    st.column_config.NumberColumn("Read (min)", format="%d"),
        "is_sponsor":      st.column_config.CheckboxColumn("Sponsor"),
        "url":             st.column_config.LinkColumn("URL"),
    },
)

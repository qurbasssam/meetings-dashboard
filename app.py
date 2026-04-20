import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="T-Hub Meetings Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130, #252d3d);
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid #4f8ef7;
        margin: 5px 0;
    }
    .hot { border-left-color: #ff4b4b !important; }
    .warm { border-left-color: #ffa500 !important; }
    .cold { border-left-color: #4f8ef7 !important; }
    .stMetric label { font-size: 13px !important; color: #adb5bd !important; }
    .block-container { padding-top: 1rem; }
    h1 { color: #ffffff; font-size: 2rem !important; }
    h2, h3 { color: #e0e0e0; }
    .sidebar .sidebar-content { background-color: #1e2130; }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# GOOGLE SHEETS — TAB NAMES (EXACT MATCH)
# ─────────────────────────────────────────────
Q1_SHEETS = [
    "Corporate Innovation Meetings",
    "Delivery XDC Stealth AI Outreach",
    "Delivery Kotak Outreach",
    "Delivery Kotak Roadshow",
    "Delivery Youth Co Lab",
    "Delivery Honda Outreach",
    "Funding Telangana Founders Day",
]

# ─────────────────────────────────────────────
# LOAD DATA FROM GOOGLE SHEETS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_all_sheets():
    conn = st.connection("gsheets", type=GSheetsConnection)
    all_dfs = []
    sheet_dfs = {}

    for sheet in Q1_SHEETS:
        try:
            df = conn.read(worksheet=sheet, usecols=list(range(20)), ttl=300)
            df = df.dropna(how="all")
            if not df.empty:
                df["Sheet"] = sheet
                df["Quarter"] = "Q1"
                # Detect category from sheet name
                if "Innovation" in sheet:
                    df["Category"] = "Corporate Innovation"
                elif "Delivery" in sheet:
                    df["Category"] = "Delivery"
                elif "Funding" in sheet:
                    df["Category"] = "Funding"
                else:
                    df["Category"] = "Other"
                all_dfs.append(df)
                sheet_dfs[sheet] = df
        except Exception as e:
            st.warning(f"⚠️ Could not load sheet: **{sheet}** — {e}")

    combined = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    return combined, sheet_dfs

# ─────────────────────────────────────────────
# COLUMN DETECTION HELPER
# ─────────────────────────────────────────────
def find_col(df, keywords):
    """Find column by partial keyword match (case-insensitive)."""
    for col in df.columns:
        for kw in keywords:
            if kw.lower() in str(col).lower():
                return col
    return None

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("# 🚀 T-Hub Meetings Dashboard")
st.markdown("**Real-time insights across all outreach, delivery & funding activities**")
st.markdown("---")

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
with st.spinner("📊 Loading data from Google Sheets..."):
    df_all, sheet_dfs = load_all_sheets()

if df_all.empty:
    st.error("❌ No data loaded. Please check your Google Sheet tab names and connection.")
    st.stop()

# ─────────────────────────────────────────────
# SIDEBAR FILTERS
# ─────────────────────────────────────────────
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/T-Hub_Logo.svg/200px-T-Hub_Logo.svg.png", width=150)
st.sidebar.markdown("## 🎛️ Filters")

# Quarter filter
quarters = ["All", "Q1"]
selected_quarter = st.sidebar.selectbox("📅 Quarter", quarters)

# Category filter
categories = ["All"] + sorted(df_all["Category"].dropna().unique().tolist())
selected_category = st.sidebar.selectbox("🏷️ Category", categories)

# Sheet filter
sheets_available = ["All"] + sorted(df_all["Sheet"].dropna().unique().tolist())
selected_sheet = st.sidebar.selectbox("📋 Sheet / Program", sheets_available)

# ─────────────────────────────────────────────
# APPLY FILTERS
# ─────────────────────────────────────────────
df = df_all.copy()
if selected_quarter != "All":
    df = df[df["Quarter"] == selected_quarter]
if selected_category != "All":
    df = df[df["Category"] == selected_category]
if selected_sheet != "All":
    df = df[df["Sheet"] == selected_sheet]

# ─────────────────────────────────────────────
# DETECT KEY COLUMNS DYNAMICALLY
# ─────────────────────────────────────────────
col_status     = find_col(df, ["status", "lead status", "stage"])
col_meeting    = find_col(df, ["meeting type", "type", "in person", "virtual", "mode"])
col_email      = find_col(df, ["email", "email sent", "outreach"])
col_company    = find_col(df, ["company", "organisation", "organization", "name"])
col_contacted  = find_col(df, ["contacted", "contact", "reached"])
col_date       = find_col(df, ["date", "meeting date", "scheduled"])
col_attended   = find_col(df, ["attended", "showed", "show"])
col_confirmed  = find_col(df, ["confirmed", "booked", "accepted"])
col_response   = find_col(df, ["response", "reply", "replied"])

# ─────────────────────────────────────────────
# KPI CALCULATIONS
# ─────────────────────────────────────────────
total_rows     = len(df)
total_sheets   = df["Sheet"].nunique()

# Meetings booked / confirmed
total_confirmed = 0
if col_confirmed:
    total_confirmed = df[col_confirmed].apply(
        lambda x: str(x).lower() in ["yes", "confirmed", "booked", "true", "1"]
    ).sum()

# Attended / showed up
total_attended = 0
if col_attended:
    total_attended = df[col_attended].apply(
        lambda x: str(x).lower() in ["yes", "attended", "showed", "true", "1"]
    ).sum()

# Hot / Warm / Cold
hot_count = warm_count = cold_count = 0
if col_status:
    statuses = df[col_status].astype(str).str.lower()
    hot_count  = statuses.str.contains("hot").sum()
    warm_count = statuses.str.contains("warm").sum()
    cold_count = statuses.str.contains("cold").sum()

# In-Person vs Virtual
inperson_count = virtual_count = 0
if col_meeting:
    modes = df[col_meeting].astype(str).str.lower()
    inperson_count = modes.str.contains("in.person|in person|physical|offline").sum()
    virtual_count  = modes.str.contains("virtual|online|zoom|teams|meet").sum()

# Emails sent
emails_sent = 0
if col_email:
    emails_sent = df[col_email].apply(
        lambda x: str(x).lower() in ["yes", "sent", "true", "1"]
    ).sum()

# ─────────────────────────────────────────────
# TOP KPI CARDS — ROW 1
# ─────────────────────────────────────────────
st.markdown("## 📊 Key Metrics Overview")
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.metric("📋 Total Records", f"{total_rows:,}")
with k2:
    st.metric("📁 Programs Tracked", f"{total_sheets}")
with k3:
    st.metric("✅ Meetings Confirmed", f"{int(total_confirmed):,}")
with k4:
    st.metric("👥 Meetings Attended", f"{int(total_attended):,}")
with k5:
    show_rate = round((total_attended / total_confirmed * 100), 1) if total_confirmed > 0 else 0
    st.metric("📈 Show Rate", f"{show_rate}%")

st.markdown("---")

# ─────────────────────────────────────────────
# TOP KPI CARDS — ROW 2
# ─────────────────────────────────────────────
k6, k7, k8, k9, k10 = st.columns(5)
with k6:
    st.metric("🔥 Hot Leads",  f"{int(hot_count):,}")
with k7:
    st.metric("🟠 Warm Leads", f"{int(warm_count):,}")
with k8:
    st.metric("🔵 Cold Leads", f"{int(cold_count):,}")
with k9:
    st.metric("🏢 In-Person",  f"{int(inperson_count):,}")
with k10:
    st.metric("💻 Virtual",    f"{int(virtual_count):,}")

st.markdown("---")

# ─────────────────────────────────────────────
# CHARTS SECTION
# ─────────────────────────────────────────────
st.markdown("## 📈 Visual Insights")

chart_col1, chart_col2 = st.columns(2)

# ── Chart 1: Records by Program ──
with chart_col1:
    st.markdown("### 📁 Meetings by Program")
    sheet_counts = df.groupby("Sheet").size().reset_index(name="Count")
    sheet_counts = sheet_counts.sort_values("Count", ascending=True)
    fig1 = px.bar(
        sheet_counts, x="Count", y="Sheet", orientation="h",
        color="Count", color_continuous_scale="Blues",
        template="plotly_dark"
    )
    fig1.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False, height=350,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="", xaxis_title="Count"
    )
    st.plotly_chart(fig1, use_container_width=True)

# ── Chart 2: Hot / Warm / Cold Funnel ──
with chart_col2:
    st.markdown("### 🎯 Lead Status Funnel")
    if col_status and (hot_count + warm_count + cold_count) > 0:
        funnel_data = pd.DataFrame({
            "Status": ["🔥 Hot", "🟠 Warm", "🔵 Cold"],
            "Count": [hot_count, warm_count, cold_count]
        })
        fig2 = px.funnel(
            funnel_data, x="Count", y="Status",
            color_discrete_sequence=["#ff4b4b", "#ffa500", "#4f8ef7"],
            template="plotly_dark"
        )
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=350,
            margin=dict(l=10, r=10, t=20, b=10)
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        # Pie chart fallback — breakdown by category
        cat_counts = df.groupby("Category").size().reset_index(name="Count")
        fig2 = px.pie(
            cat_counts, values="Count", names="Category",
            color_discrete_sequence=px.colors.sequential.Blues_r,
            template="plotly_dark", hole=0.4
        )
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            height=350,
            margin=dict(l=10, r=10, t=20, b=10)
        )
        st.plotly_chart(fig2, use_container_width=True)

# ── Chart 3: In-Person vs Virtual ──
chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    st.markdown("### 🏢 In-Person vs 💻 Virtual")
    if inperson_count > 0 or virtual_count > 0:
        mode_data = pd.DataFrame({
            "Mode": ["In-Person", "Virtual"],
            "Count": [inperson_count, virtual_count]
        })
        fig3 = px.pie(
            mode_data, values="Count", names="Mode",
            color_discrete_sequence=["#4f8ef7", "#7c3aed"],
            template="plotly_dark", hole=0.45
        )
        fig3.update_traces(textposition="inside", textinfo="percent+label")
        fig3.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            height=320,
            margin=dict(l=10, r=10, t=20, b=10),
            showlegend=True
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("💡 No 'Meeting Type' column found. Add a column named 'Meeting Type' with values 'In-Person' or 'Virtual' in your sheet.")

# ── Chart 4: Category Breakdown ──
with chart_col4:
    st.markdown("### 🏷️ Activity by Category")
    cat_sheet = df.groupby(["Category", "Sheet"]).size().reset_index(name="Count")
    fig4 = px.bar(
        cat_sheet, x="Category", y="Count", color="Sheet",
        barmode="stack", template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig4.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(font=dict(size=9))
    )
    st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# ─────────────────────────────────────────────
# SHEET-BY-SHEET BREAKDOWN
# ─────────────────────────────────────────────
st.markdown("## 📋 Program-Level Breakdown")

for sheet_name, sheet_df in sheet_dfs.items():
    if selected_sheet != "All" and sheet_name != selected_sheet:
        continue
    if selected_category != "All":
        cat = sheet_df["Category"].iloc[0] if "Category" in sheet_df.columns else ""
        if cat != selected_category:
            continue

    with st.expander(f"📂 {sheet_name}  —  {len(sheet_df)} records", expanded=False):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Total Records", len(sheet_df))
        with col_b:
            c = find_col(sheet_df, ["confirmed", "booked"])
            val = 0
            if c:
                val = sheet_df[c].apply(
                    lambda x: str(x).lower() in ["yes", "confirmed", "booked", "true", "1"]
                ).sum()
            st.metric("✅ Confirmed", int(val))
        with col_c:
            s = find_col(sheet_df, ["status", "lead status"])
            hot = 0
            if s:
                hot = sheet_df[s].astype(str).str.lower().str.contains("hot").sum()
            st.metric("🔥 Hot Leads", int(hot))

        st.dataframe(
            sheet_df.drop(columns=["Sheet", "Quarter", "Category"], errors="ignore"),
            use_container_width=True, height=200
        )

st.markdown("---")

# ─────────────────────────────────────────────
# FULL DATA TABLE
# ─────────────────────────────────────────────
st.markdown("## 🗃️ Full Data View")
show_data = st.checkbox("Show Full Combined Data Table", value=False)
if show_data:
    st.dataframe(
        df.drop(columns=["Quarter"], errors="ignore"),
        use_container_width=True, height=400
    )

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color: #555; font-size: 12px;'>"
    "🚀 T-Hub Meetings Dashboard | Powered by Streamlit + Google Sheets"
    "</div>",
    unsafe_allow_html=True
)

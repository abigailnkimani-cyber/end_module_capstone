import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Income, Child Mortality and Life Expectancy", layout="wide")
alt.data_transformers.disable_max_rows()  # Altair's default 5,000-row cap is too low for country-year data

QUARTILES = ["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"]
QUARTILE_COLORS = ["#e4572e", "#f2a541", "#4ea8de", "#1f4e79"]
QUARTILE_SCALE = alt.Scale(domain=QUARTILES, range=QUARTILE_COLORS)

# styling
st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; max-width: 1300px;}
    .hero {
        background: linear-gradient(135deg, #1f4e79 0%, #2a9d8f 100%);
        padding: 1.5rem 1.8rem; border-radius: 16px; color: white; margin-bottom: 1.2rem;
    }
    .hero h1 {color: white; margin: 0; font-size: 2rem; padding: 0;}
    .hero p {margin: .4rem 0 0; opacity: .92; font-size: .95rem;}
    [data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 12px; padding: .8rem 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {gap: .5rem;}
    .stTabs [data-baseweb="tab"] {font-weight: 600; padding: .5rem 1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def style(chart, height=320):
    return (chart.properties(height=height)
            .configure_view(stroke=None)
            .configure_axis(labelFontSize=11, titleFontSize=12, gridColor="#8883", domainColor="#8886")
            .configure_legend(labelFontSize=11, titleFontSize=12, orient="top"))


# data
@st.cache_data
def load_data():
    df = pd.read_csv("clean_data.csv")
    df["log_gdp"] = np.log(df["gdp_per_capita"])
    df["log_mortality"] = np.log(df["child_mortality"])
    df["decade"] = (df["year"] // 10) * 10
    df["gdp_quartile"] = pd.qcut(df["gdp_per_capita"], 4, labels=QUARTILES)
    return df


df = load_data()

# sidebar filters
st.sidebar.header("Filters")
year_range = st.sidebar.slider("Year range", int(df["year"].min()), int(df["year"].max()),
                               (int(df["year"].min()), int(df["year"].max())))
quartiles = st.sidebar.multiselect("GDP per capita quartile", QUARTILES, default=QUARTILES)
countries = st.sidebar.multiselect("Countries (optional)", sorted(df["Country Name"].unique()))

view = df[df["year"].between(*year_range) & df["gdp_quartile"].isin(quartiles)]
if countries:
    view = view[view["Country Name"].isin(countries)]

# header
st.markdown(
    """
    <div class="hero">
        <h1>Income, Child Mortality and Life Expectancy</h1>
        <p>World Bank World Development Indicators: life expectancy, under-5 mortality,
        GDP per capita and population, joined on country code and year.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if view.empty:
    st.warning("No data matches these filters. Widen the year range or quartile selection.")
    st.stop()

tab_overview, tab_dist, tab_rel = st.tabs(["Overview", "Distributions", "Relationships"])

# overview
with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{len(view):,}")
    c2.metric("Countries", view["Country Code"].nunique())
    c3.metric("Median under-5 mortality", f"{view['child_mortality'].median():.1f} per 1,000")
    c4.metric("Median life expectancy", f"{view['life_expectancy'].median():.1f} years")

    with st.container(border=True):
        st.subheader("Median under-5 mortality over time, by GDP quartile")
        trend = (view.groupby(["year", "gdp_quartile"], observed=True)["child_mortality"]
                 .median().reset_index())
        trend["gdp_quartile"] = trend["gdp_quartile"].astype(str)
        line = alt.Chart(trend).mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(size=35)).encode(
            x=alt.X("year:Q", title="Year", axis=alt.Axis(format="d")),
            y=alt.Y("child_mortality:Q", title="Deaths per 1,000 live births"),
            color=alt.Color("gdp_quartile:N", title="GDP quartile", scale=QUARTILE_SCALE),
            tooltip=[alt.Tooltip("year:Q", title="Year", format="d"),
                     alt.Tooltip("gdp_quartile:N", title="Quartile"),
                     alt.Tooltip("child_mortality:Q", title="Median mortality", format=".1f")],
        )
        st.altair_chart(style(line, 340), use_container_width=True)

    with st.container(border=True):
        st.subheader("Data")
        shown = ["Country Name", "Country Code", "year", "life_expectancy", "child_mortality",
                 "gdp_per_capita", "population", "gdp_quartile"]
        st.dataframe(view[shown].reset_index(drop=True), height=300, use_container_width=True)

        download_choice = st.radio(
            "Download option",
            ["Displayed columns", "All columns"],
            horizontal=True,
        )
        export_df = view[shown] if download_choice == "Displayed columns" else view
        st.download_button(
            "Download filtered data (CSV)",
            export_df.to_csv(index=False),
            file_name="filtered_data.csv",
            mime="text/csv",
        )

# distributions
with tab_dist:
    labels = {"child_mortality": "Under-5 mortality (per 1,000)",
              "life_expectancy": "Life expectancy (years)",
              "gdp_per_capita": "GDP per capita (US$)",
              "log_gdp": "Log GDP per capita"}
    with st.container(border=True):
        var = st.selectbox("Variable", list(labels), format_func=lambda v: labels[v])
        x = view[var]

        c1, c2, c3 = st.columns(3)
        c1.metric("Mean", f"{x.mean():,.2f}")
        c2.metric("Median", f"{x.median():,.2f}")
        c3.metric("Skewness", f"{x.skew():.2f}")

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.subheader("Histogram")
            hist = alt.Chart(view[[var]]).mark_bar(color="#4ea8de", opacity=0.9).encode(
                x=alt.X(f"{var}:Q", bin=alt.Bin(maxbins=40), title=labels[var]),
                y=alt.Y("count()", title="Count"),
            )
            lines_df = pd.DataFrame({"stat": ["Mean", "Median"], "value": [x.mean(), x.median()]})
            rules = alt.Chart(lines_df).mark_rule(strokeWidth=2.5, strokeDash=[6, 4]).encode(
                x="value:Q",
                color=alt.Color("stat:N", title=None,
                                scale=alt.Scale(domain=["Mean", "Median"],
                                                range=["#e4572e", "#2a9d8f"])),
                tooltip=[alt.Tooltip("stat:N", title="Statistic"),
                         alt.Tooltip("value:Q", title="Value", format=",.2f")],
            )
            st.altair_chart(style(hist + rules, 340), use_container_width=True)
    with right:
        with st.container(border=True):
            st.subheader("By GDP quartile")
            box_data = view[["gdp_quartile", var]].copy()
            box_data["gdp_quartile"] = box_data["gdp_quartile"].astype(str)
            box = alt.Chart(box_data).mark_boxplot(extent=1.5, size=45).encode(
                x=alt.X("gdp_quartile:N", sort=QUARTILES, title="GDP per capita quartile",
                        axis=alt.Axis(labelAngle=0)),
                y=alt.Y(f"{var}:Q", title=labels[var]),
                color=alt.Color("gdp_quartile:N", scale=QUARTILE_SCALE, legend=None),
            )
            st.altair_chart(style(box, 340), use_container_width=True)

    if x.skew() > 0.5:
        st.info("Right-skewed: the mean sits above the median, so the median describes a typical "
                "country-year better than the mean.")
    elif x.skew() < -0.5:
        st.info("Left-skewed: the mean sits below the median.")
    else:
        st.info("Roughly symmetric: the mean and median are close.")

# relationships
with tab_rel:
    with st.container(border=True):
        st.subheader("Log GDP per capita vs life expectancy")
        scatter = alt.Chart(view[["Country Name", "year", "decade", "log_gdp", "life_expectancy"]]).mark_circle(
            size=40, opacity=0.55).encode(
            x=alt.X("log_gdp:Q", title="Log GDP per capita", scale=alt.Scale(zero=False)),
            y=alt.Y("life_expectancy:Q", title="Life expectancy (years)", scale=alt.Scale(zero=False)),
            color=alt.Color("decade:O", title="Decade", scale=alt.Scale(scheme="viridis")),
            tooltip=[alt.Tooltip("Country Name:N", title="Country"),
                     alt.Tooltip("year:Q", title="Year", format="d"),
                     alt.Tooltip("log_gdp:Q", title="Log GDP", format=".2f"),
                     alt.Tooltip("life_expectancy:Q", title="Life expectancy", format=".1f")],
        ).interactive()
        st.altair_chart(style(scatter, 420), use_container_width=True)

    with st.container(border=True):
        st.subheader("Median under-5 mortality by decade and GDP quartile")
        pivot = view.pivot_table(index="gdp_quartile", columns="decade", values="child_mortality",
                                 aggfunc="median", observed=True)
        heat_df = pivot.reset_index().melt(id_vars="gdp_quartile", var_name="decade",
                                           value_name="median_mortality").dropna()
        heat_df["gdp_quartile"] = heat_df["gdp_quartile"].astype(str)
        heat_df["decade"] = heat_df["decade"].astype(int).astype(str) + "s"
        threshold = heat_df["median_mortality"].max() * 0.55
        base = alt.Chart(heat_df).encode(
            x=alt.X("decade:O", title="Decade", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("gdp_quartile:O", sort=QUARTILES, title="GDP per capita quartile"),
        )
        rect = base.mark_rect(cornerRadius=4).encode(
            color=alt.Color("median_mortality:Q", title="Median mortality",
                            scale=alt.Scale(scheme="yelloworangered")),
            tooltip=[alt.Tooltip("gdp_quartile:O", title="Quartile"),
                     alt.Tooltip("decade:O", title="Decade"),
                     alt.Tooltip("median_mortality:Q", title="Median mortality", format=".1f")],
        )
        text = base.mark_text(fontSize=13, fontWeight="bold").encode(
            text=alt.Text("median_mortality:Q", format=".0f"),
            color=alt.condition(alt.datum.median_mortality > threshold,
                                alt.value("white"), alt.value("black")),
        )
        st.altair_chart(style(rect + text, 260), use_container_width=True)
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

st.set_page_config(page_title="Income, Child Mortality and Life Expectancy", layout="wide")

QUARTILES = ["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"]
ALPHA = 0.05
TARGET = 25  # UN SDG target: 25 or fewer under-5 deaths per 1,000 live births
LIFE_CUTOFF = 70  # life expectancy benchmark in years


# data
@st.cache_data
def load_data():
    df = pd.read_csv("clean_data.csv")
    df["log_gdp"] = np.log(df["gdp_per_capita"])
    df["log_mortality"] = np.log(df["child_mortality"])
    df["decade"] = (df["year"] // 10) * 10
    df["gdp_quartile"] = pd.qcut(df["gdp_per_capita"], 4, labels=QUARTILES)
    return df


def fmt_p(p):
    if p == 0:
        return "< 1e-300 (below floating-point precision)"
    return f"{p:.3g}"


def decision(p):
    return "Reject H0" if p < ALPHA else "Fail to reject H0"


#  tests (always on the full dataset)
@st.cache_data
def run_anova(df, col):
    groups = [g[col].values for _, g in df.groupby("gdp_quartile", observed=True)]
    k, n = len(groups), len(df)
    f, p = stats.f_oneway(*groups)
    grand = df[col].mean()
    eta_sq = sum(len(g) * (g.mean() - grand) ** 2 for g in groups) / ((df[col] - grand) ** 2).sum()
    lev = stats.levene(*groups)
    return dict(f=f, p=p, eta_sq=eta_sq, df1=k - 1, df2=n - k, n=n, levene_p=lev.pvalue)


@st.cache_data
def run_paired(df):
    pair = (df[df["year"].isin([2000, 2024])]
            .pivot(index="Country Code", columns="year", values="log_mortality")
            .dropna())
    t, p = stats.ttest_rel(pair[2000], pair[2024])
    diff = pair[2000] - pair[2024]  # positive = mortality fell
    return dict(t=t, p=p, n=len(pair), d=diff.mean() / diff.std(ddof=1),
                share_fell=(diff > 0).mean(), ratio=float(np.exp(-diff.mean())))


@st.cache_data
def run_ab(df):
    latest = df[df["year"] == 2024].copy()
    above = latest["gdp_per_capita"] >= latest["gdp_per_capita"].median()
    hit = latest["child_mortality"] <= TARGET
    xA, nA = int(hit[~above].sum()), int((~above).sum())
    xB, nB = int(hit[above].sum()), int(above.sum())
    pA, pB = xA / nA, xB / nB
    pool = (xA + xB) / (nA + nB)
    z = (pB - pA) / np.sqrt(pool * (1 - pool) * (1 / nA + 1 / nB))
    p = 2 * stats.norm.sf(abs(z))
    se = np.sqrt(pA * (1 - pA) / nA + pB * (1 - pB) / nB)
    _, p_fisher = stats.fisher_exact([[xA, nA - xA], [xB, nB - xB]])
    return dict(xA=xA, nA=nA, xB=xB, nB=nB, pA=pA, pB=pB, z=z, p=p, p_fisher=p_fisher,
                diff=pB - pA, lo=(pB - pA) - 1.96 * se, hi=(pB - pA) + 1.96 * se,
                min_cell=min(xA, nA - xA, xB, nB - xB))


@st.cache_data
def run_chi2(df):
    latest = df[df["year"] == 2024].copy()
    latest["quartile"] = pd.qcut(latest["gdp_per_capita"], 4, labels=QUARTILES)
    latest["long_life"] = np.where(latest["life_expectancy"] >= LIFE_CUTOFF,
                                   f"{LIFE_CUTOFF} or more", f"under {LIFE_CUTOFF}")
    ct = pd.crosstab(latest["quartile"], latest["long_life"])
    chi2, p, dof, expected = stats.chi2_contingency(ct)
    v = np.sqrt(chi2 / (len(latest) * (min(ct.shape) - 1)))
    return dict(ct=ct, pct=ct.div(ct.sum(axis=1), axis=0), chi2=chi2, p=p, dof=dof, v=v,
                n=len(latest), min_expected=expected.min())


df = load_data()

#  sidebar filters
st.sidebar.header("Filters")
st.sidebar.caption("Filters apply to the Overview, Distributions and Relationships tabs. "
                   "The hypothesis tests always use the full dataset.")
year_range = st.sidebar.slider("Year range", int(df["year"].min()), int(df["year"].max()),
                               (int(df["year"].min()), int(df["year"].max())))
quartiles = st.sidebar.multiselect("GDP per capita quartile", QUARTILES, default=QUARTILES)
countries = st.sidebar.multiselect("Countries (optional)", sorted(df["Country Name"].unique()))

view = df[df["year"].between(*year_range) & df["gdp_quartile"].isin(quartiles)]
if countries:
    view = view[view["Country Name"].isin(countries)]

#  header
st.title("Income, Child Mortality and Life Expectancy")
st.caption("World Bank World Development Indicators: life expectancy, under-5 mortality, "
           "GDP per capita and population, joined on country code and year.")

if view.empty:
    st.warning("No data matches these filters. Widen the year range or quartile selection.")
    st.stop()

tab_overview, tab_dist, tab_rel, tab_tests = st.tabs(
    ["Overview", "Distributions", "Relationships", "Hypothesis tests"])

#  overview
with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{len(view):,}")
    c2.metric("Countries", view["Country Code"].nunique())
    c3.metric("Median under-5 mortality", f"{view['child_mortality'].median():.1f} per 1,000")
    c4.metric("Median life expectancy", f"{view['life_expectancy'].median():.1f} years")

    st.subheader("Median under-5 mortality over time, by GDP quartile")
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.lineplot(data=view, x="year", y="child_mortality", hue="gdp_quartile",
                 hue_order=[q for q in QUARTILES if q in quartiles],
                 estimator="median", errorbar=None, ax=ax)
    ax.set_ylabel("Deaths per 1,000 live births", fontsize=9)
    ax.set_xlabel("Year", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.legend(title="GDP quartile", loc="upper left", bbox_to_anchor=(1.02, 1),
              fontsize=8, title_fontsize=9, frameon=False)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    st.subheader("Data")
    shown = ["Country Name", "Country Code", "year", "life_expectancy", "child_mortality",
             "gdp_per_capita", "population", "gdp_quartile"]
    st.dataframe(view[shown].reset_index(drop=True), height=300)

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

#  distributions
with tab_dist:
    labels = {"child_mortality": "Under-5 mortality (per 1,000)",
              "life_expectancy": "Life expectancy (years)",
              "gdp_per_capita": "GDP per capita (US$)",
              "log_gdp": "Log GDP per capita"}
    var = st.selectbox("Variable", list(labels), format_func=lambda v: labels[v])
    x = view[var]

    c1, c2, c3 = st.columns(3)
    c1.metric("Mean", f"{x.mean():,.2f}")
    c2.metric("Median", f"{x.median():,.2f}")
    c3.metric("Skewness", f"{x.skew():.2f}")

    left, right = st.columns(2)
    with left:
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.histplot(x, bins=40, kde=True, ax=ax)
        ax.axvline(x.mean(), color="red", linestyle="--", label=f"mean {x.mean():,.1f}")
        ax.axvline(x.median(), color="green", linestyle="--", label=f"median {x.median():,.1f}")
        ax.set_xlabel(labels[var])
        ax.legend()
        st.pyplot(fig)
        plt.close(fig)
    with right:
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.boxplot(data=view, x="gdp_quartile", y=var,
                    order=[q for q in QUARTILES if q in quartiles], ax=ax)
        ax.set_xlabel("GDP per capita quartile")
        ax.set_ylabel(labels[var])
        st.pyplot(fig)
        plt.close(fig)

    if x.skew() > 0.5:
        st.info("Right-skewed: the mean sits above the median, so the median describes a typical "
                "country-year better than the mean.")
    elif x.skew() < -0.5:
        st.info("Left-skewed: the mean sits below the median.")
    else:
        st.info("Roughly symmetric: the mean and median are close.")

#  relationships
with tab_rel:
    st.subheader("Log GDP per capita vs life expectancy")
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.scatterplot(data=view, x="log_gdp", y="life_expectancy", hue="decade",
                    palette="viridis", alpha=0.5, s=18, ax=ax)
    ax.set_xlabel("Log GDP per capita")
    ax.set_ylabel("Life expectancy (years)")
    st.pyplot(fig)
    plt.close(fig)

    st.subheader("Median under-5 mortality by decade and GDP quartile")
    pivot = view.pivot_table(index="gdp_quartile", columns="decade", values="child_mortality",
                            aggfunc="median", observed=True)
    fig, ax = plt.subplots(figsize=(9, 3.5))
    sns.heatmap(pivot, annot=True, fmt=".0f", cmap="YlOrRd", ax=ax)
    ax.set_xlabel("Decade")
    ax.set_ylabel("GDP per capita quartile")
    st.pyplot(fig)
    plt.close(fig)

#  hypothesis tests
with tab_tests:
    st.caption(f"All tests use alpha = {ALPHA} and the full cleaned dataset ({len(df):,} rows), "
               "regardless of the sidebar filters.")

    # ANOVA: child mortality
    a = run_anova(df, "log_mortality")
    st.header("1. One-way ANOVA: child mortality across GDP quartiles")
    st.markdown("**H0:** mean log child mortality is the same in all four GDP quartiles.  \n"
                "**H1:** at least one quartile has a different mean.")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"F({a['df1']}, {a['df2']})", f"{a['f']:,.1f}")
    c2.metric("p-value", fmt_p(a["p"]))
    c3.metric("Eta-squared", f"{a['eta_sq']:.2f}")
    medians = df.groupby("gdp_quartile", observed=True)["child_mortality"].median().round(1)
    st.write(f"**Decision:** {decision(a['p'])} at alpha = {ALPHA}. "
             f"Median mortality by quartile (per 1,000): "
             + ", ".join(f"{q} {v}" for q, v in medians.items()) + ".")
    st.caption(f"Levene's test for equal variances: p = {fmt_p(a['levene_p'])}. Variances differ, but groups are "
               "nearly equal in size, so ANOVA is reasonably robust.")
    with st.expander("What the p-value is not"):
        st.write("It is not the probability that H0 is true or that the result happened by chance, and it "
                 "does not say how big the difference is: the size comes from eta-squared and the medians. "
                 "It does not show that income causes lower mortality. Countries repeat across years, so "
                 "the rows are not independent and the p-value looks more certain than it is.")

    
    #  paired t-test
    t = run_paired(df)
    st.header("2. Paired t-test: child mortality, 2000 vs 2024")
    st.markdown("**H0:** the mean change in log child mortality between 2000 and 2024 is zero.  \n"
                "**H1:** the mean change is not zero.")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"t({t['n'] - 1})", f"{t['t']:.1f}")
    c2.metric("p-value", fmt_p(t["p"]))
    c3.metric("Cohen's d", f"{t['d']:.2f}")
    st.write(f"**Decision:** {decision(t['p'])} at alpha = {ALPHA}. Based on {t['n']} countries with data in "
             f"both years, {t['share_fell']:.0%} fell, and a typical country's 2024 mortality is about "
             f"{t['ratio']:.0%} of its 2000 level.")
    with st.expander("What the p-value is not"):
        st.write("It is not the probability that H0 is true or that the fall happened by chance, and it "
                 "does not say how big the fall was: the size comes from Cohen's d and the share of "
                 "countries that fell. It says nothing about why mortality fell. Only countries with data "
                 "in both years are included.")

    #  chi-square
    c = run_chi2(df)
    st.header(f"3. Chi-square test: income group and life expectancy of {LIFE_CUTOFF}+ (2024)")
    st.markdown(f"**H0:** GDP per capita quartile and life expectancy category ({LIFE_CUTOFF} or more vs under "
                f"{LIFE_CUTOFF}) are independent.  \n"
                "**H1:** they are associated.")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Chi-square({c['dof']})", f"{c['chi2']:.1f}")
    c2.metric("p-value", fmt_p(c["p"]))
    c3.metric("Cramer's V", f"{c['v']:.2f}")
    st.write(f"**Decision:** {decision(c['p'])} at alpha = {ALPHA}. Based on {c['n']} countries in 2024.")
    st.dataframe(c["ct"])
    st.caption("Row shares (proportion of each quartile in each life expectancy category):")
    st.dataframe(c["pct"].round(2))
    st.caption(f"Smallest expected count: {c['min_expected']:.1f} (the test needs 5 or more).")
    with st.expander("What the p-value is not"):
        st.write("It is not the probability that H0 is true or that the association is due to chance, and it "
                 "does not say how strong the association is: the strength comes from Cramer's V and the row "
                 f"shares. It does not show that income causes longer life or say which quartiles differ. The "
                 f"{LIFE_CUTOFF}-year cutoff turns a numeric variable into two categories and loses detail, "
                 f"and the result uses 2024 only.")

    #  A/B two-proportion z-test
    b = run_ab(df)
    st.header("4. A/B-style comparison: richer vs poorer half (2024)")
    st.markdown(f"Groups: A = countries below the median GDP per capita, B = countries at or above it. "
                f"Metric: share with under-5 mortality of {TARGET} or fewer per 1,000.  \n"
                "**H0:** the share meeting the target is the same in both groups.  \n"
                "**H1:** the shares differ.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("A: below median", f"{b['pA']:.0%}", f"{b['xA']} of {b['nA']}", delta_color="off")
    c2.metric("B: above median", f"{b['pB']:.0%}", f"{b['xB']} of {b['nB']}", delta_color="off")
    c3.metric("z", f"{b['z']:.2f}")
    c4.metric("p-value", fmt_p(b["p"]))
    st.write(f"**Decision:** {decision(b['p'])} at alpha = {ALPHA}. The difference is "
             f"{b['diff'] * 100:.0f} percentage points (95% CI {b['lo'] * 100:.0f} to {b['hi'] * 100:.0f}). "
             f"Fisher's exact check: p = {fmt_p(b['p_fisher'])}.")
    if b["min_cell"] < 10:
        st.caption(f"The smallest cell has {b['min_cell']} countries, below the usual rule of thumb of 10 "
                   "for the z-test, so Fisher's exact test is shown as a check.")
    st.warning("Groups were not randomly assigned. Countries were already in the richer or poorer half, so a "
               "significant result shows the groups differ. It does not by itself prove that income caused "
               "the difference, the way a true randomized A/B test would.")
    with st.expander("What the p-value is not"):
        st.write("It is not the probability that H0 is true or that the gap is due to chance, and it does not "
                 "say how big the gap is: the size comes from the percentage-point difference and its "
                 "confidence interval. It uses 2024 only, so it cannot say how the gap has changed over time.")

    st.divider()
    st.caption("Limitations: countries repeat across years in the ANOVA; incomplete rows were dropped, which "
               "underrepresents poorer and less documented countries and early years; quartiles are my own "
               "splits of GDP per capita, not official World Bank income classes; results show association, "
               "not causation.")

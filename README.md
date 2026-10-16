# Income, Child Mortality and Life Expectancy

An end-to-end data project that examines how national income relates to under-5 mortality and life expectancy across countries, 1960–2024. The analysis was developed in a Jupyter notebook following the CRISP-DM framework and deployed as an interactive Streamlit app.---

## 1. Project Overview

| Item | Detail |
|---|---|
| Question | How are income levels associated with child mortality and life expectancy, and how has this changed over time? |
| Coverage | 194 countries, 10,525 rows, 1960–2024 |
| Key variables | `life_expectancy`, `child_mortality` (deaths per 1,000 live births), `gdp_per_capita`, `population`, `gdp_quartile` |
| Tools | Python, pandas, matplotlib, seaborn, SciPy, Streamlit |
| Deliverables | Jupyter notebook (`capstone.ipynb`), Streamlit app (`app.py`), cleaned dataset (`clean_data.csv`) |

---

## 2. Repository Structure
.
├── app.py                      # Streamlit application
├── capstone.ipynb              # CRISP-DM analysis notebook
├── data/
│   ├── raw/                    # Source files as downloaded (World Bank)
│   └── clean_data.csv          # Cleaned, merged dataset used by the app
├── docs/
│   └── end_module_capstone.pdf # Presentation slides and project overview
├── requirements.txt
└── README.md

---

## 3. Methodology (CRISP-DM)

### 3.1 Business Understanding
- **Objective:** Establish whether higher-income countries have lower child mortality and longer life expectancy, and whether the gap between income groups has narrowed.
- **Success criteria:** A clean, reproducible dataset; documented statistical evidence; an interactive dashboard that allows non-technical users to explore the findings.

### 3.2 Data Understanding
- **Sources:** **[ World Bank Indicators: NY.GDP.PCAP.CD, SP.DYN.LE00.IN, SH.DYN.MORT downloaded October 2026 under CC-BY 4.0 license).**
- **Initial checks:** shape, data types, missing values per indicator, duplicate country-year records, and coverage by year and country.
- **Observations:** **[e.g. aggregates (regions, income groups) mixed with countries; missing GDP values in early years; indicators with different year coverage.]**

### 3.3 Data Preparation
Steps carried out in the notebook:

1. **Loading:** each indicator imported as a separate file.
2. **Reshaping:** converted from wide format (one column per year) to long format (one row per country-year).
3. **Merging:** joined indicators on `Country Code` and `year`.
4. **Filtering:** removed regional and income-group aggregates so that only countries remain.
5. **Cleaning:** standardised column names, corrected data types, handled missing values by droping them since guessing values would mean misrepresentation, and removed duplicates.
6. **Feature engineering:** created `gdp_quartile` (Q1 lowest to Q4 highest) gdp_quartile was computed globally across all 1960–2024 rows using pd.qcut
7. **Export:** saved the final dataset to `clean_data.csv`.

### 3.4 Modelling and Analysis
- **Descriptive statistics:** medians are used throughout because the indicators are skewed.
- **Distributions:** histograms and box plots of each indicator by GDP quartile.
- **Relationships:** scatter plots and correlations between income, child mortality and life expectancy 
- **Hypothesis tests:** One-way ANOVA comparing life expectancy across GDP quartiles, $p < 0.05$). H0: mean log child mortality is the same in all four quartiles.**.

### 3.5 Evaluation
Key findings:

- Median under-5 mortality has fallen sharply in every income group since 1960.
- The lowest-income quartile (Q1) started at roughly 195 deaths per 1,000 live births and has fallen to roughly 50 by 2024.
- The highest-income quartile (Q4) has remained below roughly 10 per 1,000 for most of the period.
- The gap between the lowest and highest quartiles has narrowed substantially but has not closed.

Limitations: **missing data in early years; GDP quartile grouping hides within-group variation; correlation does not imply causation; the 1970s spike in Q4 reflects few reporting countries in that quartile and year**.

### 3.6 Deployment
The analysis was converted into a Streamlit app (`app.py`) and deployed **[on Streamlit Community Cloud / locally; **(http://localhost:8501)**.

---

## 4. The Streamlit App (`app.py`)

**Sidebar:** filters that control the data shown on every tab.

| Tab | Contents |
|---|---|
| Overview | Key metrics (rows, countries, median under-5 mortality, median life expectancy); line chart of median under-5 mortality over time by GDP quartile; filtered data table; CSV download |
| Distributions | Under-5 mortality (per 1,000) Right-skewed: the mean sits above the median, so the median describes a typical country-year better than the mean.
life expectancy (years) Left-skewed: the mean sits below the median.
GDP per capita (US$) Right-skewed: the mean sits above the median, so the median describes a typical country-year better than the mean.
| Relationships | I used a scatter plot to show log GDP per capita against Life expectancy (years)
| Hypothesis tests | I used one-way ANOVA, Paired t-test, CHi-square test and A/B style comparison

**Downloads:** the Overview tab exports the filtered data as CSV, either the displayed columns or all columns.

---

## 5. Running the Project Locally

```bash
# 1. Clone the repository
git clone https://github.com/abigailnkimani-cyber/end_module_capstone.git
cd end_module_capstone

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

To explore the analysis, open the notebook with `jupyter notebook capstone.ipynb`.

---

## 6. Deploying to Streamlit Community Cloud

Live app: (https://endmodulecapstone-gbrncegpkwpvqvjkjukejb.streamlit.app/)

---

## 7. Dependencies

```
streamlit
pandas
numpy
matplotlib
seaborn
scipy
```
## 8. Article
Read the full write-up on [Substack](https://abnk.substack.com/p/do-richer-countries-really-keep-more?r=6xvpog&utm_campaign=post&utm_medium=web&showWelcomeOnShare=true).

---

## 9. Presentation
Presentation slides: https://eu.wps.com/cms/docs/d/cbOakhgqDf8cJXMu?platform=pc&refer=copylink

---

## 10. Author
**Abigail Kimani** — *Zindua School Data Analytics Capstone*

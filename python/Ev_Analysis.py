
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler
scaler = MinMaxScaler()


################### Data Loading & Quality Check ##################

# Load datasets
state_sales = pd.read_csv("../data/electric_vehicle_sales_by_state.csv")
maker_sales = pd.read_csv("../data/electric_vehicle_sales_by_makers.csv")
dim_date = pd.read_csv("../data/dim_date.csv")

## Preview datasets
print("State Sales:")
print(maker_sales.head())
print(dim_date.head())

## Check Structure
print("STATE SALES")
print(state_sales.shape)
print(state_sales.info())

print("\nMAKER SALES")
print(maker_sales.shape)
print(maker_sales.info())

print("\nDATE DIMENSION")
print(dim_date.shape)
print(dim_date.info())

## Missing values
print("State Sales Missing Values:")
print(state_sales.isnull().sum())

print("\nMaker Sales Missing Values:")
print(maker_sales.isnull().sum())

print("\nDate Dimension Missing Values:")
print(dim_date.isnull().sum())

## Duplicates
print("State Sales Duplicates:", state_sales.duplicated().sum())
print("Maker Sales Duplicates:", maker_sales.duplicated().sum())
print("Date Dimension Duplicates:", dim_date.duplicated().sum())

## Date conversion
state_sales["date"] = pd.to_datetime (state_sales["date"],format="%d-%b-%y")
maker_sales["date"] = pd.to_datetime(maker_sales["date"],format="%d-%b-%y")
dim_date["date"] = pd.to_datetime(dim_date["date"],format="%d-%b-%y")

## Add fiscal information
state_sales = state_sales.merge(dim_date[["date", "fiscal_year", "quarter"]],on="date",how="left")
maker_sales = maker_sales.merge(dim_date[["date", "fiscal_year", "quarter"]],on="date",how="left")

#################################################### State-Level EV Market ##################################################

## State × Fiscal Year analytical dataset ##
state_year = (state_sales.groupby(["state", "fiscal_year"], as_index=False).agg(EV_Sales=("electric_vehicles_sold", "sum"),Total_Vehicle_Sales=("total_vehicles_sold", "sum"))
            .sort_values(["state", "fiscal_year"]))

##  Market indicators ##
state_year["EV_Penetration"] = (state_year["EV_Sales"] /state_year["Total_Vehicle_Sales"]) * 100
state_year["EV_Growth_%"] = (state_year.groupby("state")["EV_Sales"].pct_change() * 100)
state_year["Penetration_Change"] = (state_year.groupby("state")["EV_Penetration"].diff())
print(state_year.head())

## Latest fiscal year snapshot ##
latest_fy = state_year["fiscal_year"].max()
latest_state = state_year[state_year["fiscal_year"] == latest_fy].copy()
print(latest_state.head())

############################################ STATE-LEVEL EV OPPORTUNITY SCORE ############################################

## Normalized component scores ##
latest_state["Market_Size_Score"] = (scaler.fit_transform(latest_state[["Total_Vehicle_Sales"]]).flatten()* 100)

## EV Growth Score ##
latest_state["EV_Growth_Score"] = (scaler.fit_transform(latest_state[["EV_Growth_%"]].fillna(0)).flatten()* 100)

## Lower EV penetration = larger potential adoption gap ##
latest_state["EV_Penetration_Gap"] = (100 - latest_state["EV_Penetration"])

## Penetration_Momentum_Score ##
latest_state["Penetration_Momentum_Score"] = (scaler.fit_transform(latest_state[["Penetration_Change"]].fillna(0)).flatten()* 100)

## Weighted State EV Opportunity Score ## 

latest_state["Opportunity_Score"] = (
    latest_state["Market_Size_Score"] * 0.30
    + latest_state["EV_Growth_Score"] * 0.30
    + latest_state["EV_Penetration_Gap"] * 0.20
    + latest_state["Penetration_Momentum_Score"] * 0.20)

print(latest_state[["state","Market_Size_Score","EV_Growth_Score","EV_Penetration_Gap","Penetration_Momentum_Score","Opportunity_Score"]]
    .sort_values("Opportunity_Score", ascending=False).head(10))




############################################ MARKET OPPORTUNITY RANKING & CLASSIFICATION ############################################

## Ranking states ##
latest_state["Opportunity_Rank"] = (latest_state["Opportunity_Score"].rank(ascending=False,method="dense").astype(int))

## opportunity categories
def classify_opportunity(score):
    if score >= 75:
        return "Very High Opportunity"
    elif score >= 50:
        return "High Opportunity"
    elif score >= 25:
        return "Moderate Opportunity"
    else:
        return "Low Opportunity"

latest_state["Opportunity_Category"] = (latest_state["Opportunity_Score"].apply(classify_opportunity))

# Final ranking
opportunity_ranking = (latest_state[["Opportunity_Rank","state","Total_Vehicle_Sales","EV_Sales","EV_Penetration","EV_Growth_%","Penetration_Change","Opportunity_Score","Opportunity_Category"]]
    .sort_values("Opportunity_Rank"))
print(opportunity_ranking.head(15))

## Visualize the opportunity ranking
top_states = (latest_state.sort_values("Opportunity_Score", ascending=False).head(10))

plt.figure(figsize=(10, 6))
plt.barh(top_states["state"],top_states["Opportunity_Score"])

plt.xlabel("Opportunity Score")
plt.ylabel("State")
plt.title("Top 10 Indian States by EV Market Opportunity")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()

##  Market Size vs EV Penetration
plt.figure(figsize=(10, 7))
plt.scatter(latest_state["Total_Vehicle_Sales"],latest_state["EV_Penetration"],s=80)

plt.xlabel("Total Vehicle Sales")
plt.ylabel("EV Penetration (%)")
plt.title("State Market Size vs EV Penetration")
plt.tight_layout()
plt.show()

# Export final analysis
latest_state.to_csv("state_ev_opportunity_analysis.csv",index=False)




############################################ Market Maturity Matrix ############################################

##  Median benchmarks ##
penetration_median = latest_state["EV_Penetration"].median()
growth_median = latest_state["EV_Growth_%"].median()

### Market maturity classification ###
def classify_market(row):
    if (row["EV_Penetration"] >= penetration_median and row["EV_Growth_%"] >= growth_median): return "High-Potential Market"
    elif (row["EV_Penetration"] < penetration_median and row["EV_Growth_%"] >= growth_median):return "Emerging Market"
    elif (row["EV_Penetration"] >= penetration_median and row["EV_Growth_%"] < growth_median):return "Mature Market"
    else:return "Low-Priority Market"

latest_state["Market_Maturity"] = (latest_state.apply(classify_market,axis=1))

## Count states in each segment ##
plt.figure(figsize=(11, 7))

plt.scatter(latest_state["EV_Penetration"],latest_state["EV_Growth_%"],s=100 )
plt.axvline(penetration_median,linestyle="--")
plt.axhline(growth_median,linestyle="--")

for _, row in latest_state.iterrows():
    plt.annotate(
        row["state"],
        (row["EV_Penetration"], row["EV_Growth_%"]),
        xytext=(5, 5),
        textcoords="offset points",
        fontsize=8
    )

plt.xlabel("EV Penetration (%)")
plt.ylabel("EV Sales Growth (%)")
plt.title("India EV Market Maturity Matrix")

plt.tight_layout()
plt.show()

## final strategy classification
def strategy(row):
    if (row["Market_Maturity"] == "Emerging Market" and row["Opportunity_Score"] >= 50):
        return "Priority Entry"
    elif (row["Market_Maturity"] == "High-Potential Market"and row["Opportunity_Score"] >= 50):
        return "Strategic Entry"
    elif row["Market_Maturity"] == "Mature Market":
        return "Selective Entry"
    elif row["Market_Maturity"] == "Emerging Market":
        return "Monitor / Evaluate"
    else:
        return "Low Priority"

latest_state["Entry_Strategy"] = (latest_state.apply(strategy,axis=1))

# Final output
maturity_analysis = (
    latest_state[["state","EV_Penetration","EV_Growth_%","Opportunity_Score","Market_Maturity","Entry_Strategy"]].sort_values("Opportunity_Score", ascending=False))
print(maturity_analysis)




############################################ Manufacturer Competitive Intelligence ############################################


## Manufacturer × Fiscal Year summary
maker_year = (maker_sales.groupby(["maker", "fiscal_year"],as_index=False).agg(EV_Sales=("electric_vehicles_sold", "sum")))

## Total EV by fiscal year
market_year = (maker_year.groupby("fiscal_year",as_index=False).agg(Total_EV_Market=("EV_Sales", "sum")))

# Add market size
maker_year = maker_year.merge(market_year,on="fiscal_year",how="left")

## Manufacturer market share
maker_year["Market_Share_%"] = (maker_year["EV_Sales"]/maker_year["Total_EV_Market"]) * 100

## YoY growth
maker_year = maker_year.sort_values(["maker", "fiscal_year"]).copy()
maker_year["YoY_Growth_%"] = (maker_year.groupby("maker")["EV_Sales"].pct_change()* 100)

## Market Share Change
maker_year["Market_Share_Change"] = (maker_year.groupby("maker")["Market_Share_%"].diff())

## latest fiscal year snapshot
latest_fy_maker = maker_year["fiscal_year"].max()
latest_maker = (maker_year[maker_year["fiscal_year"] == latest_fy_maker].copy().sort_values("Market_Share_%",ascending=False))
print(latest_maker[["maker","EV_Sales","Market_Share_%","YoY_Growth_%","Market_Share_Change"]])

## Manufacturers gaining momentum
def classify_competitor(row):

    if (row["Market_Share_Change"] > 0 and row["YoY_Growth_%"] > 0 ):
        return "Gaining Momentum"
    elif (row["Market_Share_Change"] < 0 and row["YoY_Growth_%"] < 0 ):
        return "Losing Momentum"
    elif row["YoY_Growth_%"] > 0:
        return "Growing Challenger"
    else:
        return "Stable / Slow Growth"

latest_maker["Competitive_Position"] = (latest_maker.apply(classify_competitor,axis=1))
print(latest_maker[["maker","Market_Share_%","YoY_Growth_%","Market_Share_Change","Competitive_Position"]])

## Visualization
plt.figure(figsize=(11, 7))
plt.scatter(latest_maker["Market_Share_%"],latest_maker["YoY_Growth_%"],s=100 )

for _, row in latest_maker.iterrows():plt.annotate(row["maker"],(row["Market_Share_%"], row["YoY_Growth_%"]),
        xytext=(5, 5),
        textcoords="offset points",
        fontsize=8 )

plt.xlabel("Market Share (%)")
plt.ylabel("YoY EV Sales Growth (%)")
plt.title("EV Manufacturer Competitive Landscape")

plt.tight_layout()
plt.show()




############################################ EV GROWTH & MARKET STRUCTURE ANALYSIS ############################################

# Sort state-level data
state_year = state_year.sort_values(["state", "fiscal_year"]).copy()

## Previous-year values:
state_year["Previous_EV_Sales"] = (state_year.groupby("state")["EV_Sales"].shift(1))
state_year["Previous_Total_Vehicle_Sales"] = (state_year.groupby("state")["Total_Vehicle_Sales"].shift(1))
state_year["Previous_EV_Penetration"] = (state_year.groupby("state")["EV_Penetration"].shift(1))

## EV Sales Change
state_year["EV_Sales_Change"] = (state_year["EV_Sales"] - state_year["Previous_EV_Sales"])

## Market Size Effect
state_year["Market_Size_Effect"] = ((state_year["Total_Vehicle_Sales"] - state_year["Previous_Total_Vehicle_Sales"]) * ( state_year["Previous_EV_Penetration"] / 100))

##  EV Adoption Effect
state_year["EV_Adoption_Effect"] = (state_year["Total_Vehicle_Sales"] * (state_year["EV_Penetration"] - state_year["Previous_EV_Penetration"]) / 100)

## Primary growth classification
def classify_growth_driver(row):
    if pd.isna(row["EV_Sales_Change"]):
        return np.nan
    elif row["EV_Sales_Change"] <= 0:
        return "Declining / No Growth"
    elif row["EV_Adoption_Effect"] > row["Market_Size_Effect"]:
        return "EV Adoption Driven"
    elif row["Market_Size_Effect"] > row["EV_Adoption_Effect"]:
        return "Market Expansion Driven"
    else:
        return "Balanced Growth"

state_year["Primary_Growth_Driver"] = (state_year.apply(classify_growth_driver,axis=1))




############################################ Market Concentration Analysis ############################################

# Market concentration metrics
latest_maker = latest_maker.sort_values("Market_Share_%",ascending=False).copy()

## Top 5 Market Concentration
cr5 = (latest_maker.head(5)["Market_Share_%"].sum())

## Calculate Herfindahl-Hirschman Index
hhi = (latest_maker["Market_Share_%"] ** 2).sum()

## Market Concentration
def classify_hhi(hhi):
    if hhi < 1500:
        return "Competitive / Fragmented Market"
    elif hhi < 2500:
        return "Moderately Concentrated Market"
    else:
        return "Highly Concentrated Market"

market_structure = classify_hhi(hhi)
print("Market Structure:", market_structure)
print("CR5:", round(cr5, 2), "%")
print("HHI:", round(hhi, 2))


############################################ Statistical Analysis ############################################

## Descriptive statistics
stats_summary = latest_state[["EV_Sales","Total_Vehicle_Sales","EV_Growth_%", "EV_Penetration","Penetration_Change" ]].describe()
print(stats_summary)

## Correlation Analysis
correlation_cols = ["EV_Sales","Total_Vehicle_Sales", "EV_Growth_%","EV_Penetration","Penetration_Change"]
correlation_matrix = (latest_state[correlation_cols].corr())
print(correlation_matrix.round(2))

## Statistical Outliers - Ev Penetration
q1 = latest_state["EV_Penetration"].quantile(0.25)
q3 = latest_state["EV_Penetration"].quantile(0.75)
iqr = q3 - q1
lower_bound = q1 - (1.5 * iqr)
upper_bound = q3 + (1.5 * iqr)

latest_state["Penetration_Outlier"] = np.where((latest_state["EV_Penetration"] < lower_bound) | (latest_state["EV_Penetration"] > upper_bound),"Outlier","Normal")
penetration_outliers = latest_state[latest_state["Penetration_Outlier"] == "Outlier"]
print(penetration_outliers[["state","EV_Sales","EV_Penetration","EV_Growth_%","Opportunity_Score"]])


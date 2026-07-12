import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Nassau Candy Shipping Route Efficiency Dashboard",
    layout="wide"
)

st.title("Factory-to-Customer Shipping Route Efficiency Analysis")
st.subheader("Nassau Candy Distributor")

try:
    df = pd.read_csv("Nassau Candy Distributor.csv")
except FileNotFoundError:
    st.error("Dataset not found.")
    st.stop()

df.columns = (
        df.columns
        .str.strip()
        .str.replace(" ", "_")
        .str.replace("/", "_")
        )

df["Order_Date"] = pd.to_datetime(df["Order_Date"], dayfirst=True, errors="coerce")
df["Ship_Date"] = pd.to_datetime(df["Ship_Date"], dayfirst=True, errors="coerce")
df["Shipping_Lead_Time"] = (df["Ship_Date"] - df["Order_Date"]).dt.days

df = df.dropna(subset=["Order_Date", "Ship_Date"])
df = df[df["Shipping_Lead_Time"] >= 0]
product_factory_map = {
        "Wonka Bar - Nutty Crunch Surprise": "Lot's O' Nuts",
        "Wonka Bar - Fudge Mallows": "Lot's O' Nuts",
        "Wonka Bar -Scrumdiddlyumptious": "Lot's O' Nuts",
        "Wonka Bar - Milk Chocolate": "Wicked Choccy's",
        "Wonka Bar - Triple Dazzle Caramel": "Wicked Choccy's",
        "Laffy Taffy": "Sugar Shack",
        "SweeTARTS": "Sugar Shack",
        "Nerds": "Sugar Shack",
        "Fun Dip": "Sugar Shack",
        "Fizzy Lifting Drinks": "Sugar Shack",
        "Everlasting Gobstopper": "Secret Factory",
        "Lickable Wallpaper": "Secret Factory",
        "Wonka Gum": "Secret Factory",
        "Hair Toffee": "The Other Factory",
        "Kazookles": "The Other Factory"
    }

df["Factory"] = df["Product_Name"].map(product_factory_map)

df["Factory_to_State_Route"] = df["Factory"] + " -> " + df["State_Province"]
df["Factory_to_Region_Route"] = df["Factory"] + " -> " + df["Region"]

st.sidebar.header("Filters")

min_date = df["Order_Date"].min()
max_date = df["Order_Date"].max()

date_range = st.sidebar.date_input(
        "Order Date Range",
        [min_date, max_date]
)

selected_regions = st.sidebar.multiselect(
        "Select Region",
        sorted(df["Region"].dropna().unique()),
        default=sorted(df["Region"].dropna().unique())
)

selected_states = st.sidebar.multiselect(
        "Select State",
        sorted(df["State_Province"].dropna().unique()),
        default=sorted(df["State_Province"].dropna().unique())
)

selected_ship_modes = st.sidebar.multiselect(
        "Select Ship Mode",
        sorted(df["Ship_Mode"].dropna().unique()),
        default=sorted(df["Ship_Mode"].dropna().unique())
)

threshold = st.sidebar.slider(
        "Delay Threshold Days",
        int(df["Shipping_Lead_Time"].min()),
        int(df["Shipping_Lead_Time"].max()),
        int(df["Shipping_Lead_Time"].quantile(0.75))
)

df["Delayed"] = df["Shipping_Lead_Time"] > threshold

filtered_df = df[
        (df["Region"].isin(selected_regions)) &
        (df["State_Province"].isin(selected_states)) &
        (df["Ship_Mode"].isin(selected_ship_modes))
]

if len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        filtered_df = filtered_df[
            (filtered_df["Order_Date"] >= start_date) &
            (filtered_df["Order_Date"] <= end_date)
        ]

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Shipments", len(filtered_df))
col2.metric("Average Lead Time", round(filtered_df["Shipping_Lead_Time"].mean(), 2))
col3.metric("Delay Frequency %", round(filtered_df["Delayed"].mean() * 100, 2))
col4.metric("Total Sales", round(filtered_df["Sales"].sum(), 2))

st.divider()

st.header("Route Efficiency Overview")

route_perf = (
        filtered_df
        .groupby("Factory_to_State_Route", as_index=False)
        .agg(
            Total_Shipments=("Order_ID", "count"),
            Average_Lead_Time=("Shipping_Lead_Time", "mean"),
            Delay_Frequency=("Delayed", "mean")
        )
    )

route_perf["Average_Lead_Time"] = route_perf["Average_Lead_Time"].round(2)
route_perf["Delay_Frequency_%"] = (route_perf["Delay_Frequency"] * 100).round(2)

st.dataframe(route_perf.sort_values("Average_Lead_Time"))

top_routes = route_perf.sort_values("Average_Lead_Time").head(10)

fig = px.bar(
        top_routes,
        x="Average_Lead_Time",
        y="Factory_to_State_Route",
        orientation="h",
        title="Top 10 Most Efficient Routes",
        color="Average_Lead_Time"
    )

st.plotly_chart(fig, use_container_width=True)

st.header("Geographic Bottleneck Analysis")

state_perf = (
        filtered_df
        .groupby("State_Province", as_index=False)
        .agg(
            Total_Shipments=("Order_ID", "count"),
            Average_Lead_Time=("Shipping_Lead_Time", "mean"),
            Delay_Frequency=("Delayed", "mean")
        )
    )

state_perf["Average_Lead_Time"] = state_perf["Average_Lead_Time"].round(2)
state_perf["Delay_Frequency_%"] = (state_perf["Delay_Frequency"] * 100).round(2)

fig = px.scatter(
        state_perf,
        x="Total_Shipments",
        y="Average_Lead_Time",
        size="Total_Shipments",
        color="Delay_Frequency_%",
        hover_name="State_Province",
        title="State-Level Bottleneck View",
        color_continuous_scale="Reds"
    )

st.plotly_chart(fig, use_container_width=True)

st.header("Ship Mode Comparison")

ship_mode_perf = (
        filtered_df
        .groupby("Ship_Mode", as_index=False)
        .agg(
            Total_Shipments=("Order_ID", "count"),
            Average_Lead_Time=("Shipping_Lead_Time", "mean"),
            Delay_Frequency=("Delayed", "mean")
        )
    )

ship_mode_perf["Average_Lead_Time"] = ship_mode_perf["Average_Lead_Time"].round(2)
ship_mode_perf["Delay_Frequency_%"] = (ship_mode_perf["Delay_Frequency"] * 100).round(2)

fig = px.bar(
        ship_mode_perf,
        x="Ship_Mode",
        y="Average_Lead_Time",
        color="Ship_Mode",
        text="Average_Lead_Time",
        title="Average Lead Time by Ship Mode"
    )

st.plotly_chart(fig, use_container_width=True)

st.header("Route Drill Down")

selected_route = st.selectbox(
    "Select Route",
    sorted(filtered_df["Factory_to_State_Route"].dropna().unique())
)

route_drill = filtered_df[
    filtered_df["Factory_to_State_Route"] == selected_route
]

st.dataframe(
    route_drill[
        [
            "Order_ID",
            "Order_Date",
            "Ship_Date",
            "Shipping_Lead_Time",
            "Ship_Mode",
            "Customer_ID",
            "City",
            "State_Province",
            "Product_Name",
            "Sales",
            "Gross_Profit"
        ]
    ].sort_values("Shipping_Lead_Time", ascending=False)
)

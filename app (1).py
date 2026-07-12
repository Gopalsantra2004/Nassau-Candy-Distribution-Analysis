import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Nassau Candy Shipping Route Efficiency Dashboard",
    layout="wide"
)

st.title("Factory-to-Customer Shipping Route Efficiency Analysis")
st.subheader("Nassau Candy Distributor")


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data
def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace("/", "_", regex=False)
    )

    required_cols = [
        "Order_Date",
        "Ship_Date",
        "Region",
        "State_Province",
        "Ship_Mode",
        "Sales",
        "Product_Name",
        "Order_ID",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce", dayfirst=True)
    df["Ship_Date"] = pd.to_datetime(df["Ship_Date"], errors="coerce", dayfirst=True)
    df["Shipping_Lead_Time"] = (df["Ship_Date"] - df["Order_Date"]).dt.days

    df = df.dropna(subset=["Order_Date", "Ship_Date", "Shipping_Lead_Time"])
    df = df[df["Shipping_Lead_Time"] >= 0].copy()

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
        "Kazookles": "The Other Factory",
    }

    df["Factory"] = df["Product_Name"].map(product_factory_map)
    df = df.dropna(subset=["Factory"]).copy()

    df["Factory_to_State_Route"] = df["Factory"] + " -> " + df["State_Province"].astype(str)
    df["Factory_to_Region_Route"] = df["Factory"] + " -> " + df["Region"].astype(str)

    return df


try:
    raw_df = load_data("Nassau Candy Distributor.csv")
    df = prepare_data(raw_df)
except FileNotFoundError:
    st.error("Dataset not found.")
    st.stop()
except Exception as e:
    st.error(f"Data preparation failed: {e}")
    st.stop()

if df.empty:
    st.error("No valid rows remain after cleaning the dataset.")
    st.stop()

st.sidebar.header("Filters")

min_date = df["Order_Date"].min().date()
max_date = df["Order_Date"].max().date()

date_range = st.sidebar.date_input("Order Date Range", [min_date, max_date])

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

lead_time_min = int(df["Shipping_Lead_Time"].min())
lead_time_max = int(df["Shipping_Lead_Time"].max())

if lead_time_min == lead_time_max:
    lead_time_max += 1

q75 = df["Shipping_Lead_Time"].quantile(0.75)
threshold_default = int(q75) if pd.notna(q75) else lead_time_min
threshold_default = max(lead_time_min, min(threshold_default, lead_time_max))

threshold = st.sidebar.slider(
    "Delay Threshold Days",
    lead_time_min,
    lead_time_max,
    threshold_default
)

apply_filters = st.sidebar.button("Apply Filters")

if apply_filters or "filtered_df" not in st.session_state:
    if not selected_regions or not selected_states or not selected_ship_modes:
        st.warning("Please select at least one option in each filter.")
        st.stop()

    filtered_df = df[
        df["Region"].isin(selected_regions)
        & df["State_Province"].isin(selected_states)
        & df["Ship_Mode"].isin(selected_ship_modes)
    ].copy()

    if len(date_range) == 2:
        start_date = pd.Timestamp(date_range[0])
        end_date = pd.Timestamp(date_range[1])
        filtered_df = filtered_df[
            (filtered_df["Order_Date"] >= start_date)
            & (filtered_df["Order_Date"] <= end_date)
        ]

    if filtered_df.empty:
        st.warning("No shipments match the selected filters. Adjust the filters in the sidebar.")
        st.stop()

    filtered_df["Delayed"] = filtered_df["Shipping_Lead_Time"] > threshold
    st.session_state.filtered_df = filtered_df
else:
    filtered_df = st.session_state.filtered_df.copy()
    filtered_df["Delayed"] = filtered_df["Shipping_Lead_Time"] > threshold
    st.session_state.filtered_df = filtered_df

route_perf = (
    filtered_df.groupby("Factory_to_State_Route", as_index=False)
    .agg(
        Total_Shipments=("Order_ID", "count"),
        Average_Lead_Time=("Shipping_Lead_Time", "mean"),
        Delay_Frequency=("Delayed", "mean")
    )
)

state_perf = (
    filtered_df.groupby("State_Province", as_index=False)
    .agg(
        Total_Shipments=("Order_ID", "count"),
        Average_Lead_Time=("Shipping_Lead_Time", "mean"),
        Delay_Frequency=("Delayed", "mean")
    )
)

ship_mode_perf = (
    filtered_df.groupby("Ship_Mode", as_index=False)
    .agg(
        Total_Shipments=("Order_ID", "count"),
        Average_Lead_Time=("Shipping_Lead_Time", "mean"),
        Delay_Frequency=("Delayed", "mean")
    )
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Shipments", len(filtered_df))
col2.metric("Average Lead Time", round(filtered_df["Shipping_Lead_Time"].mean(), 2))
col3.metric("Delay Frequency %", round(filtered_df["Delayed"].mean() * 100, 2))
col4.metric("Total Sales", round(filtered_df["Sales"].sum(), 2) if "Sales" in filtered_df.columns else 0)

st.divider()

st.header("Route Efficiency Overview")
if route_perf.empty:
    st.info("No routes available for the current filters.")
else:
    route_perf = route_perf.copy()
    route_perf["Average_Lead_Time"] = route_perf["Average_Lead_Time"].round(2)
    route_perf["Delay_Frequency_%"] = (route_perf["Delay_Frequency"] * 100).round(2)

    st.dataframe(route_perf.sort_values("Average_Lead_Time"), use_container_width=True)

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
if state_perf.empty:
    st.info("No state-level data available for the current filters.")
else:
    state_perf = state_perf.copy()
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
if ship_mode_perf.empty:
    st.info("No ship mode data available for the current filters.")
else:
    ship_mode_perf = ship_mode_perf.copy()
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
route_options = sorted(filtered_df["Factory_to_State_Route"].dropna().unique())

if not route_options:
    st.info("No routes available to drill into for the current filters.")
else:
    selected_route = st.selectbox("Select Route", route_options)
    route_drill = filtered_df[filtered_df["Factory_to_State_Route"] == selected_route]

    drill_cols = [
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
    available_cols = [c for c in drill_cols if c in route_drill.columns]

    st.dataframe(
        route_drill[available_cols].sort_values("Shipping_Lead_Time", ascending=False),
        use_container_width=True
    )

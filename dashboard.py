"""
TailorAI Lakehouse Dashboard

A lightweight Streamlit dashboard to visualize job data from the Gold Delta table.
Run with: streamlit run dashboard.py
"""
import streamlit as st
import polars as pl
from deltalake import DeltaTable
from datetime import datetime

from backend.settings import settings


# Page configuration
st.set_page_config(
    page_title="TailorAI Lakehouse",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_gold_data() -> pl.DataFrame:
    """Load data from Gold Delta table."""
    storage_options = {
        "AWS_ENDPOINT_URL": f"http://{settings.MINIO_ENDPOINT}",
        "AWS_ACCESS_KEY_ID": settings.MINIO_ACCESS_KEY,
        "AWS_SECRET_ACCESS_KEY": settings.MINIO_SECRET_KEY,
        "AWS_REGION": "us-east-1",
        "AWS_ALLOW_HTTP": "true",
    }
    
    gold_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/gold/jobs"
    
    try:
        dt = DeltaTable(gold_path, storage_options=storage_options)
        return pl.from_arrow(dt.to_pyarrow_table())
    except Exception as e:
        st.error(f"Failed to load Gold table: {e}")
        return pl.DataFrame()


def main():
    # Header
    st.title("📊 TailorAI Lakehouse Dashboard")
    st.markdown("*Visualizing job data from the Delta Lake Gold layer*")
    
    # Load data
    df = load_gold_data()
    
    if df.is_empty():
        st.warning("No data available. Run the lakehouse pipeline first.")
        st.code("python3 -m lakehouse.bronze\npython3 -m lakehouse.silver\npython3 -m lakehouse.gold")
        return
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Company filter
    companies = ["All"] + sorted(df["company_name"].unique().to_list())
    selected_company = st.sidebar.selectbox("Company", companies)
    
    # Location filter
    locations = ["All"] + sorted([loc for loc in df["location"].unique().to_list() if loc])
    selected_location = st.sidebar.selectbox("Location", locations)
    
    # Seniority filter
    seniority_levels = ["All"] + sorted([s for s in df["seniority_level"].unique().to_list() if s])
    selected_seniority = st.sidebar.selectbox("Seniority Level", seniority_levels)
    
    # Apply filters
    filtered_df = df
    if selected_company != "All":
        filtered_df = filtered_df.filter(pl.col("company_name") == selected_company)
    if selected_location != "All":
        filtered_df = filtered_df.filter(pl.col("location") == selected_location)
    if selected_seniority != "All":
        filtered_df = filtered_df.filter(pl.col("seniority_level") == selected_seniority)
    
    # Metric cards
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Total Jobs", len(filtered_df))
    
    with col2:
        st.metric("🏢 Unique Companies", filtered_df["company_name"].n_unique())
    
    with col3:
        # Top poster
        if not filtered_df.is_empty():
            top_company = (
                filtered_df
                .group_by("company_name")
                .len()
                .sort("len", descending=True)
                .head(1)
            )
            if top_company.height > 0:
                st.metric("🏆 Top Poster", top_company["company_name"][0])
            else:
                st.metric("🏆 Top Poster", "-")
        else:
            st.metric("🏆 Top Poster", "-")
    
    with col4:
        # Last ingestion date
        if not filtered_df.is_empty() and "valid_from" in filtered_df.columns:
            last_date = filtered_df["valid_from"].max()
            if last_date:
                st.metric("📅 Last Ingestion", last_date.strftime("%Y-%m-%d"))
            else:
                st.metric("📅 Last Ingestion", "-")
        else:
            st.metric("📅 Last Ingestion", "-")
    
    # Charts row
    st.markdown("---")
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("📊 Jobs by Company (Top 10)")
        if not filtered_df.is_empty():
            company_counts = (
                filtered_df
                .group_by("company_name")
                .len()
                .sort("len", descending=True)
                .head(10)
                .rename({"len": "count"})
            )
            st.bar_chart(company_counts.to_pandas().set_index("company_name"))
        else:
            st.info("No data to display")
    
    with chart_col2:
        st.subheader("🎯 Jobs by Seniority Level")
        if not filtered_df.is_empty():
            seniority_counts = (
                filtered_df
                .filter(pl.col("seniority_level").is_not_null())
                .group_by("seniority_level")
                .len()
                .rename({"len": "count"})
            )
            if seniority_counts.height > 0:
                st.bar_chart(seniority_counts.to_pandas().set_index("seniority_level"))
            else:
                st.info("No seniority data available")
        else:
            st.info("No data to display")
    
    # Jobs table
    st.markdown("---")
    st.subheader("📋 Job Listings")
    
    # Search box
    search_term = st.text_input("🔎 Search jobs by title or description", "")
    
    display_df = filtered_df
    if search_term:
        display_df = display_df.filter(
            pl.col("title").str.contains(search_term, literal=False) |
            pl.col("description_text").str.contains(search_term, literal=False)
        )
    
    # Select columns to display
    display_columns = [
        "id", "title", "company_name", "location", 
        "seniority_level", "employment_type", "posted_at", "applicants_count"
    ]
    available_columns = [c for c in display_columns if c in display_df.columns]
    
    if not display_df.is_empty():
        st.dataframe(
            display_df.select(available_columns).to_pandas(),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"Showing {len(display_df)} of {len(df)} total jobs")
    else:
        st.info("No jobs match your filters")
    
    # Footer
    st.markdown("---")
    st.caption("Data sourced from Delta Lakehouse Gold layer")


if __name__ == "__main__":
    main()

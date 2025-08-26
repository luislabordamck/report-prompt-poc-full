
import os, json
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime

from agent import local_demo_answer, call_openai

st.set_page_config(page_title="COGs Report • Full Dashboard Agent", layout="wide")

DATA_PATH = "data_cogs_sample.xlsx"
PROMPT_FILE = "report_prompt.txt"
PROMPT_PACK = "prompt_pack.json"

@st.cache_data
def load_data():
    xl = pd.ExcelFile(DATA_PATH)
    df = pd.read_excel(xl, "line_items")
    daily = pd.read_excel(xl, "daily_summary")
    meta = pd.read_excel(xl, "data_dictionary")
    # types
    df["date"] = pd.to_datetime(df["date"])
    daily["date"] = pd.to_datetime(daily["date"])
    return df, daily, meta

df, daily, meta = load_data()

# --------------------
# Sidebar filters
# --------------------
st.sidebar.header("Filters")

date_min, date_max = daily["date"].min(), daily["date"].max()
date_range = st.sidebar.date_input("Date range", (date_min, date_max))

sites_all = sorted(df["site"].unique())
cust_all = sorted(df["customer_id"].unique())
prod_all = sorted(df["product_name"].unique())

sites = st.sidebar.multiselect("Sites", sites_all, default=sites_all)
customers = st.sidebar.multiselect("Customers", cust_all, default=cust_all)
products = st.sidebar.multiselect("Products", prod_all, default=prod_all)
generic_choice = st.sidebar.selectbox("Product type", ["All","Generic only","Brand only"], index=0)

mask = (
    (df["date"] >= pd.to_datetime(date_range[0])) &
    (df["date"] <= pd.to_datetime(date_range[1])) &
    (df["site"].isin(sites)) &
    (df["customer_id"].isin(customers)) &
    (df["product_name"].isin(products))
)
if generic_choice == "Generic only":
    mask &= df["is_generic"] == True
elif generic_choice == "Brand only":
    mask &= df["is_generic"] == False

df_f = df.loc[mask].copy()

daily_mask = (daily["date"] >= pd.to_datetime(date_range[0])) & (daily["date"] <= pd.to_datetime(date_range[1]))
daily_f = daily.loc[daily_mask].copy()
daily_f["margin_dollars"] = daily_f["daily_rev"] - daily_f["daily_cogs"]
daily_f["margin_pct"] = np.where(daily_f["daily_rev"]>0, daily_f["margin_dollars"]/daily_f["daily_rev"], np.nan)

# --------------------
# KPIs
# --------------------
st.title("COGs Dashboard + Report Agent")

k1, k2, k3, k4 = st.columns(4)
k1.metric("COGs", f"${daily_f['daily_cogs'].sum():,.0f}")
k2.metric("Revenue", f"${daily_f['daily_rev'].sum():,.0f}")
k3.metric("Avg GCR", f"{daily_f['avg_gcr'].mean():.2%}" if len(daily_f) else "—")
k4.metric("Margin %", f"{daily_f['margin_pct'].mean():.1%}" if len(daily_f) else "—")

# --------------------
# Tabs: Overview, Sites, Customers, Products
# --------------------
tab_over, tab_sites, tab_custs, tab_prods, tab_agent = st.tabs(
    ["Overview", "Sites", "Customers", "Products", "Ask the Agent"]
)

with tab_over:
    st.subheader("Trends")
    col1, col2 = st.columns(2)

    with col1:
        fig1, ax1 = plt.subplots()
        ax1.plot(daily_f["date"], daily_f["daily_cogs"])
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Daily COGs ($)")
        st.pyplot(fig1)

    with col2:
        fig2, ax2 = plt.subplots()
        ax2.plot(daily_f["date"], daily_f["avg_gcr"])
        ax2.set_xlabel("Date")
        ax2.set_ylabel("Average GCR")
        st.pyplot(fig2)

    fig3, ax3 = plt.subplots()
    ax3.plot(daily_f["date"], daily_f["margin_pct"])
    ax3.set_xlabel("Date")
    ax3.set_ylabel("Margin %")
    st.pyplot(fig3)

    st.subheader("Daily Summary (filtered)")
    st.dataframe(
        daily_f.sort_values("date").assign(
            daily_cogs=lambda x: x["daily_cogs"].round(2),
            daily_rev=lambda x: x["daily_rev"].round(2),
            avg_gcr=lambda x: x["avg_gcr"].round(4),
            margin_pct=lambda x: (x["margin_pct"]*100).round(2)
        ),
        use_container_width=True, height=300
    )

    # Download filtered extract
    st.download_button(
        "Download filtered line items (CSV)",
        data=df_f.to_csv(index=False).encode("utf-8"),
        file_name="filtered_line_items.csv",
        mime="text/csv"
    )

with tab_sites:
    st.subheader("Sites — COGs, Revenue, Margin")
    g = (df_f.groupby("site", as_index=False)
            .agg(
                cogs=("extended_cogs","sum"),
                rev=("extended_revenue","sum"),
                avg_gcr=("GCR","mean")
            ))
    g["margin"] = g["rev"] - g["cogs"]
    g["margin_pct"] = np.where(g["rev"]>0, g["margin"]/g["rev"], np.nan)
    st.dataframe(g.sort_values("cogs", ascending=False), use_container_width=True, height=350)

with tab_custs:
    st.subheader("Customers — COGs, Revenue, Margin")
    gc = (df_f.groupby("customer_id", as_index=False)
            .agg(
                cogs=("extended_cogs","sum"),
                rev=("extended_revenue","sum"),
                avg_gcr=("GCR","mean")
            ))
    gc["margin"] = gc["rev"] - gc["cogs"]
    gc["margin_pct"] = np.where(gc["rev"]>0, gc["margin"]/gc["rev"], np.nan)
    st.dataframe(gc.sort_values("cogs", ascending=False), use_container_width=True, height=350)

with tab_prods:
    st.subheader("Products — COGs, Revenue, Generic/Brand")
    gp = (df_f.groupby(["product_id","product_name","is_generic"], as_index=False)
            .agg(
                qty=("qty","sum"),
                cogs=("extended_cogs","sum"),
                rev=("extended_revenue","sum")
            ))
    gp["margin"] = gp["rev"] - gp["cogs"]
    gp["margin_pct"] = np.where(gp["rev"]>0, gp["margin"]/gp["rev"], np.nan)
    st.dataframe(gp.sort_values("cogs", ascending=False), use_container_width=True, height=400)

with tab_agent:
    st.subheader("Ask the Report Agent")
    with open(PROMPT_PACK, "r", encoding="utf-8") as f:
        pack = json.load(f)
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    prompt_def = pack["prompts"][0]

    default_q = prompt_def["defaults"]["question"]
    question = st.text_input("Your question", value=default_q, key="agent_question")

    # Compact context for the agent
    ctx = {
        "date_start": str(pd.to_datetime(date_range[0]).date()),
        "date_end": str(pd.to_datetime(date_range[1]).date()),
        "sites": sites,
        "customers": customers,
        "products": products,
        "generic_filter": generic_choice,
        "headline": {
            "cogs_sum": float(daily_f["daily_cogs"].sum() if len(daily_f) else 0.0),
            "rev_sum": float(daily_f["daily_rev"].sum() if len(daily_f) else 0.0),
            "avg_gcr": float(daily_f["avg_gcr"].mean() if len(daily_f) else 0.0),
            "avg_margin_pct": float(daily_f["margin_pct"].mean() if len(daily_f) else 0.0),
        },
        "samples": {
            "daily": daily_f.tail(21).to_dict(orient="records"),
            "sites": (df_f.groupby("site").agg(cogs=("extended_cogs","sum")).reset_index()
                        .to_dict(orient="records")),
            "customers": (df_f.groupby("customer_id").agg(cogs=("extended_cogs","sum")).reset_index()
                        .to_dict(orient="records")),
            "products": (df_f.groupby(["product_id","product_name"]).agg(cogs=("extended_cogs","sum")).reset_index()
                        .to_dict(orient="records"))
        }
    }

    mode = st.radio("Analysis mode", ["LOCAL-DEMO", "OPENAI"],
                    captions=["No API needed; quick heuristics.", "Use OpenAI API for richer insights."])

    if st.button("Analyze with Agent"):
        if mode == "LOCAL-DEMO":
            answer = local_demo_answer(ctx, question)
        else:
            answer = call_openai(system_prompt, ctx, question)

        st.subheader("Insights")
        if "key_insights" in answer:
            for item in answer["key_insights"]:
                st.write(item)
        else:
            st.write(answer)

        if "narrative" in answer and answer["narrative"]:
            st.subheader("Narrative")
            st.write(answer["narrative"])

        if "next_questions" in answer:
            st.subheader("Suggested next questions")
            for q in answer["next_questions"]:
                st.caption(f"• {q}")

        # Render chart suggestion if compatible
        if "chart_suggestions" in answer and isinstance(answer["chart_suggestions"], list):
            for cs in answer["chart_suggestions"][:2]:
                if cs.get("type") == "line" and "x" in cs and "y" in cs:
                    st.subheader("Chart suggestion")
                    ycols = [c for c in cs["y"] if c in daily_f.columns]
                    fig, ax = plt.subplots()
                    for y in ycols:
                        ax.plot(daily_f[cs["x"]], daily_f[y], label=y)
                    ax.set_xlabel(cs["x"])
                    ax.set_ylabel(", ".join(ycols))
                    ax.legend()
                    st.pyplot(fig)
                    if cs.get("note"):
                        st.caption(cs["note"])

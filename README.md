# Report-as-a-Prompt (POC): COGs + GCR

This POC shows how to treat a **report as a predefined prompt**. You load an Excel file (our "DB"), explore charts, and ask an LLM questions about the report. The LLM answers with **Key Insights**, a short **narrative**, and **next questions**, while your charts stay in view.

## What's included

- `data_cogs_sample.xlsx` — 3 months of synthetic line-items + daily summary
- `report_prompt.txt` — system prompt for a focused "Report LLM"
- `prompt_pack.json` — one predefined prompt entry ("COGs + GCR Overview")
- `app.py` — a Streamlit app that loads the Excel "DB", plots trends, and lets you query the report
- This README

## How to run

1. Create a new virtual environment and install deps:

```bash
pip install streamlit pandas numpy openpyxl xlsxwriter matplotlib openai
```

2. Put all files in the same folder. Then run:

```bash
streamlit run app.py
```

3. Use **LOCAL-DEMO** mode to try it without any API.
4. For **OPENAI** mode, set an environment variable with your key:

```bash
export OPENAI_API_KEY="sk-..."
```

## How it works

- The app loads the Excel "DB" and applies your filters (date range, sites, customers).
- It shows **COGs**, **Revenue**, **Avg GCR**, and **Margin %** at the top.
- It plots three basic trends (COGs, GCR, Margin%). (You can expand this.)
- When you ask the report a question, the app builds a **compact context**:
  - Selected dates/sites/customers
  - Headline metrics
  - Small, recent samples (to keep tokens low)
- The **system prompt** (`report_prompt.txt`) instructs the LLM how to answer (JSON with insights, narrative, next questions, and chart suggestions).
- The **prompt pack** (`prompt_pack.json`) defines a reusable prompt template so you can add more "report prompts" later.

## Extend it

- Add more prompts in `prompt_pack.json` (e.g., "COGs Drivers", "Customer Variance", "Site Benchmarking").
- Add more charts & drill-downs in `app.py` (e.g., per-site COGs by week, GCR quantiles vs margin%).
- Swap the LLM (OpenAI, Azure OpenAI, local models via ollama/llama.cpp) — keep the same system prompt and payload.

## Notes

- In pharma, **GCR** is typically "Generic Compliance Ratio". Here we simulate it as the share of generic units per date/site/customer. Higher GCR often correlates with cost efficiency, but always validate with your real data.
- **COGs** is calculated from discounted WAC and negotiated adjustments (simplified here). Adjust to match your business logic.
- This is a learning scaffold — refine the schema, prompts, and visual design for production.
## What’s new in the full dashboard
- Multi-tab layout (Overview, Sites, Customers, Products, Ask the Agent)
- Interactive tables with COGs/Revenue/Margin by site, customer, and product
- Download filtered line items as CSV
- Agent panel renders insights + narrative; can also render an extra chart suggested by the agent

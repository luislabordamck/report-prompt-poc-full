
import json
import numpy as np

def local_demo_answer(context, question: str):
    """Heuristic 'agent' that analyzes the filtered context and returns structured insights."""
    notes = []
    narrative = []
    next_q = []

    trend = context.get("samples", {}).get("daily", [])
    sites_rows = context.get("samples", {}).get("sites", [])
    cust_rows = context.get("samples", {}).get("customers", [])
    prod_rows = context.get("samples", {}).get("products", [])

    # Correlation (GCR vs COGs) on the sample window
    if len(trend) >= 5:
        d_cogs = np.array([x.get("daily_cogs", 0.0) for x in trend], dtype=float)
        d_gcr = np.array([x.get("avg_gcr", 0.0) for x in trend], dtype=float)
        if np.std(d_gcr) > 1e-6 and np.std(d_cogs) > 1e-6:
            corr = float(np.corrcoef(d_gcr, d_cogs)[0,1])
            notes.append(f"GCR↔COGs correlation on the last {len(trend)} days: {corr:+.2f} (indicative).")
        else:
            notes.append("Not enough variance to relate GCR to COGs in the recent window.")
    else:
        notes.append("Not enough recent days to compute a meaningful correlation (need ≥5).")

    # Top drivers
    if sites_rows:
        top_site = max(sites_rows, key=lambda r: r["cogs"])
        notes.append(f"Top site by COGs: {top_site['site']} (${top_site['cogs']:,.0f}).")
    if cust_rows:
        top_c = max(cust_rows, key=lambda r: r["cogs"])
        notes.append(f"Top customer by COGs: {top_c['customer_id']} (${top_c['cogs']:,.0f}).")
    if prod_rows:
        top_p = max(prod_rows, key=lambda r: r["cogs"])
        notes.append(f"Top product by COGs: {top_p['product_name']} ({top_p['product_id']}).")

    # Margin context
    notes.append(f"Avg margin% in scope: {context['headline'].get('avg_margin_pct', 0.0):.1%}.")

    narrative.append(
        "Within the selected filters, COGs is concentrated among a few sites/customers/products. "
        "Monitor how generic mix (GCR) moves relative to COGs: if correlation is negative, higher GCR may be lowering cost. "
        "Focus where COGs is highest and GCR is lagging."
    )

    next_q = [
        "On which dates did COGs spike with low GCR, and who drove it?",
        "Which products have the highest COGs at the lowest GCR deciles?",
        "Are margin% improvements aligned with GCR increases by site?"
    ]

    return {
        "key_insights": [f"• {x}" for x in notes],
        "narrative": " ".join(narrative)[:600],
        "next_questions": next_q,
        "chart_suggestions": [
            {"type":"line","x":"date","y":["daily_cogs","avg_gcr"],"note":"Dual-axis if available; else two panels."}
        ]
    }

def call_openai(system_prompt: str, context: dict, question: str):
    """Optional OpenAI call; returns parsed JSON or text fallback."""
    import os
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY",""))
    payload = json.dumps({"context": context, "question": question})
    messages = [
        {"role":"system","content": system_prompt},
        {"role":"user","content": payload}
    ]
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2
    )
    content = resp.choices[0].message.content
    try:
        return json.loads(content)
    except Exception:
        return {"raw": content}

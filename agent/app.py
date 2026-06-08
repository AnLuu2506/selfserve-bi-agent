"""Streamlit front end. Run locally for testing:
    streamlit run agent/app.py
On the VM it is served by docker-compose on port 8501.
"""
import streamlit as st
from dotenv import load_dotenv

from agent import answer
from guardrails import UnsafeQuery

load_dotenv()

st.set_page_config(page_title="Ask the data", page_icon="📊")
st.title("📊 Self-serve analytics agent")
st.caption("Ask a business question in plain language. The agent writes SQL, you see exactly what it ran.")

examples = [
    "Total revenue by region last quarter",
    "Top 5 products by revenue",
    "Which category grew the most month over month?",
]
with st.sidebar:
    st.subheader("Try")
    for ex in examples:
        if st.button(ex):
            st.session_state["q"] = ex

q = st.text_input("Your question", key="q", placeholder="e.g. revenue by category in 2025")

if q:
    with st.spinner("Thinking..."):
        try:
            sql, df = answer(q)
            st.success(f"{len(df)} rows")
            st.dataframe(df, use_container_width=True)
            # Auto-chart when the shape is chartable.
            numeric = df.select_dtypes("number").columns
            if len(df) > 1 and len(numeric) >= 1 and len(df.columns) >= 2:
                st.bar_chart(df.set_index(df.columns[0])[numeric[-1]])
            with st.expander("SQL the agent ran"):
                st.code(sql, language="sql")
        except UnsafeQuery as e:
            st.error(f"Rejected for safety: {e}")
        except Exception as e:
            st.warning(f"Could not answer that from the available data. ({e})")

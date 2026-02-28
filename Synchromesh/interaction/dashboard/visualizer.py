import streamlit as st
import pandas as pd

def render_metrics(context_store):
    st.subheader("📊 Modernization Metrics")
    
    # Mock data for demonstration - in production, this pulls from evaluation module
    parity_data = {
        "Metric": ["Design-Token Parity", "Drift Reduction", "Coverage"],
        "Value": [72.5, 85.0, 91.2]
    }
    df = pd.DataFrame(parity_data)
    
    st.metric(label="Current Parity Score", value="72.5%", delta="12.4%")
    st.bar_chart(df.set_index("Metric"))
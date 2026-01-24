import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import random

st.set_page_config(layout="wide", page_title="FraudGuard - Case Management")

st.title("🕵️‍♂️ FraudGuard - Case Management Dashboard")
st.caption("Alice - Fraud Analyst View")

# --- Placeholder Data ---
# In a real scenario, this data would come from a Kafka topic or PostgreSQL
def get_placeholder_alerts():
    """Generate realistic alert data with different risk levels."""
    base_time = datetime.now()

    return [
        # HIGH RISK (score >= 0.7)
        {"event_id": "evt_001", "score": 0.98, "decision": "DENY", "amount": 9500.75, "merchant": "suspicious-crypto.ru", "country": "RU", "status": "Pending Review", "timestamp": (base_time - timedelta(minutes=5)).isoformat(), "user_id": "u_789"},
        {"event_id": "evt_002", "score": 0.92, "decision": "DENY", "amount": 4500.00, "merchant": "unknown-vendor.cn", "country": "CN", "status": "Pending Review", "timestamp": (base_time - timedelta(minutes=12)).isoformat(), "user_id": "u_456"},
        {"event_id": "evt_003", "score": 0.85, "decision": "CHALLENGE", "amount": 3200.50, "merchant": "electronics-bulk.com", "country": "US", "status": "Pending Review", "timestamp": (base_time - timedelta(minutes=18)).isoformat(), "user_id": "u_123"},
        {"event_id": "evt_004", "score": 0.78, "decision": "CHALLENGE", "amount": 1800.00, "merchant": "gift-cards-online.net", "country": "NL", "status": "Pending Review", "timestamp": (base_time - timedelta(minutes=25)).isoformat(), "user_id": "u_321"},

        # MEDIUM RISK (0.3 <= score < 0.7)
        {"event_id": "evt_005", "score": 0.65, "decision": "CHALLENGE", "amount": 850.00, "merchant": "travel-agency.com", "country": "FR", "status": "Pending Review", "timestamp": (base_time - timedelta(minutes=30)).isoformat(), "user_id": "u_654"},
        {"event_id": "evt_006", "score": 0.58, "decision": "CHALLENGE", "amount": 450.75, "merchant": "online-shop.de", "country": "DE", "status": "Pending Review", "timestamp": (base_time - timedelta(minutes=45)).isoformat(), "user_id": "u_987"},
        {"event_id": "evt_007", "score": 0.45, "decision": "APPROVE", "amount": 125.00, "merchant": "supermarket-chain.fr", "country": "FR", "status": "Pending Review", "timestamp": (base_time - timedelta(minutes=60)).isoformat(), "user_id": "u_234"},
        {"event_id": "evt_008", "score": 0.38, "decision": "APPROVE", "amount": 89.99, "merchant": "restaurant-paris.fr", "country": "FR", "status": "Pending Review", "timestamp": (base_time - timedelta(hours=2)).isoformat(), "user_id": "u_567"},

        # LOW RISK (score < 0.3)
        {"event_id": "evt_009", "score": 0.25, "decision": "APPROVE", "amount": 45.50, "merchant": "local-bakery.fr", "country": "FR", "status": "Pending Review", "timestamp": (base_time - timedelta(hours=3)).isoformat(), "user_id": "u_890"},
        {"event_id": "evt_010", "score": 0.18, "decision": "APPROVE", "amount": 12.00, "merchant": "coffee-shop.fr", "country": "FR", "status": "Pending Review", "timestamp": (base_time - timedelta(hours=4)).isoformat(), "user_id": "u_111"},
        {"event_id": "evt_011", "score": 0.12, "decision": "APPROVE", "amount": 8.50, "merchant": "parking-meter.fr", "country": "FR", "status": "Pending Review", "timestamp": (base_time - timedelta(hours=5)).isoformat(), "user_id": "u_222"},

        # REVIEWED (for history)
        {"event_id": "evt_012", "score": 0.89, "decision": "DENY", "amount": 5000.00, "merchant": "scam-site.com", "country": "XX", "status": "Confirmed Fraud", "timestamp": (base_time - timedelta(hours=6)).isoformat(), "user_id": "u_333"},
        {"event_id": "evt_013", "score": 0.72, "decision": "CHALLENGE", "amount": 1200.00, "merchant": "legit-store.com", "country": "US", "status": "False Positive", "timestamp": (base_time - timedelta(hours=8)).isoformat(), "user_id": "u_444"},
    ]

def classify_risk_level(score):
    """Classify transaction risk level based on score."""
    if score >= 0.7:
        return "🔴 HIGH"
    elif score >= 0.3:
        return "🟡 MEDIUM"
    else:
        return "🟢 LOW"

# --- Load Data ---
alerts_df = pd.DataFrame(get_placeholder_alerts())
alerts_df['risk_level'] = alerts_df['score'].apply(classify_risk_level)
alerts_df = alerts_df.sort_values(by="score", ascending=False)

# --- Metrics Overview ---
st.header("📊 Queue Overview")

col1, col2, col3, col4 = st.columns(4)

pending_alerts = alerts_df[alerts_df['status'] == 'Pending Review']
high_risk_count = len(pending_alerts[pending_alerts['risk_level'] == '🔴 HIGH'])
medium_risk_count = len(pending_alerts[pending_alerts['risk_level'] == '🟡 MEDIUM'])
low_risk_count = len(pending_alerts[pending_alerts['risk_level'] == '🟢 LOW'])
total_pending = len(pending_alerts)

col1.metric("🔴 High Risk", high_risk_count, help="Score >= 0.7")
col2.metric("🟡 Medium Risk", medium_risk_count, help="0.3 <= Score < 0.7")
col3.metric("🟢 Low Risk", low_risk_count, help="Score < 0.3")
col4.metric("📋 Total Pending", total_pending)

# --- Queue Tabs ---
st.header("🗂️ Alert Queues")

tab1, tab2, tab3, tab4 = st.tabs(["🔴 High Risk", "🟡 Medium Risk", "🟢 Low Risk", "📜 History"])

with tab1:
    st.subheader("High Risk Queue (Score >= 0.7)")
    st.caption("⚡ Priority alerts requiring immediate investigation")

    high_risk_df = pending_alerts[pending_alerts['risk_level'] == '🔴 HIGH']

    if len(high_risk_df) > 0:
        # Display with color coding
        st.dataframe(
            high_risk_df[['event_id', 'score', 'amount', 'merchant', 'country', 'decision', 'timestamp']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ No high risk alerts pending")

with tab2:
    st.subheader("Medium Risk Queue (0.3 <= Score < 0.7)")
    st.caption("⚠️ Moderate priority alerts")

    medium_risk_df = pending_alerts[pending_alerts['risk_level'] == '🟡 MEDIUM']

    if len(medium_risk_df) > 0:
        st.dataframe(
            medium_risk_df[['event_id', 'score', 'amount', 'merchant', 'country', 'decision', 'timestamp']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("ℹ️ No medium risk alerts pending")

with tab3:
    st.subheader("Low Risk Queue (Score < 0.3)")
    st.caption("✅ Low priority alerts - routine review")

    low_risk_df = pending_alerts[pending_alerts['risk_level'] == '🟢 LOW']

    if len(low_risk_df) > 0:
        st.dataframe(
            low_risk_df[['event_id', 'score', 'amount', 'merchant', 'country', 'decision', 'timestamp']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ No low risk alerts pending")

with tab4:
    st.subheader("Reviewed Alerts History")
    st.caption("📜 Previously reviewed cases")

    reviewed_df = alerts_df[alerts_df['status'].isin(['Confirmed Fraud', 'False Positive'])]

    if len(reviewed_df) > 0:
        st.dataframe(
            reviewed_df[['event_id', 'score', 'amount', 'merchant', 'status', 'timestamp']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No reviewed alerts yet")

# --- Alert Detail Review ---
st.header("🔍 Alert Review")

# Filter to only pending alerts
pending_event_ids = pending_alerts['event_id'].tolist()

if len(pending_event_ids) > 0:
    selected_event_id = st.selectbox(
        "Select an Event ID to review:",
        pending_event_ids,
        help="Choose an alert to investigate and take action"
    )

    if selected_event_id:
        alert_details = alerts_df[alerts_df['event_id'] == selected_event_id].iloc[0]

        st.subheader(f"Reviewing Event: `{alert_details['event_id']}`")

        # Risk badge
        risk_level = alert_details['risk_level']
        st.markdown(f"**Risk Level:** {risk_level}")

        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Risk Score", f"{alert_details['score']:.2f}")
        col2.metric("Decision", alert_details['decision'])
        col3.metric("Amount", f"€{alert_details['amount']:.2f}")
        col4.metric("Country", alert_details['country'])

        st.write(f"**Merchant:** `{alert_details['merchant']}`")
        st.write(f"**User ID:** `{alert_details['user_id']}`")
        st.write(f"**Timestamp:** `{alert_details['timestamp']}`")

        # Additional context
        with st.expander("📋 Additional Context"):
            st.write("**Transaction Details:**")
            st.json({
                "event_id": alert_details['event_id'],
                "risk_score": alert_details['score'],
                "amount": alert_details['amount'],
                "merchant": alert_details['merchant'],
                "country": alert_details['country'],
                "user_id": alert_details['user_id']
            })

        st.subheader("✅ Analyst Action")

        col1_action, col2_action, col3_action = st.columns(3)

        with col1_action:
            if st.button("🚨 Confirm as Fraud", type="primary", use_container_width=True):
                st.success(f"✅ Event {selected_event_id} marked as 'Confirmed Fraud'.")
                st.info("📤 Feedback sent to ML model for retraining.")
                # In a real app, this would:
                # 1. Update PostgreSQL cases table
                # 2. Produce message to Kafka 'fraud-feedback' topic
                # 3. Trigger ML model retraining pipeline

        with col2_action:
            if st.button("✅ Mark as False Positive", use_container_width=True):
                st.warning(f"⚠️ Event {selected_event_id} marked as 'False Positive'.")
                st.info("📤 Feedback sent to ML model for retraining.")
                # In a real app, same as above

        with col3_action:
            if st.button("⏭️ Skip / Escalate", use_container_width=True):
                st.info(f"ℹ️ Event {selected_event_id} escalated to senior analyst.")
else:
    st.success("🎉 All alerts have been reviewed! No pending cases.")

# --- Footer ---
st.divider()
st.caption("SafeGuard Financial - Case Management System v1.0")
st.caption("💡 **Note**: This is a demo interface. In production, data comes from Kafka and PostgreSQL.")

# TODO:
# 1. Replace placeholder with real Kafka consumer or PostgreSQL query
# 2. Implement Kafka producer to send feedback to 'fraud-feedback' topic
# 3. Add customer history view (past transactions, risk profile)
# 4. Add real-time updates using Streamlit auto-refresh
# 5. Implement pagination for large alert volumes


import streamlit as st
import pandas as pd
import plotly.express as px
import csv
import os
from utils import check_and_initialize_user_data
def portfolio():
    st.markdown("<h3 style='color: white;'>Portfolio Overview</h3>", unsafe_allow_html=True)
    username = st.session_state.get("login_username", "")
    if not username:
        st.error("User not logged in!")
        return

    user_file = check_and_initialize_user_data()
    if not os.path.exists(user_file):
        st.error(f"User data file not found: {user_file}. Please upload your data file.")
        return

    tag_mapping_file = "data/tag_mapping.csv"
    if not os.path.exists(tag_mapping_file):
        st.error(f"Tag mapping file not found: {tag_mapping_file}. Please ensure the file exists.")
        return

    try:
        df = pd.read_csv(user_file)
        if df.empty:
            st.warning("No transactions available for this user. Please add transactions to view the portfolio.")
            return

        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['month'] = df['date'].dt.strftime('%B')
        df['year'] = df['date'].dt.year
        df['tags'] = df['tags'].str.split(',')

        tag_mapping_df = pd.read_csv(tag_mapping_file)
        tag_mapping = pd.Series(tag_mapping_df['category'].values, index=tag_mapping_df['tag'].str.lower()).to_dict()
        df = df.explode('tags')
        df['tags'] = df['tags'].str.strip().str.lower()
        df['category'] = df['tags'].map(tag_mapping).fillna('Uncategorized')
        total_spent = df[df['category'] != 'Income']['amount'].sum()
        total_income = df[df['category'] == 'Income']['amount'].sum()
        savings = total_income - total_spent

        # Display summary
        st.write("### Summary")
        st.metric("Total Income", f"₹{total_income:,.2f}")
        st.metric("Total Spent", f"₹{total_spent:,.2f}")
        st.metric("Savings", f"₹{savings:,.2f}")

        # Spending distribution by category
        st.write("### Spending Distribution by Category")
        category_totals = df[df['category'] != 'Income'].groupby('category')['amount'].sum().reset_index()
        fig = px.pie(
            category_totals,
            names='category',
            values='amount',
            title="Spending Distribution",
            hole=0.5
        )
        fig.update_traces(hovertemplate='%{label}: ₹%{value:,.2f}<extra></extra>')
        st.plotly_chart(fig)

        # Spending trends over time
        st.write("### Spending Trends")
        df['month_year'] = df['date'].dt.to_period('M').dt.to_timestamp()
        spending_trends = df[df['category'] != 'Income'].groupby('month_year')['amount'].sum().reset_index()
        fig = px.line(
            spending_trends,
            x='month_year',
            y='amount',
            title="Monthly Spending Trends",
            labels={'amount': 'Spent (₹)', 'month_year': 'Month'},
            markers=True
        )
        fig.update_layout(xaxis=dict(title="Month"), yaxis=dict(title="Amount Spent (₹)"))
        st.plotly_chart(fig)

        # Savings trends over time
        st.write("### Savings Trends")
        savings_trends = (
            df.groupby('month_year')
            .apply(lambda x: x[x['category'] == 'Income']['amount'].sum() - x[x['category'] != 'Income']['amount'].sum())
            .reset_index(name='savings')
        )
        fig = px.bar(
            savings_trends,
            x='month_year',
            y='savings',
            title="Monthly Savings Trends",
            labels={'savings': 'Savings (₹)', 'month_year': 'Month'},
            color='savings',
            color_continuous_scale=['red', 'green'],
        )
        fig.update_layout(xaxis=dict(title="Month"), yaxis=dict(title="Savings (₹)"))
        st.plotly_chart(fig)

        # Spending breakdown by individual categories
        st.write("### Detailed Spending Breakdown")
        category_breakdown = df[df['category'] != 'Income'].groupby(['category', 'month_year'])['amount'].sum().reset_index()
        fig = px.bar(
            category_breakdown,
            x='month_year',
            y='amount',
            color='category',
            title="Spending Breakdown by Category",
            labels={'amount': 'Spent (₹)', 'month_year': 'Month'},
        )
        fig.update_layout(xaxis=dict(title="Month"), yaxis=dict(title="Amount Spent (₹)"))
        st.plotly_chart(fig)

    except Exception as e:
        st.error(f"Error processing portfolio: {str(e)}")

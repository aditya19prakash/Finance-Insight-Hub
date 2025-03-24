import time
import plotly.express as px
import os
import pandas as pd
import streamlit as st
from utils import check_and_initialize_user_data
def budget():
    st.markdown("<h3 style='color: white;'>Budget</h3>", unsafe_allow_html=True)
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
            st.warning("No transactions available for this user. Please add transactions to view the budget.")
            return

        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['month'] = df['date'].dt.strftime('%B')
        df['year'] = df['date'].dt.year
        df['tags'] = df['tags'].str.split(',')

        tag_mapping_df = pd.read_csv(tag_mapping_file)
        tag_mapping = pd.Series(tag_mapping_df['category'].values, index=tag_mapping_df['tag'].str.lower()).to_dict()
        unique_months = df['month'].unique()
        years = sorted(df['year'].dropna().astype(int).unique())
        if not years:
            st.warning("No data available")
            return
        selected_year = st.selectbox("Select Year", years, index=len(years) - 1)
        selected_month = st.selectbox("Select Month", unique_months, index=0)

        current_month = pd.to_datetime('today').strftime('%B')
        current_year = pd.to_datetime('today').year
        is_current_period = (selected_month == current_month and selected_year == current_year)
        is_previous_period = (selected_year < current_year) or (selected_year == current_year and unique_months.tolist().index(selected_month) < unique_months.tolist().index(current_month))

        current_df = df[(df['month'] == selected_month) & (df['year'] == selected_year)]
        current_df = current_df.explode('tags')
        current_df['tags'] = current_df['tags'].str.strip().str.lower()
        current_df['category'] = current_df['tags'].map(tag_mapping).fillna('Uncategorized')

        current_df = current_df[current_df['category'] != 'Income']

        budget_file = f"data/{username}/{selected_year}_{selected_month}_budget.csv"

        try:
            budget_df = pd.read_csv(budget_file)
            existing_budgets = dict(zip(budget_df['Category'], budget_df['Budget']))
        except FileNotFoundError:
            existing_budgets = {}

        category_totals = current_df.groupby('category')['amount'].sum()

        budget_overview = pd.DataFrame({
            'Category': category_totals.index,
            'Spent': category_totals.values.astype(int),
            'Budget': [existing_budgets.get(category, 0.0) for category in category_totals.index],
        })
        budget_overview['Budget'] = budget_overview['Budget'].apply(
            lambda x: "Budget is not set" if x == 0 else f"{int(x)}"
        )
        budget_overview['Remaining'] = budget_overview['Budget'].apply(
            lambda x: 0 if x == "Budget is not set" else float(x)
        ) - budget_overview['Spent']
        budget_overview['Status'] = budget_overview['Remaining'].apply(
            lambda x: 'Within Budget' if x >= 0 else 'Exceeding Budget'
        )
        budget_overview['Remaining'] = budget_overview['Remaining'].astype(int)
        st.write(f"### Budget Overview for {selected_month} {selected_year}")
        st.table(budget_overview.round(2))
        st.write("### Budget Usage")
        budget_overview['Color'] = budget_overview['Status'].map({'Within Budget': 'green', 'Exceeding Budget': 'red'})
        charts_per_row = 2
        categories = budget_overview['Category'].unique()
        for i in range(0, len(categories), charts_per_row):
          cols = st.columns(charts_per_row)
          for j in range(charts_per_row):
              if i + j < len(categories):
                  category = categories[i + j]
                  row = budget_overview[budget_overview['Category'] == category].iloc[0]
                  fig = px.pie(
                names=['Spent', 'Remaining'],
                values=[row['Spent'], max(0, row['Remaining'])],
                color=['Spent', 'Remaining'],
                color_discrete_map={'Spent': row['Color'], 'Remaining': 'red'},
                hole=0.5,
                title=f"{row['Category']} Budget Usage<br><sub>Status: {row['Status']}</sub>"
            )

                  fig.update_traces(
                hovertemplate='%{label}: %{value}<extra></extra>'
            )
                  fig.update_layout(
                annotations=[
                    dict(
                        text=f"<b>{row['Category']}</b>",
                        x=0.5,
                        y=0.5,
                        font_size=14,
                        showarrow=False
                    )
                ],
                showlegend=False,
                width=350,
                height=350
            )
                  cols[j].plotly_chart(fig)
        if is_current_period:
            st.write("### Set Budget")
            budget_settings = {}
            for category in current_df['category'].unique():
                default_value = existing_budgets.get(category, 0.0)
                try:
                    input_value = st.text_input(
                        f"Budget for {category}",
                        value=str(default_value)
                    )
                    # Check if input is a valid float
                    if input_value and input_value.replace(".", "").isdigit():
                        budget_settings[category] = float(input_value)
                    else:
                        st.error(f"Please enter a valid number for {category}")
                        budget_settings[category] = default_value
                except ValueError:
                    st.error(f"Invalid input for {category}. Using default value.")
                    budget_settings[category] = default_value
            if st.button("Save Budget"):
                budget_data = pd.DataFrame({
                    'Category': list(budget_settings.keys()),
                    'Budget': list(budget_settings.values())
                })
                budget_data.to_csv(budget_file, index=False)
                st.success("Budget saved successfully!")
                time.sleep(2)
                st.rerun()
        elif is_previous_period:
            st.warning("Budget settings for previous months are locked. You can only view the overview.")

    except Exception as e:
        st.error(f"Error processing budget: {str(e)}")
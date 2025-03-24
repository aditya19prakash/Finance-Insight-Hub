import streamlit as st
import pandas as pd
import plotly.express as px
from utils import check_and_initialize_user_data

def format_amount(amount):
    """Formats the amount in Indian numbering style."""
    return '₹{:,.0f}'.format(amount).replace(',', 'X').replace('X', ',', 1) 

def summary():
    st.markdown("<h3 style='color: white;'>Summary</h3>", unsafe_allow_html=True)
    username = st.session_state.get("login_username", "")
    if not username:
        st.error("User not logged in!")
        return    
    user_file = check_and_initialize_user_data()
    if not user_file:
        st.warning("No file uploaded.")
        return
    try:
        df = pd.read_csv(user_file)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        df['month'] = df['date'].dt.strftime('%B')
        df['year'] = df['date'].dt.year
        years = sorted(df['year'].dropna().astype(int).unique())
        if not years:
            st.warning("No data available")
            return
        selected_year = st.selectbox("Select Year", years, index=len(years) - 1)
        yearly_df = df[df['year'] == selected_year]
        monthly_totals = yearly_df.groupby('month')['amount'].sum().reindex([
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]).fillna(0)
        formatted_amounts = monthly_totals.apply(format_amount)
        plot_df = pd.DataFrame({
            'Month': monthly_totals.index,
            'Amount': monthly_totals.values
        })
        fig = px.bar(
            plot_df,
            x='Month',
            y='Amount',
            title=f'Monthly Transactions - {selected_year}',
            labels={'Month': 'Month', 'Amount': 'Total Amount'}
        )
        fig.update_traces(
            selector=dict(type='bar'),
            marker_color='rgb(158,202,225)',
            marker_line_color='rgb(8,48,107)',
            marker_line_width=1.5,
            opacity=0.8,
            width=0.8,
            hovertemplate='<span style="font-size: 20px">%{x}: %{customdata[0]}</span><extra></extra>',
            customdata=[[formatted_amounts[i]] for i in range(len(formatted_amounts))]
        )
        fig.update_layout(
            width=1200,
            height=600,
            font=dict(size=18),
            title_font_size=32,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                showgrid=False,
                showline=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=1.5,
                tickfont=dict(size=20)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgb(204, 204, 204)',
                showline=True,
                linecolor='rgb(204, 204, 204)',
                linewidth=1.5,
                tickfont=dict(size=20)
            )
        )
        st.plotly_chart(fig)
        try:
            tag_mapping_df = pd.read_csv("data/tag_mapping.csv")
            tag_mapping = pd.Series(tag_mapping_df['category'].values, index=tag_mapping_df['tag'].str.lower()).to_dict()
        except Exception as e:
            st.error("Failed to load tag mapping from CSV.")
            return
        try: 
            st.subheader("Spending by Tags")
            tags_df = yearly_df.assign(tags=yearly_df['tags'].astype(str).str.split(',')).explode('tags')
            tags_df['tags'] = tags_df['tags'].str.strip().str.lower()
            tags_df['category'] = tags_df['tags'].map(tag_mapping).fillna('Uncategorized')
            category_totals = tags_df.groupby('category')['amount'].sum()
            
            tag_df = pd.DataFrame({
                'Category': category_totals.index,
                'Amount (₹)': category_totals.values
            })
            tag_df['Amount (₹)'] = tag_df['Amount (₹)'].apply(lambda x: f"₹{x:,.2f}")
            st.table(tag_df)
            
            total_amount = yearly_df['amount'].sum()
            st.write(f"Total amount spent in {selected_year}: ₹{total_amount:,.2f}")
        except Exception as e:
            st.error(f"Error processing tags: {str(e)}")

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")

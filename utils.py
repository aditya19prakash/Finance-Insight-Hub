import streamlit as st
import csv
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import plotly.express as px
import os

def check_and_initialize_user_data():
    """Ensure the user's data directory and file exist."""
    username = st.session_state.get("login_username", "")
    if not username:
        st.error("User not logged in!")
        return False
    user_directory = os.path.join("data", username)
    user_file = os.path.join(user_directory, f"{username}_data.csv")
    if not os.path.exists(user_directory):
        os.makedirs(user_directory)
    if not os.path.exists(user_file):
        with open(user_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['date', 'Account Name', 'description', 'amount', 'category', 'type', 'payment_method', 'tags'])
        st.info(f"Data file created for {username}. Start by adding your first transaction.")
    return user_file

def add_transaction():
    try:
        try:
            tag_mapping_df = pd.read_csv("data/tag_mapping.csv")
            tag_mapping = pd.Series(tag_mapping_df['category'].values, index=tag_mapping_df['tag'].str.lower()).to_dict()
        except Exception as e:
            st.error("Failed to load tag mapping from CSV.")
            return
        user_file = check_and_initialize_user_data()
        username = st.session_state.get("login_username", "")
        if not username:
            st.error("User not logged in!")
            return
        if not os.path.exists(user_file):
            st.error(f"User data file not found: {user_file}. Please ensure the file exists.")
            return
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<h3 style='color: white;'>Add Transaction</h3>", unsafe_allow_html=True)
            account_name = st.text_input("Account Name")
            amount_str = st.text_input("Amount")
            category = st.selectbox("Category", ["Income", "Expense"])
            payment_method = st.selectbox("Payment Method", ["Cash", "UPI", "Credit Card", "Debit Card", "Bank Transfer"])
        with col2:
            st.markdown("<h3 style='color: white;'>Transaction Details</h3>", unsafe_allow_html=True)
            date = st.date_input("Date")
            description = st.text_input("Description")
            tag_options = ["Type your own tag"] + list(tag_mapping_df['tag'].unique())
            tag_selection = st.selectbox("Select or Type Tag", tag_options)
            if tag_selection == "Type your own tag":
                tags = st.text_input("Enter custom tag")
            else:
                tags = tag_selection
        try:
            amount = int(amount_str) if amount_str else None
        except ValueError:
            st.error("Amount must be a valid Number")
            amount = None
        transaction_type = (
            'Uncategorized'
            if not pd.notna(tags) or tags.strip() == ''
            else tag_mapping.get(tags.strip().lower(), 'Uncategorized')
        )
        if st.button("Submit"):
            if not all([account_name, amount, date, description, category, payment_method]):
                st.error("Please fill in all fields")
            else:
                try:
                    with open(user_file, mode='a', newline='', encoding='utf-8') as file:
                        writer = csv.writer(file)
                        writer.writerow([
                            date,
                            account_name,
                            description,
                            amount,
                            category,
                            transaction_type,
                            payment_method,
                            tags
                        ])
                    st.success("Transaction added successfully!")
                except Exception as e:
                    st.error(f"Error saving transaction to {user_file}: {str(e)}")
    except Exception as e:
        st.error(f"Error adding transaction: {str(e)}")
def view_transaction():
    try:
        st.markdown("<h3 style='color: white;'>View Transactions</h3>", unsafe_allow_html=True)
        username = st.session_state.get("login_username", "")
        if not username:
            st.error("User not logged in!")
            return
        
        user_file = os.path.join("data", username, f"{username}_data.csv")
        tag_mapping_file = os.path.join("data", "tag_mapping.csv")
        
        try:
            tag_mapping_df = pd.read_csv(tag_mapping_file)
            tag_mapping = pd.Series(tag_mapping_df['category'].values, index=tag_mapping_df['tag'].str.lower()).to_dict()
        except FileNotFoundError:
            st.error(f"Tag mapping file '{tag_mapping_file}' not found!")
            return
        except Exception as e:
            st.error(f"Error loading tag mapping: {str(e)}")
            return
        
        month_mapping = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        selected_month = st.selectbox("Select Month", options=["All"] + list(month_mapping.keys()))
        
        try:
            df = pd.read_csv(user_file)
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['year'] = df['date'].dt.year
        except FileNotFoundError:
            st.error(f"User transaction file '{user_file}' not found!")
            return
        except Exception as e:
            st.error(f"Error loading transactions: {str(e)}")
            return
        
        years = sorted(df['year'].dropna().astype(int).unique())
        if not years:
            st.warning("No data available")
            return
        
        selected_year = st.selectbox("Select Year", years, index=len(years) - 1)
        
        if st.button("View Transactions"):
            try:
                filtered_df = df[df['year'] == selected_year]            
                if selected_month != "All":
                    month_number = month_mapping[selected_month]
                    filtered_df = filtered_df[filtered_df["date"].dt.month == month_number]
                new_df= filtered_df
                filtered_df = filtered_df[filtered_df['tags'].isna()]   
                print(filtered_df["Account Name"])       
                if not filtered_df.empty:
                    account_names = filtered_df['Account Name'].unique()  
                    for account_name in account_names:
                        rows_with_account = filtered_df[filtered_df['Account Name'] == account_name]                          
                        tag_input = st.text_input(f"Enter tags for transactions with account name: {account_name}")
                        if tag_input:
                            for index in rows_with_account.index:
                                filtered_df.at[index, 'tags'] = tag_input
                            # Append new tags to tag_mapping.csv
                            new_tags = tag_input.split(',')
                            with open(tag_mapping_file, mode='a', newline='', encoding='utf-8') as file:
                                writer = csv.writer(file)
                                for tag in new_tags:
                                    writer.writerow([tag.strip(), 'Uncategorized'])  # Assuming new tags are Uncategorized
                    filtered_df=new_df
                    filtered_df["date"] = filtered_df["date"].dt.date
                    filtered_df['tags'] = filtered_df['tags'].fillna('')
                    filtered_df['amount'] = pd.to_numeric(filtered_df['amount'], errors='coerce')
                    
                    tags_df = filtered_df.assign(tags=filtered_df['tags'].str.split(',')).explode('tags')
                    tags_df['tags'] = tags_df['tags'].str.strip()
                    tags_df['category'] = tags_df['tags'].apply(
                        lambda tag: tag_mapping.get(tag.lower(), 'Uncategorized') if pd.notna(tag) else 'Uncategorized'
                    )
                    category_amounts = tags_df.groupby('category')['amount'].sum()
                    
                    if not category_amounts.empty:
                        fig1 = px.pie(
                            category_amounts,
                            values=category_amounts.values,
                            names=category_amounts.index,
                            title=f"Transaction Amounts by Category - {selected_month} {selected_year}"
                        )
                        fig1.update_layout(
                            width=1100, height=700,
                            font=dict(size=18),
                            title_font_size=18,
                            legend_font_size=14
                        )
                        st.plotly_chart(fig1)
                    else:
                        st.info("No categories found for the selected period.")
                    
                    filtered_df.rename(columns={'amount': 'amount (INR)'}, inplace=True)
                    del filtered_df["year"]
                    st.table(filtered_df)
                    
                    excel_buffer = BytesIO()
                    filtered_df.to_excel(excel_buffer, index=False, engine='openpyxl')
                    excel_buffer.seek(0)
                    st.download_button(
                        label="Download as Excel",
                        data=excel_buffer.getvalue(),
                        file_name=f"transactions_{selected_month}_{selected_year}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    # Generate PDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(190, 10, f"Transaction Report - {selected_month} {selected_year}", ln=True, align='C')
                    pdf.ln(10)
                    pdf.set_font("Arial", "B", 10)
                    cols = ['Date', 'Account Name', 'Description', 'amount (INR)', 'Category', 'Payment Method']
                    col_widths = [25, 35, 60, 35, 35, 35]
                    for col, width in zip(cols, col_widths):
                        pdf.cell(width, 10, col, 1, 0, 'C')
                    pdf.ln()
                    
                    pdf.set_font("Arial", "", 10)
                    for _, row in filtered_df.iterrows():
                        pdf.cell(col_widths[0], 10, str(row['date']), 1, 0, 'C')
                        pdf.cell(col_widths[1], 10, str(row['Account Name']), 1, 0, 'C')
                        pdf.cell(col_widths[2], 10, str(row['description'])[:55], 1, 0, 'L')
                        pdf.cell(col_widths[3], 10, f"{row['amount (INR)']:.2f}", 1, 0, 'R')
                        pdf.cell(col_widths[4], 10, str(row['category']), 1, 0, 'C')
                        pdf.cell(col_widths[5], 10, str(row['payment_method']), 1, 1, 'C')
                    
                    pdf_buffer = BytesIO()
                    pdf_buffer.write(pdf.output(dest='S').encode('latin-1'))
                    pdf_buffer.seek(0)
                    st.download_button(
                        label="Download as PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=f"transactions_{selected_month}_{selected_year}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.warning("No transactions found for the selected month and year!")
            except Exception as e:
                st.error(f"Error processing transactions: {str(e)}")
    except Exception as e:
        st.error(f"Error viewing transactions: {str(e)}")

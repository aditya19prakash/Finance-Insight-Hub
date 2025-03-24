import os
import re
import pandas as pd
import streamlit as st
import csv

def convert_xls_to_xlsx(xls_file_path, xlsx_file_path):
    """Converts an .xls file to .xlsx format."""
    try:
        df = pd.read_excel(xls_file_path, engine='xlrd')
        df.to_excel(xlsx_file_path, index=False, engine='openpyxl')
        st.success(f"File successfully converted to: {xlsx_file_path}")
    except Exception as e:
        st.error(f"Error converting file: {str(e)}")

def check_and_initialize_user_data():
    """Checks if the user has existing data and initializes new data if necessary."""
    user_directory = os.path.join("data", st.session_state.get("login_username", ""))
    if not os.path.exists(user_directory):
        os.makedirs(user_directory)
    user_file = os.path.join(user_directory, "transactions.csv")
    if not os.path.exists(user_file):
        with open(user_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Date", "Description", "Amount", "Category", "Transaction Type", "Payment Method", "Tags"])
    return user_file


def add_bank_statement():
    """Handles the process of uploading, converting, and cleaning bank statement files."""
    try:
        uploaded_file = st.file_uploader("Upload your bank statement (Excel format)", type=["xls", "xlsx"])
        if uploaded_file is not None:
            file_extension = uploaded_file.name.split('.')[-1]
            user_directory = os.path.join("data", st.session_state.get("login_username", ""))
            os.makedirs(user_directory, exist_ok=True)
            file_path = os.path.join(user_directory, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            if file_extension == "xls":
                xlsx_file_path = file_path.replace(".xls", ".xlsx")
                convert_xls_to_xlsx(file_path, xlsx_file_path)
                file_path = xlsx_file_path
            if file_path.endswith(".xlsx"):
                df = pd.read_excel(file_path)
                df_cleaned = df.dropna(how='all')
                df_cleaned.iloc[:, 0] = df_cleaned.iloc[:, 0].astype(str)
                start_index = df_cleaned[df_cleaned.iloc[:, 0].str.contains('Txn Date', na=False, case=False)].index[0] + 1
                df_relevant = df_cleaned.iloc[start_index:].copy()
                expected_columns = ['Txn Date', 'Value Date', 'Description', 'Ref No./Cheque No.', 'Debit', 'Credit', 'Balance']
                df_relevant.columns = expected_columns[:len(df_relevant.columns)]
                df_relevant['Account Name'] = df_relevant['Description'].apply(extract_name_after_third_slash)
                df_relevant.dropna(inplace=True)
                df_relevant.reset_index(drop=True, inplace=True)
                df_relevant['Txn Date'] = pd.to_datetime(df_relevant['Txn Date']).dt.date
                
                if st.button("Add Transactions from Bank Statement"):
                    add_transaction(df_relevant)
                
    except Exception as e:
        st.error(f"Error processing the uploaded file: {str(e)}")

def extract_name_after_third_slash(description):
    """Extracts a name from the given description string after the third slash, or sets to 'Debit Card' or 'Credit Card'."""
    if not isinstance(description, str):
        return "Unknown"
    if 'DEBIT CARD' in description.upper():
        return "Debit Card" 
    elif 'CREDIT CARD' in description.upper():
        return "Credit Card" 
    parts = description.split('/')
    if len(parts) > 3:
        return parts[3].strip()  
    return "Unknown"

def add_transaction(df):
        try:
            try:
                tag_mapping_df = pd.read_csv("data/tag_mapping.csv")
                tag_mapping = pd.Series(tag_mapping_df['category'].values, index=tag_mapping_df['tag'].str.lower()).to_dict()
                st.write("Tag mapping loaded successfully.")
            except Exception as e:
                st.error("Failed to load tag mapping from CSV.")
                return
            
            username = st.session_state.get("login_username", "")
            if not username:
                st.error("User not logged in!")
                return
            user_file = os.path.join("data", username, f"{username}_data.csv")
            
            if not os.path.exists(user_file):
                st.error(f"User data file not found: {user_file}. Please ensure the file exists.")
                return
            
            columns_to_keep = ['Txn Date', 'Account Name', 'Description', 'Debit', 'Credit']
            df_cleaned = df[columns_to_keep]
            df_cleaned['Txn Date'] = pd.to_datetime(df_cleaned['Txn Date'], errors='coerce')

            for _, row in df_cleaned.iterrows():
                amount = row['Debit'] if pd.notna(row['Debit']) else row['Credit']
                amount = int(amount) if pd.notna(amount) and str(amount).strip() else 0  
                transaction_type = 'Expense' if pd.notna(row['Debit']) else 'Income'
                description_lower = str(row['Description']).lower()
                tags = [tag for tag in tag_mapping if tag in description_lower]
                account_name = row['Account Name']
                row_data = [
                    row['Txn Date'].strftime('%Y-%m-%d') if pd.notna(row['Txn Date']) else '',  # Format date as 'YYYY-MM-DD'
                    account_name,
                    row['Description'],
                    amount,
                    transaction_type,
                    'Uncategorized',  
                    'Bank Transfer', 
                    ', '.join(tags) 
                ]
                with open(user_file, mode='a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(row_data)
            
            st.success("Transactions added successfully!")
        except Exception as e:
            st.error(f"Error adding transaction: {str(e)}")

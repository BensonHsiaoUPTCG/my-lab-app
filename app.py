import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from datetime import datetime, date
import qrcode
from io import BytesIO
import hashlib 

# --- 1. Configuration & Styling ---
st.set_page_config(page_title="IMS - Lab Asset Manager", page_icon="🔬", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
    }
    div[data-testid="stMetric"] label { color: #666666 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #333333 !important; }
    img { max-width: 100%; border-radius: 8px; }
    .stButton>button { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Model Layer (Data & Logic) ---
FILE_PATH = 'inventory_v2.json'
HISTORY_PATH = 'history_log.json'
USER_DB_PATH = 'users.json'
IMAGE_DIR = 'images'

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_user_db():
    if not os.path.exists(USER_DB_PATH):
        df = pd.DataFrame({
            'Username': ['admin'],
            'Password': [make_hashes('admin123')],
            'Role': ['Admin']
        })
        df.to_json(USER_DB_PATH, orient='records', indent=4, force_ascii=False)

def login_user(username, password):
    create_user_db()
    try:
        df = pd.read_json(USER_DB_PATH, orient='records')
        hashed_pswd = make_hashes(password)
        result = df[df['Username'] == username]
        if not result.empty:
            if result.iloc[0]['Password'] == hashed_pswd:
                return result.iloc[0]['Role']
    except:
        return None
    return None

def add_user(username, password, role='Student'):
    create_user_db()
    df = pd.read_json(USER_DB_PATH, orient='records')
    if not df.empty and username in df['Username'].values:
        return False
    
    new_user = pd.DataFrame({
        'Username': [username],
        'Password': [make_hashes(password)],
        'Role': [role]
    })
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_json(USER_DB_PATH, orient='records', indent=4, force_ascii=False)
    return True

def load_data():
    if os.path.exists(FILE_PATH):
        df = pd.read_json(FILE_PATH, orient='records')
        if 'Due Date' not in df.columns: df['Due Date'] = None
        
        # FIX: Date Cleanup Logic
        # Convert to string, then replace 'nan', 'None', 'NaT' with empty string
        df['Due Date'] = df['Due Date'].astype(str)
        df['Due Date'] = df['Due Date'].replace(['nan', 'None', 'NaT', '<NA>'], '')
        
        return df
    else:
        data = {
            'ID': [101, 102],
            'Name': ['Arduino Uno R3', 'Raspberry Pi 4'],
            'Category': ['Dev Board', 'Dev Board'],
            'Location': ['Cabinet A-1', 'Cabinet A-2'],
            'Status': ['In Stock', 'Checked Out'],
            'Quantity': [10, 2],
            'Image': [
                'https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Arduino_Uno_major_components.JPG/320px-Arduino_Uno_major_components.JPG', 
                'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f1/Raspberry_Pi_4_Model_B_-_Side.jpg/320px-Raspberry_Pi_4_Model_B_-_Side.jpg'
            ], 
            'Due Date': ['', '2023-12-31'] # Use empty string for no date
        }
        df = pd.DataFrame(data)
        df.to_json(FILE_PATH, orient='records', indent=4, force_ascii=False)
        return df

def save_data(df):
    # FIX: Ensure Due Date is clean string before saving
    df['Due Date'] = df['Due Date'].astype(str).replace(['nan', 'None', 'NaT', '<NA>'], '')
    # date_format='iso' helps prevents timestamp conversion issues
    df.to_json(FILE_PATH, orient='records', indent=4, force_ascii=False, date_format='iso')

def log_history(asset_name, action, detail):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_log = pd.DataFrame([{'Time': timestamp, 'Asset': asset_name, 'Action': action, 'Detail': detail}])
    if os.path.exists(HISTORY_PATH):
        hist_df = pd.read_json(HISTORY_PATH, orient='records')
        hist_df = pd.concat([new_log, hist_df], ignore_index=True)
    else:
        hist_df = new_log
    hist_df.to_json(HISTORY_PATH, orient='records', indent=4, force_ascii=False)
    return hist_df

def load_history():
    if os.path.exists(HISTORY_PATH): 
        return pd.read_json(HISTORY_PATH, orient='records')
    return pd.DataFrame(columns=['Time', 'Asset', 'Action', 'Detail'])

def save_uploaded_image(uploaded_file):
    if uploaded_file is not None:
        file_path = os.path.join(IMAGE_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return ""

def generate_qr_code(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue()

# --- 3. View & Controller Layer ---

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = 'Guest'
if 'role' not in st.session_state:
    st.session_state['role'] = 'Student'

st.sidebar.title("🔬 IMS Mobile (v2.3)")

if not st.session_state['logged_in']:
    tab_login, tab_signup = st.sidebar.tabs(["Login", "Sign Up"])
    
    with tab_login:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            role = login_user(username, password)
            if role:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['role'] = role
                st.success(f"Welcome {username}!")
                st.rerun()
            else:
                st.error("Invalid Username or Password")
                
    with tab_signup:
        st.markdown("Create a new account")
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        role_mode = st.radio("Account Type", ["Student (View Only)", "Admin (Manager)"])
        
        admin_key = ""
        if "Admin" in role_mode:
            admin_key = st.text_input("Admin Secret Key", type="password", help="Ask your professor for the key (Demo: 1234)")
        
        if st.button("Create Account"):
            if new_user and new_pass:
                role_to_save = "Student"
                valid = True
                if "Admin" in role_mode:
                    if admin_key == "1234":
                        role_to_save = "Admin"
                    else:
                        st.error("❌ Invalid Admin Key!")
                        valid = False
                
                if valid:
                    if add_user(new_user, new_pass, role_to_save):
                        st.success(f"✅ Account created as {role_to_save}! Please Login.")
                    else:
                        st.error("❌ Username already exists.")
            else:
                st.warning("⚠️ Please fill all fields")

else:
    st.sidebar.success(f"User: **{st.session_state['username']}**")
    st.sidebar.info(f"Role: **{st.session_state['role']}**")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['role'] = 'Student'
        st.session_state['username'] = 'Guest'
        st.rerun()

st.sidebar.divider()

if st.session_state['role'] == 'Admin':
    menu_options = ["📊 Dashboard", "🔍 Search & View", "➕ Add Asset", "📝 History Log", "⚙️ Admin"]
else:
    menu_options = ["📊 Dashboard", "🔍 Search & View", "📝 History Log"]

menu = st.sidebar.radio("Menu", menu_options)

df = load_data()
today = date.today().strftime("%Y-%m-%d")

# FIX: Robust Overdue Filtering
# Since we converted all Due Dates to strings (and empty strings), we filter carefully
# Condition: Status is Checked Out AND Due Date is not empty AND Due Date < Today
overdue_df = df[
    (df['Status'] == 'Checked Out') & 
    (df['Due Date'] != '') & 
    (df['Due Date'] < today)
]

if menu == "📊 Dashboard":
    st.title("📊 Lab Status Dashboard")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Assets", f"{len(df)}")
    c2.metric("Checked Out", f"{len(df[df['Status']=='Checked Out'])}")
    if not overdue_df.empty:
        c3.metric("⚠️ Overdue", f"{len(overdue_df)}", delta="-Action Required", delta_color="inverse")
    else:
        c3.metric("Overdue Items", "0", delta="All Good")
    st.divider()
    if not overdue_df.empty:
        st.error(f"⚠️ Warning: {len(overdue_df)} items are overdue!")
        st.dataframe(overdue_df[['ID', 'Name', 'Location', 'Due Date']], hide_index=True)
    
    col_chart, col_recent = st.columns([2, 1])
    with col_chart:
        st.subheader("Category Distribution")
        if not df.empty:
            cat_counts = df['Category'].value_counts()
            fig1, ax1 = plt.subplots(figsize=(4,3))
            fig1.patch.set_alpha(0)
            ax1.pie(cat_counts, labels=cat_counts.index, autopct='%1.1f%%', textprops={'color':"white" if st.session_state.get('dark_mode', True) else "black"})
            st.pyplot(fig1)
    with col_recent:
        st.subheader("Latest Activity")
        hist = load_history()
        if not hist.empty:
            st.dataframe(hist.head(5), hide_index=True, use_container_width=True)
        else:
            st.info("No activity yet.")

elif menu == "🔍 Search & View":
    st.title("🔍 Gallery View")
    col_search, _ = st.columns([3, 1])
    with col_search:
        search_term = st.text_input("Search assets...", placeholder="Name, ID, Location...")
    filtered_df = df.copy()
    if search_term:
        filtered_df = filtered_df[
            filtered_df['Name'].str.contains(search_term, case=False) | 
            filtered_df['ID'].astype(str).str.contains(search_term)
        ]
    if not filtered_df.empty:
        cols = st.columns(3)
        for idx, row in filtered_df.iterrows():
            with cols[idx % 3]:
                st.markdown(f"#### {row['Name']}")
                img_path = row['Image']
                if pd.notna(img_path) and img_path != "":
                    if img_path.startswith("http") or os.path.exists(img_path):
                         st.image(img_path, use_container_width=True)
                    else:
                         st.image("https://via.placeholder.com/300x200?text=No+Image", use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/300x200?text=No+Image", use_container_width=True)
                
                status_color = "green" if row['Status'] == 'In Stock' else "red" if row['Status'] == 'Checked Out' else "orange"
                st.markdown(f"**Loc:** {row['Location']}")
                st.markdown(f":{status_color}[● {row['Status']}]")
                if row['Status'] == 'Checked Out' and row['Due Date'] != '':
                    if str(row['Due Date']) < today:
                         st.markdown(f"🔴 **Overdue: {row['Due Date']}**")
                    else:
                         st.markdown(f"📅 Due: {row['Due Date']}")
                if st.button("📱 QR Code", key=f"qr_{row['ID']}"):
                    qr_img = generate_qr_code(f"ID: {row['ID']}\nName: {row['Name']}")
                    st.image(qr_img, width=150)
                st.divider()
    else:
        st.info("No assets found.")

elif menu == "➕ Add Asset":
    if st.session_state['role'] != 'Admin':
        st.warning("Access Denied.")
        st.stop()
    st.title("➕ New Asset (Admin)")
    with st.form("add_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Asset Name*")
            cat = st.selectbox("Category", ["Dev Board", "Sensor", "Instrument", "Tool", "Other"])
            loc = st.text_input("Location")
        with c2:
            qty = st.number_input("Quantity", 1, 100, 1)
            status = st.selectbox("Status", ["In Stock", "Maintenance"])
            img_file = st.file_uploader("Upload Photo", type=['png', 'jpg'])
        if st.form_submit_button("Save Asset") and name:
            img_path = save_uploaded_image(img_file)
            new_id = df['ID'].max() + 1 if not df.empty else 101
            # FIX: Ensure Due Date is empty string for new items
            new_entry = pd.DataFrame([{
                'ID': new_id, 'Name': name, 'Category': cat, 'Location': loc, 
                'Status': status, 'Quantity': qty, 'Image': img_path, 'Due Date': ''
            }])
            df = pd.concat([df, new_entry], ignore_index=True)
            save_data(df)
            log_history(name, "CREATED", f"Added by {st.session_state['username']}")
            st.success("Asset Added!")
            st.rerun()

elif menu == "📝 History Log":
    st.title("📝 System Audit Log")
    st.dataframe(load_history(), use_container_width=True)

elif menu == "⚙️ Admin":
    if st.session_state['role'] != 'Admin':
        st.warning("Access Denied.")
        st.stop()
    st.title("⚙️ Admin Controls")
    
    # Backup Section
    st.subheader("💾 Database Backup")
    with open(FILE_PATH, "r", encoding='utf-8') as f:
        json_data = f.read()
    st.download_button(
        label="Download Inventory JSON",
        data=json_data,
        file_name="inventory_backup.json",
        mime="application/json"
    )
    st.divider()

    tab1, tab2 = st.tabs(["Update Status", "Delete"])
    with tab1:
        asset_id = st.selectbox("Select Asset", df['ID'].tolist())
        row = df[df['ID'] == asset_id].iloc[0]
        st.write(f"Editing: **{row['Name']}**")
        c1, c2 = st.columns(2)
        with c1: new_status = st.selectbox("New Status", ["In Stock", "Checked Out", "Maintenance", "Lost"])
        with c2: 
            borrower = st.text_input("Borrower/Note")
            # Date Input Widget
            due_date_input = st.date_input("Due Date", min_value=date.today()) if new_status == "Checked Out" else None
        
        if st.button("Update"):
            df.loc[df['ID'] == asset_id, 'Status'] = new_status
            
            # FIX: Convert Date Object to String immediately to avoid JSON timestamp issues
            if new_status == "Checked Out" and due_date_input:
                df.loc[df['ID'] == asset_id, 'Due Date'] = str(due_date_input) # Force String
            elif new_status == "In Stock": 
                df.loc[df['ID'] == asset_id, 'Due Date'] = '' # Clear as empty string
            
            save_data(df)
            log_history(row['Name'], "UPDATE", f"{new_status} by {st.session_state['username']}")
            st.success("Updated!")
            st.rerun()
            
    with tab2:
        del_id = st.selectbox("Delete Asset", df['ID'].tolist(), key='del')
        if st.button("Delete Permanently", type="primary"):
            df = df[df['ID'] != del_id]
            save_data(df)
            log_history(str(del_id), "DELETED", f"Deleted by {st.session_state['username']}")
            st.error("Deleted.")
            st.rerun()

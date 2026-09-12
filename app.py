import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
import json
from datetime import datetime, date
import warnings
import os

# Configuration flag for database backend
try:
    has_secrets = hasattr(st, 'secrets') and bool(st.secrets)
    USE_SUPABASE = (st.secrets.get("DATABASE_URL") is not None) if has_secrets else (os.getenv("DATABASE_URL") is not None)
except Exception:
    USE_SUPABASE = os.getenv("DATABASE_URL") is not None

# Import our modules - conditional based on database backend
if USE_SUPABASE:
    try:
        from supabase_store import add_user, validate_user, add_waste_log, get_user_logs, migrate
        # Run migration on startup
        if not migrate():
            st.sidebar.warning("Database migration failed. Using in-memory storage.")
            USE_SUPABASE = False
    except Exception as e:
        st.sidebar.warning(f"Database connection failed. Using in-memory storage.")
        USE_SUPABASE = False

if not USE_SUPABASE:
    from auth_inmemory import AuthStore, add_user, validate_user, add_waste_log, get_user_logs, generate_dummy_logs
else:
    class AuthStore:
        def __init__(self):
            pass
    from auth_inmemory import generate_dummy_logs
from bia_core.data_io import load_curated_data
from bia_core.schemas import UserProfile, WasteLog
from bia_core.features import create_forecast_features
from bia_core.models import DeterministicModel, SARIMAModel, ModelSelector
from bia_core.finance import FinanceCalculator
from bia_core.eval import calculate_mape, backtest_model
from bia_core.maps import create_facilities_map
from bia_core.utils import format_currency, format_number, validate_range

warnings.filterwarnings('ignore')

# Language translations
TRANSLATIONS = {
    "en": {
        "app_title": "BIA - Bio-energy Intelligence Application",
        "welcome_message": "Welcome to the Bio-energy Intelligence Platform",
        "login": "Login",
        "signup": "Sign Up",
        "username": "Username",
        "password": "Password",
        "entity_name": "Entity Name",
        "city": "City",
        "waste_type": "Waste Type",
        "login_success": "Login successful!",
        "invalid_credentials": "Invalid username or password",
        "enter_credentials": "Please enter both username and password",
        "demo_user": "Demo user: **demo** / **demo123**",
        "account_created": "Account created successfully! Please login.",
        "username_exists": "Username already exists",
        "fill_fields": "Please fill in all fields",
        "bia_controls": "BIA Controls",
        "user": "User",
        "entity": "Entity",
        "technical_params": "Technical Parameters",
        "yield_rate": "Yield Rate (kWh/ton)",
        "capacity_factor": "Capacity Factor (%)",
        "financial_params": "Financial Parameters",
        "tariff": "Tariff (₹/kWh)",
        "opex_per_ton": "OPEX per ton (₹)",
        "fixed_opex": "Fixed OPEX (₹ lakhs/year)",
        "capex": "CAPEX (₹ crores)",
        "discount_rate": "Discount Rate (%)",
        "project_horizon": "Project Horizon (years)",
        "advanced_options": "Advanced Options",
        "logout": "Logout",
        "language": "Language",
        "theme": "Theme",
        "light": "Light",
        "dark": "Dark",
        "log_waste": "➕ Log Waste",
        "waste_amount": "Waste Amount (tons)",
        "date": "Date",
        "add_waste_log": "Add Waste Log",
        "waste_processed": "Waste Processed",
        "energy_generated": "Energy Generated",
        "co2_saved": "CO₂ Saved",
        "dashboard": "Dashboard",
        "entity_profile": "Entity Profile",
        "waste_trend_forecast": "Waste Trend & Forecast",
        "energy_finance": "Energy & Finance",
        "npv_sensitivity": "NPV & Sensitivity",
        "facilities_map": "Facilities Map",
        "audit": "Audit",
        "tons": "tons",
        "kwh": "kWh",
        "years": "years",
        "optional_revenue": "Optional Revenue Streams",
        "carbon_credits": "Carbon Credits (₹/credit)",
        "carbon_credits_help": "Revenue from carbon credit sales (1 credit = 1 ton CO₂)",
        "byproduct_sales": "Enable Byproduct Sales",
        "byproduct_price": "Byproduct Price (₹/ton)",
        "byproduct_help": "Revenue from digestate/compost sales",
        "with_credits": "With Credits",
        "without_credits": "Without Credits",
        "byproduct_revenue": "Byproduct Revenue"
    },
    "hi": {
        "app_title": "BIA - जैव-ऊर्जा बुद्धिमत्ता अनुप्रयोग",
        "welcome_message": "जैव-ऊर्जा बुद्धिमत्ता मंच में आपका स्वागत है",
        "login": "लॉगिन",
        "signup": "साइन अप",
        "username": "उपयोगकर्ता नाम",
        "password": "पासवर्ड",
        "entity_name": "संस्था का नाम",
        "city": "शहर",
        "waste_type": "अपशिष्ट प्रकार",
        "login_success": "लॉगिन सफल!",
        "invalid_credentials": "अमान्य उपयोगकर्ता नाम या पासवर्ड",
        "enter_credentials": "कृपया उपयोगकर्ता नाम और पासवर्ड दर्ज करें",
        "demo_user": "डेमो उपयोगकर्ता: **demo** / **demo123**",
        "account_created": "खाता सफलतापूर्वक बनाया गया! कृपया लॉगिन करें।",
        "username_exists": "उपयोगकर्ता नाम पहले से मौजूद है",
        "fill_fields": "कृपया सभी फ़ील्ड भरें",
        "bia_controls": "BIA नियंत्रण",
        "user": "उपयोगकर्ता",
        "entity": "संस्था",
        "technical_params": "तकनीकी मापदंड",
        "yield_rate": "उत्पादन दर (kWh/टन)",
        "capacity_factor": "क्षमता कारक (%)",
        "financial_params": "वित्तीय मापदंड",
        "tariff": "टैरिफ (₹/kWh)",
        "opex_per_ton": "OPEX प्रति टन (₹)",
        "fixed_opex": "निश्चित OPEX (₹ लाख/वर्ष)",
        "capex": "CAPEX (₹ करोड़)",
        "discount_rate": "छूट दर (%)",
        "project_horizon": "परियोजना अवधि (वर्ष)",
        "advanced_options": "उन्नत विकल्प",
        "logout": "लॉगआउट",
        "language": "भाषा",
        "theme": "थीम",
        "light": "हल्का",
        "dark": "गहरा",
        "log_waste": "➕ अपशिष्ट लॉग करें",
        "waste_amount": "अपशिष्ट मात्रा (टन)",
        "date": "दिनांक",
        "add_waste_log": "अपशिष्ट लॉग जोड़ें",
        "waste_processed": "प्रसंस्कृत अपशिष्ट",
        "energy_generated": "उत्पन्न ऊर्जा",
        "co2_saved": "CO₂ बचत",
        "dashboard": "डैशबोर्ड",
        "entity_profile": "संस्था प्रोफ़ाइल",
        "waste_trend_forecast": "अपशिष्ट प्रवृत्ति और पूर्वानुमान",
        "energy_finance": "ऊर्जा और वित्त",
        "npv_sensitivity": "NPV और संवेदनशीलता",
        "facilities_map": "सुविधाएं मानचित्र",
        "audit": "ऑडिट",
        "tons": "टन",
        "kwh": "kWh",
        "years": "वर्ष",
        "optional_revenue": "वैकल्पिक राजस्व स्रोत",
        "carbon_credits": "कार्बन क्रेडिट (₹/क्रेडिट)",
        "carbon_credits_help": "कार्बन क्रेडिट बिक्री से राजस्व (1 क्रेडिट = 1 टन CO₂)",
        "byproduct_sales": "उप-उत्पाद बिक्री सक्षम करें",
        "byproduct_price": "उप-उत्पाद मूल्य (₹/टन)",
        "byproduct_help": "डाइजेस्टेट/कंपोस्ट बिक्री से राजस्व",
        "with_credits": "क्रेडिट के साथ",
        "without_credits": "क्रेडिट के बिना",
        "byproduct_revenue": "उप-उत्पाद राजस्व"
    }
}

def t(key):
    """Translation function"""
    language = st.session_state.get('language', 'en')
    return TRANSLATIONS.get(language, {}).get(key, key)

# Page configuration
st.set_page_config(
    page_title="BIA - Bio-energy Intelligence Application",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
SUPPORTED_CITIES = ["Ahmedabad", "Gandhinagar", "Indore", "Delhi", "Mumbai", "Pune", "Bengaluru", "Chennai"]
WASTE_TYPES = ["organic", "industrial", "agricultural"]

# Initialize auth store
auth_store = AuthStore()

def init_session_state():
    """Initialize session state variables"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = None
    if 'language' not in st.session_state:
        st.session_state.language = 'en'
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'

def login_signup_page():
    """Handle login and signup"""
    st.title(f"🔋 {t('app_title')}")
    st.markdown(f"### {t('welcome_message')}")
    
    tab1, tab2 = st.tabs([t("login"), t("signup")])
    
    with tab1:
        st.subheader(t("login"))
        with st.form("login_form"):
            username = st.text_input(t("username"))
            password = st.text_input(t("password"), type="password")
            login_btn = st.form_submit_button(t("login"))
            
            if login_btn:
                if username and password:
                    user_profile = validate_user(username, password)
                    if user_profile:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_profile = user_profile
                        st.success(t("login_success"))
                        st.rerun()
                    else:
                        st.error(t("invalid_credentials"))
                else:
                    st.error(t("enter_credentials"))
        
        st.info(t("demo_user"))
    
    with tab2:
        st.subheader(t("signup"))
        with st.form("signup_form"):
            new_username = st.text_input(t("username"), key="signup_username")
            new_password = st.text_input(t("password"), type="password", key="signup_password")
            entity_name = st.text_input(t("entity_name"))
            city = st.selectbox(t("city"), SUPPORTED_CITIES)
            waste_type = st.selectbox(t("waste_type"), WASTE_TYPES)
            signup_btn = st.form_submit_button(t("signup"))
            
            if signup_btn:
                if all([new_username, new_password, entity_name, city, waste_type]):
                    if add_user(new_username, new_password, entity_name, city, waste_type):
                        st.success(t("account_created"))
                    else:
                        st.error(t("username_exists"))
                else:
                    st.error(t("fill_fields"))

def sidebar_controls():
    """Create sidebar controls for parameters"""
    st.sidebar.title(f"🔋 {t('bia_controls')}")
    
    # Language and theme selector
    col1, col2 = st.sidebar.columns(2)
    with col1:
        language = st.selectbox(
            t("language"),
            options=["en", "hi"],
            format_func=lambda x: "English" if x == "en" else "हिन्दी",
            index=0 if st.session_state.language == "en" else 1,
            key="language_selector"
        )
        if language != st.session_state.language:
            st.session_state.language = language
            st.rerun()
    
    with col2:
        theme = st.selectbox(
            t("theme"),
            options=["light", "dark"],
            format_func=lambda x: t("light") if x == "light" else t("dark"),
            index=0 if st.session_state.theme == "light" else 1,
            key="theme_selector"
        )
        if theme != st.session_state.theme:
            st.session_state.theme = theme
            st.rerun()
    
    # Apply theme styling
    if st.session_state.theme == "dark":
        st.markdown("""
        <style>
        .stApp { background-color: #0E1117; }
        .stSidebar { background-color: #262730; }
        </style>
        """, unsafe_allow_html=True)
    
    # User info
    if st.session_state.user_profile:
        st.sidebar.write(f"**{t('user')}:** {st.session_state.username}")
        st.sidebar.write(f"**{t('entity')}:** {st.session_state.user_profile.entity_name}")
        st.sidebar.write(f"**{t('city')}:** {st.session_state.user_profile.city}")
        st.sidebar.write(f"**{t('waste_type')}:** {st.session_state.user_profile.waste_type}")
        
        # Database backend indicator
        db_status = "🗄️ Database" if USE_SUPABASE else "💾 In-Memory"
        st.sidebar.write(f"**Storage:** {db_status}")
    
    st.sidebar.divider()
    
    # Basic parameters
    st.sidebar.subheader(t("technical_params"))
    
    yield_rate = st.sidebar.slider(
        t("yield_rate"), 
        min_value=100.0, max_value=2000.0, value=800.0, step=50.0,
        help="Energy yield per ton of waste"
    )
    
    capacity_factor = st.sidebar.slider(
        t("capacity_factor"), 
        min_value=30.0, max_value=95.0, value=85.0, step=5.0,
        help="Plant capacity utilization factor"
    ) / 100
    
    st.sidebar.subheader(t("financial_params"))
    
    tariff = st.sidebar.slider(
        t("tariff"), 
        min_value=2.0, max_value=8.0, value=4.5, step=0.1,
        help="Electricity selling price"
    )
    
    opex_per_ton = st.sidebar.slider(
        t("opex_per_ton"), 
        min_value=200.0, max_value=1000.0, value=500.0, step=50.0,
        help="Operating expenses per ton of waste"
    )
    
    # Optional Revenue Streams
    st.sidebar.subheader(f"{t('optional_revenue')} (Optional)")
    
    carbon_credit_price = st.sidebar.slider(
        t("carbon_credits"),
        min_value=0.0, max_value=1000.0, value=300.0, step=10.0,
        help=t("carbon_credits_help")
    )
    
    enable_byproduct = st.sidebar.checkbox(
        t("byproduct_sales"),
        value=False,
        help=t("byproduct_help")
    )
    
    byproduct_price = 0.0
    if enable_byproduct:
        byproduct_price = st.sidebar.slider(
            t("byproduct_price"),
            min_value=0.0, max_value=500.0, value=50.0, step=5.0,
            help=t("byproduct_help")
        )
    
    # Advanced options in expander
    with st.sidebar.expander(t("advanced_options")):
        fixed_opex = st.number_input(
            t("fixed_opex"), 
            min_value=0.0, max_value=100.0, value=10.0, step=1.0,
            help="Fixed annual operating expenses"
        ) * 100000  # Convert to rupees
        
        capex = st.number_input(
            t("capex"), 
            min_value=1.0, max_value=100.0, value=25.0, step=1.0,
            help="Capital expenditure"
        ) * 10000000  # Convert to rupees
        
        discount_rate = st.slider(
            t("discount_rate"), 
            min_value=5.0, max_value=20.0, value=12.0, step=0.5,
            help="Cost of capital"
        ) / 100
        
        horizon_years = st.slider(
            t("project_horizon"), 
            min_value=10, max_value=30, value=20, step=1,
            help="Project lifetime"
        )
    
    st.sidebar.divider()
    
    # Logout button
    if st.sidebar.button(t("logout"), type="secondary"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_profile = None
        st.rerun()
    
    return {
        'yield_rate': yield_rate,
        'capacity_factor': capacity_factor,
        'tariff': tariff,
        'opex_per_ton': opex_per_ton,
        'fixed_opex': fixed_opex,
        'capex': capex,
        'discount_rate': discount_rate,
        'horizon_years': horizon_years,
        'carbon_credit_price': carbon_credit_price,
        'enable_byproduct': enable_byproduct,
        'byproduct_price': byproduct_price
    }

def waste_logging_section():
    """Waste logging interface"""
    st.subheader(t("log_waste"))
    
    with st.form("waste_log_form"):
        col1, col2 = st.columns(2)
        with col1:
            waste_amount = st.number_input(
                t("waste_amount"), 
                min_value=0.01, max_value=1000.0, value=1.0, step=0.1
            )
        with col2:
            log_date = st.date_input(t("date"), value=date.today())
        
        submit_btn = st.form_submit_button(t("add_waste_log"))
        
        if submit_btn:
            if waste_amount > 0:
                waste_log = WasteLog(
                    username=st.session_state.username,
                    date=log_date,
                    waste_tons=waste_amount
                )
                add_waste_log(waste_log)
                st.success(f"Added {waste_amount} {t('tons')} of waste for {log_date}")
                st.rerun()
            else:
                st.error("Please enter a valid waste amount")

def entity_profile_tab():
    """Entity profile and logs"""
    st.header("🏢 Entity Profile")
    
    profile = st.session_state.user_profile
    
    # Profile information
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"""
        **Entity Name:** {profile.entity_name}  
        **City:** {profile.city}  
        **Waste Type:** {profile.waste_type}  
        **Username:** {st.session_state.username}
        """)
    
    with col2:
        waste_logging_section()
    
    # Waste logs
    st.subheader("📊 Waste Logs")
    
    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn2:
        if st.button("🎲 Generate 100 Dummy Logs", help="Populate 100 realistic daily waste log entries"):
            generate_dummy_logs(st.session_state.username, 100)
            st.success("Generated 100 dummy waste log records!")
            st.rerun()
            
    logs = get_user_logs(st.session_state.username)
    if not logs:
        # Auto-generate 100 dummy logs if none exist
        generate_dummy_logs(st.session_state.username, 100)
        logs = get_user_logs(st.session_state.username)
    
    if logs:
        df_logs = pd.DataFrame([{
            'Date': log.date,
            'Waste (tons)': log.waste_tons
        } for log in logs])
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Waste", f"{df_logs['Waste (tons)'].sum():.2f} tons")
        with col2:
            today_waste = df_logs[df_logs['Date'] == date.today()]['Waste (tons)'].sum()
            st.metric("Today's Waste", f"{today_waste:.2f} tons")
        with col3:
            st.metric("Total Logs", len(df_logs))
        
        # Logs table
        st.dataframe(df_logs, use_container_width=True)
        
        # Download logs
        csv = df_logs.to_csv(index=False)
        st.download_button(
            label="Download Logs CSV",
            data=csv,
            file_name=f"waste_logs_{st.session_state.username}.csv",
            mime="text/csv"
        )
    else:
        st.info("No waste logs found. Add some logs to get started!")

def forecast_tab(params):
    """Waste trend and forecast"""
    st.header("📈 Waste Trend & Forecast")
    
    logs = get_user_logs(st.session_state.username)
    if not logs or len(logs) < 2:
        generate_dummy_logs(st.session_state.username, 100)
        logs = get_user_logs(st.session_state.username)
    
    # Prepare data
    df_logs = pd.DataFrame([{
        'date': log.date,
        'waste_tons': log.waste_tons
    } for log in logs])
    
    df_logs = df_logs.sort_values('date')
    df_logs['cumulative_waste'] = df_logs['waste_tons'].cumsum()
    
    # Create forecast features
    forecast_features = create_forecast_features(df_logs)
    
    # Initialize models
    det_model = DeterministicModel()
    sarima_model = SARIMAModel()
    
    # Fit models
    det_model.fit(forecast_features)
    sarima_model.fit(forecast_features)
    
    # Generate forecasts
    forecast_days = 30
    det_forecast = det_model.predict(forecast_days)
    sarima_forecast = sarima_model.predict(forecast_days)
    
    # Model selection based on backtest
    model_selector = ModelSelector([det_model, sarima_model])
    best_model = model_selector.select_best_model(forecast_features)
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Historical trend
        fig_hist = px.line(df_logs, x='date', y='waste_tons', 
                          title="Historical Waste Logs")
        fig_hist.update_layout(xaxis_title="Date", yaxis_title="Waste (tons)")
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # Cumulative waste
        fig_cum = px.line(df_logs, x='date', y='cumulative_waste', 
                         title="Cumulative Waste")
        fig_cum.update_layout(xaxis_title="Date", yaxis_title="Cumulative Waste (tons)")
        st.plotly_chart(fig_cum, use_container_width=True)
    
    # Forecast comparison
    st.subheader("📊 Forecast Comparison")
    
    forecast_dates = pd.date_range(
        start=df_logs['date'].max() + pd.Timedelta(days=1),
        periods=forecast_days,
        freq='D'
    )
    
    forecast_df = pd.DataFrame({
        'Date': forecast_dates,
        'Deterministic': det_forecast,
        'SARIMA': sarima_forecast
    })
    
    fig_forecast = go.Figure()
    
    # Add historical data
    fig_forecast.add_trace(go.Scatter(
        x=df_logs['date'], y=df_logs['waste_tons'],
        mode='lines+markers', name='Historical',
        line=dict(color='blue')
    ))
    
    # Add forecasts
    fig_forecast.add_trace(go.Scatter(
        x=forecast_df['Date'], y=forecast_df['Deterministic'],
        mode='lines', name='Deterministic Forecast',
        line=dict(color='red', dash='dash')
    ))
    
    fig_forecast.add_trace(go.Scatter(
        x=forecast_df['Date'], y=forecast_df['SARIMA'],
        mode='lines', name='SARIMA Forecast',
        line=dict(color='green', dash='dot')
    ))
    
    fig_forecast.update_layout(
        title="Waste Forecast (30 days)",
        xaxis_title="Date",
        yaxis_title="Waste (tons)"
    )
    
    st.plotly_chart(fig_forecast, use_container_width=True)
    
    # Model performance
    st.subheader("🎯 Model Performance")
    
    if len(forecast_features) >= 10:  # Need sufficient data for backtest
        det_mape = backtest_model(det_model, forecast_features)
        sarima_mape = backtest_model(sarima_model, forecast_features)
        
        perf_df = pd.DataFrame({
            'Model': ['Deterministic', 'SARIMA'],
            'MAPE (%)': [det_mape, sarima_mape],
            'Selected': ['✓' if best_model == det_model else '✗',
                        '✓' if best_model == sarima_model else '✗']
        })
        
        st.dataframe(perf_df, use_container_width=True)
        
        st.info(f"**Best Model:** {type(best_model).__name__} (Lower MAPE is better)")
    else:
        st.info("Need more data points for model backtesting")

def energy_finance_tab(params):
    """Energy and finance calculations"""
    st.header("⚡ Energy & Finance")
    
    logs = get_user_logs(st.session_state.username)
    if not logs:
        generate_dummy_logs(st.session_state.username, 100)
        logs = get_user_logs(st.session_state.username)
    
    # Calculate totals
    total_waste = sum(log.waste_tons for log in logs)
    today_waste = sum(log.waste_tons for log in logs if log.date == date.today())
    
    # Energy calculations
    gross_electricity = total_waste * params['yield_rate'] * params['capacity_factor']
    estimated_daily_electricity = today_waste * params['yield_rate'] * params['capacity_factor']
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Gross Electricity Generated", 
            f"{format_number(gross_electricity)} kWh",
            help="Total electricity from all logged waste"
        )
    
    with col2:
        st.metric(
            "Today's Est. Electricity", 
            f"{format_number(estimated_daily_electricity)} kWh",
            help="Estimated electricity from today's waste"
        )
    
    with col3:
        revenue_potential = gross_electricity * params['tariff']
        st.metric(
            "Revenue Potential", 
            f"₹{format_number(revenue_potential)}",
            help="Revenue from gross electricity"
        )
    
    # Financial projections
    st.subheader("💰 Financial Projections")
    
    # Initialize finance calculator
    calc = FinanceCalculator(
        yield_rate=params['yield_rate'],
        capacity_factor=params['capacity_factor'],
        tariff=params['tariff'],
        opex_per_ton=params['opex_per_ton'],
        fixed_opex=params['fixed_opex'],
        capex=params['capex'],
        discount_rate=params['discount_rate'],
        carbon_credit_price=params['carbon_credit_price'],
        byproduct_price=params['byproduct_price'],
        enable_byproduct=params['enable_byproduct']
    )
    
    # Calculate average daily waste for projections
    if logs:
        avg_daily_waste = total_waste / max(1, len(set(log.date for log in logs)))
    else:
        avg_daily_waste = 45.0  # Default
    
    # Generate cashflows
    cashflows = calc.calculate_cashflows(avg_daily_waste, params['horizon_years'])
    
    # Create cashflow chart
    years = list(range(1, params['horizon_years'] + 1))
    
    fig_cf = go.Figure()
    
    # Split revenue into components for stacked bar chart
    electricity_revenues = [cf['electricity_revenue'] for cf in cashflows]
    carbon_revenues = [cf['carbon_revenue'] for cf in cashflows] 
    byproduct_revenues = [cf['byproduct_revenue'] for cf in cashflows]
    
    fig_cf.add_trace(go.Bar(
        x=years, y=electricity_revenues,
        name='Electricity Revenue', marker_color='green'
    ))
    
    fig_cf.add_trace(go.Bar(
        x=years, y=carbon_revenues,
        name='Carbon Credits', marker_color='lightgreen'
    ))
    
    if params['enable_byproduct']:
        fig_cf.add_trace(go.Bar(
            x=years, y=byproduct_revenues,
            name=t('byproduct_revenue'), marker_color='darkgreen'
        ))
    
    fig_cf.add_trace(go.Bar(
        x=years, y=[-cf['opex'] for cf in cashflows],
        name='OPEX', marker_color='red'
    ))
    
    fig_cf.add_trace(go.Scatter(
        x=years, y=[cf['ncf'] for cf in cashflows],
        mode='lines+markers', name='Net Cash Flow',
        line=dict(color='blue', width=3)
    ))
    
    fig_cf.update_layout(
        title="Annual Cashflows",
        xaxis_title="Year",
        yaxis_title="Amount (₹)",
        barmode='stack'
    )
    
    st.plotly_chart(fig_cf, use_container_width=True)
    
    # Export cashflows
    cf_df = pd.DataFrame([{
        'Year': i+1,
        'Waste (tons)': cf['waste_tons'],
        'Electricity (kWh)': cf['electricity_kwh'],
        'Electricity Revenue (₹)': cf['electricity_revenue'],
        'Carbon Credits Revenue (₹)': cf['carbon_revenue'],
        'Byproduct Revenue (₹)': cf['byproduct_revenue'],
        'Total Revenue (₹)': cf.get('total_revenue', cf.get('revenue', 0)),
        'OPEX (₹)': cf['opex'],
        'Net Cash Flow (₹)': cf['ncf']
    } for i, cf in enumerate(cashflows)])
    
    st.subheader("📋 Annual Cashflow Table")
    st.dataframe(cf_df, use_container_width=True)
    
    # Download button
    csv = cf_df.to_csv(index=False)
    st.download_button(
        label="Download Cashflows CSV",
        data=csv,
        file_name=f"cashflows_{st.session_state.username}.csv",
        mime="text/csv"
    )

def npv_sensitivity_tab(params):
    """NPV calculations and sensitivity analysis"""
    st.header("💹 NPV & Sensitivity Analysis")
    
    logs = get_user_logs(st.session_state.username)
    if not logs:
        # Auto generate 100 dummy logs so NPV calculations always show full results
        generate_dummy_logs(st.session_state.username, 100)
        logs = get_user_logs(st.session_state.username)
    
    # Calculate average daily waste
    total_waste = sum(log.waste_tons for log in logs)
    unique_dates = len(set(log.date for log in logs))
    avg_daily_waste = total_waste / max(1, unique_dates)
    
    # Initialize finance calculator
    calc = FinanceCalculator(
        yield_rate=params['yield_rate'],
        capacity_factor=params['capacity_factor'],
        tariff=params['tariff'],
        opex_per_ton=params['opex_per_ton'],
        fixed_opex=params['fixed_opex'],
        capex=params['capex'],
        discount_rate=params['discount_rate'],
        carbon_credit_price=params['carbon_credit_price'],
        byproduct_price=params['byproduct_price'],
        enable_byproduct=params['enable_byproduct']
    )
    
    # Calculate base case metrics
    npv = calc.calculate_npv(avg_daily_waste, params['horizon_years'])
    payback = calc.calculate_payback(avg_daily_waste, params['horizon_years'])
    roi = calc.calculate_roi(avg_daily_waste, params['horizon_years'])
    irr = calc.calculate_irr(avg_daily_waste, params['horizon_years'])
    
    # CO2 savings calculation
    total_kwh = total_waste * params['yield_rate'] * params['capacity_factor']
    co2_savings = (total_kwh * 0.9) / 1000  # kg to tons
    trees_equivalent = 50 * co2_savings
    
    # Key Metrics Cards
    st.subheader("📌 Key Financial & Climate Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("NPV", f"₹{format_currency(npv)}", help="Net Present Value over project horizon")
    with col2:
        st.metric("Payback Period", f"{payback:.1f} yrs" if payback != float('inf') else "> Horizon", help="Time to recover initial CAPEX")
    with col3:
        st.metric("ROI", f"{roi:.1f}%", help="Return on Investment percentage")
    with col4:
        st.metric("IRR", f"{irr:.1f}%", help="Internal Rate of Return")
    with col5:
        st.metric("CO₂ Savings", f"{co2_savings:.1f} tons", help="Cumulative CO2 emissions avoided")

    st.divider()
    
    # Sensitivity Analysis
    st.subheader("📊 Tornado Sensitivity Analysis")
    st.markdown("Assess the impact of key technical and financial parameter fluctuations on Net Present Value (NPV).")
    
    col_slide1, col_slide2 = st.columns([2, 2])
    with col_slide1:
        variation_pct = st.slider("Sensitivity Variation Range (±%)", min_value=5, max_value=30, value=15, step=5, help="Percentage fluctuation applied to base parameters") / 100.0

    sensitivity_params = {
        'Yield Rate': ('yield_rate', params['yield_rate']),
        'Tariff': ('tariff', params['tariff']),
        'OPEX per ton': ('opex_per_ton', params['opex_per_ton']),
        'CAPEX': ('capex', params['capex']),
        'Discount Rate': ('discount_rate', params['discount_rate'])
    }
    
    sensitivity_results = []
    
    for param_name, (param_key, base_value) in sensitivity_params.items():
        # High variation case (+variation%)
        params_high = params.copy()
        params_high[param_key] = base_value * (1.0 + variation_pct)
        calc_high = FinanceCalculator(
            yield_rate=params_high['yield_rate'],
            capacity_factor=params_high['capacity_factor'],
            tariff=params_high['tariff'],
            opex_per_ton=params_high['opex_per_ton'],
            fixed_opex=params_high['fixed_opex'],
            capex=params_high['capex'],
            discount_rate=params_high['discount_rate'],
            carbon_credit_price=params_high['carbon_credit_price'],
            byproduct_price=params_high['byproduct_price'],
            enable_byproduct=params_high['enable_byproduct']
        )
        npv_high = calc_high.calculate_npv(avg_daily_waste, params['horizon_years'])
        
        # Low variation case (-variation%)
        params_low = params.copy()
        params_low[param_key] = base_value * (1.0 - variation_pct)
        calc_low = FinanceCalculator(
            yield_rate=params_low['yield_rate'],
            capacity_factor=params_low['capacity_factor'],
            tariff=params_low['tariff'],
            opex_per_ton=params_low['opex_per_ton'],
            fixed_opex=params_low['fixed_opex'],
            capex=params_low['capex'],
            discount_rate=params_low['discount_rate'],
            carbon_credit_price=params_low['carbon_credit_price'],
            byproduct_price=params_low['byproduct_price'],
            enable_byproduct=params_low['enable_byproduct']
        )
        npv_low = calc_low.calculate_npv(avg_daily_waste, params['horizon_years'])
        
        # Swing difference
        swing = npv_high - npv_low
        low_delta = npv_low - npv
        high_delta = npv_high - npv
        
        sensitivity_results.append({
            'Parameter': param_name,
            'Base Value': base_value,
            'Low Case NPV': npv_low,
            'High Case NPV': npv_high,
            'Low Delta': low_delta,
            'High Delta': high_delta,
            'Total Swing': abs(swing)
        })
    
    # Sort by total swing impact
    sensitivity_results.sort(key=lambda x: x['Total Swing'], reverse=True)
    
    # Create Tornado Plotly Chart
    fig_tornado = go.Figure()
    params_labels = [r['Parameter'] for r in sensitivity_results]
    low_deltas = [r['Low Delta'] for r in sensitivity_results]
    high_deltas = [r['High Delta'] for r in sensitivity_results]
    
    fig_tornado.add_trace(go.Bar(
        y=params_labels,
        x=low_deltas,
        name=f'-{int(variation_pct*100)}% Variation',
        orientation='h',
        marker_color='#e74c3c'
    ))
    
    fig_tornado.add_trace(go.Bar(
        y=params_labels,
        x=high_deltas,
        name=f'+{int(variation_pct*100)}% Variation',
        orientation='h',
        marker_color='#2ecc71'
    ))
    
    fig_tornado.update_layout(
        title=f"Tornado Diagram — NPV Sensitivity (±{int(variation_pct*100)}% fluctuation)",
        barmode='overlay',
        xaxis_title="NPV Deviation from Base Case (₹)",
        yaxis_title="Parameter",
        height=450
    )
    
    st.plotly_chart(fig_tornado, use_container_width=True)
    
    # Sensitivity Results Table
    st.subheader("📋 Sensitivity Results Table")
    sens_df = pd.DataFrame([{
        'Parameter': r['Parameter'],
        f'Low (-{int(variation_pct*100)}%) NPV': f"₹{format_currency(r['Low Case NPV'])}",
        'Base Case NPV': f"₹{format_currency(npv)}",
        f'High (+{int(variation_pct*100)}%) NPV': f"₹{format_currency(r['High Case NPV'])}",
        'Total Swing': f"₹{format_currency(r['Total Swing'])}"
    } for r in sensitivity_results])
    
    st.dataframe(sens_df, use_container_width=True)

    # Scenario Analysis Table
    st.subheader("🎯 Scenario Analysis (Base vs Optimistic vs Pessimistic)")
    
    # Optimistic: Tariff +20%, Yield +10%, OPEX -10%
    calc_opt = FinanceCalculator(
        yield_rate=params['yield_rate'] * 1.10,
        capacity_factor=params['capacity_factor'],
        tariff=params['tariff'] * 1.20,
        opex_per_ton=params['opex_per_ton'] * 0.90,
        fixed_opex=params['fixed_opex'],
        capex=params['capex'],
        discount_rate=params['discount_rate'],
        carbon_credit_price=params['carbon_credit_price'],
        byproduct_price=params['byproduct_price'],
        enable_byproduct=params['enable_byproduct']
    )
    npv_opt = calc_opt.calculate_npv(avg_daily_waste, params['horizon_years'])
    payback_opt = calc_opt.calculate_payback(avg_daily_waste, params['horizon_years'])
    roi_opt = calc_opt.calculate_roi(avg_daily_waste, params['horizon_years'])
    
    # Pessimistic: Tariff -15%, Yield -10%, OPEX +15%
    calc_pess = FinanceCalculator(
        yield_rate=params['yield_rate'] * 0.90,
        capacity_factor=params['capacity_factor'],
        tariff=params['tariff'] * 0.85,
        opex_per_ton=params['opex_per_ton'] * 1.15,
        fixed_opex=params['fixed_opex'],
        capex=params['capex'],
        discount_rate=params['discount_rate'],
        carbon_credit_price=params['carbon_credit_price'],
        byproduct_price=params['byproduct_price'],
        enable_byproduct=params['enable_byproduct']
    )
    npv_pess = calc_pess.calculate_npv(avg_daily_waste, params['horizon_years'])
    payback_pess = calc_pess.calculate_payback(avg_daily_waste, params['horizon_years'])
    roi_pess = calc_pess.calculate_roi(avg_daily_waste, params['horizon_years'])
    
    scenario_df = pd.DataFrame([
        {
            'Scenario': 'Pessimistic (-15% Tariff, -10% Yield, +15% OPEX)',
            'NPV (₹)': f"₹{format_currency(npv_pess)}",
            'Payback (Years)': f"{payback_pess:.1f}" if payback_pess != float('inf') else "> Horizon",
            'ROI (%)': f"{roi_pess:.1f}%"
        },
        {
            'Scenario': 'Base Case (Current Parameters)',
            'NPV (₹)': f"₹{format_currency(npv)}",
            'Payback (Years)': f"{payback:.1f}" if payback != float('inf') else "> Horizon",
            'ROI (%)': f"{roi:.1f}%"
        },
        {
            'Scenario': 'Optimistic (+20% Tariff, +10% Yield, -10% OPEX)',
            'NPV (₹)': f"₹{format_currency(npv_opt)}",
            'Payback (Years)': f"{payback_opt:.1f}" if payback_opt != float('inf') else "> Horizon",
            'ROI (%)': f"{roi_opt:.1f}%"
        }
    ])
    st.dataframe(scenario_df, use_container_width=True)

    # Optional Revenue Impact Comparison
    st.subheader("🌱 Revenue Stream Breakdown & Extras Impact")
    
    calc_base = FinanceCalculator(
        yield_rate=params['yield_rate'],
        capacity_factor=params['capacity_factor'],
        tariff=params['tariff'],
        opex_per_ton=params['opex_per_ton'],
        fixed_opex=params['fixed_opex'],
        capex=params['capex'],
        discount_rate=params['discount_rate'],
        carbon_credit_price=0.0,
        byproduct_price=0.0,
        enable_byproduct=False
    )
    
    npv_base = calc_base.calculate_npv(avg_daily_waste, params['horizon_years'])
    npv_with_extras = calc.calculate_npv(avg_daily_waste, params['horizon_years'])
    npv_improvement = npv_with_extras - npv_base
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Base NPV (Electricity Sales Only)", f"₹{format_currency(npv_base)}")
    with col2:
        st.metric("NPV with All Revenue Streams", f"₹{format_currency(npv_with_extras)}")
    with col3:
        st.metric("Additional Value Created", f"₹{format_currency(npv_improvement)}", 
                 delta=f"{((npv_improvement/npv_base)*100):.1f}%" if npv_base != 0 else "N/A")
    
    cashflows = calc.calculate_cashflows(avg_daily_waste, params['horizon_years'])
    total_electricity_rev = sum(cf['electricity_revenue'] for cf in cashflows)
    total_carbon_rev = sum(cf['carbon_revenue'] for cf in cashflows)
    total_byproduct_rev = sum(cf['byproduct_revenue'] for cf in cashflows)
    total_rev_sum = max(1.0, total_electricity_rev + total_carbon_rev + total_byproduct_rev)
    
    revenue_breakdown = pd.DataFrame({
        'Revenue Stream': ['Electricity Sales', 'Carbon Credits', 'Byproduct Sales'],
        'Total (₹)': [f"₹{format_currency(total_electricity_rev)}", f"₹{format_currency(total_carbon_rev)}", f"₹{format_currency(total_byproduct_rev)}"],
        'Share (%)': [
            f"{(total_electricity_rev / total_rev_sum * 100):.1f}%",
            f"{(total_carbon_rev / total_rev_sum * 100):.1f}%",
            f"{(total_byproduct_rev / total_rev_sum * 100):.1f}%"
        ]
    })
    st.dataframe(revenue_breakdown, use_container_width=True)

def facilities_map_tab():
    """Facilities mapping with interactive filters"""
    st.header("🗺️ Facilities Map")
    
    try:
        facilities_data = load_curated_data()['facilities']
        if facilities_data.empty:
            st.info("No verified facilities found in database.")
            return
            
        user_city = st.session_state.user_profile.city if st.session_state.user_profile else "Mumbai"
        
        # Interactive Filter Controls
        col_f1, col_f2, col_f3 = st.columns(3)
        
        all_cities = ["All Cities"] + list(facilities_data['city'].unique())
        default_city_idx = all_cities.index(user_city) if user_city in all_cities else 0
        
        with col_f1:
            selected_city = st.selectbox("Select City", all_cities, index=default_city_idx)
            
        with col_f2:
            available_types = list(facilities_data['type'].unique())
            selected_types = st.multiselect("Facility Type", options=available_types, default=available_types)
            
        with col_f3:
            available_statuses = list(facilities_data['status'].unique())
            selected_statuses = st.multiselect("Status", options=available_statuses, default=available_statuses)
            
        # Apply filters
        filtered_df = facilities_data.copy()
        if selected_city != "All Cities":
            filtered_df = filtered_df[filtered_df['city'] == selected_city]
        if selected_types:
            filtered_df = filtered_df[filtered_df['type'].isin(selected_types)]
        if selected_statuses:
            filtered_df = filtered_df[filtered_df['status'].isin(selected_statuses)]
            
        if not filtered_df.empty:
            # Create interactive Folium map
            facilities_map = create_facilities_map(filtered_df, city=selected_city)
            
            # Display map
            st_folium(facilities_map, use_container_width=True, height=500)
            
            # Summary Metrics Cards
            st.subheader(f"🏭 Facilities Summary ({selected_city})")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Facilities", len(filtered_df))
            with col2:
                total_capacity = filtered_df['capacity_mw'].sum()
                st.metric("Total Capacity", f"{total_capacity:.1f} MW")
            with col3:
                op_count = len(filtered_df[filtered_df['status'] == 'operational'])
                st.metric("Operational", op_count)
            with col4:
                uc_count = len(filtered_df[filtered_df['status'] == 'under_construction'])
                st.metric("Under Construction", uc_count)
            
            # Facilities Table
            st.subheader("📋 Verified Facilities List")
            display_df = filtered_df[['name', 'city', 'state', 'type', 'capacity_mw', 'status', 'source']].copy()
            display_df.columns = ['Facility Name', 'City', 'State', 'Type', 'Capacity (MW)', 'Status', 'Data Source']
            st.dataframe(display_df, use_container_width=True)
            
            # Download CSV
            csv_data = display_df.to_csv(index=False)
            st.download_button(
                label="Download Facilities CSV",
                data=csv_data,
                file_name=f"facilities_{selected_city.lower().replace(' ', '_')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("No facilities match the selected filter criteria.")
            
    except Exception as e:
        st.error(f"Error rendering facilities map: {str(e)}")

def audit_tab(params):
    """Audit trail with formulas and parameters"""
    st.header("🔍 Audit Trail")
    
    # LaTeX formulas
    st.subheader("📐 Mathematical Formulas")
    
    st.markdown("### Energy Calculations")
    st.latex(r"kWh_{year,t} = tons_{year,t} \times yield \times capacity\_factor")
    st.latex(r"tons_{year,t} = tpd_t \times 365")
    
    st.markdown("### Deterministic Forecast")
    st.latex(r"tpd_t = base\_tpd \times (1+g)^{(t-1)}")
    
    st.markdown("### Financial Calculations")
    st.latex(r"electricity\_revenue_t = kWh_{year,t} \times tariff")
    st.latex(r"carbon\_revenue_t = \frac{kWh_{year,t} \times 0.9}{1000} \times carbon\_price")
    st.latex(r"byproduct\_revenue_t = tons_{year,t} \times 0.3 \times byproduct\_price")
    st.latex(r"total\_revenue_t = electricity\_revenue_t + carbon\_revenue_t + byproduct\_revenue_t")
    st.latex(r"opex_t = tons_{year,t} \times opex\_per\_ton + fixed\_opex")
    st.latex(r"ncf_t = total\_revenue_t - opex_t")
    
    st.markdown("### NPV Calculation")
    st.latex(r"NPV = -CAPEX + \sum_{t=1}^{horizon} \frac{ncf_t}{(1+r)^t}")
    
    st.markdown("### Environmental Impact")
    st.latex(r"CO_2\_savings = \frac{kWh \times 0.9}{1000} \text{ tons}")
    st.latex(r"Trees\_equivalent = 50 \times CO_2\_savings")
    
    # Parameter table
    st.subheader("⚙️ Current Parameters")
    
    param_data = {
        'Parameter': [
            'Yield Rate (kWh/ton)',
            'Capacity Factor (%)',
            'Tariff (₹/kWh)',
            'OPEX per ton (₹)',
            'Fixed OPEX (₹/year)',
            'CAPEX (₹)',
            'Discount Rate (%)',
            'Project Horizon (years)',
            'Carbon Credit Price (₹/credit)',
            'Byproduct Sales Enabled',
            'Byproduct Price (₹/ton)'
        ],
        'Value': [
            f"{params['yield_rate']:.1f}",
            f"{params['capacity_factor']*100:.1f}%",
            f"₹{params['tariff']:.2f}",
            f"₹{params['opex_per_ton']:.0f}",
            f"₹{params['fixed_opex']:,.0f}",
            f"₹{params['capex']:,.0f}",
            f"{params['discount_rate']*100:.1f}%",
            f"{params['horizon_years']} years",
            f"₹{params['carbon_credit_price']:.0f}" if params['carbon_credit_price'] > 0 else "Not used",
            "Yes" if params['enable_byproduct'] else "No",
            f"₹{params['byproduct_price']:.0f}" if params['enable_byproduct'] else "N/A"
        ],
        'Unit': [
            'kWh/ton',
            'Percentage',
            'INR per kWh',
            'INR per ton',
            'INR per year',
            'INR',
            'Percentage',
            'Years',
            'INR per credit',
            'Boolean',
            'INR per ton'
        ]
    }
    
    param_df = pd.DataFrame(param_data)
    st.dataframe(param_df, use_container_width=True)
    
    # Data provenance
    st.subheader("📊 Data Provenance")
    
    provenance_info = {
        "User Data": "In-memory storage during session",
        "Waste Logs": "User-entered data with auto-recorded timestamps",
        "City Data": "Curated from government and industry sources",
        "Facility Data": "Verified bioenergy facilities database",
        "Tariff Data": "State electricity regulatory commission rates",
        "Cost Parameters": "Industry benchmarks and user-adjustable"
    }
    
    for source, description in provenance_info.items():
        st.write(f"**{source}:** {description}")
    
    # Configuration export
    st.subheader("💾 Export Configuration")
    
    # Create run configuration
    run_config = {
        "timestamp": datetime.now().isoformat(),
        "user": st.session_state.username,
        "entity": st.session_state.user_profile.entity_name,
        "city": st.session_state.user_profile.city,
        "waste_type": st.session_state.user_profile.waste_type,
        "parameters": params,
        "total_logs": len(get_user_logs(st.session_state.username)),
        "application_version": "BIA v1.0"
    }
    
    config_json = json.dumps(run_config, indent=2, default=str)
    
    st.download_button(
        label="Download Run Configuration",
        data=config_json,
        file_name=f"bia_config_{st.session_state.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )
    
    # Assumptions and limitations
    st.subheader("⚠️ Assumptions & Limitations")
    
    st.markdown("""
    **Key Assumptions:**
    - Constant yield rate and capacity factor over project lifetime
    - Linear waste growth for deterministic forecasting
    - Constant tariff rates (inflation not modeled)
    - No major policy or regulatory changes
    - Standard CO₂ emission factor (0.9 kg/kWh)
    
    **Limitations:**
    - Supports only 8 cities in current version
    - In-memory authentication (no data persistence)
    - Simplified financial modeling (no tax considerations)
    - SARIMA model assumes sufficient historical data
    - No detailed technical feasibility assessment
    """)

def get_kpi_data(params):
    """Calculate KPI data for dashboard"""
    logs = get_user_logs(st.session_state.username)
    
    if not logs:
        return {
            'total_waste': 0,
            'total_energy': 0,
            'co2_saved': 0
        }
    
    total_waste = sum(log.waste_tons for log in logs)
    total_energy = total_waste * params['yield_rate'] * params['capacity_factor']
    co2_saved = (total_energy * 0.9) / 1000  # kg to tons
    
    return {
        'total_waste': total_waste,
        'total_energy': total_energy,
        'co2_saved': co2_saved
    }

def clean_dashboard_screen(params):
    """Clean first screen with KPI cards and log waste action"""
    st.title(f"🔋 {t('dashboard')}")
    st.markdown(f"**Welcome, {st.session_state.user_profile.entity_name}!**")
    
    # Get KPI data
    kpi_data = get_kpi_data(params)
    
    # KPI Cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label=t("waste_processed"),
            value=f"{kpi_data['total_waste']:.1f} {t('tons')}",
            delta=None,
            help="Total waste processed so far"
        )
    
    with col2:
        st.metric(
            label=t("energy_generated"),
            value=f"{format_number(kpi_data['total_energy'])} {t('kwh')}",
            delta=None,
            help="Total energy generated from waste"
        )
    
    with col3:
        st.metric(
            label=t("co2_saved"),
            value=f"{kpi_data['co2_saved']:.1f} {t('tons')}",
            delta=None,
            help="CO₂ emissions saved"
        )
    
    st.divider()
    
    # Quick waste logging
    st.subheader(t("log_waste"))
    
    with st.form("quick_waste_log"):
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            waste_amount = st.number_input(
                t("waste_amount"),
                min_value=0.01,
                max_value=1000.0,
                value=1.0,
                step=0.1
            )
        
        with col2:
            log_date = st.date_input(t("date"), value=date.today())
        
        with col3:
            st.write("")  # Spacer
            st.write("")  # Spacer
            submit_btn = st.form_submit_button(
                t("add_waste_log"),
                type="primary",
                use_container_width=True
            )
        
        if submit_btn:
            if waste_amount > 0:
                waste_log = WasteLog(
                    username=st.session_state.username,
                    date=log_date,
                    waste_tons=waste_amount
                )
                add_waste_log(waste_log)
                st.success(f"Added {waste_amount} {t('tons')} of waste for {log_date}")
                st.rerun()
            else:
                st.error("Please enter a valid waste amount")

def main_dashboard():
    """Main dashboard with tabs"""
    # Get parameters from sidebar
    params = sidebar_controls()
    
    # Show clean dashboard first
    clean_dashboard_screen(params)
    
    st.divider()
    
    # Create tabs for detailed analysis
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        f"🏢 {t('entity_profile')}",
        f"📈 {t('waste_trend_forecast')}", 
        f"⚡ {t('energy_finance')}",
        f"💹 {t('npv_sensitivity')}",
        f"🗺️ {t('facilities_map')}",
        f"🔍 {t('audit')}"
    ])
    
    with tab1:
        entity_profile_tab()
    
    with tab2:
        forecast_tab(params)
    
    with tab3:
        energy_finance_tab(params)
    
    with tab4:
        npv_sensitivity_tab(params)
    
    with tab5:
        facilities_map_tab()
    
    with tab6:
        audit_tab(params)

def main():
    """Main application"""
    init_session_state()
    
    if not st.session_state.logged_in:
        login_signup_page()
    else:
        main_dashboard()

if __name__ == "__main__":
    main()

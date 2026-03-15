"""
Healthcare Compliance Agent — Streamlit UI
Run: streamlit run app.py --server.port 8505
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json, io, time

API = "http://localhost:8000"
st.set_page_config(page_title="HCA — Healthcare Compliance Agent", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

# ━━━ CSS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
:root{--bg:#0A1628;--card:#111D35;--card2:#162040;--blue:#1A56DB;--blue2:#3B82F6;--red:#EF4444;--green:#22C55E;--amber:#F59E0B;--text:#E2E8F0;--muted:#94A3B8;--border:#1E3A5F;}
html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"]{background:#0A1628!important;color:#E2E8F0!important;font-family:'Inter',sans-serif!important;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0D1F3C 0%,#0A1628 100%)!important;border-right:1px solid #1E3A5F!important;}
[data-testid="stSidebar"] .stMarkdown h1,[data-testid="stSidebar"] .stMarkdown h2,[data-testid="stSidebar"] .stMarkdown h3{color:#3B82F6!important;}
.stTabs [data-baseweb="tab-list"]{gap:8px;background:#111D35;border-radius:12px;padding:4px;}
.stTabs [data-baseweb="tab"]{background:transparent;color:#94A3B8;border-radius:8px;font-weight:500;}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#1A56DB,#3B82F6)!important;color:white!important;}
.stButton>button{background:linear-gradient(135deg,#1A56DB,#3B82F6)!important;color:white!important;border:none!important;border-radius:8px!important;padding:8px 24px!important;font-weight:600!important;transition:all .3s ease!important;}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 8px 25px rgba(26,86,219,.4)!important;}
div[data-testid="stMetric"]{background:linear-gradient(135deg,#111D35,#162040)!important;border:1px solid #1E3A5F!important;border-radius:12px!important;padding:16px 20px!important;box-shadow:0 4px 15px rgba(0,0,0,.3)!important;}
div[data-testid="stMetric"] label{color:#94A3B8!important;font-size:0.85rem!important;}
div[data-testid="stMetric"] [data-testid="stMetricValue"]{color:#E2E8F0!important;font-weight:700!important;}
.stTextInput>div>div>input,.stTextArea>div>div>textarea,.stSelectbox>div>div{background:#111D35!important;color:#E2E8F0!important;border:1px solid #1E3A5F!important;border-radius:8px!important;}
.stDataFrame{border-radius:12px!important;overflow:hidden!important;}
div[data-testid="stExpander"]{background:#111D35!important;border:1px solid #1E3A5F!important;border-radius:12px!important;}
.risk-high{background:linear-gradient(135deg,#7F1D1D,#991B1B);color:#FCA5A5;padding:4px 12px;border-radius:20px;font-weight:700;font-size:.8rem;display:inline-block;animation:pulse 2s infinite;}
.risk-medium{background:linear-gradient(135deg,#78350F,#92400E);color:#FCD34D;padding:4px 12px;border-radius:20px;font-weight:700;font-size:.8rem;display:inline-block;}
.risk-low{background:linear-gradient(135deg,#14532D,#166534);color:#86EFAC;padding:4px 12px;border-radius:20px;font-weight:700;font-size:.8rem;display:inline-block;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:.6;}}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}
.fade-in{animation:fadeIn .5s ease-out;}
.header-bar{background:linear-gradient(135deg,#0D1F3C,#1A3A6B);padding:12px 24px;border-radius:12px;margin-bottom:20px;border:1px solid #1E3A5F;display:flex;align-items:center;justify-content:space-between;}
</style>""", unsafe_allow_html=True)

# ━━━ Helpers ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def api_get(path):
    try: return requests.get(f"{API}{path}", timeout=10).json()
    except: return []

def api_post(path, data=None, files=None):
    try:
        if files: return requests.post(f"{API}{path}", files=files, timeout=30).json()
        return requests.post(f"{API}{path}", json=data, timeout=30).json()
    except Exception as e: return {"error": str(e)}

def api_delete(path):
    try: return requests.delete(f"{API}{path}", timeout=10).json()
    except Exception as e: return {"error": str(e)}

def risk_badge(level):
    cls = {"HIGH":"risk-high","MEDIUM":"risk-medium","LOW":"risk-low"}.get(level,"risk-low")
    return f'<span class="{cls}">● {level}</span>'

def plotly_dark(fig):
    fig.update_layout(plot_bgcolor="#111D35",paper_bgcolor="#111D35",font_color="#E2E8F0",
        legend=dict(bgcolor="rgba(0,0,0,0)"),margin=dict(l=20,r=20,t=40,b=20))
    return fig

# ━━━ Sidebar ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.sidebar:
    st.markdown("## 🏥 HCA Agent")
    st.markdown(f"🕐 `{datetime.now().strftime('%I:%M %p — %b %d')}`")
    st.markdown("---")
    page = st.radio("Navigation",["📊 Dashboard","📁 Data Management","👁 Watcher","🧠 Thinker","🔧 Fixer","📋 Audit Trail"],label_visibility="collapsed")
    st.markdown("---")

    # Dynamic sidebar stats — always fetched fresh
    _patients = api_get("/patients/")
    _claims_stats = api_get("/claims/stats")
    _policies = api_get("/policies/")

    patient_count = len(_patients) if isinstance(_patients, list) else 0
    claim_count = _claims_stats.get("total_claims", 0) if isinstance(_claims_stats, dict) else 0
    policy_count = len(_policies) if isinstance(_policies, list) else 0
    at_risk = (_claims_stats.get("high_risk", 0) + _claims_stats.get("medium_risk", 0)) if isinstance(_claims_stats, dict) else 0
    rev_risk = _claims_stats.get("total_at_risk", 0) if isinstance(_claims_stats, dict) else 0

    st.metric("👤 Total Patients", patient_count)
    st.metric("📋 Total Claims", claim_count)
    st.metric("📜 Policies", policy_count)
    st.metric("⚠ At Risk", at_risk)
    st.metric("💰 Revenue at Risk", f"${rev_risk:,.0f}")

    st.markdown("---")
    st.caption("Healthcare Compliance Agent v2.0")

# ━━━ Header ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown(f"""<div class="header-bar"><div>🏥 <b style="font-size:1.3rem;color:#3B82F6;">Healthcare Compliance Agent</b> <span style="color:#94A3B8;margin-left:12px;">Autonomous Policy Monitor</span></div><div style="color:#94A3B8;">{datetime.now().strftime('%A, %B %d, %Y — %I:%M %p')}</div></div>""", unsafe_allow_html=True)

# ╔══════════════════════════════════════════════════════════════
# ║  PAGE: DASHBOARD
# ╚══════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.markdown("### 📊 Compliance Dashboard")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total Patients", patient_count)
    c2.metric("Total Claims", claim_count)
    c3.metric("⚠ High Risk", _claims_stats.get("high_risk",0) if isinstance(_claims_stats, dict) else 0)
    c4.metric("Total Billed", f"${_claims_stats.get('total_billed',0):,.0f}" if isinstance(_claims_stats, dict) else "$0")
    c5.metric("Policies", policy_count)

    claims = api_get("/claims/")
    if claims and isinstance(claims, list) and len(claims) > 0:
        df = pd.DataFrame(claims)
        col1, col2 = st.columns(2)
        with col1:
            if "service_date" in df.columns:
                df["_parsed_date"] = pd.to_datetime(df["service_date"], errors="coerce")
                valid_dates = df.dropna(subset=["_parsed_date"])
                if len(valid_dates) > 0:
                    valid_dates["month"] = valid_dates["_parsed_date"].dt.to_period("M").astype(str)
                    monthly = valid_dates.groupby("month").size().reset_index(name="count")
                    fig = px.line(monthly, x="month", y="count", title="Claims Over Time", markers=True,
                        color_discrete_sequence=["#3B82F6"])
                    st.plotly_chart(plotly_dark(fig), use_container_width=True)
                else:
                    st.info("No valid service dates to chart")
        with col2:
            if "risk_level" in df.columns:
                risk_dist = df["risk_level"].value_counts().reset_index()
                risk_dist.columns = ["Risk Level","Count"]
                fig = px.pie(risk_dist, values="Count", names="Risk Level", title="Risk Distribution",
                    color="Risk Level", color_discrete_map={"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#22C55E"}, hole=0.4)
                st.plotly_chart(plotly_dark(fig), use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            denied = df[df["claim_status"]=="Denied"]
            if len(denied) > 0 and "denial_reason" in denied.columns:
                reasons = denied["denial_reason"].value_counts().head(5).reset_index()
                reasons.columns = ["Reason","Count"]
                fig = px.bar(reasons, x="Count", y="Reason", orientation="h", title="Top Denial Reasons",
                    color_discrete_sequence=["#EF4444"])
                st.plotly_chart(plotly_dark(fig), use_container_width=True)
            else:
                st.info("No denied claims to analyze")
        with col4:
            if "billed_amount" in df.columns and "risk_level" in df.columns:
                rev = df.groupby("risk_level")["billed_amount"].sum().reset_index()
                rev.columns = ["Risk Level","Revenue"]
                fig = px.bar(rev, x="Risk Level", y="Revenue", title="Revenue by Risk Level",
                    color="Risk Level", color_discrete_map={"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#22C55E"})
                st.plotly_chart(plotly_dark(fig), use_container_width=True)

        st.markdown("#### 🏆 Top High-Risk Claims")
        if "risk_score" in df.columns and "patient_name" in df.columns:
            agg_cols = {}
            if "risk_score" in df.columns: agg_cols["risk_score"] = "mean"
            if "billed_amount" in df.columns: agg_cols["billed_amount"] = "sum"
            agg_cols["claim_id"] = "count"
            providers = df.groupby("patient_name").agg(agg_cols).reset_index()
            col_names = ["Patient"]
            if "risk_score" in agg_cols: col_names.append("Avg Risk Score")
            if "billed_amount" in agg_cols: col_names.append("Total Billed")
            col_names.append("Claims")
            providers.columns = col_names
            sort_col = "Avg Risk Score" if "Avg Risk Score" in providers.columns else "Claims"
            providers = providers.sort_values(sort_col, ascending=False).head(5)
            st.dataframe(providers, use_container_width=True, hide_index=True)
    else:
        st.info("No claims data yet. Upload data or add claims to see the dashboard.")

# ╔══════════════════════════════════════════════════════════════
# ║  PAGE: DATA MANAGEMENT
# ╚══════════════════════════════════════════════════════════════
elif page == "📁 Data Management":
    st.markdown("### 📁 Data Management")
    tab1, tab2, tab3 = st.tabs(["👤 Patients","📋 Claims","📤 Excel Upload"])

    with tab1:
        st.markdown("#### Add New Patient")
        with st.form("add_patient", clear_on_submit=True):
            r1c1,r1c2,r1c3 = st.columns(3)
            pid = r1c1.text_input("Patient ID", placeholder="P-10006")
            name = r1c2.text_input("Full Name", placeholder="Jane Doe")
            dob = r1c3.text_input("Date of Birth", placeholder="1990-01-15")
            r2c1,r2c2,r2c3,r2c4 = st.columns(4)
            gender = r2c1.selectbox("Gender",["Male","Female","Other"])
            provider = r2c2.text_input("Provider", placeholder="Dr. Smith")
            facility = r2c3.text_input("Facility", placeholder="City Hospital")
            payer = r2c4.selectbox("Payer",["Medicare","Blue Cross","Aetna","United Health","Cigna","Humana","Other"])
            if st.form_submit_button("➕ Add Patient", use_container_width=True):
                if pid and name:
                    with st.spinner("Adding patient..."):
                        res = api_post("/patients/", {"patient_id":pid,"name":name,"dob":dob,"gender":gender,"provider_name":provider,"facility":facility,"payer":payer})
                    if "error" in res or "detail" in res:
                        st.error(f"❌ {res.get('detail', res.get('error','Unknown error'))}")
                    else:
                        st.success(f"✅ Patient '{name}' added!")
                        time.sleep(1); st.rerun()
                else: st.warning("Patient ID and Name are required")

        patients = api_get("/patients/")
        if patients and isinstance(patients, list) and len(patients) > 0:
            st.markdown(f"#### Patient Records ({len(patients)})")
            df = pd.DataFrame(patients)
            cols_show = [c for c in ["patient_id","name","dob","gender","provider_name","facility","payer"] if c in df.columns]
            st.dataframe(df[cols_show], use_container_width=True, hide_index=True)

            csv = df.to_csv(index=False)
            st.download_button("📥 Export CSV", csv, "patients.csv", "text/csv")

            st.markdown("---")
            st.markdown("#### 🗑 Delete Patient")
            del_opts = {f"{p['patient_id']} — {p['name']}": p['id'] for p in patients}
            sel_del = st.selectbox("Select patient to delete", list(del_opts.keys()), key="del_patient_sel")
            if st.button("🗑 Delete Selected Patient", key="del_one_patient"):
                res = api_delete(f"/patients/{del_opts[sel_del]}")
                if "error" in res or "detail" in res:
                    st.error(f"❌ {res.get('detail', res.get('error',''))}")
                else:
                    st.success("✅ Patient deleted!")
                    time.sleep(1); st.rerun()

            with st.expander("🗑 Delete ALL Patients (Danger Zone)", expanded=False):
                st.error("⚠ This will permanently delete ALL patient records!")
                confirm_text = st.text_input("Type DELETE to confirm", key="confirm_del_patients_text", placeholder="Type DELETE here...")
                if st.button("🗑 Confirm Delete All Patients", key="exec_del_all_patients"):
                    if confirm_text == "DELETE":
                        res = api_delete("/patients/delete-all/confirm")
                        st.success(f"✅ {res.get('message', 'All patients deleted.')}")
                        time.sleep(1); st.rerun()
                    else:
                        st.warning("You must type DELETE exactly to confirm.")
        else:
            st.info("No patients in database.")

    with tab2:
        st.markdown("#### Add New Claim")
        with st.form("add_claim", clear_on_submit=True):
            r1c1,r1c2,r1c3,r1c4 = st.columns(4)
            cid = r1c1.text_input("Claim ID", placeholder="CLM-B0001")
            pname = r1c2.text_input("Patient Name", placeholder="John Doe")
            cpt = r1c3.text_input("CPT Code", placeholder="99214")
            icd = r1c4.text_input("ICD-10", placeholder="E11.9")
            r2c1,r2c2,r2c3,r2c4 = st.columns(4)
            amt = r2c1.number_input("Billed Amount ($)",0.0,100000.0,250.0)
            sdate = r2c2.text_input("Service Date", placeholder="2025-12-15")
            status = r2c3.selectbox("Status",["Pending","Approved","Denied"])
            pa = r2c4.checkbox("Prior Auth Required")
            if st.form_submit_button("➕ Add Claim", use_container_width=True):
                if cid and cpt:
                    with st.spinner("Adding claim..."):
                        res = api_post("/claims/", {"claim_id":cid,"patient_name":pname,"cpt_code":cpt,"icd10_code":icd,"billed_amount":amt,"service_date":sdate,"claim_status":status,"prior_auth_required":pa})
                    if "error" in res or "detail" in res:
                        st.error(f"❌ {res.get('detail', res.get('error',''))}")
                    else:
                        st.success(f"✅ Claim '{cid}' added!")
                        time.sleep(1); st.rerun()
                else: st.warning("Claim ID and CPT Code are required")

        claims = api_get("/claims/")
        if claims and isinstance(claims, list) and len(claims) > 0:
            st.markdown(f"#### Claims ({len(claims)})")
            df = pd.DataFrame(claims)
            cols = [c for c in ["claim_id","patient_name","cpt_code","icd10_code","billed_amount","claim_status","risk_level","service_date"] if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)

            csv = df.to_csv(index=False)
            st.download_button("📥 Export CSV", csv, "claims.csv", "text/csv")

            st.markdown("---")
            st.markdown("#### 🗑 Delete Claim")
            del_opts = {f"{c['claim_id']} — {c.get('patient_name','')} ({c.get('claim_status','')})": c['id'] for c in claims}
            sel_del = st.selectbox("Select claim to delete", list(del_opts.keys()), key="del_claim_sel")
            if st.button("🗑 Delete Selected Claim", key="del_one_claim"):
                res = api_delete(f"/claims/{del_opts[sel_del]}")
                if "error" in res or "detail" in res:
                    st.error(f"❌ {res.get('detail', res.get('error',''))}")
                else:
                    st.success("✅ Claim deleted!")
                    time.sleep(1); st.rerun()

            with st.expander("🗑 Delete ALL Claims (Danger Zone)", expanded=False):
                st.error("⚠ This will permanently delete ALL claim records!")
                confirm_text = st.text_input("Type DELETE to confirm", key="confirm_del_claims_text", placeholder="Type DELETE here...")
                if st.button("🗑 Confirm Delete All Claims", key="exec_del_all_claims"):
                    if confirm_text == "DELETE":
                        res = api_delete("/claims/delete-all/confirm")
                        st.success(f"✅ {res.get('message', 'All claims deleted.')}")
                        time.sleep(1); st.rerun()
                    else:
                        st.warning("You must type DELETE exactly to confirm.")
        else:
            st.info("No claims in database.")

    with tab3:
        st.markdown("#### 📤 Smart Excel Upload (Patients + Claims)")
        st.markdown("Upload any hospital Excel file — the system will **auto-detect and map** your column names to the correct database fields, even if the headers are messy or non-standard.")
        uploaded = st.file_uploader("Choose Excel file", type=["xlsx","xls"], key="bulk_upload")
        if uploaded:
            # Preview raw columns
            try:
                preview_df = pd.read_excel(io.BytesIO(uploaded.getvalue()))
                st.markdown(f"**Detected {len(preview_df.columns)} columns, {len(preview_df)} rows**")
                with st.expander("👀 Preview Raw Data (first 5 rows)", expanded=False):
                    st.dataframe(preview_df.head(5), use_container_width=True, hide_index=True)
            except Exception:
                pass

            if st.button("🚀 Smart Map & Upload", use_container_width=True):
                with st.spinner("🧠 Analyzing columns and uploading..."):
                    res = api_post("/claims/bulk", files={"file": (uploaded.name, uploaded.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
                if "error" in res or "detail" in res:
                    st.error(f"❌ {res.get('detail', res.get('error',''))}")
                else:
                    st.success(f"✅ {res.get('message','Upload complete')}")
                    # Show column mapping results
                    cm = res.get("column_mapping", {})
                    if cm:
                        st.markdown("#### 🗺️ Column Mapping Results")
                        mc1, mc2, mc3 = st.columns(3)
                        mc1.metric("Mapped Columns", res.get("mapped_columns", 0))
                        mc2.metric("Total Columns", res.get("total_raw_columns", 0))
                        mc3.metric("Unmapped", len(res.get("unmapped_columns", [])))
                        map_rows = [{"Original Column": raw, "Mapped To": info["mapped_to"], "Confidence": f"{info['confidence']*100:.0f}%"} for raw, info in cm.items()]
                        st.dataframe(pd.DataFrame(map_rows), use_container_width=True, hide_index=True)
                        if res.get("unmapped_columns"):
                            st.warning(f"⚠ Unmapped columns (ignored): {', '.join(res['unmapped_columns'])}")
                    time.sleep(1); st.rerun()

# ╔══════════════════════════════════════════════════════════════
# ║  PAGE: WATCHER
# ╚══════════════════════════════════════════════════════════════
elif page == "👁 Watcher":
    st.markdown("### 👁 Watcher — Policy Monitor")
    tab1,tab2,tab3,tab4,tab5 = st.tabs(["📝 Paste Text","🔗 Scan URL","📄 Upload File","📚 Policy Library","📰 CMS News"])

    with tab1:
        st.markdown("#### Paste policy text for AI analysis")
        text = st.text_area("Policy text", height=200, placeholder="Paste CMS policy document, billing guideline, or regulation text here...")
        if st.button("🔍 Analyze Text", key="wt", use_container_width=True):
            if text:
                with st.spinner("🤖 AI analyzing policy..."):
                    res = api_post("/agents/watcher/scan-text", {"text":text})
                if res.get("status")=="success":
                    p = res["policy"]
                    st.success(f"✅ Policy saved: **{p['title']}**")
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Impact Level", p.get("impact_level",""))
                    c2.metric("Affected Codes", p.get("affected_codes","")[:30])
                    c3.metric("Deadline", f"{p.get('deadline_days',30)} days")
                    st.markdown(f"**Summary:** {p.get('summary','')}")
                else: st.error(f"❌ {res.get('detail', res.get('error','Analysis failed'))}")
            else: st.warning("Please paste policy text")

    with tab2:
        url = st.text_input("Policy URL", placeholder="https://www.cms.gov/...")
        if st.button("🌐 Scan URL", key="wu", use_container_width=True):
            if url:
                with st.spinner("🌐 Fetching and analyzing URL..."):
                    res = api_post("/agents/watcher/scan-url", {"url":url})
                if res.get("status")=="success":
                    p = res["policy"]
                    st.success(f"✅ Policy saved: **{p['title']}**")
                    st.json(p)
                else: st.error(f"❌ {res.get('detail', res.get('error',''))}")
            else: st.warning("Enter a URL")

    with tab3:
        st.markdown("#### Upload Policy Document (PDF/TXT/Excel)")
        uploaded = st.file_uploader("Choose file", type=["pdf","txt","xlsx","xls","csv"], key="watcher_upload")
        if uploaded and st.button("📄 Analyze File", key="wf", use_container_width=True):
            with st.spinner("📄 Extracting and analyzing..."):
                res = api_post("/agents/watcher/upload", files={"file":(uploaded.name, uploaded.getvalue())})
            if res.get("status")=="success":
                p = res["policy"]
                st.success(f"✅ Policy extracted from {res.get('filename','')}: **{p['title']}**")
                st.json(p)
            else: st.error(f"❌ {res.get('detail', res.get('error',''))}")

    with tab4:
        st.markdown("#### 📚 CMS Policy Library")
        policies = api_get("/policies/")
        if policies and isinstance(policies, list) and len(policies)>0:
            for p in policies:
                il = p.get("impact_level","LOW")
                badge = risk_badge(il)
                with st.expander(f"{p['title']} {badge}", expanded=False):
                    st.markdown(f"**Type:** {p.get('policy_type','')} | **Codes:** `{p.get('affected_codes','')}` | **Deadline:** {p.get('deadline_days','')} days", unsafe_allow_html=True)
                    st.markdown(f"**Requirements:** {p.get('requirements','')}")
                    st.markdown(f"**Denial Triggers:** {p.get('denial_triggers','')}")
                    st.markdown(f"**Summary:** {p.get('summary','')}")
        else: st.info("No policies in database. Use the tabs above to add policies, or run `python seed_db.py`.")

    with tab5:
        st.markdown("#### 📰 Latest CMS News")
        if st.button("🔄 Fetch Latest News", key="wn", use_container_width=True):
            with st.spinner("Fetching CMS news..."):
                res = api_get("/agents/watcher/news")
            if isinstance(res, dict) and res.get("news"):
                for n in res["news"]:
                    with st.container():
                        st.markdown(f"**[{n['title']}]({n.get('link','#')})**")
                        st.caption(f"{n.get('published','')} — {n.get('source','')}")
                        st.markdown(n.get("summary",""))
                        st.markdown("---")
            else: st.warning("No news available")

# ╔══════════════════════════════════════════════════════════════
# ║  PAGE: THINKER
# ╚══════════════════════════════════════════════════════════════
elif page == "🧠 Thinker":
    st.markdown("### 🧠 Thinker — Risk Analysis Engine")
    tab1,tab2,tab3,tab4 = st.tabs(["👤 Patient Input","📤 Upload Claims Excel","🔄 Scan Existing","🔍 Data Quality Check"])

    with tab1:
        st.markdown("#### Enter Patient & Claim Details for Risk Analysis")
        with st.form("thinker_input"):
            st.markdown("**Patient Information**")
            r1 = st.columns(4)
            pname = r1[0].text_input("Patient Name", placeholder="John Doe")
            pid = r1[1].text_input("Patient ID", placeholder="P-10001")
            payer = r1[2].selectbox("Payer",["Medicare","Blue Cross","Aetna","United Health","Cigna","Humana"])
            provider = r1[3].text_input("Provider", placeholder="Dr. Smith")

            st.markdown("**Claim Information**")
            r2 = st.columns(4)
            cpt = r2[0].text_input("CPT Code", placeholder="99214")
            icd = r2[1].text_input("ICD-10 Code", placeholder="E11.9")
            amt = r2[2].number_input("Billed Amount ($)", 0.0, 100000.0, 250.0)
            sdate = r2[3].text_input("Service Date", placeholder="2025-12-15")

            r3 = st.columns(4)
            pa = r3[0].checkbox("Prior Auth Required")
            doc = r3[1].checkbox("Documentation Required")
            comp = r3[2].slider("Compliance Score", 0.0, 1.0, 0.85, 0.05)
            status = r3[3].selectbox("Claim Status",["Pending","Approved","Denied"])

            submitted = st.form_submit_button("🧠 Analyze Risk", use_container_width=True)

        if submitted and cpt:
            with st.spinner("🧠 Running XGBoost + AI risk analysis..."):
                res = api_post("/agents/thinker/scan", {
                    "patient_name":pname,"patient_id":pid,"cpt_code":cpt,"icd10_code":icd,
                    "billed_amount":amt,"payer":payer,"provider_name":provider,
                    "prior_auth_required":pa,"documentation_required":doc,
                    "provider_compliance_score":comp,"service_date":sdate,"claim_status":status
                })
            if res.get("status")=="success":
                r = res["result"]
                st.markdown("---")
                st.markdown("#### Analysis Results")
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Risk Score", f"{r.get('risk_score',0)}/100")
                rl = r.get("risk_level","LOW")
                c2.markdown(f"**Risk Level**\n\n{risk_badge(rl)}", unsafe_allow_html=True)
                c3.metric("Matched Policy", r.get("matched_policy","None")[:30])
                c4.metric("Claim ID", r.get("claim_id",""))

                with st.expander("🤖 AI Reasoning", expanded=True):
                    st.markdown(r.get("reasoning","No reasoning available"))

                fi = r.get("feature_importance",{})
                if fi:
                    st.markdown("#### Feature Importance")
                    fig = go.Figure(go.Bar(x=list(fi.values()),y=list(fi.keys()),orientation="h",
                        marker_color=["#EF4444" if v>0.5 else "#F59E0B" if v>0.3 else "#22C55E" for v in fi.values()]))
                    fig.update_layout(title="Risk Factor Contribution",xaxis_title="Impact")
                    st.plotly_chart(plotly_dark(fig), use_container_width=True)
            else: st.error(f"❌ {res.get('detail', res.get('error',''))}")

    with tab2:
        st.markdown("#### Upload Claims Excel for Batch Scoring")
        uploaded = st.file_uploader("Claims Excel", type=["xlsx","xls"], key="thinker_excel")
        if uploaded and st.button("🚀 Score All Claims", key="te", use_container_width=True):
            with st.spinner("🧠 Scoring claims..."):
                res = api_post("/agents/thinker/upload-excel", files={"file":(uploaded.name, uploaded.getvalue())})
            if res.get("status")=="success" and res.get("results"):
                results = res["results"]
                st.success(f"✅ Scored {len(results)} claims")
                df = pd.DataFrame(results)
                cols = [c for c in ["claim_id","patient_name","cpt_code","billed_amount","risk_score","risk_level","matched_policy","recommended_action"] if c in df.columns]
                st.dataframe(df[cols], use_container_width=True, hide_index=True)

                buf = io.BytesIO()
                df.to_excel(buf, index=False)
                st.download_button("📥 Download Results Excel", buf.getvalue(), "risk_results.xlsx")
            else: st.error(f"❌ {res.get('detail',res.get('error',''))}")

    with tab3:
        st.markdown("#### Scan All Existing Claims Against Policies")
        if st.button("🔄 Scan All Claims", key="tse", use_container_width=True):
            with st.spinner("Scanning existing claims..."):
                res = api_post("/agents/thinker/scan-existing")
            if res.get("status")=="success":
                st.success(f"✅ {res.get('message','')}")
                st.rerun()
            else: st.error(f"❌ {res.get('detail','')}")

        claims = api_get("/claims/")
        if claims and isinstance(claims, list) and len(claims) > 0:
            df = pd.DataFrame(claims)
            risk_filter = st.selectbox("Filter by Risk", ["ALL","HIGH","MEDIUM","LOW"])
            if risk_filter != "ALL":
                df = df[df.get("risk_level",pd.Series())==risk_filter] if "risk_level" in df.columns else df
            cols = [c for c in ["claim_id","patient_name","cpt_code","billed_amount","risk_score","risk_level","matched_policy"] if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No claims to display. Upload data first.")

    with tab4:
        st.markdown("#### 🔍 Data Quality Check")
        st.markdown("Upload a hospital Excel file to check for **missing or incomplete data** compared against CMS policy requirements. The system will flag critical missing fields that could cause claim denials.")
        dq_file = st.file_uploader("Upload Excel for Quality Analysis", type=["xlsx","xls"], key="dq_upload")
        if dq_file and st.button("🔍 Analyze Data Quality", key="dq_btn", use_container_width=True):
            with st.spinner("🔍 Mapping columns and checking data quality..."):
                res = api_post("/agents/thinker/analyze-data-quality", files={"file":(dq_file.name, dq_file.getvalue())})
            if res.get("status")=="success":
                qr = res.get("quality_report", {})
                cm = res.get("column_mapping", {})

                # Summary metrics
                st.markdown("---")
                st.markdown("#### 📊 Data Quality Summary")
                m1,m2,m3,m4,m5 = st.columns(5)
                m1.metric("Total Rows", qr.get("total_rows",0))
                m2.metric("🚩 Critical", qr.get("critical_count",0))
                m3.metric("⚠ Warnings", qr.get("warning_count",0))
                m4.metric("ℹ Info", qr.get("info_count",0))
                comp = qr.get("completeness_pct", 0)
                m5.metric("Completeness", f"{comp}%")

                # Completeness gauge
                fig = go.Figure(go.Indicator(mode="gauge+number", value=comp,
                    title={"text": "Data Completeness"},
                    gauge={"axis":{"range":[0,100]},"bar":{"color":"#3B82F6"},
                           "steps":[{"range":[0,50],"color":"#7F1D1D"},{"range":[50,75],"color":"#78350F"},{"range":[75,100],"color":"#14532D"}]}))
                st.plotly_chart(plotly_dark(fig), use_container_width=True)

                # Column mapping
                if cm:
                    with st.expander("🗺️ Column Mapping", expanded=False):
                        map_rows = [{"Original": raw, "Mapped To": info["mapped_to"], "Confidence": f"{info['confidence']*100:.0f}%"} for raw, info in cm.items()]
                        st.dataframe(pd.DataFrame(map_rows), use_container_width=True, hide_index=True)
                    unmapped = res.get("unmapped_columns", [])
                    if unmapped:
                        st.warning(f"Unmapped columns: {', '.join(unmapped)}")

                # Field-level summary
                fs = qr.get("field_summary", {})
                if fs:
                    st.markdown("#### 🏷️ Flags by Field")
                    fs_rows = [{"Field": f, "🚩 Critical": c.get("CRITICAL",0), "⚠ Warning": c.get("WARNING",0), "ℹ Info": c.get("INFO",0)} for f, c in fs.items()]
                    st.dataframe(pd.DataFrame(fs_rows), use_container_width=True, hide_index=True)

                # Per-row flags
                flagged = qr.get("rows_with_flags", [])
                if flagged:
                    st.markdown(f"#### 🚩 Flagged Rows ({len(flagged)})")
                    for item in flagged[:20]:  # Show first 20
                        row_idx = item.get("row_index", 0)
                        flags = item.get("flags", [])
                        criticals = [f for f in flags if f["level"] == "CRITICAL"]
                        warnings = [f for f in flags if f["level"] == "WARNING"]
                        icon = "🚩" if criticals else "⚠" if warnings else "ℹ"
                        label = f"{icon} Row {row_idx+1}: {len(criticals)} critical, {len(warnings)} warnings"
                        with st.expander(label, expanded=bool(criticals)):
                            for fl in flags:
                                color = {"CRITICAL":"🚩","WARNING":"⚠","INFO":"ℹ"}.get(fl["level"],"ℹ")
                                st.markdown(f"{color} **{fl['field']}**: {fl['message']}")

                # Download flagged report
                if flagged:
                    flag_export = []
                    for item in flagged:
                        for fl in item.get("flags",[]):
                            flag_export.append({"Row": item["row_index"]+1, "Level": fl["level"], "Field": fl["field"], "Issue": fl["message"]})
                    if flag_export:
                        buf = io.BytesIO()
                        pd.DataFrame(flag_export).to_excel(buf, index=False)
                        st.download_button("📥 Download Flagged Report", buf.getvalue(), "data_quality_flags.xlsx")
            else:
                st.error(f"❌ {res.get('detail', res.get('error',''))}")

# ╔══════════════════════════════════════════════════════════════
# ║  PAGE: FIXER
# ╚══════════════════════════════════════════════════════════════
elif page == "🔧 Fixer":
    st.markdown("### 🔧 Fixer — Corrective Action Engine")
    tab1, tab2 = st.tabs(["🛠 Generate Fix","📋 Fix History"])

    with tab1:
        claims = api_get("/claims/")
        policies = api_get("/policies/")
        if claims and isinstance(claims, list):
            high_risk = [c for c in claims if c.get("risk_level") in ("HIGH","MEDIUM")]
            if high_risk:
                claim_opts = {f"{c['claim_id']} — {c.get('patient_name','')} (Risk: {c.get('risk_level','')})": c['claim_id'] for c in high_risk}
                selected = st.selectbox("Select Claim to Fix", list(claim_opts.keys()))
                claim_id = claim_opts[selected]

                policy_id = None
                if policies and isinstance(policies, list):
                    pol_opts = {"Auto-detect": None}
                    pol_opts.update({f"{p['title']} ({p.get('affected_codes','')})": p['id'] for p in policies})
                    pol_sel = st.selectbox("Match Against Policy", list(pol_opts.keys()))
                    policy_id = pol_opts[pol_sel]

                if st.button("🔧 Generate Fix Plan", use_container_width=True):
                    with st.spinner("🤖 Generating corrective action plan..."):
                        res = api_post("/agents/fixer/generate", {"claim_id":claim_id,"policy_id":policy_id})
                    if res.get("status")=="success":
                        f = res["fix"]
                        st.success("✅ Fix plan generated!")
                        c1,c2,c3 = st.columns(3)
                        c1.metric("Claim", f.get("claim_id",""))
                        c2.metric("Deadline", f.get("deadline",""))
                        c3.metric("Est. Savings", f"${f.get('estimated_savings',0):,.2f}")
                        st.markdown("#### 📋 Action Plan")
                        st.markdown(f.get("action_plan",""))
                        with st.expander("📧 Email Template"):
                            st.code(f.get("email_template",""), language="text")
                    else: st.error(f"❌ {res.get('detail','')}")
            else: st.info("No high or medium risk claims to fix. Run Thinker first.")
        else: st.info("No claims found.")

    with tab2:
        fixes = api_get("/agents/fixer/list")
        if fixes and isinstance(fixes, list) and len(fixes)>0:
            for f in fixes:
                status_icon = "✅" if f["status"]=="Fixed" else "⏳"
                with st.expander(f"{status_icon} {f['claim_id']} — {f.get('policy_title','')} [{f['status']}]"):
                    st.markdown(f"**Deadline:** {f.get('deadline','')} | **Savings:** ${f.get('estimated_savings',0):,.2f}")
                    st.markdown(f.get("action_plan",""))
                    if f["status"] != "Fixed":
                        if st.button(f"✅ Mark as Fixed", key=f"fix_{f['id']}"):
                            with st.spinner("Updating..."):
                                api_post(f"/agents/fixer/mark-fixed/{f['id']}")
                            st.success("Marked as fixed!")
                            time.sleep(1); st.rerun()
        else: st.info("No fix plans generated yet.")

# ╔══════════════════════════════════════════════════════════════
# ║  PAGE: AUDIT TRAIL
# ╚══════════════════════════════════════════════════════════════
elif page == "📋 Audit Trail":
    st.markdown("### 📋 Audit Trail")
    logs = api_get("/agents/audit-logs")
    if logs and isinstance(logs, list) and len(logs)>0:
        df = pd.DataFrame(logs)
        entity_filter = st.multiselect("Filter by Entity", df["entity_type"].unique().tolist(), default=df["entity_type"].unique().tolist())
        filtered = df[df["entity_type"].isin(entity_filter)]
        cols = [c for c in ["timestamp","action","entity_type","entity_id","details","user"] if c in filtered.columns]
        st.dataframe(filtered[cols], use_container_width=True, hide_index=True)

        csv = filtered.to_csv(index=False)
        st.download_button("📥 Export Audit Log CSV", csv, "audit_log.csv", "text/csv")
        st.metric("Total Actions", len(filtered))
    else:
        st.info("No audit logs yet. Actions will be logged as you use the app.")

import streamlit as st
import pandas as pd
import datetime
import provenance_core as pl
# Page Configuration
st.set_page_config(
    page_title="Provenance Lab",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Provenance Lab · Practical Dashboard")

user = pl.login_gate()
ROLE = user["role"]

# Sidebar Navigation
st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Go to Section",
    pl.pages_for(ROLE),
    format_func=lambda p: f"{pl.PAGE_ICONS.get(p, '')} {p}",
)
pl.sidebar_user_box(user)

# Initialize Session State Variables
if "aim" not in st.session_state:
    st.session_state["aim"] = "Design and evaluation of modified release dosage forms."

# Daily Report State
if "daily_reports" not in st.session_state:
    st.session_state["daily_reports"] = []
if "report_deadline" not in st.session_state:
    st.session_state["report_deadline"] = datetime.time(17, 30)

# Systematic Literature Search & Research Scope State
if "lit_query" not in st.session_state:
    st.session_state["lit_query"] = "(\"modified release\" OR \"sustained release\") AND (\"dissolution kinetics\" OR \"Korsmeyer-Peppas\")"
if "lit_databases" not in st.session_state:
    st.session_state["lit_databases"] = "PubMed, ScienceDirect, Google Scholar"
if "lit_drugs" not in st.session_state:
    st.session_state["lit_drugs"] = "Metoprolol Succinate, Curcumin, Diltiazem HCl"
if "lit_formulations" not in st.session_state:
    st.session_state["lit_formulations"] = "Hydrophilic Matrix Tablets, Solid Dispersions, Floating Microballoons"
if "lit_diseases" not in st.session_state:
    st.session_state["lit_diseases"] = "Hypertension, Inflammatory Bowel Disease (IBD), Cardiovascular Disorders"
if "lit_criteria" not in st.session_state:
    st.session_state["lit_criteria"] = "Inclusion: Peer-reviewed articles (2015-2026), English language.\nExclusion: Non-oral dosage forms, missing kinetic parameters."
if "lit_summary" not in st.session_state:
    st.session_state["lit_summary"] = "Identified key formulation parameters influencing polymer matrix hydration and release rates."
if "lit_gaps" not in st.session_state:
    st.session_state["lit_gaps"] = "Limited in vivo correlation for high-variability gastrointestinal transit times; lack of standardized release kinetics models for complex multi-polymer matrices."
if "lit_prospects" not in st.session_state:
    st.session_state["lit_prospects"] = "Application of 3D printing for personalized controlled release doses and integration of Machine Learning (QbD) for automated dissolution modeling."

# Protocol & Review State
if "materials" not in st.session_state:
    st.session_state["materials"] = "Active Pharmaceutical Ingredient (API), Hydrophilic Polymers, Excipients, Buffer Solution (pH 6.8)."
if "method" not in st.session_state:
    st.session_state["method"] = "1. Prepare formulation powder blend.\n2. Compress tablets using rotary press.\n3. Perform dissolution testing (USP Type II Apparatus)."
if "mentor_status" not in st.session_state:
    st.session_state["mentor_status"] = "Pending Review"
if "mentor_comments" not in st.session_state:
    st.session_state["mentor_comments"] = ""


# ==========================================
# SECTION 1: PROTOCOL & SYSTEMATIC LITERATURE SEARCH
# ==========================================
if page == "1. Protocol & Literature Search":
    st.header("📋 Experiment Protocol & Research Scope")
    
    st.subheader("Aim")
    st.session_state["aim"] = st.text_area("State the Aim of the Experiment", value=st.session_state["aim"], height=80)
    
    st.subheader("🔍 Literature Search")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state["lit_query"] = st.text_input("Search Strategy / Keywords", value=st.session_state["lit_query"])
        st.session_state["lit_drugs"] = st.text_input("Target Model Drugs (APIs)", value=st.session_state["lit_drugs"])
        st.session_state["lit_diseases"] = st.text_input("Target Diseases / Indications", value=st.session_state["lit_diseases"])
    with col2:
        st.session_state["lit_databases"] = st.text_input("Databases Searched", value=st.session_state["lit_databases"])
        st.session_state["lit_formulations"] = st.text_input("Dosage Forms / Formulations", value=st.session_state["lit_formulations"])
        
    st.session_state["lit_criteria"] = st.text_area("Inclusion & Exclusion Criteria", value=st.session_state["lit_criteria"], height=100)
    st.session_state["lit_summary"] = st.text_area("Key Literature Findings / Theory Overview", value=st.session_state["lit_summary"], height=120)
    with st.expander("📚 Related dissertations from the department library"):
        pl.related_dissertations(" ".join([st.session_state["lit_drugs"], st.session_state["lit_formulations"], st.session_state["lit_query"]]))
        st.caption("Keyword match. Open page 8 for full search.")
    
    st.subheader("💡 Research Gap & Future Prospects")
    st.session_state["lit_gaps"] = st.text_area("Identified Research Gaps", value=st.session_state["lit_gaps"], height=100)
    st.session_state["lit_prospects"] = st.text_area("Future Prospects & Directions", value=st.session_state["lit_prospects"], height=100)

    st.subheader("Materials & Reagents")
    st.caption("Record exact chemical quantities used on page 7 (Chemicals & Inventory).")
    st.session_state["materials"] = st.text_area("List Materials & Equipment Used", value=st.session_state["materials"], height=100)
    
    st.subheader("Method / Methodology")
    st.session_state["method"] = st.text_area("Step-by-Step Procedure", value=st.session_state["method"], height=120)

# ==============================================================================
# SECTION 2: RESULTS & DATA UPLOAD
# ==============================================================================
elif page == "2. Results & Data Upload":
    st.header("📊 Results & Data Upload")
    
    uploaded_file = st.file_uploader("Upload Experimental Data (Excel or CSV)", type=["csv", "xlsx"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Save raw dataframe to session state
            st.session_state["results_df"] = df
            st.success("File uploaded successfully!")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # Display Data & Plot Chart
    if "results_df" in st.session_state:
        df = st.session_state["results_df"]
        
        st.subheader("📋 Uploaded Data Table")
        st.dataframe(df, use_container_width=True)
        
        st.subheader("📈 Interactive Release / Calibration Curve")
        
        # Filter for numeric-only columns to avoid Streamlit plot crashes
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        
        if len(numeric_cols) >= 2:
            x_axis = st.selectbox("Select X-Axis (e.g., Time / Concentration):", numeric_cols, index=0)
            y_axis = st.selectbox("Select Y-Axis (e.g., % Release / Absorbance):", numeric_cols, index=min(1, len(numeric_cols)-1))
            
            # Clean data: drop rows where selected X or Y values are missing
            chart_data = df[[x_axis, y_axis]].dropna().set_index(x_axis)
            st.line_chart(chart_data)
        elif len(numeric_cols) == 1:
            st.line_chart(df[numeric_cols].dropna())
        else:
            st.warning("No pure numeric columns detected in the uploaded file to generate a chart. Please check your Excel formatting.")
    else:
        st.info("No data file uploaded yet.")

# ==========================================
# SECTION 3: CHECKER / MENTOR
# ==========================================
elif page == "3. Checker / Mentor Review":
    st.header("👨‍🏫 Checker / Mentor Verification")
    
    st.session_state["mentor_status"] = st.selectbox(
        "Verification Status",
        ["Pending Review", "Approved", "Needs Revision", "Rejected"],
        index=["Pending Review", "Approved", "Needs Revision", "Rejected"].index(st.session_state["mentor_status"])
    )
    
    st.session_state["mentor_comments"] = st.text_area(
        "Mentor / Checker Feedback",
        value=st.session_state["mentor_comments"],
        placeholder="Enter evaluation remarks here..."
    )
    
    if st.button("Save Evaluation"):
        st.success(f"Status updated to: {st.session_state['mentor_status']}")

# ==========================================
# SECTION 4: PRINT / SUBMISSION PREVIEW
# ==========================================
elif page == "4. Print & Submission Preview":
    st.header("📄 Experiment Report Preview")
    st.write("Review the complete practical document before final submission.")
    
    st.markdown("---")
    st.markdown(f"### *Aim:*\n{st.session_state['aim']}")
    
    st.markdown("### *Systematic Literature Search & Scope:*")
    st.markdown(f"- *Search Query:* {st.session_state['lit_query']}")
    st.markdown(f"- *Databases:* {st.session_state['lit_databases']}")
    st.markdown(f"- *Model Drugs:* {st.session_state['lit_drugs']}")
    st.markdown(f"- *Formulation Types:* {st.session_state['lit_formulations']}")
    st.markdown(f"- *Target Indications:* {st.session_state['lit_diseases']}")
    st.markdown(f"- *Criteria:*\n{st.session_state['lit_criteria']}")
    st.markdown(f"- *Findings & Theory:*\n{st.session_state['lit_summary']}")
    st.markdown(f"- *Research Gaps Identified:*\n{st.session_state['lit_gaps']}")
    st.markdown(f"- *Future Prospects:*\n{st.session_state['lit_prospects']}")
    
    st.markdown(f"### *Materials:*\n{st.session_state['materials']}")
    st.markdown(f"### *Method:*\n{st.session_state['method']}")
    
    st.markdown("### *Results & Data:*")
    if "results_df" in st.session_state:
        st.dataframe(st.session_state["results_df"])
        st.line_chart(st.session_state["results_df"].set_index(st.session_state["results_df"].columns[0]))
    else:
        st.write("No data uploaded.")
        
    st.markdown("---")
    st.markdown(f"*Mentor Status:* {st.session_state['mentor_status']}")
    st.markdown(f"*Mentor Comments:* {st.session_state['mentor_comments']}")
# ==============================================================================
    # EXPORT / SAVE REPORT FEATURE
    # ==============================================================================
    st.markdown("---")
    st.subheader("💾 Export & Save Record")
    st.write("Download a permanent copy of your compiled practical logbook and evaluation report.")

    # 1. Compile all Session State entries into a clean text document
    compiled_report = f"""
================================================================================
                    PHARMACEUTICS PRACTICAL LOGBOOK & REPORT
================================================================================

1. EXPERIMENTAL PROTOCOL
--------------------------------------------------------------------------------
Aim:
{st.session_state.get('aim', 'N/A')}

Target Drug(s) / APIs:
{st.session_state.get('lit_drugs', 'N/A')}

2. SYSTEMATIC LITERATURE SEARCH & GAP ANALYSIS
--------------------------------------------------------------------------------
Search Query / Keywords:
{st.session_state.get('lit_query', 'N/A')}

Literature Summary:
{st.session_state.get('lit_summary', 'N/A')}

Identified Research Gaps & Rationale:
{st.session_state.get('lit_gaps', 'N/A')}

3. MENTOR REVIEW & VERIFICATION STATUS
--------------------------------------------------------------------------------
Verification Status : {st.session_state.get('mentor_status', 'Pending Review')}
Mentor Comments     : {st.session_state.get('mentor_comments', 'No comments added.')}

================================================================================
Generated via Pharmaceutics Practical Dashboard
================================================================================
"""

    # 2. Add Download Buttons for TXT and CSV summary formats
    col_dl1, col_dl2 = st.columns(2)

    with col_dl1:
        st.download_button(
            label="📄 Download Full Report (.txt)",
            data=compiled_report,
            file_name="Pharmaceutics_Practical_Report.txt",
            mime="text/plain",
            use_container_width=True
        )

    with col_dl2:
        # Create a summary CSV format for record keeping
        summary_data = {
            "Field": ["Aim", "Target Drugs", "Literature Summary", "Research Gaps", "Mentor Status"],
            "Value": [
                st.session_state.get('aim', 'N/A'),
                st.session_state.get('lit_drugs', 'N/A'),
                st.session_state.get('lit_summary', 'N/A'),
                st.session_state.get('lit_gaps', 'N/A'),
                st.session_state.get('mentor_status', 'Pending Review')
            ]
        }
        df_summary = pd.DataFrame(summary_data)
        csv_data = df_summary.to_csv(index=False)

        st.download_button(
            label="📊 Download Summary Table (.csv)",
            data=csv_data,
            file_name="Pharmaceutics_Practical_Summary.csv",
            mime="text/csv",
            use_container_width=True
        )
# ==========================================
# SECTION 5: POWER BI INTEGRATION
# ==========================================
elif page == "5. Power BI Analytics":
    st.header("📈 Power BI Analytics Integration")
    st.write("Embed your live Power BI report or view interactive analytical dashboards.")
    
    powerbi_url = st.text_input("Enter Power BI Embed URL / Share Link:", value="")
    
    if powerbi_url:
        st.components.v1.iframe(powerbi_url, width=1000, height=600, scrolling=True)
    else:
        st.info("Paste a public Power BI embed link above to view your embedded dashboard.")

# ==========================================
# SECTION 6: DAILY REPORT (SDP / CLASSES / PROJECT)
# ==========================================
elif page == "6. Daily Report":
    st.header("📝 Daily Report")
    st.caption("Prototype: reports are kept for this browser session only. A database is needed for real use.")

    IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    now = datetime.datetime.now(IST)
    today = now.date()
    DAY_TYPES = ["Class day", "SDP session", "Project day", "Leave request"]
    SUBJ, COV = "Subject", "Covered today (2 lines)"

    def _clean(v):
        return "" if pd.isna(v) else str(v).strip()

    tab_submit, tab_review = st.tabs(["Submit report", "Coordinator / faculty view"])

    # ---------------- Student: submit a report ----------------
    with tab_submit:
        col_a, col_b = st.columns(2)
        with col_a:
            if ROLE == "student" and not st.session_state.get("dr_student"):
                st.session_state["dr_student"] = user["name"]
            student = st.text_input("Student name", key="dr_student")
            day_type = st.selectbox("Type of day", DAY_TYPES, key="dr_type")
        with col_b:
            report_date = st.date_input("Date", value=today, key="dr_date")
            st.write(f"Deadline today: **{st.session_state['report_deadline'].strftime('%H:%M')}** (set by coordinator)")

        fields = {}
        required = []

        if day_type == "Class day":
            st.caption("Two lines per subject attended.")
            rows = st.data_editor(
                pd.DataFrame({SUBJ: [""], COV: [""]}),
                num_rows="dynamic",
                key="dr_class_rows",
            )
            fields["Class summary"] = "; ".join(
                f"{_clean(r[SUBJ])}: {_clean(r[COV])}"
                for _, r in rows.iterrows()
                if _clean(r[SUBJ]) or _clean(r[COV])
            )
            fields["Doubts / topics to revisit"] = st.text_area("Doubts or topics to revisit (optional)", key="dr_doubts")
            required = ["Class summary"]

        elif day_type == "SDP session":
            fields["Topic"] = st.text_input("Today's session topic", key="dr_topic")
            fields["What I learned"] = st.text_area("What I learned today", key="dr_learned")
            fields["Faculty question"] = st.text_input("Question asked by faculty", key="dr_q")
            fields["My answer"] = st.text_area("My answer (2-3 lines)", key="dr_ans")
            fields["Understanding"] = st.slider(
                "How well did I understand today's topic? (1 = not at all, 5 = fully)",
                1, 5, 3, key="dr_rate",
            )
            required = ["Topic", "What I learned", "My answer"]

        elif day_type == "Project day":
            fields["Work done"] = st.text_area("Work done today", key="dr_work")
            fields["Result / observation"] = st.text_area("Result or observation", key="dr_result")
            fields["Issues faced"] = st.text_area("Issues faced or help needed", key="dr_issues")
            fields["Plan for tomorrow"] = st.text_area("Plan for tomorrow", key="dr_plan")
            attach = st.file_uploader("Attach a photo or file (optional)", key="dr_file")
            if attach is not None:
                fields["Attachment"] = attach.name
            required = ["Work done", "Plan for tomorrow"]

        else:
            fields["Leave reason"] = st.text_area("Reason for leave", key="dr_leave")
            st.caption("No daily report is due once leave is approved. In the full system, the lecturers for those days approve it in the app.")
            required = ["Leave reason"]

        # Late check (not applicable to leave requests)
        late = False
        if day_type != "Leave request":
            late = report_date < today or (
                report_date == today and now.time() > st.session_state["report_deadline"]
            )
        late_reason = ""
        if late:
            st.warning("This is after the deadline. Add a reason; the coordinator decides whether to accept it.")
            late_reason = st.text_input("Reason for late submission", key="dr_late")

        if st.button("Submit report", type="primary", key="dr_submit"):
            missing = [k for k in required if not str(fields.get(k, "")).strip()]
            if not student.strip():
                st.error("Enter your name.")
            elif report_date > today:
                st.error("The date cannot be in the future.")
            elif missing:
                st.error("Please fill: " + ", ".join(missing))
            elif late and not late_reason.strip():
                st.error("Add a reason for the late submission.")
            else:
                if day_type == "Leave request":
                    status = "Leave requested"
                elif late:
                    status = "Pending (late entry)"
                else:
                    status = "Submitted - attendance counted"
                details = " | ".join(
                    f"{k}: {v}" for k, v in fields.items()
                    if k != "Understanding" and str(v).strip()
                )
                st.session_state["daily_reports"].append({
                    "Date": str(report_date),
                    "Student": student.strip(),
                    "Type": day_type,
                    "Status": status,
                    "Submitted at": now.strftime("%Y-%m-%d %H:%M"),
                    "Late reason": late_reason.strip(),
                    "Topic": fields.get("Topic", ""),
                    "Understanding": fields.get("Understanding"),
                    "Details": details,
                })
                st.success(f"Report saved. Status: {status}")
                if status.startswith("Submitted"):
                    st.toast("Attendance counted ✅")
                    st.balloons()

    # ---------------- Coordinator / faculty view ----------------
    with tab_review:
        if ROLE not in ("lecturer", "admin"):
            st.info("🔒 Coordinator view is for lecturers and admins.")
            st.stop()
        st.time_input("Submission deadline (coordinator sets this)", key="report_deadline")

        if st.button("Load sample data (demo only)", key="dr_demo"):
            def _d(name, kind, status, days_ago=0, topic="", rating=None):
                return {
                    "Date": str(today - datetime.timedelta(days=days_ago)),
                    "Student": name, "Type": kind, "Status": status,
                    "Submitted at": now.strftime("%Y-%m-%d %H:%M"),
                    "Late reason": "", "Topic": topic, "Understanding": rating,
                    "Details": "Sample entry",
                }
            ok = "Submitted - attendance counted"
            demo = [
                _d("Demo A", "SDP session", ok, 2, "Resume writing", 4),
                _d("Demo B", "SDP session", ok, 2, "Resume writing", 5),
                _d("Demo C", "SDP session", ok, 2, "Resume writing", 4),
                _d("Demo A", "SDP session", ok, 1, "Group discussion", 2),
                _d("Demo B", "SDP session", ok, 1, "Group discussion", 3),
                _d("Demo C", "SDP session", ok, 1, "Group discussion", 2),
                _d("Demo D", "SDP session", "Pending (late entry)", 0, "Interview basics", 3),
                _d("Demo E", "Class day", ok),
                _d("Demo F", "Project day", ok),
                _d("Demo G", "Leave request", "Leave requested"),
            ]
            kept = [r for r in st.session_state["daily_reports"] if not str(r["Student"]).startswith("Demo ")]
            st.session_state["daily_reports"] = kept + demo

        reports = st.session_state["daily_reports"]
        if not reports:
            st.info("No reports submitted yet.")
        else:
            df_r = pd.DataFrame(reports)
            types_sel = st.multiselect("Filter by type", DAY_TYPES, default=DAY_TYPES, key="dr_filter")
            view = df_r[df_r["Type"].isin(types_sel)]

            m1, m2, m3 = st.columns(3)
            counted = view["Status"].str.startswith("Submitted")
            m1.metric("Reports", len(view))
            m2.metric("Attendance counted", int(counted.sum()))
            m3.metric("Pending or leave", int((~counted).sum()))
            st.dataframe(view.drop(columns=["Topic", "Understanding"]), hide_index=True)

            sdp = df_r[(df_r["Type"] == "SDP session") & (df_r["Topic"].astype(str).str.strip() != "")].copy()
            if not sdp.empty:
                st.subheader("SDP: what students understood")
                sdp["Understanding"] = pd.to_numeric(sdp["Understanding"], errors="coerce")
                summary = (
                    sdp.groupby("Topic")["Understanding"]
                    .agg(["count", "mean", "min"]).round(1).reset_index()
                    .rename(columns={"count": "Reports", "mean": "Avg rating (1-5)", "min": "Lowest"})
                )
                summary["Suggestion"] = summary["Avg rating (1-5)"].apply(
                    lambda m: "Revisit in next session" if m < 3
                    else ("Check a few students" if m < 4 else "Understood")
                )
                st.dataframe(summary, hide_index=True)
                st.bar_chart(summary.set_index("Topic")["Avg rating (1-5)"])
                st.caption("Self-ratings are subjective. Read them together with each student's answer to the faculty question.")
                low = sdp[sdp["Understanding"] <= 2]
                if not low.empty:
                    st.write("Students who rated 2 or below:")
                    st.dataframe(low[["Date", "Student", "Topic", "Understanding", "Details"]], hide_index=True)

            st.download_button(
                label="Download all reports (.csv)",
                data=df_r.to_csv(index=False),
                file_name="Daily_Reports.csv",
                mime="text/csv",
            )
        

elif page == "7. Chemicals & Inventory":
    pl.inventory_page(user)

elif page == "8. Dissertation Library":
    pl.library_page(user)

elif page == "9. Admin":
    pl.admin_page(user)

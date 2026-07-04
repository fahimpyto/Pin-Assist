import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import re
from pathlib import Path

st.set_page_config(page_title="Pinterest SEO Assistant", layout="wide")
st.title("Pinterest SEO Visualisation Assistant")
st.markdown("---")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
PIN_PLAN_FILE = Path("pin_plan.csv")
KEYWORD_FILE = Path("keyword_topics.json")

def parse_analytics_csv(file):
    content = file.read().decode("utf-8").splitlines()
    lines = [line.strip() for line in content]

    impressions_data = []
    top_boards_data = []
    top_pins_data = []

    section = None

    for line in lines:
        if line.startswith("Date,"):
            section = "impressions"
            continue
        if "Top Boards" in line and "Pinterest" not in line:
            section = "top_boards"
            continue
        if "Top Pins" in line and "Pinterest" not in line:
            section = "top_pins"
            continue
        if "Top boards table" in line or "Top pins table" in line:
            section = None
            continue

        if section == "impressions" and line:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                date_val, imp_val = parts[0], parts[1]
                try:
                    impressions_data.append({"Date": date_val, "Impressions": int(imp_val)})
                except ValueError:
                    pass

        elif section == "top_boards" and line:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6 and parts[0].startswith("http"):
                board_link = parts[0]
                impressions = int(parts[1]) if parts[1].isdigit() else 0
                engagement = int(parts[2]) if parts[2].isdigit() else 0
                pin_clicks = int(parts[3]) if parts[3].isdigit() else 0
                outbound_clicks = int(parts[4]) if parts[4].isdigit() else 0
                saves = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 0
                board_name = board_link.rstrip("/").split("/")[-1].replace("-", " ").title()
                top_boards_data.append({
                    "Board": board_name,
                    "Impressions": impressions,
                    "Engagement": engagement,
                    "Pin Clicks": pin_clicks,
                    "Outbound Clicks": outbound_clicks,
                    "Saves": saves
                })

        elif section == "top_pins" and line:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 5 and parts[0].startswith("http"):
                pin_link = parts[0]
                content_type = parts[1] if len(parts) > 1 else ""
                source = parts[2] if len(parts) > 2 else ""
                canonical = parts[3] if len(parts) > 3 else ""
                impressions = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
                top_pins_data.append({
                    "Pin URL": pin_link,
                    "Content Type": content_type,
                    "Source": source,
                    "Canonical": canonical,
                    "Impressions": impressions
                })

    return impressions_data, top_boards_data, top_pins_data

def load_pin_plan():
    if PIN_PLAN_FILE.exists():
        df = pd.read_csv(PIN_PLAN_FILE)
        if "Status" not in df.columns:
            df["Status"] = "Pending"
        return df
    return pd.DataFrame(columns=["Pin", "Topic", "Image Type", "Status"])

def save_pin_plan(df):
    df.to_csv(PIN_PLAN_FILE, index=False)

def load_keywords():
    if KEYWORD_FILE.exists():
        with open(KEYWORD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"niche": "", "topics": []}

def save_keywords(data):
    with open(KEYWORD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

tab1, tab2, tab3, tab4 = st.tabs([
    "Analytics Dashboard",
    "Pin Planner",
    "Keyword Research",
    "Pin Ideas Generator"
])

with tab1:
    st.header("Pinterest Analytics")

    col_left, col_right = st.columns([1, 2])

    with col_left:
        uploaded_file = st.file_uploader("Upload Pinterest CSV", type=["csv"])
        local_files = list(DATA_DIR.glob("*.csv"))
        selected_file = None
        if local_files:
            file_names = [f.name for f in local_files]
            selected_name = st.selectbox("Or select an existing CSV", ["-- None --"] + file_names)
            if selected_name != "-- None --":
                selected_file = DATA_DIR / selected_name

    csv_source = None
    if uploaded_file is not None:
        csv_source = uploaded_file
    elif selected_file is not None:
        csv_source = open(selected_file, "rb")

    if csv_source is not None:
        impressions_data, top_boards_data, top_pins_data = parse_analytics_csv(csv_source)
        if csv_source is not selected_file:
            csv_source.seek(0)

        if impressions_data:
            df_imp = pd.DataFrame(impressions_data)
            df_imp["Date"] = pd.to_datetime(df_imp["Date"])

            total_impressions = df_imp["Impressions"].sum()
            avg_daily = df_imp["Impressions"].mean()
            best_day = df_imp.loc[df_imp["Impressions"].idxmax()]
            best_day_str = f"{best_day['Date'].strftime('%b %d')} ({best_day['Impressions']})"

            st.subheader("Summary")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Impressions", f"{total_impressions:,}")
            m2.metric("Avg Daily", f"{avg_daily:,.0f}")
            m3.metric("Date Range", f"{df_imp['Date'].min().strftime('%b %d')} - {df_imp['Date'].max().strftime('%b %d')}")
            m4.metric("Best Day", best_day_str)

            fig = px.line(df_imp, x="Date", y="Impressions",
                          title="Impressions Over Time",
                          markers=True)
            fig.update_layout(height=400)
            st.plotly_chart(fig, width="stretch")

        if top_boards_data:
            st.subheader("Top Boards")
            df_boards = pd.DataFrame(top_boards_data)
            fig = px.bar(df_boards, x="Board", y=["Impressions", "Pin Clicks", "Saves"],
                         title="Board Performance",
                         barmode="group")
            fig.update_layout(height=400)
            st.plotly_chart(fig, width="stretch")

            with st.expander("View Board Data Table"):
                st.dataframe(df_boards, width="stretch", hide_index=True)

        if top_pins_data:
            st.subheader("Top Pins")
            df_pins = pd.DataFrame(top_pins_data)
            df_pins["Pin ID"] = df_pins["Pin URL"].str.extract(r"(\d+)$")
            df_pins_display = df_pins[["Pin ID", "Content Type", "Source", "Impressions"]]

            num_pins = st.slider("Number of top pins to show", 5, min(50, len(df_pins_display)), 10)
            st.dataframe(df_pins_display.head(num_pins), width="stretch", hide_index=True)

            fig = px.bar(df_pins.head(num_pins), x="Pin ID", y="Impressions",
                         title=f"Top {num_pins} Pins by Impressions",
                         color="Content Type")
            fig.update_layout(height=400)
            st.plotly_chart(fig, width="stretch")
    else:
        st.info("Upload a Pinterest analytics CSV or select one from the data/ folder to view insights.")

with tab2:
    st.header("Pin Planner")
    st.markdown("Track your upcoming 20 pins and mark them as done.")

    df_plan = load_pin_plan()

    if df_plan.empty:
        st.warning("No pins in the plan. Add entries to pin_plan.csv.")
    else:
        total = len(df_plan)
        done_count = len(df_plan[df_plan["Status"] == "Done"])
        progress = done_count / total if total > 0 else 0

        st.subheader(f"Progress: {done_count} / {total} pins completed")
        st.progress(progress)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total", total)
        col2.metric("Done", done_count)
        col3.metric("Remaining", total - done_count)

        status_filter = st.selectbox("Filter by status", ["All", "Pending", "Done", "Skipped"])
        if status_filter != "All":
            df_plan = df_plan[df_plan["Status"] == status_filter]

        st.subheader("Pin Schedule")
        edited_df = st.data_editor(
            df_plan,
            column_config={
                "Pin": st.column_config.NumberColumn("Pin", width="small"),
                "Topic": st.column_config.TextColumn("Topic", width="large"),
                "Image Type": st.column_config.TextColumn("Image Type", width="medium"),
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Pending", "Done", "Skipped"],
                    width="small"
                )
            },
            hide_index=True,
            width="stretch",
            key="pin_editor"
        )

        if st.button("Save Changes to pin_plan.csv"):
            save_pin_plan(edited_df)
            st.success("Pin plan saved!")

        st.subheader("Quick Actions")
        qa_col1, qa_col2, qa_col3 = st.columns(3)
        if qa_col1.button("Mark Next Pending as Done"):
            df_full = load_pin_plan()
            pending_idx = df_full[df_full["Status"] == "Pending"].index
            if len(pending_idx) > 0:
                df_full.at[pending_idx[0], "Status"] = "Done"
                save_pin_plan(df_full)
                st.rerun()
        if qa_col2.button("Mark All Pending as Done"):
            df_full = load_pin_plan()
            df_full.loc[df_full["Status"] == "Pending", "Status"] = "Done"
            save_pin_plan(df_full)
            st.rerun()
        if qa_col3.button("Reset All to Pending"):
            df_full = load_pin_plan()
            df_full["Status"] = "Pending"
            save_pin_plan(df_full)
            st.rerun()

with tab3:
    st.header("Keyword Research")
    kw_data = load_keywords()

    st.subheader("Niche: " + (kw_data.get("niche", "") or "Not set"))

    new_niche = st.text_input("Set your niche", value=kw_data.get("niche", ""))
    if new_niche != kw_data.get("niche", ""):
        kw_data["niche"] = new_niche
        save_keywords(kw_data)
        st.success("Niche updated!")
        st.rerun()

    st.markdown("---")

    st.subheader("Your Topics & Keywords")
    for i, topic in enumerate(kw_data.get("topics", [])):
        with st.expander(f"{topic.get('name', 'Unnamed')} ({topic.get('priority', 'Medium')})"):
            st.markdown(f"**Keywords:** {', '.join(topic.get('keywords', []))}")
            st.markdown(f"**Notes:** {topic.get('notes', '')}")
            st.markdown(f"**Priority:** {topic.get('priority', 'Medium')}")

            col_e1, col_e2 = st.columns(2)
            if col_e1.button(f"Edit Topic #{i+1}", key=f"edit_{i}"):
                st.session_state[f"editing_topic_{i}"] = True
            if col_e2.button(f"Delete Topic #{i+1}", key=f"del_{i}"):
                kw_data["topics"].pop(i)
                save_keywords(kw_data)
                st.rerun()

            if st.session_state.get(f"editing_topic_{i}", False):
                with st.form(key=f"edit_form_{i}"):
                    new_name = st.text_input("Topic Name", value=topic.get("name", ""))
                    new_keywords = st.text_area("Keywords (comma-separated)", value=", ".join(topic.get("keywords", [])))
                    new_notes = st.text_area("Notes", value=topic.get("notes", ""))
                    new_priority = st.selectbox("Priority", ["High", "Medium", "Low"],
                                               index=["High", "Medium", "Low"].index(topic.get("priority", "Medium")))
                    save_col1, save_col2 = st.columns(2)
                    with save_col1:
                        if st.form_submit_button("Save"):
                            kw_data["topics"][i] = {
                                "name": new_name,
                                "keywords": [k.strip() for k in new_keywords.split(",") if k.strip()],
                                "notes": new_notes,
                                "priority": new_priority
                            }
                            save_keywords(kw_data)
                            st.session_state[f"editing_topic_{i}"] = False
                            st.rerun()
                    with save_col2:
                        if st.form_submit_button("Cancel"):
                            st.session_state[f"editing_topic_{i}"] = False
                            st.rerun()

    st.markdown("---")
    st.subheader("Add New Topic")

    with st.form("new_topic_form"):
        new_name = st.text_input("Topic Name", placeholder="e.g. Homepage Schema Mistakes")
        new_keywords = st.text_input("Keywords (comma-separated)", placeholder="homepage schema mistakes, homepage SEO errors")
        new_notes = st.text_area("Notes", placeholder="Any research notes or ideas for this topic")
        new_priority = st.selectbox("Priority", ["Medium", "High", "Low"])
        submitted = st.form_submit_button("Add Topic")

        if submitted and new_name:
            kw_data["topics"].append({
                "name": new_name,
                "keywords": [k.strip() for k in new_keywords.split(",") if k.strip()],
                "notes": new_notes,
                "priority": new_priority
            })
            save_keywords(kw_data)
            st.success(f"Topic '{new_name}' added!")
            st.rerun()

with tab4:
    st.header("Pin Ideas Generator")
    st.markdown("Generate pin topic + image type ideas based on your niche.")

    IMAGE_TYPES = [
        "Infographic", "Illustration", "Visual Explanation", "Flowchart",
        "Decision Tree", "Checklist", "Comparison Chart", "Card",
        "Comparison", "Carousel style", "Cheat Sheet", "Listicle",
        "How-To Guide", "Template", "Case Study", "Tip Card",
        "Step-by-Step Guide", "Quote Graphic", "Data Visualisation", "Mind Map"
    ]

    df_plan_current = load_pin_plan()
    existing_topics = set(df_plan_current["Topic"].tolist()) if not df_plan_current.empty else set()

    niche_for_ideas = st.text_input("Enter your niche / topic area",
                                    value=load_keywords().get("niche", ""),
                                    placeholder="e.g. Homepage Schema")

    if niche_for_ideas:
        st.subheader("Suggested Pin Ideas")

        image_type_mapping = {
            "Explainer": ["Infographic", "Visual Explanation", "Illustration"],
            "Comparison": ["Comparison Chart", "Comparison", "Decision Tree"],
            "How-To": ["Step-by-Step Guide", "How-To Guide", "Checklist"],
            "List": ["Listicle", "Cheat Sheet", "Card"],
            "Deep": ["Mind Map", "Flowchart", "Data Visualisation"],
            "Visual": ["Infographic", "Carousel style", "Illustration"],
            "Quick": ["Tip Card", "Checklist", "Cheat Sheet"]
        }

        kw_data = load_keywords()
        keyword_pool = []
        for t in kw_data.get("topics", []):
            keyword_pool.extend(t.get("keywords", []))

        if keyword_pool:
            st.markdown("**Keywords from your research topics:**")
            st.write(", ".join(keyword_pool))

        angle_type = st.selectbox("Content angle", list(image_type_mapping.keys()))
        suggested_types = image_type_mapping[angle_type]

        num_ideas = st.slider("Number of ideas", 5, 20, 10)

        prefixes = ["Ultimate", "Complete", "Essential", "Beginner's", "Advanced",
                    "Simple", "Comprehensive", "Actionable", "Visual", "Quick"]
        actions = ["Guide to", "Checklist for", "Explanation of", "Comparison of",
                   "Introduction to", "Overview of", "Walkthrough of", "Examples of"]

        used_topics = set()
        generated_ideas = []
        attempt = 0
        while len(generated_ideas) < num_ideas and attempt < 100:
            import random
            prefix = random.choice(prefixes)
            action = random.choice(actions)

            if keyword_pool:
                use_kw = random.choice(keyword_pool)
            else:
                use_kw = niche_for_ideas

            pattern = random.choice([
                f"{prefix} {action} {use_kw}",
                f"{prefix} {use_kw} {random.choice(['Guide', 'Checklist', 'Overview', 'Handbook'])}",
                f"{use_kw}: {prefix} {action.title()}",
                f"{prefix} {random.choice(['Guide', 'Handbook', 'Overview'])} to {use_kw}"
            ])
            img_type = random.choice(suggested_types)

            if pattern not in used_topics and pattern not in existing_topics:
                used_topics.add(pattern)
                generated_ideas.append({"Topic": pattern, "Image Type": img_type})
            attempt += 1

        if generated_ideas:
            df_ideas = pd.DataFrame(generated_ideas)
            df_ideas.insert(0, "#", range(1, len(df_ideas) + 1))
            st.dataframe(df_ideas, width="stretch", hide_index=True)

            csv_ideas = df_ideas.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Ideas as CSV",
                data=csv_ideas,
                file_name="pin_ideas.csv",
                mime="text/csv"
            )

            if st.button("Add These Ideas to Pin Plan"):
                df_current = load_pin_plan()
                next_pin_num = df_current["Pin"].max() + 1 if not df_current.empty else 1
                new_rows = []
                for _, row in df_ideas.iterrows():
                    new_rows.append({
                        "Pin": next_pin_num,
                        "Topic": row["Topic"],
                        "Image Type": row["Image Type"],
                        "Status": "Pending"
                    })
                    next_pin_num += 1
                df_new = pd.concat([df_current, pd.DataFrame(new_rows)], ignore_index=True)
                save_pin_plan(df_new)
                st.success(f"{len(new_rows)} ideas added to pin_plan.csv!")
                st.rerun()
        else:
            st.info("Not enough unique ideas generated. Try a different niche or keyword.")

    st.markdown("---")
    st.subheader("Quick Topic + Image Type Reference")
    st.markdown("""
    | Topic Type | Best Image Types |
    |---|---|
    | **Concept explanation** | Infographic, Visual Explanation, Illustration |
    | **Comparison** | Comparison Chart, Decision Tree, Side-by-Side |
    | **Step-by-step** | Checklist, How-To Guide, Step-by-Step Guide |
    | **List / Roundup** | Listicle, Card, Carousel style |
    | **Deep dive** | Mind Map, Flowchart, Guide |
    | **Quick tips** | Tip Card, Cheat Sheet, Checklist |
    """)

st.markdown("---")
st.caption("Pinterest SEO Visualisation Assistant v1.0")

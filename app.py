import os
import json
import requests
import streamlit as st
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from openai import OpenAI
from fpdf import FPDF
from io import BytesIO

# --- Initialize session state ---
if "has_summary" not in st.session_state:
    st.session_state.has_summary = False
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "initial_query" not in st.session_state:
    st.session_state.initial_query = ""
if "followups" not in st.session_state:
    st.session_state.followups = []

# --- Load previous session if it exists ---
if os.path.exists("data.json") and not st.session_state.has_summary:
    with open("data.json", "r") as f:
        saved = json.load(f)
        st.session_state.initial_query = saved.get("initial_query", "")
        st.session_state.summary = saved.get("summary", "")
        st.session_state.followups = saved.get("followups", [])
        st.session_state.has_summary = True

# --- OpenAI client ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# --- Helpers ---
def get_text_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        return ' '.join([p.get_text() for p in paragraphs])
    except Exception as e:
        return f"Error scraping {url}: {e}"


def summarize_content(text):
    prompt = f"Summarize the following information:\n\n{text[:4000]}"
    response = client.chat.completions.create(model="gpt-3.5-turbo",
                                              messages=[{
                                                  "role": "user",
                                                  "content": prompt
                                              }],
                                              temperature=0.5)
    return response.choices[0].message.content


def answer_follow_up(summary, followup_question):
    prompt = f"Using the following summary as context:\n\n{summary}\n\nAnswer this follow-up question: {followup_question}"
    response = client.chat.completions.create(model="gpt-3.5-turbo",
                                              messages=[{
                                                  "role": "user",
                                                  "content": prompt
                                              }],
                                              temperature=0.5)
    return response.choices[0].message.content


def save_session_data(initial_query, summary, followups):
    data = {
        "initial_query": initial_query,
        "summary": summary,
        "followups": followups
    }
    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)


def generate_markdown_report(query, summary, followups):
    report = f"# AI Research Report\n\n"
    report += f"**Topic:** {query}\n\n"
    report += f"## Summary\n\n{summary}\n\n"
    if followups:
        report += "## Follow-Up Questions\n"
        for item in followups:
            report += f"**Q:** {item['question']}\n\n"
            report += f"**A:** {item['answer']}\n\n"
    return report


def generate_pdf_report(query, summary, followups):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "AI Research Report", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.multi_cell(0, 10, f"Topic: {query}")
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Summary", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 10, summary)
    pdf.ln(5)
    if followups:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Follow-Up Q&A", ln=True)
        pdf.set_font("Arial", '', 12)
        for item in followups:
            pdf.multi_cell(0, 10, f"Q: {item['question']}")
            pdf.multi_cell(0, 10, f"A: {item['answer']}")
            pdf.ln(3)
    pdf_output = pdf.output(dest='S').encode('latin1')
    buffer = BytesIO(pdf_output)
    return buffer


# --- UI ---
st.title("AI Research Agent")
query = st.text_input("What would you like to research?")

if st.button("Search and Summarize") and query:
    st.info("Searching and summarizing...")
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=3)
        urls = [r["href"] for r in results]

    all_text = ""
    for url in urls:
        st.write(f"Scraping: {url}")
        page_text = get_text_from_url(url)
        all_text += page_text + "\n\n"

    if all_text:
        summary = summarize_content(all_text)
        st.session_state.summary = summary
        st.session_state.initial_query = query
        st.session_state.followups = []
        st.session_state.has_summary = True
        save_session_data(query, summary, [])
        st.subheader("Summary")
        st.write(summary)
    else:
        st.error("No content found to summarize.")

# --- Follow-up Q&A ---
if st.session_state.has_summary:
    st.markdown("---")
    st.subheader("Ask a Follow-up Question")
    followup = st.text_input("Ask a question about the summary:")

    if st.button("Get Answer") and followup:
        with st.spinner("Thinking..."):
            followup_answer = answer_follow_up(st.session_state.summary,
                                               followup)
            st.markdown("Answer:")
            st.write(followup_answer)

            st.session_state.followups.append({
                "question": followup,
                "answer": followup_answer
            })

            save_session_data(st.session_state.initial_query,
                              st.session_state.summary,
                              st.session_state.followups)

# --- Download buttons ---
if st.session_state.has_summary:
    st.markdown("---")
    st.subheader("Download Your Research Report")

    json_data = json.dumps(
        {
            "initial_query": st.session_state.initial_query,
            "summary": st.session_state.summary,
            "followups": st.session_state.followups
        },
        indent=2)

    st.download_button("Download Report (JSON)",
                       json_data,
                       file_name="research_report.json")

    markdown_content = generate_markdown_report(st.session_state.initial_query,
                                                st.session_state.summary,
                                                st.session_state.followups)
    st.download_button("Download Markdown Report",
                       markdown_content,
                       file_name="research_report.md",
                       mime="text/markdown")

    pdf_file = generate_pdf_report(st.session_state.initial_query,
                                   st.session_state.summary,
                                   st.session_state.followups)
    st.download_button(label="Download PDF Report",
                       data=pdf_file,
                       file_name="research_report.pdf",
                       mime="application/pdf")

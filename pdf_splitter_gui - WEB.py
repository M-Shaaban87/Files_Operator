import os
import fitz  # PyMuPDF
import streamlit as st
import tempfile
from pathlib import Path
import shutil
import re

st.set_page_config(page_title="PDF Splitter", layout="centered")
st.title("📄 PDF Splitter - Student Reports")

# ----------------------------- Utility Functions ----------------------------- #
def extract_student_id(text):
    match = re.search(r'Student ID\s*:?\s*(\d+)', text)
    return match.group(1) if match else None

def extract_student_id_brackets(text):
    match = re.search(r'\[(\d+)\]', text)
    return match.group(1) if match else None

def save_pdf(new_doc, student_id, filename, base_output_dir):
    folder = base_output_dir / student_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    new_doc.save(path)
    return path

# ----------------------------- Splitting Functions ----------------------------- #
def split_registered_courses(doc, base_output_dir):
    paths = []
    for i, page in enumerate(doc):
        text = page.get_text()
        student_id = extract_student_id(text) or f"Unknown_{i+1}"
        new_pdf = fitz.open()
        new_pdf.insert_pdf(doc, from_page=i, to_page=i)
        path = save_pdf(new_pdf, student_id, f"01-RegisteredCourses {student_id}.pdf", base_output_dir)
        paths.append((student_id, path))
    return paths

def split_grouped_pdf(doc, extract_id_func, prefix, base_output_dir):
    paths = []
    student_ranges = []
    current_range = []
    for i, page in enumerate(doc):
        text = page.get_text()
        student_id = extract_id_func(text)
        if student_id:
            if current_range:
                student_ranges.append(current_range)
            current_range = [i]
        elif current_range:
            current_range.append(i)
    if current_range:
        student_ranges.append(current_range)
    for page_range in student_ranges:
        first_text = doc[page_range[0]].get_text()
        student_id = extract_id_func(first_text) or f"Unknown_{page_range[0]+1}"
        new_pdf = fitz.open()
        for page_num in page_range:
            new_pdf.insert_pdf(doc, from_page=page_num, to_page=page_num)
        path = save_pdf(new_pdf, student_id, f"{prefix} {student_id}.pdf", base_output_dir)
        paths.append((student_id, path))
    return paths

# ----------------------------- Streamlit Interface ----------------------------- #

st.markdown("Upload any of the supported PDF files:")

col1, col2 = st.columns(2)
with col1:
    reg_pdf = st.file_uploader("RegisteredCourses (1 page per student)", type="pdf", key="reg")
    cgpa_pdf = st.file_uploader("CGPAProgress (starts with ID)", type="pdf", key="cgpa")
with col2:
    history_pdf = st.file_uploader("History (starts with ID)", type="pdf", key="hist")
    schedual_pdf = st.file_uploader("Schedual (ID inside brackets)", type="pdf", key="sched")

base_output_dir_str = st.text_input("Enter a local output directory to save all split files:")

if st.button("Split PDFs"):
    if not base_output_dir_str:
        st.error("Please provide an output directory to save the split files.")
    else:
        base_output_dir = Path(base_output_dir_str)
        with st.spinner("Processing PDFs..."):
            all_outputs = []
            if reg_pdf:
                doc = fitz.open(stream=reg_pdf.read(), filetype="pdf")
                all_outputs += split_registered_courses(doc, base_output_dir)
            if cgpa_pdf:
                doc = fitz.open(stream=cgpa_pdf.read(), filetype="pdf")
                all_outputs += split_grouped_pdf(doc, extract_student_id, "02-CGPAProgress", base_output_dir)
            if history_pdf:
                doc = fitz.open(stream=history_pdf.read(), filetype="pdf")
                all_outputs += split_grouped_pdf(doc, extract_student_id, "01-history", base_output_dir)
            if schedual_pdf:
                doc = fitz.open(stream=schedual_pdf.read(), filetype="pdf")
                all_outputs += split_grouped_pdf(doc, extract_student_id_brackets, "02-Schedual", base_output_dir)

        st.success(f"✅ Split complete! {len(all_outputs)} files saved to: {base_output_dir_str}")

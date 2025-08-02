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

def save_pdf(new_doc, student_id, filename):
    folder = Path(tempfile.gettempdir()) / student_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    new_doc.save(path)
    return path

def move_to_output_dir(source_path, base_output_dir, student_id):
    student_folder = base_output_dir / student_id
    student_folder.mkdir(parents=True, exist_ok=True)
    target_path = student_folder / source_path.name
    shutil.copy(source_path, target_path)
    return target_path

# ----------------------------- Splitting Functions ----------------------------- #
def split_registered_courses(doc):
    paths = []
    for i, page in enumerate(doc):
        text = page.get_text()
        student_id = extract_student_id(text) or f"Unknown_{i+1}"
        new_pdf = fitz.open()
        new_pdf.insert_pdf(doc, from_page=i, to_page=i)
        path = save_pdf(new_pdf, student_id, f"01-RegisteredCourses {student_id}.pdf")
        paths.append((student_id, path))
    return paths

def split_grouped_pdf(doc, extract_id_func, prefix):
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
        path = save_pdf(new_pdf, student_id, f"{prefix} {student_id}.pdf")
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

base_output_dir = st.text_input("Enter a local output directory (only applies when running locally):")

if st.button("Split PDFs"):
    with st.spinner("Processing PDFs..."):
        all_outputs = []
        if reg_pdf:
            doc = fitz.open(stream=reg_pdf.read(), filetype="pdf")
            all_outputs += split_registered_courses(doc)
        if cgpa_pdf:
            doc = fitz.open(stream=cgpa_pdf.read(), filetype="pdf")
            all_outputs += split_grouped_pdf(doc, extract_student_id, "02-CGPAProgress")
        if history_pdf:
            doc = fitz.open(stream=history_pdf.read(), filetype="pdf")
            all_outputs += split_grouped_pdf(doc, extract_student_id, "01-history")
        if schedual_pdf:
            doc = fitz.open(stream=schedual_pdf.read(), filetype="pdf")
            all_outputs += split_grouped_pdf(doc, extract_student_id_brackets, "02-Schedual")

        final_outputs = []
        for student_id, path in all_outputs:
            if base_output_dir:
                try:
                    target = move_to_output_dir(path, Path(base_output_dir), student_id)
                    final_outputs.append((student_id, target))
                except Exception as e:
                    st.error(f"Failed to move {path.name}: {e}")
            else:
                final_outputs.append((student_id, path))

    if final_outputs:
        st.success(f"✅ Split complete! {len(final_outputs)} files generated.")
        st.markdown("### Download Files:")
        for student_id, path in final_outputs:
            with open(path, "rb") as f:
                st.download_button(
                    label=f"Download {path.name}",
                    data=f.read(),
                    file_name=path.name,
                    mime="application/pdf"
                )
    else:
        st.warning("No files were processed. Please upload valid PDFs.")

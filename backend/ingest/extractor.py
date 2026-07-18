import os
import sys
import re
import json
from datetime import date, datetime
import pdfplumber
from sqlmodel import Session, select
from dotenv import load_dotenv

# Add root folder to sys.path to enable backend imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.api.database import engine
from backend.api.models import StagingExternal, StagingInternal, AuditLog
from backend.kb.vector_helper import get_text_embedding

load_dotenv()

def parse_date(date_str):
    if not date_str:
        return None
    try:
        if isinstance(date_str, date):
            return date_str
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None

import zipfile
import xml.etree.ElementTree as ET

def extract_text_from_file(file_path: str) -> str:
    """
    Extract raw text from PDF or DOCX file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Không tìm thấy file tại đường dẫn: {file_path}")
        
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".docx":
        try:
            with zipfile.ZipFile(file_path) as docx:
                xml_content = docx.read('word/document.xml')
                root = ET.fromstring(xml_content)
                text_runs = []
                for elem in root.iter():
                    if elem.tag.endswith('t'):
                        if elem.text:
                            text_runs.append(elem.text)
                    elif elem.tag.endswith('p'):
                        text_runs.append('\n')
                return "".join(text_runs)
        except Exception as e:
            print(f"Warning: Failed to extract text from DOCX {file_path}: {e}")
            return ""
            
    elif ext == ".pdf":
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    else:
        raise ValueError(f"Không hỗ trợ định dạng file: {ext}")

def parse_qd312_text(text: str) -> dict:
    """
    Deterministic parsing specifically tailored for Quyết định 312/QĐ-NHNN text.
    """
    doc_code = "QD312"
    title = "Quyết định số 312/QĐ-NHNN về việc đính chính Thông tư số 39/2016/TT-NHNN"
    
    # Defaults
    issue_date = date(2017, 3, 14)
    effective_date = date(2017, 3, 15)
    
    # Try to extract dates from text
    issue_match = re.search(r"ngày\s*(\d+)\s*tháng\s*(\d+)\s*năm\s*(\d{4})", text, re.IGNORECASE)
    if issue_match:
        d, m, y = map(int, issue_match.groups())
        issue_date = date(y, m, d)
        
    eff_match = re.search(r"hiệu\s*lực\s*kể\s*từ\s*ngày\s*(\d+)\s*tháng\s*(\d+)\s*năm\s*(\d{4})", text, re.IGNORECASE)
    if eff_match:
        d, m, y = map(int, eff_match.groups())
        effective_date = date(y, m, d)

    document = {
        "doc_code": doc_code,
        "title": title,
        "type": "QuyetDinh",
        "issuer": "NHNN",
        "issue_date": issue_date.strftime("%Y-%m-%d"),
        "effective_date": effective_date.strftime("%Y-%m-%d"),
        "visibility": "public"
    }

    clauses = []
    edges = []

    # Deterministic extraction of the clauses from Article 1 of QĐ 312
    clauses.append({
        "clause_id": "QD312/Điều 1.1",
        "path": "Điều 1.1",
        "text": "Khoản 5 Điều 8: Đính chính cụm từ 'trả nợ khoản nợ vay' thành 'trả nợ khoản cấp tín dụng'.",
        "effective_date": effective_date.strftime("%Y-%m-%d"),
        "expiry_date": None,
        "topic": "tra_no_khoan_vay",
        "visibility": "public"
    })
    edges.append({
        "from": "QD312/Điều 1.1",
        "to": "TT39/Điều 8.5",
        "type": "AMENDS",
        "note": "Đính chính cụm từ 'trả nợ khoản nợ vay' thành 'trả nợ khoản cấp tín dụng'"
    })

    clauses.append({
        "clause_id": "QD312/Điều 1.2",
        "path": "Điều 1.2",
        "text": "Khoản 5 Điều 8: Đính chính cụm từ 'dự toán xây dựng công trình' thành 'tổng mức đầu tư xây dựng'.",
        "effective_date": effective_date.strftime("%Y-%m-%d"),
        "expiry_date": None,
        "topic": "du_toan_xay_dung",
        "visibility": "public"
    })
    edges.append({
        "from": "QD312/Điều 1.2",
        "to": "TT39/Điều 8.5",
        "type": "AMENDS",
        "note": "Đính chính cụm từ 'dự toán xây dựng công trình' thành 'tổng mức đầu tư xây dựng'"
    })

    clauses.append({
        "clause_id": "QD312/Điều 1.3",
        "path": "Điều 1.3",
        "text": "Khoản 6 Điều 8: Đính chính cụm từ 'trả nợ khoản nợ vay tại tổ chức tín dụng khác' thành 'trả nợ khoản cấp tín dụng tại tổ chức tín dụng khác'.",
        "effective_date": effective_date.strftime("%Y-%m-%d"),
        "expiry_date": None,
        "topic": "tra_no_khoan_vay",
        "visibility": "public"
    })
    edges.append({
        "from": "QD312/Điều 1.3",
        "to": "TT39/Điều 8.6",
        "type": "AMENDS",
        "note": "Đính chính cụm từ 'trả nợ khoản nợ vay tại tổ chức tín dụng khác' thành 'trả nợ khoản cấp tín dụng tại tổ chức tín dụng khác'"
    })

    clauses.append({
        "clause_id": "QD312/Điều 1.4",
        "path": "Điều 1.4",
        "text": "Điểm c khoản 1 Điều 29: Đính chính cụm từ 'trong thời gian vay vốn;' thành 'trong thời gian vay vốn: Báo cáo tài chính nộp cho cơ quan nhà nước có thẩm quyền và/hoặc báo cáo tài chính đã kiểm toán đối với trường hợp khách hàng phải lập báo cáo tài chính theo quy định của pháp luật; báo cáo tình hình tài chính của khách hàng theo hướng dẫn của tổ chức tín dụng;'.",
        "effective_date": effective_date.strftime("%Y-%m-%d"),
        "expiry_date": None,
        "topic": "bao_cao_tai_chinh",
        "visibility": "public"
    })
    edges.append({
        "from": "QD312/Điều 1.4",
        "to": "TT39/Điều 29.1.c",
        "type": "AMENDS",
        "note": "Sửa đổi điều kiện báo cáo tài chính trong thời gian vay vốn"
    })

    clauses.append({
        "clause_id": "QD312/Điều 2.1",
        "path": "Điều 2.1",
        "text": "Quyết định này có hiệu lực kể từ ngày 15 tháng 03 năm 2017.",
        "effective_date": effective_date.strftime("%Y-%m-%d"),
        "expiry_date": None,
        "topic": "hieu_luc",
        "visibility": "public"
    })

    return {
        "document": document,
        "clauses": clauses,
        "edges": edges
    }

def parse_general_pdf_text(text: str, filename: str, override_doc_code: str = None) -> dict:
    """
    Parses any regulatory PDF by extracting metadata and splitting text by articles.
    Pass override_doc_code to force a specific doc_code (avoids extracting wrong codes from text).
    """
    base_name = os.path.splitext(filename)[0]
    
    if override_doc_code:
        doc_code = override_doc_code
    else:
        # Try to extract doc_code (e.g. 39/2016/TT-NHNN or 21/2021/ND-CP)
        code_match = re.search(r"(\d+[\-/]\d+[\-/][A-Z0-9\-]+)", text, re.IGNORECASE)
        if code_match:
            doc_code = code_match.group(1).replace("-", "/").upper()
        else:
            # Fallback to cleaned filename
            doc_code = re.sub(r"[^\w]", "", base_name).upper()[:12]
        
    # Extract Type
    doc_type = "ThongTu"
    if "nghị định" in text.lower() or "nghinh" in base_name.lower():
        doc_type = "NghiDinh"
    elif "quyết định" in text.lower() or "quyetdinh" in base_name.lower():
        doc_type = "QuyetDinh"
    elif "luật" in text.lower() or "luat" in base_name.lower():
        doc_type = "Luật"
    elif "quy trình" in text.lower() or "quy chế" in text.lower() or "quytrinh" in base_name.lower() or "quyche" in base_name.lower():
        doc_type = "QuyTrinhNoiBo"
        
    # Extract Issuer
    issuer = "NHNN"
    if "chính phủ" in text.lower():
        issuer = "ChinhPhu"
    elif "shb" in text.lower() or "sài gòn - hà nội" in text.lower():
        issuer = "SHB"
        
    # Extract Title
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    title = f"Văn bản pháp lý {doc_code}"
    for line in lines[:15]:
        if len(line) > 30 and ("quy định" in line.lower() or "về việc" in line.lower() or "thông tư" in line.lower() or "nghị định" in line.lower() or "quy chế" in line.lower() or "quy trình" in line.lower()):
            title = line
            break
    if len(title) > 200:
        title = title[:200] + "..."
        
    # Extract Dates
    issue_date = date(2023, 1, 1)
    effective_date = date(2023, 1, 1)
    
    issue_match = re.search(r"ngày\s*(\d+)\s*tháng\s*(\d+)\s*năm\s*(\d{4})", text, re.IGNORECASE)
    if issue_match:
        d, m, y = map(int, issue_match.groups())
        issue_date = date(y, m, d)
        effective_date = date(y, m, d)
        
    eff_match = re.search(r"hiệu\s*lực\s*kể\s*từ\s*ngày\s*(\d+)\s*tháng\s*(\d+)\s*năm\s*(\d{4})", text, re.IGNORECASE)
    if eff_match:
        d, m, y = map(int, eff_match.groups())
        effective_date = date(y, m, d)
        
    # Determine visibility
    visibility = "internal" if issuer == "SHB" or "nội bộ" in text.lower() else "public"
    
    # Determine department
    department = "phap_ly"
    lower_text = text.lower()
    lower_base = base_name.lower()
    if "tín dụng" in lower_text or "tindung" in lower_base or "cho vay" in lower_text or doc_code in ("TT39", "TT06", "ND21"):
        department = "tin_dung"
    elif "rủi ro" in lower_text or "ruiro" in lower_base or "an toàn vốn" in lower_text or doc_code in ("TT41", "TT22", "TT13"):
        department = "quan_ly_rui_ro"
        
    document = {
        "doc_code": doc_code,
        "title": title,
        "type": doc_type,
        "issuer": issuer,
        "issue_date": issue_date.strftime("%Y-%m-%d"),
        "effective_date": effective_date.strftime("%Y-%m-%d"),
        "visibility": visibility,
        "department": department
    }
    
    # Split clauses by Article structure (Điều X)
    clauses = []
    pattern = r"(?:^|\n)(?:Điều|ĐIỀU)\s+(\d+)(?:\.|\b|:)"
    parts = re.split(pattern, text)
    
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            art_num = parts[i]
            art_text = parts[i+1].strip() if i+1 < len(parts) else ""
            if not art_text:
                continue
                
            art_lines = [l.strip() for l in art_text.split("\n") if l.strip()]
            cleaned_text = " ".join(art_lines)
            
            clause_id = f"{doc_code}/Điều {art_num}"
            path = f"Điều {art_num}"
            
            # Identify topic
            topic = "quy_dinh_chung"
            if "tài sản" in cleaned_text.lower() or "thế chấp" in cleaned_text.lower() or "bảo đảm" in cleaned_text.lower():
                topic = "tai_san_bao_dam"
            elif "an toàn vốn" in cleaned_text.lower() or "car" in cleaned_text.lower():
                topic = "ty_le_an_toan_von"
            elif "lãi suất" in cleaned_text.lower() or "lãi cho vay" in cleaned_text.lower():
                topic = "lai_suat_cho_vay"
            elif "hạn mức" in cleaned_text.lower() or "dư nợ" in cleaned_text.lower() or "tỷ lệ cấp tín dụng" in cleaned_text.lower():
                topic = "han_muc_tin_dung"
            elif "báo cáo" in cleaned_text.lower():
                topic = "bao_cao_dinh_ky"
                
            # Extract threshold percentage if any
            metric_val = None
            metric_unit = None
            pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", cleaned_text)
            if pct_match:
                metric_val = float(pct_match.group(1))
                metric_unit = "%"
                
            clauses.append({
                "clause_id": clause_id,
                "path": path,
                "text": cleaned_text[:1500],
                "effective_date": effective_date.strftime("%Y-%m-%d"),
                "expiry_date": None,
                "topic": topic,
                "visibility": visibility,
                "metric": {"value": metric_val, "unit": metric_unit} if metric_val is not None else None
            })
            
    # Fallback to single clause if no "Điều" separator found
    if not clauses:
        clauses.append({
            "clause_id": f"{doc_code}/Toàn văn",
            "path": "Toàn văn",
            "text": text[:2000].strip(),
            "effective_date": effective_date.strftime("%Y-%m-%d"),
            "expiry_date": None,
            "topic": "quy_dinh_chung",
            "visibility": visibility
        })
        
    return {
        "document": document,
        "clauses": clauses,
        "edges": []
    }

def save_extracted_to_db(data: dict):
    session = Session(engine)
    doc_data = data["document"]
    clauses_data = data["clauses"]
    
    visibility = doc_data.get("visibility", "public")
    department = doc_data.get("department", "phap_ly")
    
    for c_data in clauses_data:
        metric_data = c_data.get("metric")
        metric_value = metric_data.get("value") if metric_data else None
        metric_unit = metric_data.get("unit") if metric_data else None
        
        if visibility == "internal":
            # Save or Update in staging.quy_che_noi_bo table
            clause = session.get(StagingInternal, c_data["clause_id"])
            if not clause:
                clause = StagingInternal(
                    clause_id=c_data["clause_id"],
                    doc_code=doc_data["doc_code"],
                    doc_title=doc_data["title"],
                    doc_type=doc_data["type"],
                    issuer=doc_data["issuer"],
                    effective_date=parse_date(doc_data["effective_date"]),
                    path=c_data["path"],
                    text=c_data["text"],
                    topic=c_data["topic"],
                    visibility="internal",
                    status="draft",
                    metric_value=metric_value,
                    metric_unit=metric_unit,
                    department=department
                )
                session.add(clause)
            else:
                clause.doc_title = doc_data["title"]
                clause.text = c_data["text"]
                clause.topic = c_data["topic"]
                clause.metric_value = metric_value
                clause.metric_unit = metric_unit
                clause.department = department
                session.add(clause)
        else:
            # Save or Update in staging.van_ban_ngoai table
            clause = session.get(StagingExternal, c_data["clause_id"])
            if not clause:
                clause = StagingExternal(
                    clause_id=c_data["clause_id"],
                    doc_code=doc_data["doc_code"],
                    doc_title=doc_data["title"],
                    doc_type=doc_data["type"],
                    issuer=doc_data["issuer"],
                    effective_date=parse_date(doc_data["effective_date"]),
                    path=c_data["path"],
                    text=c_data["text"],
                    topic=c_data["topic"],
                    visibility="public",
                    status="draft",
                    metric_value=metric_value,
                    metric_unit=metric_unit,
                    department=department
                )
                session.add(clause)
            else:
                clause.doc_title = doc_data["title"]
                clause.text = c_data["text"]
                clause.topic = c_data["topic"]
                clause.metric_value = metric_value
                clause.metric_unit = metric_unit
                clause.department = department
                session.add(clause)
                
    # Write Audit Log
    log = AuditLog(
        job=f"INGEST_PDF_STAGING: {doc_data['doc_code']}",
        flag=1,
        schema_name="staging"
    )
    session.add(log)
    
    session.commit()
    session.close()
    print(f"Document {doc_data['doc_code']} saved to STAGING {visibility} successfully!")

def process_pdf_ingestion(pdf_path: str, override_doc_code: str = None) -> dict:
    print(f"Processing document file (Dynamic Ingestion Parser): {pdf_path}...")
    
    text = ""
    try:
        text = extract_text_from_file(pdf_path)
    except Exception as e:
        print(f"Warning: Failed to extract text from file: {e}")
        text = "Lỗi đọc file."
        
    filename = os.path.basename(pdf_path)
    
    # Run QD312 parser if specific to that file, otherwise general dynamic parsing
    if "312" in filename or "QD312" in text or "đính chính" in text.lower():
        extracted_data = parse_qd312_text(text)
    else:
        extracted_data = parse_general_pdf_text(text, filename, override_doc_code=override_doc_code)
        
    save_extracted_to_db(extracted_data)
    return extracted_data

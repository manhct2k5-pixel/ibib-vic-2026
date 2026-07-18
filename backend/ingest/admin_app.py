import os
import sys
import streamlit as st
import httpx
import pandas as pd
from sqlmodel import Session, select

# Add root folder to sys.path to enable backend imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.api.database import engine
from backend.api.models import Document, Clause, Edge, StagingExternal, StagingInternal

st.set_page_config(
    page_title="Compliance Copilot — Admin Console",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Compliance Copilot — Bảng quản trị & Nạp văn bản")
st.markdown("Hệ thống quản trị dữ liệu quy định và phân tích tác động pháp lý (Radar Tác động) của Ngân hàng SHB.")

API_BASE_URL = "http://localhost:8000"

tab1, tab2, tab3 = st.tabs(["📥 Nạp văn bản mới", "📋 Duyệt văn bản nháp (Staging)", "📡 Radar Tác động (Impact Analysis)"])

with tab1:
    st.header("Tải lên tài liệu pháp lý mới")
    st.markdown("Tải lên tệp PDF. Hệ thống sẽ tự động bóc tách và lưu vào phân vùng **Staging** chờ quản trị viên phê duyệt.")
    
    uploaded_file = st.file_uploader("Chọn file PDF", type=["pdf"])
    
    if uploaded_file is not None:
        if st.button("Bắt đầu xử lý & Đưa vào Staging", type="primary"):
            with st.spinner("Hệ thống đang đọc tệp và phân tách các Điều/Khoản vào Staging..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    response = httpx.post(f"{API_BASE_URL}/api/admin/ingest-pdf", files=files, timeout=30.0)
                    
                    if response.status_code == 200:
                        res_data = response.json()
                        st.success(f"🎉 {res_data['message']}")
                        
                        doc = res_data["document"]
                        st.subheader("Thông tin văn bản đã lưu nháp:")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Mã văn bản", doc["doc_code"])
                        col2.metric("Loại văn bản", doc["type"])
                        col3.metric("Ngày hiệu lực", doc["effective_date"])
                        
                        st.text_area("Tiêu đề", doc["title"], height=70, disabled=True, key="ingest_title")
                        st.info(f"Đã trích xuất thành công {res_data['clause_count']} điều khoản.")
                    else:
                        st.error(f"Lỗi xử lý từ server backend (Mã {response.status_code}): {response.text}")
                except Exception as e:
                    st.error(f"Không thể kết nối đến server backend: {e}")

with tab2:
    st.header("Phê duyệt văn bản nháp (Staging Approval)")
    st.markdown("Xem xét, đối chiếu dữ liệu thô được bóc tách trong khu vực Staging trước khi phê duyệt đưa lên Kho DWH chính thức.")
    
    # Query staging documents via backend API
    try:
        response = httpx.get(f"{API_BASE_URL}/api/admin/staging-documents", timeout=10.0)
        if response.status_code == 200:
            staging_docs = response.json()
        else:
            st.error(f"Lỗi lấy danh sách staging từ server: {response.text}")
            staging_docs = []
    except Exception as e:
        st.error(f"Không thể kết nối API backend: {e}")
        staging_docs = []
        
    if staging_docs:
        staging_options = {f"{d['doc_code']} - {d['title'][:60]}...": d['doc_code'] for d in staging_docs}
        selected_staging_label = st.selectbox("Chọn văn bản nháp chờ duyệt", list(staging_options.keys()))
        selected_staging_code = staging_options[selected_staging_label]
        
        # Load details directly from DB StagingExternal or StagingInternal
        session = Session(engine)
        staging_doc_details = session.exec(select(StagingExternal).where(StagingExternal.doc_code == selected_staging_code)).first()
        if staging_doc_details:
            staging_clauses = session.exec(select(StagingExternal).where(StagingExternal.doc_code == selected_staging_code)).all()
            visibility_label = "Bên ngoài (NHNN / Basel)"
        else:
            staging_doc_details = session.exec(select(StagingInternal).where(StagingInternal.doc_code == selected_staging_code)).first()
            staging_clauses = session.exec(select(StagingInternal).where(StagingInternal.doc_code == selected_staging_code)).all()
            visibility_label = "Nội bộ (SHB)"
        session.close()
        
        if staging_doc_details:
            st.subheader("1. Chi tiết văn bản nháp")
            col1, col2, col3, col4 = st.columns(4)
            col1.text_input("Mã văn bản", staging_doc_details.doc_code, disabled=True)
            col2.text_input("Loại văn bản", staging_doc_details.doc_type, disabled=True)
            col3.text_input("Phạm vi tài liệu", visibility_label, disabled=True)
            col4.text_input("Ngày hiệu lực", str(staging_doc_details.effective_date), disabled=True)
            st.text_input("Tiêu đề đầy đủ", staging_doc_details.doc_title, disabled=True)
            
            st.subheader("2. Danh sách điều khoản bóc tách")
            clause_data_list = []
            for c in staging_clauses:
                clause_data_list.append({
                    "Mã Điều khoản": c.clause_id,
                    "Vị trí (Path)": c.path,
                    "Nội dung văn bản": c.text,
                    "Chủ đề (Topic)": c.topic,
                    "Phạm vi": c.visibility.upper()
                })
            df_clauses = pd.DataFrame(clause_data_list)
            st.dataframe(df_clauses, use_container_width=True)
            
            # Action button to approve
            if st.button("Duyệt & Phát hành lên DWH", type="primary", key="btn_approve"):
                with st.spinner("Đang phê duyệt và chuyển dữ liệu sang kho vận hành..."):
                    try:
                        response = httpx.post(f"{API_BASE_URL}/api/admin/approve-document/{selected_staging_code}", timeout=30.0)
                        if response.status_code == 200:
                            st.success(f"🎉 {response.json()['message']}")
                            st.balloons()
                        else:
                            st.error(f"Lỗi phê duyệt từ server backend: {response.text}")
                    except Exception as e:
                        st.error(f"Không thể kết nối đến server backend: {e}")
    else:
        st.info("Hiện không có văn bản nháp nào đang chờ phê duyệt trong phân vùng Staging.")

with tab3:
    st.header("Radar Tác động (Impact Radar)")
    st.markdown("Chọn một văn bản sửa đổi/đính chính đã được phê duyệt trong DWH để phân tích các điều khoản chịu ảnh hưởng.")
    
    # Query database to get lists of documents in DWH
    try:
        session = Session(engine)
        docs = session.exec(select(Document)).all()
        session.close()
    except Exception as e:
        st.error(f"Không thể kết nối cơ sở dữ liệu DWH: {e}")
        docs = []
        
    if docs:
        doc_options = {f"{d.doc_code} - {d.title[:60]}...": d.doc_code for d in docs}
        selected_doc_label = st.selectbox("Chọn văn bản để chạy Radar", list(doc_options.keys()))
        selected_doc_code = doc_options[selected_doc_label]
        
        if st.button("Chạy Radar phân tích tác động", type="primary", key="btn_radar"):
            with st.spinner("Đang truy vết các liên kết trên Đồ thị tri thức DWH..."):
                session = Session(engine)
                
                # Find all clauses belonging to the selected document
                clauses = session.exec(select(Clause).where(Clause.doc_code == selected_doc_code)).all()
                clause_ids = [c.clause_id for c in clauses]
                
                # Query edges where from_clause is in the selected document's clauses
                edges = session.exec(select(Edge).where(Edge.from_clause.in_(clause_ids))).all()
                
                session.close()
                
                if edges:
                    st.subheader("Báo cáo ảnh hưởng lan tỏa (Impact Report)")
                    impact_data = []
                    for e in edges:
                        # Find destination clause metadata
                        dest_session = Session(engine)
                        dest_clause = dest_session.get(Clause, e.to_clause)
                        dest_doc = dest_session.get(Document, dest_clause.doc_code) if dest_clause else None
                        dest_session.close()
                        
                        impact_data.append({
                            "Điều khoản tác động": e.from_clause,
                            "Loại tác động": e.type,
                            "Điều khoản bị ảnh hưởng": e.to_clause,
                            "Nội dung bị ảnh hưởng": dest_clause.text[:120] + "..." if dest_clause else "N/A",
                            "Thuộc văn bản": dest_doc.title if dest_doc else dest_clause.doc_code if dest_clause else "N/A",
                            "Phạm vi": dest_clause.visibility.upper() if dest_clause else "N/A",
                            "Ghi chú": e.note
                        })
                        
                    df = pd.DataFrame(impact_data)
                    st.table(df)
                    
                    st.warning("⚠️ Khuyến nghị: Các văn bản bị ảnh hưởng ở trên cần được rà soát và cập nhật nội dung để tránh xung đột pháp lý.")
                else:
                    st.info("Văn bản này không chứa bất kỳ cạnh tác động (sửa đổi, thay thế) nào tới các văn bản khác.")
    else:
        st.info("Chưa có văn bản chính thức nào trong kho DWH để phân tích.")

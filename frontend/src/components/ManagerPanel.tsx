import { useMemo, useState } from 'react'
import type { ChangeEvent } from 'react'
import './ManagerPanel.css'

type ManagerTab = 'dashboard' | 'documents' | 'conflicts' | 'permissions'
type Notify = (title: string, message: string, kind?: 'success' | 'warning' | 'error') => void

const baseMetrics = [
  ['Câu hỏi được hỏi nhiều', '1.248', '+12,4%', 'Tỷ lệ an toàn vốn tối thiểu?'],
  ['Câu hỏi chưa trả lời được', '37', '-8,1%', '2,9% tổng truy vấn'],
  ['Người dùng đánh giá đúng', '91,6%', '+3,2%', '458 lượt đánh giá'],
  ['Citation chính xác', '94,2%', '+1,8%', 'Theo kiểm tra mẫu'],
  ['Tài liệu thường gây mâu thuẫn', '12', '+2', 'TT22 và TT41 đứng đầu'],
  ['Cần chuyển chuyên gia', '19', '-4', 'Đang chờ xử lý'],
  ['Dùng tài liệu cũ bị ngăn chặn', '97,8%', '+0,9%', '342 lượt được bảo vệ'],
  ['Thời gian phản hồi', '1,42 giây', '-0,18 giây', 'Trung bình 7 ngày'],
]

const metricDescriptions = [
  'Tổng số lượt người dùng gửi câu hỏi đến chatbot trong kỳ đã chọn.',
  'Các truy vấn hệ thống chưa tìm được đủ căn cứ để tạo câu trả lời đáng tin cậy.',
  'Tỷ lệ phản hồi tích cực trên tổng số lượt người dùng đánh giá câu trả lời.',
  'Tỷ lệ trích dẫn khớp với nội dung trả lời qua kiểm tra tự động và kiểm tra mẫu.',
  'Số tài liệu xuất hiện trong ít nhất một trường hợp nội dung không nhất quán.',
  'Các câu hỏi có độ tin cậy thấp hoặc cần quyết định nghiệp vụ từ chuyên gia.',
  'Tỷ lệ truy vấn mà bộ lọc hiệu lực đã ngăn sử dụng phiên bản tài liệu hết hiệu lực.',
  'Thời gian từ khi nhận câu hỏi đến khi trả về đầy đủ câu trả lời và citation.',
]

const initialConflicts = [
  { id: 1, topic: 'Tỷ lệ an toàn vốn tối thiểu', feedback: 'Khách hàng cho biết chatbot trả về cả mức 8% và 9%.', documents: 'TT41/2016 Điều 6.3 · TT22/2019 Điều 1', effective: '01/01/2020', suggestion: 'Ưu tiên TT22/2019 (9%); đánh dấu TT41 đã được thay thế một phần.', status: 'open' },
  { id: 2, topic: 'Thời hạn lưu trữ hồ sơ KYC', feedback: 'Citation chưa khớp với nội dung trả lời.', documents: 'QĐ 2345/QĐ-NHNN · Quy trình KYC nội bộ v3', effective: '01/07/2024', suggestion: 'Chuyển chuyên gia tuân thủ xác nhận phạm vi áp dụng nội bộ.', status: 'expert' },
]

export default function ManagerPanel({ notify }: { notify: Notify }) {
  const [tab, setTab] = useState<ManagerTab>('dashboard')
  const [documentFile, setDocumentFile] = useState<File | null>(null)
  const [documentName, setDocumentName] = useState('')
  const [documentNumber, setDocumentNumber] = useState('')
  const [issuer, setIssuer] = useState('Ngân hàng Nhà nước Việt Nam')
  const [effectiveDate, setEffectiveDate] = useState('')
  const [scope, setScope] = useState('Toàn hệ thống')
  const [approved, setApproved] = useState(false)
  const [conflicts, setConflicts] = useState(initialConflicts)
  const [search, setSearch] = useState('')
  const [roles, setRoles] = useState({ employeeChat: true, employeeSources: true, employeeFeedback: true, managerDocuments: true, managerConflicts: true, managerPermissions: true })
  const [period, setPeriod] = useState<'7' | '30' | 'quarter'>('7')
  const [selectedMetric, setSelectedMetric] = useState(0)
  const [showAllQuestions, setShowAllQuestions] = useState(false)
  const [refreshedAt, setRefreshedAt] = useState(new Date())

  const filteredConflicts = useMemo(() => conflicts.filter((item) => `${item.topic} ${item.documents}`.toLocaleLowerCase('vi').includes(search.toLocaleLowerCase('vi'))), [conflicts, search])
  const dashboardMetrics = useMemo(() => baseMetrics.map((metric, index) => {
    if (period === '7') return metric
    const values30 = ['4.892', '126', '90,8%', '93,7%', '28', '74', '96,9%', '1,51 giây']
    const valuesQuarter = ['14.306', '391', '89,9%', '92,8%', '53', '218', '95,7%', '1,63 giây']
    return [metric[0], period === '30' ? values30[index] : valuesQuarter[index], metric[2], metric[3]]
  }), [period])
  const popularQuestions = ['Tỷ lệ an toàn vốn tối thiểu hiện nay?', 'Hồ sơ vay cần lưu trữ bao lâu?', 'Quy trình báo cáo giao dịch đáng ngờ?', 'Điều kiện mở tài khoản doanh nghiệp?', 'Thời hạn cập nhật thông tin KYC?', 'Giao dịch nào cần báo cáo NHNN?', 'Quy định cấp tín dụng cho bên liên quan?', 'Cách xác định khách hàng có rủi ro cao?']

  const exportDashboard = () => {
    const rows = [['Chỉ số', 'Giá trị', 'Thay đổi', 'Ghi chú'], ...dashboardMetrics]
    const csv = rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(',')).join('\n')
    const url = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `dashboard-compliance-${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  const selectDocument = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    setDocumentFile(file)
    if (file && !documentName) setDocumentName(file.name.replace(/\.[^.]+$/, ''))
    setApproved(false)
  }

  const approveDocument = () => {
    if (!documentFile || !documentName.trim() || !documentNumber.trim() || !effectiveDate) return
    setApproved(true)
    notify('Tài liệu mới được phê duyệt', `${documentName} đã được quản lý đưa vào hệ thống.`)
  }

  const resolveConflict = (id: number, action: 'resolved' | 'expert') => {
    const item = conflicts.find((conflict) => conflict.id === id)
    setConflicts((current) => current.map((conflict) => conflict.id === id ? { ...conflict, status: action } : conflict))
    if (item) notify(action === 'resolved' ? 'Mâu thuẫn đã được xử lý' : 'Đã chuyển chuyên gia', item.topic, action === 'resolved' ? 'success' : 'warning')
  }

  return <section className="manager-page">
    <aside className="manager-sidebar">
      <div className="manager-heading"><span>◆</span><div><strong>Trung tâm quản trị</strong><small>Quản lý hệ thống</small></div></div>
      <nav aria-label="Điều hướng quản trị">
        {([['dashboard', '▦', 'Dashboard'], ['documents', '▤', 'Quản lý tài liệu'], ['conflicts', '⚠', 'Xử lý mâu thuẫn'], ['permissions', '♙', 'Phân quyền']] as const).map(([value, icon, label]) => <button className={tab === value ? 'active' : ''} type="button" onClick={() => setTab(value)} key={value}><span>{icon}</span>{label}</button>)}
      </nav>
    </aside>

    <div className="manager-content">
      {tab === 'dashboard' && <>
        <header className="manager-title dashboard-title"><div><h1>Dashboard quản trị</h1><p>Tổng quan chất lượng chatbot và tình trạng tuân thủ · cập nhật {refreshedAt.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}</p></div><div className="dashboard-actions"><button type="button" onClick={() => setRefreshedAt(new Date())}>↻ Làm mới</button><button type="button" onClick={exportDashboard}>⇩ Xuất CSV</button><select aria-label="Khoảng thời gian" value={period} onChange={(e) => setPeriod(e.target.value as typeof period)}><option value="7">7 ngày gần nhất</option><option value="30">30 ngày gần nhất</option><option value="quarter">Quý này</option></select></div></header>
        <div className="metric-grid">{dashboardMetrics.map(([label, value, change, note], index) => <button type="button" className={`metric-card ${selectedMetric === index ? 'selected' : ''}`} onClick={() => setSelectedMetric(index)} key={label}><div><span>{label}</span><i className={`metric-icon m${index}`}>{['?', '!', '✓', '⌁', '⚠', '↗', '⊘', '◷'][index]}</i></div><strong>{value}</strong><small><b>{change}</b> {note}</small></button>)}</div>
        <article className="metric-detail"><div><span>Chi tiết chỉ số</span><h2>{dashboardMetrics[selectedMetric][0]}</h2><p>{metricDescriptions[selectedMetric]}</p></div><div className="mini-trend" aria-label="Xu hướng 7 điểm">{[42, 55, 48, 68, 62, 76, 88].map((height, index) => <i style={{ height: `${height}%` }} key={index} />)}</div><strong>{dashboardMetrics[selectedMetric][1]}</strong></article>
        <div className="dashboard-grid">
          <article className="manager-card"><header><h2>Câu hỏi được hỏi nhiều</h2><button type="button" onClick={() => setShowAllQuestions((show) => !show)}>{showAllQuestions ? 'Thu gọn' : 'Xem tất cả'}</button></header>{popularQuestions.slice(0, showAllQuestions ? 8 : 4).map((q, i) => <div className="rank-row" key={q}><b>{i + 1}</b><span>{q}</span><strong>{[286, 194, 163, 121, 108, 96, 83, 75][i]} lượt</strong></div>)}</article>
          <article className="manager-card"><header><h2>Chất lượng theo tuần</h2><span className="good-status">● Đang cải thiện</span></header><div className="quality-bars">{[['Citation chính xác', 94], ['Đánh giá đúng', 92], ['Ngăn tài liệu cũ', 98], ['Trả lời được', 97]].map(([label, value]) => <div key={label}><span>{label}<strong>{value}%</strong></span><i><b style={{ width: `${value}%` }} /></i></div>)}</div></article>
        </div>
      </>}

      {tab === 'documents' && <>
        <header className="manager-title"><div><h1>Quản lý tài liệu</h1><p>Kiểm tra metadata và phê duyệt tài liệu trước khi đưa vào hệ thống.</p></div><span className="workflow-badge">Quy trình 5 bước</span></header>
        <div className="workflow-steps">{['Tải tài liệu', 'Kiểm tra metadata', 'Ngày hiệu lực', 'Phạm vi áp dụng', 'Phê duyệt'].map((step, i) => <div className={(approved || (i === 0 && documentFile) || (i > 0 && documentFile)) ? 'done' : ''} key={step}><b>{approved ? '✓' : i + 1}</b><span>{step}</span></div>)}</div>
        <div className="document-layout">
          <article className="manager-card upload-card"><h2>1. Tải tài liệu</h2><label className="upload-zone"><input type="file" accept=".pdf,.doc,.docx" onChange={selectDocument} /><strong>{documentFile ? documentFile.name : 'Kéo thả hoặc chọn tài liệu'}</strong><span>PDF, DOC, DOCX · tối đa 20 MB</span><em>{documentFile ? 'Chọn tệp khác' : 'Chọn tệp'}</em></label>{documentFile && <p className="file-ready">✓ {(documentFile.size / 1024).toFixed(1)} KB · Sẵn sàng kiểm tra</p>}</article>
          <article className="manager-card metadata-card"><h2>2–4. Xác nhận thông tin</h2><p className="system-suggestion">✦ Metadata hệ thống đề xuất — vui lòng kiểm tra trước khi phê duyệt.</p><div className="metadata-grid"><label><span>Tên tài liệu *</span><input value={documentName} onChange={(e) => setDocumentName(e.target.value)} placeholder="Tên văn bản" /></label><label><span>Số hiệu *</span><input value={documentNumber} onChange={(e) => setDocumentNumber(e.target.value)} placeholder="VD: 22/2019/TT-NHNN" /></label><label><span>Cơ quan ban hành</span><input value={issuer} onChange={(e) => setIssuer(e.target.value)} /></label><label><span>Ngày hiệu lực *</span><input type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} /></label><label className="full"><span>Phạm vi áp dụng *</span><select value={scope} onChange={(e) => setScope(e.target.value)}><option>Toàn hệ thống</option><option>Khách hàng công khai</option><option>Nội bộ nhân viên</option><option>Khối quản trị rủi ro</option></select></label></div><div className="approval-row"><p>{approved ? '✓ Tài liệu đã được phê duyệt và đưa vào hệ thống.' : 'Kiểm tra đầy đủ thông tin trước khi phê duyệt.'}</p><button type="button" disabled={!documentFile || !documentName.trim() || !documentNumber.trim() || !effectiveDate || approved} onClick={approveDocument}>{approved ? 'Đã phê duyệt' : 'Phê duyệt tài liệu'}</button></div></article>
        </div>
      </>}

      {tab === 'conflicts' && <>
        <header className="manager-title"><div><h1>Xử lý mâu thuẫn</h1><p>Đối chiếu feedback khách hàng, tài liệu liên quan và đề xuất của hệ thống.</p></div><span className="warning-badge">{conflicts.filter((item) => item.status === 'open').length} cần xử lý</span></header>
        <div className="conflict-toolbar"><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm theo nội dung hoặc tài liệu..." /><select><option>Tất cả trạng thái</option><option>Cần xử lý</option><option>Đã xử lý</option></select></div>
        <div className="manager-conflicts">{filteredConflicts.map((item) => <article className="manager-card conflict-case" key={item.id}><header><div><span className={`case-status ${item.status}`}>{item.status === 'resolved' ? 'Đã xử lý' : item.status === 'expert' ? 'Chờ chuyên gia' : 'Hai nội dung mâu thuẫn'}</span><h2>{item.topic}</h2></div><small>#{String(item.id).padStart(4, '0')}</small></header><div className="case-grid"><section><h3>Feedback của khách hàng</h3><p>{item.feedback}</p></section><section><h3>Tài liệu liên quan</h3><p>{item.documents}</p></section><section><h3>Ngày hiệu lực</h3><p>{item.effective}</p></section><section className="suggestion"><h3>✦ Đề xuất của hệ thống</h3><p>{item.suggestion}</p></section></div><footer><button type="button" className="secondary" onClick={() => resolveConflict(item.id, 'expert')}>Chuyển chuyên gia</button><button type="button" onClick={() => resolveConflict(item.id, 'resolved')}>Xác nhận xử lý</button></footer></article>)}</div>
      </>}

      {tab === 'permissions' && <>
        <header className="manager-title"><div><h1>Phân quyền</h1><p>Thiết lập quyền truy cập chức năng theo vai trò người dùng.</p></div><button className="save-permissions" type="button" onClick={() => notify('Phân quyền đã được cập nhật', 'Thiết lập quyền người dùng mới đã có hiệu lực.')}>Lưu thay đổi</button></header>
        <div className="permission-grid">{[
          ['Nhân viên', 'Tra cứu và phản hồi chatbot', [['employeeChat', 'Sử dụng chatbot'], ['employeeSources', 'Xem citation và tài liệu nguồn'], ['employeeFeedback', 'Gửi feedback câu trả lời']]],
          ['Quản lý', 'Quản trị nội dung và hệ thống', [['managerDocuments', 'Quản lý và phê duyệt tài liệu'], ['managerConflicts', 'Xử lý mâu thuẫn và feedback'], ['managerPermissions', 'Thiết lập phân quyền']]],
        ].map(([title, description, items]) => <article className="manager-card permission-card" key={title as string}><header><i>{title === 'Quản lý' ? 'QL' : 'NV'}</i><div><h2>{title as string}</h2><p>{description as string}</p></div></header>{(items as string[][]).map(([key, label]) => <label className="permission-row" key={key}><span><strong>{label}</strong><small>{key.includes('Chat') ? 'Cho phép truy cập và gửi câu hỏi' : 'Cho phép xem và thực hiện tác vụ'}</small></span><input type="checkbox" checked={roles[key as keyof typeof roles]} onChange={(e) => setRoles((current) => ({ ...current, [key]: e.target.checked }))} /></label>)}</article>)}</div>
      </>}
    </div>
  </section>
}

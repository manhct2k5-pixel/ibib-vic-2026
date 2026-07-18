-- =====================================================================
-- Compliance Copilot — PostgreSQL schema
-- Ánh xạ 1-1 với data/sample/corpus.schema.json (documents / clauses / edges).
-- corpus.json vẫn là "hạt giống" gõ tay; loader nạp vào các bảng này.
-- =====================================================================

-- Hỗ trợ bỏ dấu tiếng Việt cho full-text search
CREATE EXTENSION IF NOT EXISTS unaccent;

-- ---------- documents ----------
CREATE TABLE IF NOT EXISTS documents (
    doc_code        TEXT PRIMARY KEY,                 -- 'TT41'
    title           TEXT NOT NULL,
    type            TEXT NOT NULL,                    -- Luật/NghiDinh/ThongTu/Basel/QuyTrinhNoiBo
    issuer          TEXT NOT NULL,                    -- NHNN / ChinhPhu / SHB
    issue_date      DATE,
    effective_date  DATE NOT NULL,
    visibility      TEXT NOT NULL CHECK (visibility IN ('public','internal'))
);

-- ---------- clauses (đơn vị nguyên tử — AD-4) ----------
CREATE TABLE IF NOT EXISTS clauses (
    clause_id       TEXT PRIMARY KEY,                 -- 'TT41/Điều 6.3'
    doc_code        TEXT NOT NULL REFERENCES documents(doc_code) ON DELETE CASCADE,
    path            TEXT NOT NULL,                    -- 'Điều 6.3'
    body            TEXT NOT NULL,                    -- nội dung điều khoản
    effective_date  DATE NOT NULL,
    expiry_date     DATE,                             -- NULL = còn hiệu lực vô thời hạn (AD-5)
    topic           TEXT NOT NULL,                    -- khóa so khớp xung đột (FR-11)
    visibility      TEXT NOT NULL CHECK (visibility IN ('public','internal')),
    metric_value    NUMERIC,                          -- ngưỡng số (tùy chọn) cho rule xung đột
    metric_unit     TEXT,
    -- full-text search tiếng Việt (bỏ dấu): dùng config 'simple' + unaccent
    ts              tsvector GENERATED ALWAYS AS
                    (to_tsvector('simple', unaccent(coalesce(body,'')))) STORED
);

CREATE INDEX IF NOT EXISTS idx_clauses_topic   ON clauses(topic);
CREATE INDEX IF NOT EXISTS idx_clauses_active  ON clauses(effective_date, expiry_date);
CREATE INDEX IF NOT EXISTS idx_clauses_ts      ON clauses USING GIN(ts);

-- ---------- edges (quan hệ — KHÔNG chứa CONFLICTS_WITH, xung đột tính runtime AD-9) ----------
CREATE TABLE IF NOT EXISTS edges (
    id        BIGSERIAL PRIMARY KEY,
    from_id   TEXT NOT NULL REFERENCES clauses(clause_id) ON DELETE CASCADE,
    to_id     TEXT NOT NULL REFERENCES clauses(clause_id) ON DELETE CASCADE,
    type      TEXT NOT NULL CHECK (type IN ('AMENDS','SUPERSEDES','REFERENCES','GUIDES')),
    note      TEXT,
    UNIQUE (from_id, to_id, type)
);

CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id);
CREATE INDEX IF NOT EXISTS idx_edges_to   ON edges(to_id);

-- =====================================================================
-- CÁC TRUY VẤN LÕI (thay cho logic in-memory) — dùng $1 = asOf, $2 = câu hỏi, $3 = mode
-- =====================================================================

-- is_active(clause, asOf)  →  chỉ là một mệnh đề WHERE (AD-5):
--   WHERE effective_date <= $1 AND (expiry_date IS NULL OR $1 < expiry_date)

-- 1) RETRIEVE (full-text) + lọc hiệu lực + lọc visibility (AD-3, AD-8, AD-11)
--    (scope='public' thì thêm: AND visibility = 'public'; scope='all' thì không lọc)
--   SELECT clause_id, body, ts_rank(ts, plainto_tsquery('simple', unaccent($2))) AS score
--   FROM clauses
--   WHERE ts @@ plainto_tsquery('simple', unaccent($2))
--     AND effective_date <= $1 AND (expiry_date IS NULL OR $1 < expiry_date)
--   ORDER BY score DESC LIMIT 10;

-- 2) EXPAND dẫn chiếu 1 hop (FR-5):
--   SELECT c.* FROM edges e JOIN clauses c ON c.clause_id = e.to_id
--   WHERE e.type='REFERENCES' AND e.from_id = ANY($retrieved_ids);

-- 3) CONFLICT (rule quét thật, chạy sau lọc hiệu lực — FR-11, AD-9):
--   SELECT a.clause_id, b.clause_id, a.topic, a.metric_value, b.metric_value
--   FROM clauses a JOIN clauses b
--     ON a.topic = b.topic AND a.clause_id < b.clause_id
--    AND a.metric_value IS DISTINCT FROM b.metric_value
--   WHERE a.effective_date <= $1 AND (a.expiry_date IS NULL OR $1 < a.expiry_date)
--     AND b.effective_date <= $1 AND (b.expiry_date IS NULL OR $1 < b.expiry_date);

-- 4) TIMELINE phiên bản (FR-10): đi ngược chuỗi SUPERSEDES bằng recursive CTE.
-- 5) GRAPH cho FR-12: SELECT * FROM clauses; SELECT * FROM edges; → serialize {nodes,edges} cho FE.

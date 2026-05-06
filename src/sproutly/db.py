"""
SQLite 저장 모듈 (v2)

변경점:
- image_hash 컬럼 추가 (중복 저장 방지)
- find_by_hash 추가
- list_records에 검색/정렬 지원
- 기존 DB 마이그레이션 자동 처리
"""
import hashlib
import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger('sproutly.db')

from sproutly.paths import DB_PATH, IMAGE_DIR

SCHEMA = """
         CREATE TABLE IF NOT EXISTS records
         (
             id
             INTEGER
             PRIMARY
             KEY
             AUTOINCREMENT,
             created_at
             TEXT
             NOT
             NULL,
             image_path
             TEXT,
             image_hash
             TEXT,

             title
             TEXT
             NOT
             NULL,
             buttons
             INTEGER
             NOT
             NULL,

             score
             INTEGER
             NOT
             NULL,
             accuracy
             TEXT,
             is_score_grown
             INTEGER
             NOT
             NULL
             DEFAULT
             0,
             is_accuracy_grown
             INTEGER
             NOT
             NULL
             DEFAULT
             0,

             max_100
             INTEGER
             NOT
             NULL
             DEFAULT
             0,
             max_90
             INTEGER
             NOT
             NULL
             DEFAULT
             0,
             max_80
             INTEGER
             NOT
             NULL
             DEFAULT
             0,
             max_70
             INTEGER
             NOT
             NULL
             DEFAULT
             0,
             max_60
             INTEGER
             NOT
             NULL
             DEFAULT
             0,
             max_50
             INTEGER
             NOT
             NULL
             DEFAULT
             0,
             max_40
             INTEGER
             NOT
             NULL
             DEFAULT
             0,
             max_30
             INTEGER
             NOT
             NULL
             DEFAULT
             0,
             max_20
             INTEGER
             NOT
             NULL
             DEFAULT
             0,
             max_10
             INTEGER
             NOT
             NULL
             DEFAULT
             0,
             max_1
             INTEGER
             NOT
             NULL
             DEFAULT
             0,
             break_count
             INTEGER
             NOT
             NULL
             DEFAULT
             0,

             summary_max_100
             INTEGER,
             summary_max_1_90
             INTEGER,
             summary_break
             INTEGER
         );

         CREATE INDEX IF NOT EXISTS idx_records_created_at ON records(created_at);
         CREATE INDEX IF NOT EXISTS idx_records_title ON records(title);
         CREATE INDEX IF NOT EXISTS idx_records_image_hash ON records(image_hash); \
         """


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn: sqlite3.Connection):
    """기존 DB에 image_hash 컬럼 없으면 추가"""
    cols = [row['name'] for row in conn.execute("PRAGMA table_info(records)").fetchall()]
    if 'image_hash' not in cols:
        conn.execute("ALTER TABLE records ADD COLUMN image_hash TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_image_hash ON records(image_hash)")


def init_db():
    IMAGE_DIR.mkdir(exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


def calc_image_hash(image_path: str) -> str:
    h = hashlib.sha1()
    with open(image_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def find_by_hash(image_hash: str) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM records WHERE image_hash = ? LIMIT 1",
            (image_hash,)
        ).fetchone()


def save_record(record: dict, source_image: Optional[str] = None) -> int:
    now = datetime.now()
    iso_ts = now.isoformat(timespec='seconds')

    image_path = None
    image_hash = None
    if source_image:
        src = Path(source_image)
        if src.exists():
            image_hash = calc_image_hash(source_image)
            ext = src.suffix or '.png'
            fname = now.strftime('%Y%m%d_%H%M%S') + ext
            dst = IMAGE_DIR / fname
            shutil.copy2(src, dst)
            image_path = str(dst)

    j = record.get('judgement', {})

    sql = """
          INSERT INTO records (created_at, image_path, image_hash,
                               title, buttons,
                               score, accuracy, is_score_grown, is_accuracy_grown,
                               max_100, max_90, max_80, max_70, max_60, max_50,
                               max_40, max_30, max_20, max_10, max_1, break_count,
                               summary_max_100, summary_max_1_90, summary_break)
          VALUES (?, ?, ?,
                  ?, ?,
                  ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?,
                  ?, ?, ?) \
          """
    params = (
        iso_ts, image_path, image_hash,
        record.get('title', ''),
        record.get('buttons', 0),
        record.get('score', 0),
        record.get('accuracy', ''),
        int(record.get('is_score_grown', False)),
        int(record.get('is_accuracy_grown', False)),
        j.get('max_100', 0), j.get('max_90', 0), j.get('max_80', 0),
        j.get('max_70', 0), j.get('max_60', 0), j.get('max_50', 0),
        j.get('max_40', 0), j.get('max_30', 0), j.get('max_20', 0),
        j.get('max_10', 0), j.get('max_1', 0), j.get('break', 0),
        record.get('max_100_count'),
        record.get('max_1_90_count'),
        record.get('break_count'),
    )

    with get_conn() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def list_records(
        limit: int = 100,
        title_filter: str = '',
        order_by: str = 'created_at DESC',
) -> list[sqlite3.Row]:
    sql = "SELECT * FROM records"
    params = []
    if title_filter:
        sql += " WHERE title LIKE ?"
        params.append(f'%{title_filter}%')

    allowed = {
        'created_at DESC', 'created_at ASC',
        'score DESC', 'score ASC',
        'title ASC', 'title DESC',
    }
    if order_by not in allowed:
        order_by = 'created_at DESC'
    sql += f" ORDER BY {order_by} LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def get_record(record_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM records WHERE id = ?", (record_id,)
        ).fetchone()


def delete_record(record_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT image_path FROM records WHERE id = ?", (record_id,)
        ).fetchone()
        if row and row['image_path']:
            p = Path(row['image_path'])
            if p.exists():
                p.unlink()
        conn.execute("DELETE FROM records WHERE id = ?", (record_id,))


def get_overall_stats() -> dict:
    """전체 통계"""
    with get_conn() as conn:
        total_plays = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        unique_songs = conn.execute("SELECT COUNT(DISTINCT title || '|' || buttons) FROM records").fetchone()[0]
        score_grown_count = conn.execute("SELECT COUNT(*) FROM records WHERE is_score_grown = 1").fetchone()[0]

        # 평균 정확도 (accuracy는 "99.98%" 문자열이라 파싱)
        rows = conn.execute("SELECT accuracy FROM records WHERE accuracy IS NOT NULL AND accuracy != ''").fetchall()
        accs = []
        for r in rows:
            s = r['accuracy'].rstrip('%').strip()
            try:
                accs.append(float(s))
            except ValueError:
                pass
        avg_acc = sum(accs) / len(accs) if accs else 0.0

    return {
        'total_plays': total_plays,
        'unique_songs': unique_songs,
        'score_grown_count': score_grown_count,
        'avg_accuracy': avg_acc,
    }


def get_per_song_stats() -> list[dict]:
    """곡(title + buttons)별 통계"""
    sql = """
          SELECT title,
                 buttons,
                 COUNT(*)        AS play_count,
                 MAX(score)      AS best_score,
                 AVG(score)      AS avg_score,
                 MAX(created_at) AS last_played
          FROM records
          GROUP BY title, buttons
          ORDER BY MAX(score) DESC \
          """
    with get_conn() as conn:
        rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def get_song_history(title: str, buttons: int) -> list[dict]:
    """특정 곡의 시간순 점수 추이"""
    sql = """
          SELECT created_at, score, accuracy
          FROM records
          WHERE title = ?
            AND buttons = ?
          ORDER BY created_at ASC \
          """
    with get_conn() as conn:
        rows = conn.execute(sql, (title, buttons)).fetchall()
    return [dict(r) for r in rows]


if __name__ == '__main__':
    init_db()
    print("DB initialized")
    for row in list_records(limit=5):
        print(dict(row))

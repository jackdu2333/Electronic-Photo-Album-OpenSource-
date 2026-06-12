"""
数据库服务模块
封装 SQLite 数据库操作
"""
import json
import sqlite3
import logging
from typing import Optional, List, Dict, Any

from config import config

logger = logging.getLogger(__name__)

# 全局数据库文件路径（由 app.py 设置）
DB_FILE: str = ""


def set_db_file(db_file: str):
    """设置数据库文件路径"""
    global DB_FILE
    DB_FILE = db_file


def init_database(db_file: Optional[str] = None):
    """
    初始化 SQLite 数据库，创建 photos 表（如不存在），并开启 WAL 模式提升并发性能。

    Args:
        db_file: 数据库文件路径，如不传则使用全局 DB_FILE
    """
    file_path = db_file or DB_FILE
    if not file_path:
        raise ValueError("DB_FILE not set. Call set_db_file() first.")

    conn = sqlite3.connect(
        file_path,
        timeout=max(config.SQLITE_BUSY_TIMEOUT_MS / 1000, 1),
        isolation_level=None
    )
    c = conn.cursor()

    # 开启 WAL 模式：读写不互斥，多请求并发时不会相互阻塞
    c.execute("PRAGMA journal_mode=WAL")
    c.execute(f"PRAGMA busy_timeout={config.SQLITE_BUSY_TIMEOUT_MS}")
    c.execute(f"PRAGMA synchronous={config.SQLITE_SYNCHRONOUS}")
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA temp_store=MEMORY")

    # 建表（幂等）
    c.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            url        TEXT PRIMARY KEY,   -- 相对路径，唯一键
            date       TEXT,               -- 拍摄日期 YYYY-MM-DD（可为 NULL）
            month      INTEGER,            -- 拍摄月份（可为 NULL）
            tags       TEXT,               -- 标签字符串
            weight     REAL DEFAULT 1.0,   -- 静态标签权重
            view_count INTEGER DEFAULT 0   -- 展示次数（用于精准打捞排序）
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS app_state (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id         TEXT PRIMARY KEY,
            content    TEXT NOT NULL,
            sender     TEXT NOT NULL,
            timestamp  TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration：旧数据库可能没有 view_count 列，安全添加
    try:
        c.execute("ALTER TABLE photos ADD COLUMN view_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError as e:
        if 'duplicate column' not in str(e).lower():
            raise  # 非列重复错误（如磁盘满、权限不足）应上抛

    # ── v3.0 Migration: 新增照片源适配层字段 ──────────────────────
    _v3_columns = [
        ("id",          "TEXT"),           # 稳定 photo id（source_type + source_ref 哈希）
        ("source_type", "TEXT"),           # desktop_folder / imported_copy / ios_photokit
        ("source_ref",  "TEXT"),           # 原始引用（绝对路径 / 相对路径 / PHAsset id）
        ("display_url", "TEXT"),           # 前端展示 URL（/api/photos/{id}/image）
        ("note_title",  "TEXT"),           # 便签标题（从 JSON 迁入）
        ("note_body",   "TEXT"),           # 便签正文（从 JSON 迁入）
        ("width",       "INTEGER"),        # 图片宽度
        ("height",      "INTEGER"),        # 图片高度
        ("missing",     "INTEGER"),        # 原图是否缺失（0=正常，1=缺失）
        ("created_at",  "TEXT"),           # 入库时间
        ("updated_at",  "TEXT"),           # 更新时间
    ]
    for col_name, col_def in _v3_columns:
        try:
            c.execute(f"ALTER TABLE photos ADD COLUMN {col_name} {col_def}")
            logger.info(f"v3.0 migration: added column '{col_name}'")
        except sqlite3.OperationalError as e:
            if 'duplicate column' not in str(e).lower():
                raise

    # 复合索引：加速深海打捞查询（WHERE date <= ? ORDER BY view_count ASC）
    c.execute("CREATE INDEX IF NOT EXISTS idx_photos_date_viewcount ON photos(date, view_count)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at, id)")

    # v3.0 索引
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_photos_id ON photos(id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_photos_source_type ON photos(source_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_photos_missing ON photos(missing)")

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


def get_db_connection(timeout: int = 10, check_same_thread: bool = False):
    """
    获取数据库连接

    Args:
        timeout: 锁等待超时时间（秒）
        check_same_thread: 是否检查同一线程

    Returns:
        sqlite3.Connection 对象
    """
    if not DB_FILE:
        raise ValueError("DB_FILE not set. Call set_db_file() first.")

    effective_timeout = timeout if timeout else config.SQLITE_BUSY_TIMEOUT_MS / 1000
    conn = sqlite3.connect(
        DB_FILE,
        timeout=effective_timeout,
        check_same_thread=check_same_thread,
        isolation_level=None
    )
    conn.row_factory = sqlite3.Row  # 返回字典风格行
    conn.execute(f"PRAGMA busy_timeout={config.SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute(f"PRAGMA synchronous={config.SQLITE_SYNCHRONOUS}")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


class PhotoDAO:
    """
    照片数据访问对象（Data Access Object）
    封装所有数据库 CRUD 操作
    """

    @staticmethod
    def get_by_url(url: str) -> Optional[Dict[str, Any]]:
        """根据 URL 获取照片记录"""
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM photos WHERE url = ?", (url,))
            row = c.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """获取所有照片记录"""
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM photos ORDER BY date DESC, url DESC")
            rows = c.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def insert_or_ignore(records: List[tuple]) -> int:
        """
        批量插入照片记录（忽略已存在的）

        Args:
            records: [(url, date, month, tags, weight), ...]

        Returns:
            实际插入的记录数
        """
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            c.executemany(
                """
                INSERT OR IGNORE INTO photos (url, date, month, tags, weight, view_count)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                records
            )
            conn.commit()
            inserted = conn.total_changes
            return inserted
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def update_metadata(url: str, date: Optional[str], month: Optional[int],
                        tags: str, weight: float) -> bool:
        """
        更新照片元数据

        Args:
            url: 照片相对路径
            date: 拍摄日期
            month: 拍摄月份
            tags: 标签字符串
            weight: 权重

        Returns:
            是否更新成功
        """
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            c.execute(
                """
                UPDATE photos
                SET date=?, month=?, tags=?, weight=?
                WHERE url=?
                """,
                (date, month, tags, weight, url)
            )
            conn.commit()
            updated = c.rowcount > 0
            return updated
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def bulk_update_metadata(records: List[tuple]) -> int:
        """
        单一事务批量更新照片元数据（P2 修复：替代 N 次独立 update_metadata 调用）

        Args:
            records: [(url, date, month, tags, weight), ...]

        Returns:
            更新的行数合计
        """
        if not records:
            return 0

        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            c.executemany(
                """
                UPDATE photos
                SET date=?, month=?, tags=?, weight=?
                WHERE url=?
                """,
                [(date, month, tags, weight, url) for url, date, month, tags, weight in records]
            )
            conn.commit()
            return c.rowcount
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def delete_missing(current_urls: tuple) -> int:
        """
        删除文件系统中已不存在的照片记录

        Args:
            current_urls: 当前存在的文件 URL 元组

        Returns:
            删除的记录数
        """
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            if current_urls:
                placeholders = ','.join('?' * len(current_urls))
                c.execute(
                    f"DELETE FROM photos WHERE url NOT IN ({placeholders})",
                    current_urls
                )
            else:
                # 相册为空时清空全表
                c.execute("DELETE FROM photos")

            deleted = c.rowcount
            conn.commit()
            return deleted
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def sync_records(records: List[tuple]) -> Dict[str, int]:
        """
        在单一事务中完成照片索引同步，减少 SQLite 写锁持有次数。

        Args:
            records: [(url, date, month, tags, weight), ...]

        Returns:
            包含 inserted/updated/deleted 计数的字典
        """
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")

            inserted = 0
            updated = 0

            if records:
                before_insert = conn.total_changes
                c.executemany(
                    """
                    INSERT OR IGNORE INTO photos (url, date, month, tags, weight, view_count)
                    VALUES (?, ?, ?, ?, ?, 0)
                    """,
                    records
                )
                inserted = conn.total_changes - before_insert

                before_update = conn.total_changes
                c.executemany(
                    """
                    UPDATE photos
                    SET date=?, month=?, tags=?, weight=?
                    WHERE url=?
                    """,
                    [(date, month, tags, weight, url) for url, date, month, tags, weight in records]
                )
                updated = conn.total_changes - before_update

                current_urls = tuple(r[0] for r in records)
                placeholders = ','.join('?' * len(current_urls))
                c.execute(
                    f"""DELETE FROM photos
                        WHERE url NOT IN ({placeholders})
                          AND (source_type = 'imported_copy' OR source_type IS NULL)
                    """,
                    current_urls
                )
            else:
                c.execute(
                    "DELETE FROM photos WHERE source_type = 'imported_copy' OR source_type IS NULL"
                )

            deleted = c.rowcount
            conn.commit()
            return {
                'inserted': inserted,
                'updated': updated,
                'deleted': deleted,
            }
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def increment_view_count(url: str) -> bool:
        """
        增加照片展示次数

        Args:
            url: 照片相对路径

        Returns:
            是否更新成功
        """
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute(
                "UPDATE photos SET view_count = view_count + 1 WHERE url = ?",
                (url,)
            )
            conn.commit()
            return c.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def delete_by_url(url: str) -> bool:
        """删除单张照片记录"""
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            c.execute("DELETE FROM photos WHERE url = ?", (url,))
            conn.commit()
            return c.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def migrate_v3_records() -> int:
        """
        v3.0 数据迁移：为旧记录补充 id / source_type / source_ref / display_url。

        幂等操作，已迁移的记录不会重复处理。

        Returns:
            迁移的记录数
        """
        import hashlib

        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")

            # 找出还没有 id 的记录
            c.execute("SELECT url FROM photos WHERE id IS NULL OR id = ''")
            rows = c.fetchall()

            count = 0
            for row in rows:
                url = row['url']
                source_type = 'imported_copy'
                source_ref = url  # 旧记录的 source_ref 就是相对路径
                raw = f"{source_type}::{source_ref}"
                digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]
                photo_id = f"{source_type}_{digest}"
                display_url = f"/api/photos/{photo_id}/image"

                c.execute(
                    """
                    UPDATE photos
                    SET id=?, source_type=?, source_ref=?, display_url=?
                    WHERE url=?
                    """,
                    (photo_id, source_type, source_ref, display_url, url)
                )
                count += 1

            conn.commit()
            if count > 0:
                logger.info(f"v3.0 migration: backfilled {count} records")
            return count
        except Exception as e:
            conn.rollback()
            logger.error(f"v3.0 migration error: {e}")
            raise
        finally:
            conn.close()

    @staticmethod
    def get_by_id(photo_id: str) -> Optional[Dict[str, Any]]:
        """根据 photo id 获取照片记录"""
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM photos WHERE id = ?", (photo_id,))
            row = c.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_all_v3(source_type: Optional[str] = None, include_missing: bool = False,
                   limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        v3.0 照片列表查询。

        Args:
            source_type: 可选，按源类型过滤
            include_missing: 是否包含缺失照片
            limit: 分页大小（None 表示不限制）
            offset: 分页偏移量

        Returns:
            照片记录列表
        """
        conn = get_db_connection()
        try:
            c = conn.cursor()
            conditions = []
            params: list = []

            if not include_missing:
                conditions.append("(missing = 0 OR missing IS NULL)")
            if source_type:
                conditions.append("source_type = ?")
                params.append(source_type)

            where = ""
            if conditions:
                where = "WHERE " + " AND ".join(conditions)

            sql = f"SELECT * FROM photos {where} ORDER BY date DESC, url DESC"
            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])

            c.execute(sql, params)
            return [dict(row) for row in c.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def upsert_v3(photo: Dict[str, Any]) -> bool:
        """
        v3.0 插入或更新照片记录。

        以 id 为唯一键，存在则更新，不存在则插入。

        Args:
            photo: 照片字典，必须包含 id, url, source_type, source_ref, display_url

        Returns:
            是否为新增记录
        """
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            c.execute(
                """
                INSERT INTO photos (id, url, source_type, source_ref, display_url,
                                   date, month, tags, weight, view_count,
                                   note_title, note_body, width, height, missing,
                                   created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(url) DO UPDATE SET
                    id = CASE WHEN photos.id IS NULL OR photos.id = '' THEN excluded.id ELSE photos.id END,
                    source_type = COALESCE(excluded.source_type, photos.source_type),
                    source_ref = COALESCE(excluded.source_ref, photos.source_ref),
                    display_url = COALESCE(excluded.display_url, photos.display_url),
                    date = excluded.date,
                    month = excluded.month,
                    tags = excluded.tags,
                    weight = excluded.weight,
                    note_title = excluded.note_title,
                    note_body = excluded.note_body,
                    width = excluded.width,
                    height = excluded.height,
                    missing = excluded.missing,
                    updated_at = CURRENT_TIMESTAMP
                    -- 不覆盖 view_count，保留推荐算法累计值
                """,
                (
                    photo.get('id'), photo.get('url'), photo.get('source_type'),
                    photo.get('source_ref'), photo.get('display_url'),
                    photo.get('date'), photo.get('month'), photo.get('tags', ''),
                    photo.get('weight', 1.0), photo.get('view_count', 0),
                    photo.get('note_title', ''), photo.get('note_body', ''),
                    photo.get('width'), photo.get('height'),
                    1 if photo.get('missing') else 0,
                )
            )
            conn.commit()
            # rowcount: INSERT=1, UPDATE=1, 但用 total_changes 判断更可靠
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def bulk_upsert_v3(photos: List[Dict[str, Any]], batch_size: int = 200) -> int:
        """
        v3.0 批量插入或更新照片记录（单事务 executemany）。

        替代逐条 upsert_v3 调用，大幅减少连接创建/销毁开销。
        ON CONFLICT 不覆盖 view_count，保留推荐算法累计值。

        Args:
            photos: 照片字典列表
            batch_size: 每批大小

        Returns:
            处理的记录总数
        """
        if not photos:
            return 0

        conn = get_db_connection()
        total = 0
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")

            sql = """
                INSERT INTO photos (id, url, source_type, source_ref, display_url,
                                   date, month, tags, weight, view_count,
                                   note_title, note_body, width, height, missing,
                                   created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(url) DO UPDATE SET
                    id = CASE WHEN photos.id IS NULL OR photos.id = '' THEN excluded.id ELSE photos.id END,
                    source_type = COALESCE(excluded.source_type, photos.source_type),
                    source_ref = COALESCE(excluded.source_ref, photos.source_ref),
                    display_url = COALESCE(excluded.display_url, photos.display_url),
                    date = excluded.date,
                    month = excluded.month,
                    tags = excluded.tags,
                    weight = excluded.weight,
                    note_title = excluded.note_title,
                    note_body = excluded.note_body,
                    width = excluded.width,
                    height = excluded.height,
                    missing = excluded.missing,
                    updated_at = CURRENT_TIMESTAMP
            """

            for i in range(0, len(photos), batch_size):
                batch = photos[i:i + batch_size]
                rows = [
                    (
                        p.get('id'), p.get('url'), p.get('source_type'),
                        p.get('source_ref'), p.get('display_url'),
                        p.get('date'), p.get('month'), p.get('tags', ''),
                        p.get('weight', 1.0), p.get('view_count', 0),
                        p.get('note_title', ''), p.get('note_body', ''),
                        p.get('width'), p.get('height'),
                        1 if p.get('missing') else 0,
                    )
                    for p in batch
                ]
                c.executemany(sql, rows)
                total += len(batch)

            conn.commit()
            return total
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def mark_missing_by_source(source_type: str, valid_source_refs: set) -> int:
        """
        标记指定源中不在 valid_source_refs 中的照片为 missing=1。

        Args:
            source_type: 源类型
            valid_source_refs: 当前有效的 source_ref 集合

        Returns:
            标记为缺失的记录数
        """
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")

            if valid_source_refs:
                placeholders = ','.join('?' * len(valid_source_refs))
                params = [source_type] + list(valid_source_refs)
                c.execute(
                    f"""
                    UPDATE photos SET missing = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE source_type = ? AND source_ref NOT IN ({placeholders})
                      AND (missing = 0 OR missing IS NULL)
                    """,
                    params
                )
            else:
                c.execute(
                    """
                    UPDATE photos SET missing = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE source_type = ? AND (missing = 0 OR missing IS NULL)
                    """,
                    (source_type,)
                )

            count = c.rowcount
            conn.commit()
            return count
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def delete_by_id(photo_id: str) -> bool:
        """根据 photo id 删除照片记录（只删索引，不删原图）"""
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            c.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
            conn.commit()
            return c.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def update_note(photo_id: str, note_title: str, note_body: str) -> bool:
        """更新便签字段（不修改原图）"""
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            c.execute(
                """
                UPDATE photos
                SET note_title=?, note_body=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (note_title, note_body, photo_id)
            )
            conn.commit()
            return c.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def update_metadata_and_note(photo_id: str, url: str,
                                  date: Optional[str], month: Optional[int],
                                  tags: str, weight: float,
                                  note_title: str, note_body: str) -> bool:
        """
        在单个事务中更新照片元数据 + 便签（原子操作）。

        Args:
            photo_id: 照片 id
            url: 照片 url（用于旧 metadata 兼容）
            date, month, tags, weight: 元数据字段
            note_title, note_body: 便签字段

        Returns:
            是否更新成功
        """
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            # 更新元数据
            c.execute(
                """UPDATE photos SET date=?, month=?, tags=?, weight=? WHERE url=?""",
                (date, month, tags, weight, url)
            )
            # 更新便签
            c.execute(
                """UPDATE photos SET note_title=?, note_body=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (note_title, note_body, photo_id)
            )
            conn.commit()
            return c.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def get_deep_sea_candidate(cutoff_date: str) -> Optional[Dict[str, Any]]:
        """
        获取深海打捞候选照片（冷数据）

        SELECT + UPDATE 在 BEGIN IMMEDIATE 事务内执行，避免并发竞态。

        Args:
            cutoff_date: 截止日期，早于此日期的为冷数据

        Returns:
            照片记录字典，包含 view_count+1 后的值
        """
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")

            # 精准打捞：优先取 view_count 最小（最少被看到）的冷照片
            c.execute("""
                SELECT url, date, month, tags, weight, view_count
                FROM photos
                WHERE date IS NOT NULL
                  AND date <= ?            -- 拍摄日期早于截止线
                ORDER BY view_count ASC,   -- 首选展示次数最少的
                         RANDOM()          -- 同频次间随机打破平局
                LIMIT 1
            """, (cutoff_date,))

            row = c.fetchone()

            if row:
                # 先自增 view_count（在同一事务内，避免 TOCTOU 竞态）
                c.execute(
                    "UPDATE photos SET view_count = view_count + 1 WHERE url = ?",
                    (row["url"],)
                )
                conn.commit()

                result = dict(row)
                result["view_count"] = row["view_count"] + 1
                return result

            conn.commit()
            return None
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def get_count() -> int:
        """获取照片总数"""
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM photos")
            return c.fetchone()[0]
        finally:
            conn.close()


class AppStateDAO:
    """应用状态存储，用于跨 worker 持久化轻量级运行时状态"""

    @staticmethod
    def set_json(key: str, value: Dict[str, Any]) -> None:
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            c.execute(
                """
                INSERT INTO app_state (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, json.dumps(value, ensure_ascii=False))
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def get_json(key: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT value FROM app_state WHERE key = ?", (key,))
            row = c.fetchone()
            if not row:
                return None
            return json.loads(row["value"])
        finally:
            conn.close()

    @staticmethod
    def delete(key: str) -> None:
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            c.execute("DELETE FROM app_state WHERE key = ?", (key,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()


class MessageDAO:
    """留言数据访问对象，替代 JSON 文件存储以支持并发安全"""

    @staticmethod
    def get_recent(limit: int = 50) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(limit, 200))
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute(
                """
                SELECT id, content, sender, timestamp
                FROM (
                    SELECT id, content, sender, timestamp, created_at
                    FROM messages
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                ) recent
                ORDER BY created_at ASC, id ASC
                """,
                (safe_limit,)
            )
            return [dict(row) for row in c.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def insert_message(message: Dict[str, Any], keep_last: int = 200) -> None:
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            c.execute(
                """
                INSERT INTO messages (id, content, sender, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (
                    message["id"],
                    message["content"],
                    message["sender"],
                    message["timestamp"],
                )
            )
            c.execute(
                """
                DELETE FROM messages
                WHERE id NOT IN (
                    SELECT id
                    FROM messages
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                )
                """,
                (keep_last,)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def insert_many(messages: List[Dict[str, Any]]) -> int:
        if not messages:
            return 0

        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            c.executemany(
                """
                INSERT OR IGNORE INTO messages (id, content, sender, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        message["id"],
                        message["content"],
                        message["sender"],
                        message["timestamp"],
                    )
                    for message in messages
                ]
            )
            conn.commit()
            return conn.total_changes
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def get_count() -> int:
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM messages")
            return c.fetchone()[0]
        finally:
            conn.close()

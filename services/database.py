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
    except Exception:
        pass  # 列已存在时 SQLite 会报错，忽略即可

    # 复合索引：加速深海打捞查询（WHERE date <= ? ORDER BY view_count ASC）
    c.execute("CREATE INDEX IF NOT EXISTS idx_photos_date_viewcount ON photos(date, view_count)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at, id)")

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

    effective_timeout = max(timeout, config.SQLITE_BUSY_TIMEOUT_MS / 1000)
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
    def get_deep_sea_candidate(cutoff_date: str) -> Optional[Dict[str, Any]]:
        """
        获取深海打捞候选照片（冷数据）

        Args:
            cutoff_date: 截止日期，早于此日期的为冷数据

        Returns:
            照片记录字典，包含 view_count+1 后的值
        """
        conn = get_db_connection()
        try:
            c = conn.cursor()

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
                # 先自增 view_count
                c.execute(
                    "UPDATE photos SET view_count = view_count + 1 WHERE url = ?",
                    (row["url"],)
                )
                conn.commit()

                result = dict(row)
                result["view_count"] = row["view_count"] + 1
                return result

            return None
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

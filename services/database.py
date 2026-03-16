"""
数据库服务模块
封装 SQLite 数据库操作
"""
import sqlite3
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

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

    conn = sqlite3.connect(file_path, timeout=10)
    c = conn.cursor()

    # 开启 WAL 模式：读写不互斥，多请求并发时不会相互阻塞
    c.execute("PRAGMA journal_mode=WAL")

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

    # Migration：旧数据库可能没有 view_count 列，安全添加
    try:
        c.execute("ALTER TABLE photos ADD COLUMN view_count INTEGER DEFAULT 0")
    except Exception:
        pass  # 列已存在时 SQLite 会报错，忽略即可

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

    conn = sqlite3.connect(DB_FILE, timeout=timeout, check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row  # 返回字典风格行
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
        c = conn.cursor()
        c.execute("SELECT * FROM photos WHERE url = ?", (url,))
        row = c.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """获取所有照片记录"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM photos ORDER BY date DESC, url DESC")
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

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
        c = conn.cursor()
        c.execute("BEGIN IMMEDIATE")

        try:
            c.executemany(
                """
                INSERT OR IGNORE INTO photos (url, date, month, tags, weight, view_count)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                records
            )
            conn.commit()
            inserted = conn.total_changes
            conn.close()
            return inserted
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

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
        c = conn.cursor()
        c.execute("BEGIN IMMEDIATE")

        try:
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
            conn.close()
            return updated
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

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
        c = conn.cursor()
        c.execute("BEGIN IMMEDIATE")

        try:
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
            conn.close()
            return deleted
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

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
        c = conn.cursor()

        try:
            c.execute(
                "UPDATE photos SET view_count = view_count + 1 WHERE url = ?",
                (url,)
            )
            conn.commit()
            updated = c.rowcount > 0
            conn.close()
            return updated
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

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
            conn.close()
            return result

        conn.close()
        return None

    @staticmethod
    def get_count() -> int:
        """获取照片总数"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM photos")
        count = c.fetchone()[0]
        conn.close()
        return count

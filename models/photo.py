"""
数据模型模块
定义照片数据记录类
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class PhotoRecord:
    """
    照片记录数据类

    Attributes:
        url: 照片相对路径
        date: 拍摄日期 YYYY-MM-DD
        month: 拍摄月份 1-12
        tags: 标签字符串
        weight: 静态权重
        view_count: 展示次数
    """
    url: str
    date: Optional[str] = None
    month: Optional[int] = None
    tags: str = ""
    weight: float = 1.0
    view_count: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'url': self.url,
            'date': self.date,
            'month': self.month,
            'tags': self.tags,
            'weight': self.weight,
            'view_count': self.view_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PhotoRecord':
        """从字典创建"""
        return cls(
            url=data['url'],
            date=data.get('date'),
            month=data.get('month'),
            tags=data.get('tags', ''),
            weight=data.get('weight', 1.0),
            view_count=data.get('view_count', 0)
        )


# 别名：Photo 指向 PhotoRecord
Photo = PhotoRecord

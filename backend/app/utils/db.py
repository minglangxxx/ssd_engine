from contextlib import contextmanager

from app.extensions import db


@contextmanager
def db_released():
    """提交当前事务并释放 DB 连接回连接池。

    用于 HTTP 调用前释放连接，避免连接池耗尽。
    如果代码块内抛出异常，自动 rollback。

    ⚠ 保护范围仅限 yield 代码块内部。
    yield 之后（db_released 之外）的写操作不在保护范围内，
    调用方需自行处理异常 rollback。
    """
    db.session.commit()
    try:
        yield
    except Exception:
        db.session.rollback()
        raise

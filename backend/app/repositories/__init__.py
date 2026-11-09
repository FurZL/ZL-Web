"""数据访问层（复杂查询时使用）。

常规 CRUD 可在 Service 内直接使用 SQLAlchemy session；
本层预留 repository 用于集中管理复杂查询。
"""
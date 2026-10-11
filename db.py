"""数据层：所有和 SQLite 打交道的代码都在这个文件里。

app.py 只调用本文件提供的函数，自己不写 SQL。
这样做的好处：可以脱离浏览器单独测试 —— 直接运行 `python db.py` 就能
验证增删查统全部逻辑，界面上出问题时能立刻确定"不是数据层的锅"。
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

# 数据库文件放在本文件旁边。
# 注意必须用 __file__ 算绝对路径：如果写成 "finance.db"，它会跟随"启动时的
# 当前目录"，从别的目录启动程序就会连到另一个（或新建的）数据库上。
DB_PATH = Path(__file__).resolve().parent / "finance.db"

# 预设分类。想加"医疗"之类的新分类，改这一行就行，不用动数据库。
CATEGORIES = ["餐饮", "交通", "购物", "娱乐", "居住", "其他"]


@contextmanager
def connect():
    """打开数据库连接，用完自动提交并关闭。

    用法：
        with connect() as conn:
            conn.execute(...)

    说明：网上常见的写法 `with sqlite3.connect(...) as conn:` 是错的 ——
    那个 with 只管事务提交，根本不会关闭连接，会慢慢泄漏文件句柄。
    这里用 @contextmanager 自己包了一层，确保 finally 里一定 close()。
    """
    conn = sqlite3.connect(DB_PATH)
    # row_factory 让查询结果能按列名取值：row["amount"] 而不是 row[1]
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """建表建索引。可以重复调用，已存在就跳过。程序启动时调一次。"""
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                amount     REAL    NOT NULL CHECK (amount > 0),
                category   TEXT    NOT NULL,
                date       TEXT    NOT NULL,
                note       TEXT    NOT NULL DEFAULT '',
                created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
            """
        )


def add_expense(amount, category, date_str, note=""):
    """新增一笔支出，返回新记录的 ID。

    date_str 必须是 'YYYY-MM-DD' 格式的字符串（用 date.isoformat() 生成）。
    """
    if amount <= 0:
        raise ValueError("金额必须大于 0")
    if category not in CATEGORIES:
        raise ValueError(f"分类必须是 {CATEGORIES} 之一，收到的是 {category!r}")

    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (amount, category, date, note) VALUES (?, ?, ?, ?)",
            (round(amount, 2), category, date_str, note),
        )
        return cur.lastrowid


def list_expenses(month=None, categories=None):
    """按条件查账目，返回字典列表，最新的排在前面。

    month      : 'YYYY-MM' 字符串，None 表示不限月份
    categories : 分类名列表，None 或空列表表示不限分类
    """
    # 用 "WHERE 1=1" 打底，后面条件就可以无脑用 " AND ..." 拼接，
    # 不用判断"这是第一个条件吗，该写 WHERE 还是 AND"
    sql = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if month:
        # % 通配符放在"参数值"里，而不是 SQL 文本里
        sql += " AND date LIKE ?"
        params.append(f"{month}%")

    if categories:
        # IN 子句没有"传一个列表"的写法，必须自己生成 N 个问号。
        # 注意：只有"问号的个数"是拼进 SQL 的，分类名本身仍然走参数。
        placeholders = ",".join("?" * len(categories))
        sql += f" AND category IN ({placeholders})"
        params.extend(categories)

    sql += " ORDER BY date DESC, id DESC"

    with connect() as conn:
        return [dict(row) for row in conn.execute(sql, params)]


def get_expense(expense_id):
    """按 ID 查单条，查不到返回 None。删除前用它把内容显示给用户确认。"""
    with connect() as conn:
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        return dict(row) if row else None


def delete_expense(expense_id):
    """按 ID 删除，返回实际删掉的条数。返回 0 说明这个 ID 不存在。"""
    with connect() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        # rowcount 比"先 SELECT 查存在、再 DELETE"少一次查询，也没有中间时间窗口
        return cur.rowcount


def list_months():
    """返回数据库里实际有账目的月份，新的在前，例如 ['2026-10', '2026-09']。

    substr(date, 1, 7) 从 '2026-10-11' 里截出 '2026-10'。
    """
    with connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT substr(date, 1, 7) AS ym FROM expenses ORDER BY ym DESC"
        )
        return [row["ym"] for row in rows]


def stats_by_category(month=None):
    """按分类汇总，返回 [{'category':.., 'total':.., 'cnt':..}, ...]，金额大的在前。

    ROUND(SUM(...), 2) 是必须的：REAL 类型累加会出现 300.00000000000006 这种
    浮点尾巴，在 SQL 里就把它收干净。
    """
    sql = """
        SELECT category,
               ROUND(SUM(amount), 2) AS total,
               COUNT(*)              AS cnt
        FROM expenses
    """
    params = []
    if month:
        sql += " WHERE date LIKE ?"
        params.append(f"{month}%")
    sql += " GROUP BY category ORDER BY SUM(amount) DESC"

    with connect() as conn:
        return [dict(row) for row in conn.execute(sql, params)]


# ---------------------------------------------------------------------------
# 冒烟测试：直接运行 `python db.py` 会执行下面的代码。
# 上面所有函数靠它验证，全程不需要启动浏览器。
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile

    # 关键：把数据库指向临时文件，这样测试不会污染你的真实账本。
    # （DB_PATH 是模块级变量，connect() 在调用时才读它，所以这里改了就生效）
    DB_PATH = Path(tempfile.mkdtemp()) / "smoke_test.db"
    print(f"[测试数据库] {DB_PATH}\n")

    init_db()
    print("1. 建表完成")

    with connect() as conn:
        cols = conn.execute("PRAGMA table_info(expenses)").fetchall()
        print("   字段：", ", ".join(f"{c['name']}({c['type']})" for c in cols))

    id1 = add_expense(35.50, "餐饮", "2026-10-11", "午饭")
    id2 = add_expense(12.00, "交通", "2026-10-11", "地铁")
    id3 = add_expense(299.00, "购物", "2026-09-20", "鞋子")
    print(f"\n2. 插入 3 条记录，ID = {id1}, {id2}, {id3}")

    rows = list_expenses()
    print(f"\n3. 查询全部：共 {len(rows)} 条")
    for r in rows:
        print(f"   #{r['id']} {r['date']} {r['category']:<4} {r['amount']:>8.2f}  {r['note']}")

    oct_rows = list_expenses(month="2026-10")
    print(f"\n4. 只看 2026-10：共 {len(oct_rows)} 条（应为 2 条）")
    for r in oct_rows:
        print(f"   #{r['id']} {r['date']} {r['category']:<4} {r['amount']:>8.2f}  {r['note']}")

    food_rows = list_expenses(categories=["餐饮", "交通"])
    print(f"\n5. 只看餐饮+交通：共 {len(food_rows)} 条（应为 2 条）")

    both = list_expenses(month="2026-10", categories=["餐饮"])
    print(f"6. 2026-10 的餐饮：共 {len(both)} 条（应为 1 条）")

    print(f"\n7. 可选月份：{list_months()}（应为 ['2026-10', '2026-09']）")

    print("\n8. 分类统计（全部）：")
    stats = stats_by_category()
    total = sum(s["total"] for s in stats)
    for s in stats:
        print(f"   {s['category']:<4} {s['total']:>8.2f}  {s['cnt']} 笔  {s['total'] / total:.1%}")
    print(f"   {'合计':<4} {total:>8.2f}  {sum(s['cnt'] for s in stats)} 笔")
    print(f"   浮点尾巴检查：合计 = {total!r}（应为 346.5，不是 346.50000000000006）")

    print("\n9. 分类统计（只看 2026-10）：")
    for s in stats_by_category(month="2026-10"):
        print(f"   {s['category']:<4} {s['total']:>8.2f}  {s['cnt']} 笔")

    print(f"\n10. 查单条 get_expense({id1})：{get_expense(id1)}")
    print(f"    查不存在的 get_expense(999)：{get_expense(999)}")

    print(f"\n11. 删除 #{id3}，返回值 {delete_expense(id3)}（应为 1）")
    print(f"    再删一次 #{id3}，返回值 {delete_expense(id3)}（应为 0，说明 ID 不存在）")
    print(f"    删除后剩 {len(list_expenses())} 条")

    print(f"\n12. 校验测试：")
    for bad_call, label in [
        (lambda: add_expense(-1, "餐饮", "2026-10-11"), "金额为负"),
        (lambda: add_expense(10, "旅游", "2026-10-11"), "分类不在预设里"),
    ]:
        try:
            bad_call()
            print(f"   [失败] {label} 竟然通过了，应该报错")
        except ValueError as e:
            print(f"   [正常] {label} 被拦下：{e}")

    print("\n全部冒烟测试执行完毕。")

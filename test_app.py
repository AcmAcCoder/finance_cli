"""app.py 的端到端测试。

用 Streamlit 官方的 AppTest 框架，在命令行里模拟真实的网页操作：
填表单、切月份、选分类、走完删除的两次确认。不需要打开浏览器。

用法：
    .venv/Scripts/python test_app.py

它用的是临时数据库，**不会碰你的 finance.db**。
改完代码跑一遍，能立刻知道有没有把原来的功能改坏。
"""

import sys
import tempfile
from datetime import date
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))

import db  # noqa: E402

# 把数据库指向临时文件。之后 app.py 里的 `import db` 拿到的是同一个模块对象，
# 所以它会用这个临时库，不会污染真实账本
db.DB_PATH = Path(tempfile.mkdtemp()) / "apptest.db"

# 造数据：跨 2 个月、4 个分类
db.init_db()
db.add_expense(35.50, "餐饮", "2026-10-11", "午饭")
db.add_expense(12.00, "交通", "2026-10-11", "地铁")
db.add_expense(299.00, "购物", "2026-09-20", "鞋子")
db.add_expense(88.80, "餐饮", "2026-09-15", "聚餐")

from streamlit.testing.v1 import AppTest  # noqa: E402

FAIL = []


def check(label, cond, extra=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f"  {extra}" if extra else ""))
    if not cond:
        FAIL.append(label)


def fresh():
    at = AppTest.from_file(str(PROJECT / "app.py"), default_timeout=30)
    at.run()
    return at


def find_btn(at, label):
    return [b for b in at.button if b.label == label][0]


print("\n=== 1. 首次加载 ===")
at = fresh()
check("脚本无异常", not at.exception, str(at.exception) if at.exception else "")
check("标题存在", len(at.title) == 1 and "记账本" in at.title[0].value)
check("四个标签页", len(at.tabs) == 4, str([t.label for t in at.tabs]))

print("\n=== 2. 添加账目（模拟网页表单提交）===")
before = len(db.list_expenses())
# 关键：form 里的控件要"一次设完再 run"，中间不能 run —— 表单只有在提交那一次
# 才会把值一起送出去
at.number_input[0].set_value(66.60)      # 金额
at.selectbox[0].set_value("娱乐")         # 分类
at.text_input[0].set_value("电影票")      # 备注
find_btn(at, "保存").set_value(True)
at.run()
check("脚本无异常", not at.exception, str(at.exception) if at.exception else "")
check("记录数 +1", len(db.list_expenses()) == before + 1,
      f"{before} -> {len(db.list_expenses())}")
newest = db.list_expenses()[0]
check("金额写入正确", newest["amount"] == 66.60, str(newest["amount"]))
check("分类写入正确", newest["category"] == "娱乐", newest["category"])
check("备注写入正确", newest["note"] == "电影票", repr(newest["note"]))
check("日期默认今天", newest["date"] == date.today().isoformat(), newest["date"])
check("出现成功提示", any("已记账" in s.value for s in at.success),
      str([s.value for s in at.success]))

# 验证 clear_on_submit：紧接着"什么都不填"再提交一次，存进去的应该是表单的
# 默认值（金额 1.00 / 餐饮 / 空备注），说明上一次提交后表单确实被清空了
n_after_first = len(db.list_expenses())
find_btn(at, "保存").set_value(True)
at.run()
second = db.list_expenses()[0]
check("再次提交时表单已清空",
      len(db.list_expenses()) == n_after_first + 1
      and second["amount"] == 1.00
      and second["category"] == "餐饮"
      and second["note"] == "",
      f"新记录 = {second['amount']} / {second['category']} / {second['note']!r}")

# 金额精度：number_input 可能返回浮点尾巴，入库前必须 round
at.number_input[0].set_value(0.1 + 0.2)
find_btn(at, "保存").set_value(True)
at.run()
check("浮点尾巴被 round 掉", db.list_expenses()[0]["amount"] == 0.30,
      str(db.list_expenses()[0]["amount"]))

expected_total = sum(r["amount"] for r in db.list_expenses())

print("\n=== 3. 列表筛选 ===")
at2 = fresh()
# selectbox 顺序：[0]=添加页的分类, [1]=列表页月份, [2]=统计页月份
labels = [s.label for s in at2.selectbox]
check("三个下拉框", labels == ["分类", "月份", "月份"], str(labels))
check("月份下拉含「全部」", "全部" in at2.selectbox[1].options, str(at2.selectbox[1].options))
check("月份下拉含实际月份",
      "2026-10" in at2.selectbox[1].options and "2026-09" in at2.selectbox[1].options,
      str(at2.selectbox[1].options))

m_all = [m for m in at2.metric if "合计支出" in m.label][0]
check("全部合计正确", m_all.value == f"¥{expected_total:,.2f}",
      f"{m_all.value} vs ¥{expected_total:,.2f}")

at2.selectbox[1].set_value("2026-09").run()
sep_rows = db.list_expenses(month="2026-09")
m_sep = [m for m in at2.metric if "合计支出" in m.label][0]
check("切到 2026-09 无异常", not at2.exception, str(at2.exception) if at2.exception else "")
check("2026-09 合计正确", m_sep.value == f"¥{sum(r['amount'] for r in sep_rows):,.2f}",
      f"{m_sep.value} vs ¥{sum(r['amount'] for r in sep_rows):,.2f}")
check("2026-09 是 2 笔", len(sep_rows) == 2, str(len(sep_rows)))

at2.multiselect[0].set_value(["餐饮"]).run()
food = db.list_expenses(month="2026-09", categories=["餐饮"])
check("月份+分类组合筛选正确", len(food) == 1 and food[0]["category"] == "餐饮", str(food))

at2.multiselect[0].set_value(["居住"]).run()
check("空结果有提示", any("没有账目" in i.value for i in at2.info),
      str([i.value for i in at2.info]))

print("\n=== 4. 分类统计 ===")
at3 = fresh()
stats = db.stats_by_category()
total = sum(s["total"] for s in stats)
check("统计笔数 = 记录总数", sum(s["cnt"] for s in stats) == len(db.list_expenses()))
check("统计金额 = 列表金额", abs(total - expected_total) < 0.001,
      f"{total} vs {expected_total}")
check("按金额降序",
      [s["total"] for s in stats] == sorted([s["total"] for s in stats], reverse=True),
      str([(s["category"], s["total"]) for s in stats]))
m_total = [m for m in at3.metric if m.label == "总支出"][0]
check("总支出指标正确", m_total.value == f"¥{total:,.2f}", m_total.value)
check("统计表存在（图表有表格替身）", len(at3.table) >= 1)
check("多分类时不显示单柱提示", not any("只筛选出 1 个分类" in c.value for c in at3.caption),
      str([c.value for c in at3.caption]))

oct_stats = db.stats_by_category(month="2026-10")
check("2026-10 有 3 个分类", len(oct_stats) == 3, str([s["category"] for s in oct_stats]))

print("\n=== 5. 单一分类时的退化行为（不画单根柱子）===")
db.add_expense(50.00, "娱乐", "2026-08-05", "演唱会")
at3b = fresh()
at3b.selectbox[2].set_value("2026-08").run()      # 统计页月份
aug = db.stats_by_category(month="2026-08")
check("2026-08 只有 1 个分类", len(aug) == 1, str(aug))
check("出现单分类提示", any("只筛选出 1 个分类" in c.value for c in at3b.caption),
      str([c.value for c in at3b.caption]))
check("单分类时仍有总支出指标", any(m.label == "总支出" for m in at3b.metric))
check("单分类时脚本无异常", not at3b.exception, str(at3b.exception) if at3b.exception else "")

print("\n=== 6. 删除流程 ===")
at4 = fresh()
target = [r for r in db.list_expenses() if r["date"] == "2026-09-20"][0]
n_before = len(db.list_expenses())

at4.number_input[-1].set_value(target["id"]).run()     # delete_id 是最后一个
find_btn(at4, "删除").set_value(True).run()
check("点删除后无异常", not at4.exception, str(at4.exception) if at4.exception else "")
check("出现确认警告", any("确认删除" in w.value for w in at4.warning),
      str([w.value for w in at4.warning]))
check("确认前没有真删", len(db.list_expenses()) == n_before,
      f"{len(db.list_expenses())} vs {n_before}")
check("警告里显示了记录内容", any(target["category"] in w.value for w in at4.warning),
      str([w.value for w in at4.warning]))

find_btn(at4, "取消").set_value(True).run()
check("取消后没删", len(db.list_expenses()) == n_before)
check("取消后确认框消失", not any("确认删除" in w.value for w in at4.warning),
      str([w.value for w in at4.warning]))

at4.number_input[-1].set_value(target["id"]).run()
find_btn(at4, "删除").set_value(True).run()
find_btn(at4, "确认删除").set_value(True).run()
check("确认后真的删了", len(db.list_expenses()) == n_before - 1,
      f"{len(db.list_expenses())} vs {n_before - 1}")
check("删除后无异常", not at4.exception, str(at4.exception) if at4.exception else "")
check("出现删除成功提示", any("已删除" in s.value for s in at4.success),
      str([s.value for s in at4.success]))
check("删除后确认框消失", not any("确认删除" in w.value for w in at4.warning))
check("被删的 ID 查不到了", db.get_expense(target["id"]) is None)

at5 = fresh()
at5.number_input[-1].set_value(9999).run()
find_btn(at5, "删除").set_value(True).run()
check("不存在的 ID 报错", any("没有找到" in e.value for e in at5.error),
      str([e.value for e in at5.error]))
check("不存在的 ID 不进确认流程", not any("确认删除" in w.value for w in at5.warning))

# 残留确认框 + 查一个不存在的 ID：错误提示应取代旧确认框
at6 = fresh()
existing = db.list_expenses()[0]["id"]
at6.number_input[-1].set_value(existing).run()
find_btn(at6, "删除").set_value(True).run()
check("先弹出确认框", any("确认删除" in w.value for w in at6.warning))
at6.number_input[-1].set_value(9999).run()
find_btn(at6, "删除").set_value(True).run()
check("查不存在 ID 后旧确认框被清掉",
      not any("确认删除" in w.value for w in at6.warning),
      str([w.value for w in at6.warning]))
check("同时显示了错误提示", any("没有找到" in e.value for e in at6.error))

print("\n=== 7. 数据落盘持久化 ===")
count_now = len(db.list_expenses())
at7 = fresh()
check("重新加载后数据还在", len(db.list_expenses()) == count_now, f"{count_now} 条")
check("重新加载无异常", not at7.exception, str(at7.exception) if at7.exception else "")

print("\n" + "=" * 60)
if FAIL:
    print(f"失败 {len(FAIL)} 项：")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("全部检查通过")

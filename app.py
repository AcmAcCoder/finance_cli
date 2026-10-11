"""界面层：Streamlit 页面。

这个文件只负责"把数据和控件画到网页上"，所有数据库操作都调用 db.py。
文件里不出现 SQL —— 这样数据出问题时去 db.py 找，显示出问题时在这里找。

启动方式（在项目目录下）：
    .venv/Scripts/python -m streamlit run app.py
"""

from datetime import date

import pandas as pd
import streamlit as st

import db

# set_page_config 必须是脚本里第一个 Streamlit 调用，否则报错
st.set_page_config(page_title="记账本", page_icon="💰", layout="wide")

# 建表。重复调用是安全的，已存在就跳过
db.init_db()

# 图表柱子的颜色。这是数据可视化规范里的"序列色 1"，已用校验脚本确认它在
# Streamlit 的浅色底（#ffffff）和深色底（#0e1117）上都满足 3:1 对比度，
# 所以一个色值两种主题通用。
BAR_COLOR = "#2a78d6"

st.title("💰 记账本")

# 关于标签页顺序：Streamlit 每次交互都会把整个脚本从头到尾重跑一遍，而且
# 四个标签页的代码都会执行（标签只是视觉容器，不是"只有当前标签才运行"）。
# 所以"添加"放第一个标签，加完的账在同一轮渲染里就能出现在下面的列表里，
# 不需要 st.rerun()。同理"删除"放最后一个：删完时列表已经渲染过了，但那一
# 刻你人在删除标签上，看不到那个旧列表；切过去时是新的一轮，数据是新的。
#
# 结论：这四个标签的顺序不要随意调整。
tab_add, tab_list, tab_stats, tab_delete = st.tabs(
    ["添加账目", "账目列表", "分类统计", "删除账目"]
)


# ---------------------------------------------------------------------------
# 标签 1 · 添加账目
# ---------------------------------------------------------------------------
with tab_add:
    # st.form 的作用：表单内的控件改动不会触发脚本重跑，只有点提交按钮才触发
    # 一次。不用 form 的话，你在金额框里每敲一个数字整个页面就重跑一遍。
    # clear_on_submit=True 让提交后输入框自动清空，方便连着记好几笔。
    with st.form("add_form", clear_on_submit=True):
        col_left, col_right = st.columns(2)

        with col_left:
            # min_value 直接在控件层挡掉 0 和负数，不用自己写校验分支
            amount = st.number_input(
                "金额（元）",
                min_value=0.01,
                max_value=999999.99,
                value=1.00,
                step=1.0,
                format="%.2f",
            )
            category = st.selectbox("分类", db.CATEGORIES)

        with col_right:
            # 默认今天，记当天账时不用点日历
            spent_on = st.date_input("日期", value=date.today())
            note = st.text_input("备注", max_chars=100, placeholder="可留空")

        submitted = st.form_submit_button("保存", type="primary")

    # 判断放在 with 块外面，且用 submitted 这个变量 —— 直接写 if st.form_submit_button(...)
    # 会把它渲染到表单下方并破坏布局
    if submitted:
        note = note.strip()
        new_id = db.add_expense(
            round(amount, 2),          # number_input 可能返回 3.0000000000000004 这种值
            category,
            spent_on.isoformat(),      # 得到 'YYYY-MM-DD'，和库里的格式一致
            note,
        )
        detail = f"{spent_on.isoformat()} · {category} · ¥{amount:,.2f}"
        if note:
            detail += f" · {note}"
        st.success(f"已记账 #{new_id}　{detail}")


# ---------------------------------------------------------------------------
# 标签 2 · 账目列表
# ---------------------------------------------------------------------------
with tab_list:
    # 月份选项从数据库里取"实际有账目的月份"，避免下拉框里全是空月份。
    # 标签页之间不会同时显示，所以月份/分类这两个控件在列表和统计里各有一套，
    # 这样每个标签都是自包含的，进来就能用。
    filter_col1, filter_col2 = st.columns([1, 2])

    with filter_col1:
        list_month = st.selectbox("月份", ["全部"] + db.list_months(), key="list_month")

    with filter_col2:
        list_cats = st.multiselect(
            "分类（不选 = 全部）", db.CATEGORIES, key="list_cats"
        )

    rows = db.list_expenses(
        month=None if list_month == "全部" else list_month,
        categories=list_cats or None,
    )

    if not rows:
        st.info("这个条件下没有账目，换个筛选条件试试")
    else:
        total_amount = sum(r["amount"] for r in rows)
        st.metric(
            "合计支出",
            f"¥{total_amount:,.2f}",
            help=f"共 {len(rows)} 笔",
        )

        # SQL 查出来是英文列名（id/amount/...），在这一层改成中文给用户看。
        # 数据库字段名不要动 —— 那是给程序用的。
        df = pd.DataFrame(
            [
                {
                    "ID": r["id"],
                    "日期": r["date"],
                    "分类": r["category"],
                    "金额": r["amount"],
                    "备注": r["note"],
                }
                for r in rows
            ]
        )

        # 金额用 column_config 格式化，而不是在 Python 里转成字符串：
        # 保留数字类型，网页上点列头才能正确按数值排序。转成字符串就变成
        # 字典序了，9.00 会排在 10.00 后面。
        st.dataframe(
            df,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "金额": st.column_config.NumberColumn("金额（元）", format="¥%.2f"),
            },
        )


# ---------------------------------------------------------------------------
# 标签 3 · 分类统计
# ---------------------------------------------------------------------------
with tab_stats:
    stats_month = st.selectbox(
        "月份", ["全部"] + db.list_months(), key="stats_month"
    )

    stats = db.stats_by_category(
        month=None if stats_month == "全部" else stats_month
    )

    if not stats:
        st.info("还没有账目数据，先去「添加账目」记一笔吧")
    else:
        # 因为表结构上有 CHECK (amount > 0)，只要 stats 非空，合计就一定大于 0，
        # 下面的除法不会遇到除零
        total = sum(s["total"] for s in stats)
        total_cnt = sum(s["cnt"] for s in stats)

        st.metric("总支出", f"¥{total:,.2f}", help=f"共 {total_cnt} 笔")

        table_col, chart_col = st.columns([1, 2])

        # 统计表本身就是图表的"无障碍替身"：图表用来看趋势，数值以表格为准
        with table_col:
            table_rows = [
                {
                    "分类": s["category"],
                    "金额（元）": s["total"],
                    "笔数": s["cnt"],
                    "占比": f"{s['total'] / total:.1%}",
                }
                for s in stats
            ]
            table_rows.append(
                {
                    "分类": "合计",
                    "金额（元）": total,
                    "笔数": total_cnt,
                    "占比": "100.0%",
                }
            )
            st.table(pd.DataFrame(table_rows))

        with chart_col:
            if len(stats) >= 2:
                chart_df = pd.DataFrame(
                    [{"分类": s["category"], "金额": s["total"]} for s in stats]
                )
                # 只传一个颜色，不传 color="分类"：
                # 柱子的高度已经表达了金额大小，再按分类上色属于"用颜色做装饰"
                # —— 颜色没承载任何额外信息，反而更难读（还要多配一个图例）。
                # 分类名列已经在 x 轴上，看柱子的位置就知道是哪个分类。
                #
                # 排序：sort 默认 True 表示按金额从大到小，和左边表格的顺序一致。
                st.bar_chart(chart_df, x="分类", y="金额", color=BAR_COLOR)
            else:
                # 只有 1 个分类时，单根柱子不传达任何信息，不如直接看上面的数字
                st.caption("只筛选出 1 个分类，单根柱子看不出对比，直接看左边的数字就够了")


# ---------------------------------------------------------------------------
# 标签 4 · 删除账目
# ---------------------------------------------------------------------------
with tab_delete:
    # 为什么必须用 st.session_state：任何交互都会让整个脚本重跑一遍，普通局部
    # 变量每次都重新初始化，活不过一次重跑；按钮也只在"被点击的那一次重跑"
    # 返回 True。所以"点删除 → 点确认"必然跨两次重跑，能跨重跑记住事情的
    # 只有 st.session_state。读取用 .get() 避免 KeyError。
    #
    # 为什么每个按钮点完都要 st.rerun()：效果类的提示（st.success/st.error）和
    # 确认框都是"边算边画"的 —— 脚本从上往下执行，等执行到按钮、发现你点了它
    # 时，上面的确认框早就画出来了，这一轮改的状态要下一轮才体现。结果是"点了
    # 取消，确认框却还挂在那儿"。先改状态、再 rerun，从头重新画一遍，界面和
    # 状态就永远是一致的。
    #
    # 代价是 rerun 之后本轮画的提示会丢，所以要先把提示存进 session_state
    # （也就是下面这个 delete_flash），rerun 后在顶部取出来显示。这个
    # "存一条消息、跳转后再显示"的写法通常叫 flash 消息。
    flash = st.session_state.pop("delete_flash", None)
    if flash:
        if flash["level"] == "success":
            st.success(flash["message"])
        else:
            st.error(flash["message"])

    st.caption("删除不可恢复。输入 ID 后还需要再确认一次才会真的删掉。")

    delete_id = st.number_input(
        "要删除的账目 ID", min_value=1, value=1, step=1, key="delete_id"
    )

    if st.button("删除", key="delete_btn"):
        target = db.get_expense(int(delete_id))
        if target is None:
            # ID 不存在就清掉可能残留的待确认状态，避免界面自相矛盾
            st.session_state.pop("pending_delete", None)
            st.session_state["delete_flash"] = {
                "level": "error",
                "message": f"没有找到 ID 为 {int(delete_id)} 的记录",
            }
        else:
            # 只记下"待确认"，这里不删。真正的删除在下面确认按钮里
            st.session_state["pending_delete"] = int(delete_id)
        st.rerun()

    pending_id = st.session_state.get("pending_delete")

    if pending_id is not None:
        record = db.get_expense(pending_id)

        if record is None:
            # 记录在别处被删掉了，状态失效，清掉
            st.session_state.pop("pending_delete", None)
        else:
            preview = f"#{record['id']}　{record['date']} · {record['category']} · ¥{record['amount']:,.2f}"
            if record["note"]:
                preview += f" · {record['note']}"
            st.warning(f"确认删除这一笔吗？删除后无法恢复。\n\n{preview}")

            confirm_col, cancel_col = st.columns([1, 4])

            if confirm_col.button("确认删除", type="primary", key="confirm_delete_btn"):
                # 先 pop 取出 ID 并清掉状态，再执行删除
                deleted = db.delete_expense(st.session_state.pop("pending_delete"))
                st.session_state["delete_flash"] = {
                    "level": "success" if deleted else "error",
                    "message": (
                        f"已删除 #{record['id']}"
                        if deleted
                        else "删除失败，这条记录可能已经被删掉了"
                    ),
                }
                st.rerun()

            if cancel_col.button("取消", key="cancel_delete_btn"):
                st.session_state.pop("pending_delete", None)
                st.rerun()

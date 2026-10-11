# 记账本

一个跑在自己电脑上的记账工具。记支出，按月份和分类查，看分类花了多少。

技术栈：Python + Streamlit + SQLite。数据全部存在本地 `finance.db` 文件里，不联网、不上传。

---

## 怎么运行

> **先看你用的是哪个终端。**下面两套写法只差斜杠方向，但搞混了会报
> `'.venv' 不是内部或外部命令`。
> - 提示符长这样 `E:\VScode\AiCoding\finance_cli>` 的是 **cmd**，用**反斜杠** `\`
> - 提示符长这样 `user@PC MINGW64 /e/VScode/...$` 的是 **Git Bash**，用**正斜杠** `/`

### 第一次运行（只需做一次）

**cmd：**

```cmd
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Git Bash：**

```bash
py -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

### 日常运行

**最简单的方式：直接双击项目里的 `run.bat`。** 它会自己切到项目目录、启动服务。

想手敲的话：

**cmd：**

```cmd
.venv\Scripts\python.exe -m streamlit run app.py
```

**Git Bash：**

```bash
.venv/Scripts/python -m streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`。**按 `Ctrl+C` 停止。**

> ⚠️ **不要直接敲 `python`。** 你电脑上 PATH 里的 `python` 是 msys64 自带的，没有 pip，会报 `No module named pip`。用 `py`，或者上面 `.venv\Scripts\` 里的那个完整路径。

---

## 文件说明

| 文件 | 作用 |
|---|---|
| `db.py` | **数据层**。建表、增删查、统计。所有 SQL 都在这里 |
| `app.py` | **界面层**。四个标签页，只负责显示，不写 SQL |
| `test_app.py` | 自动测试，跑一遍能确认没改坏已有功能 |
| `run.bat` | 双击启动。**注意这个文件必须保持纯英文**，见下方说明 |
| `requirements.txt` | 依赖清单 |
| `finance.db` | 你的账本数据（自动生成，不要手动改，也不要提交到 git） |
| `.streamlit/config.toml` | 运行配置（只监听本机、首次启动不弹邮箱提示） |
| `.venv/` | 虚拟环境，装依赖用的，删了可以重建 |

为什么拆成两个文件：**数据出问题就去 `db.py` 找，显示出问题就在 `app.py` 找**，不用在一大坨代码里猜。而且 `db.py` 能脱离浏览器单独测。

---

## 四个功能

1. **添加账目** —— 填金额、分类、日期、备注，点保存。日期默认今天。
2. **账目列表** —— 按月份和分类筛选，表格展示，带合计。
3. **分类统计** —— 柱状图 + 统计表（含金额、笔数、占比）。
4. **删除账目** —— 输入 ID，**再确认一次**才会真的删。

预设分类：餐饮、交通、购物、娱乐、居住、其他。

---

## 常用操作

### 想加一个分类（比如"医疗"）

打开 `db.py`，改这一行：

```python
CATEGORIES = ["餐饮", "交通", "购物", "娱乐", "居住", "其他"]
```

加上 `"医疗"` 就行，不用动数据库。**改完记得重启服务**（`Ctrl+C` 再重新运行）。

### 改完代码，想知道有没有改坏

```cmd
.venv\Scripts\python.exe test_app.py
```

（Git Bash 用 `.venv/Scripts/python test_app.py`）

它用 Streamlit 官方的测试框架，在命令行里把 50 项功能全模拟跑一遍：填表单、切月份、选分类、走完删除的两次确认。**用临时数据库，不会碰你的 `finance.db`。**

改完 `app.py` 或 `db.py` 后跑一下，比在浏览器里手点一遍快得多，也不会漏掉边界情况。最后一行打印"全部检查通过"就说明没改坏。

### 想看 `db.py` 本身有没有问题

**cmd：**

```cmd
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe -X utf8 db.py
```

**Git Bash：**

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python -X utf8 db.py
```

会在终端跑一遍增、查、统计、删除的完整测试，用临时数据库，**不会碰你的真实账本**。

> `PYTHONIOENCODING=utf-8` 和 `-X utf8` 是为了让中文在终端正常显示。不加的话 Windows 控制台会输出乱码（只是显示问题，数据本身没错）。

### 数据备份

直接复制 `finance.db` 这个文件就行，它就是全部数据。建议偶尔复制一份到别的地方。

### 想从头开始（清空所有数据）

1. 先 `Ctrl+C` 停掉服务
2. 删掉 `finance.db`
3. 重新运行，会自动生成一个空账本

**必须先停服务**——运行中的进程占着这个文件，Windows 下删不掉，会提示"文件被占用"。

---

## 遇到问题

| 现象 | 原因和处理 |
|---|---|
| `'.venv' 不是内部或外部命令` | 你在 **cmd** 里用了正斜杠 `/`。cmd 用反斜杠 `\`，Git Bash 用正斜杠 `/` |
| `No module named pip` | 你用了 `python` 命令。改用 `py`，或 `.venv\Scripts\python.exe`（Git Bash 是 `.venv/Scripts/python`） |
| `run.bat` 双击后满屏 `不是内部或外部命令` | 这文件被存成 UTF-8 了，而 cmd 用 GBK 读 .bat，中文注释乱码后会把行粘在一起。**`run.bat` 必须保持纯英文**，中文说明写到 README 里 |
| 端口被占用 | Streamlit 会自动换到 8502，**以终端打印的地址为准**；也可以加 `--server.port 8502` |
| 改了 `db.py` 页面没反应 | 刷新浏览器；还不行就 `Ctrl+C` 重启服务 |
| 终端中文乱码 | 加 `PYTHONIOENCODING=utf-8` 和 `-X utf8`（cmd 里先单独执行 `set PYTHONIOENCODING=utf-8`） |
| `DuplicateWidgetID` 报错 | 两个控件的 label 重名了，给其中一个加 `key="xxx"` |

---

## 代码里的几个关键约定

改代码前值得先看一眼这几条，能避掉大部分坑：

- **日期一律存 `'YYYY-MM-DD'` 字符串**（`'2026-10-11'`）。这样字符串排序就等于时间排序，按月份筛选用 `LIKE '2026-10%'`。别存 `2026/10/11`，那样筛不出月份。
- **SQL 的值永远走 `?` 占位符**，不拼字符串。`IN` 子句没有"传列表"的写法，要自己生成 N 个 `?`。
- **金额存 `REAL`**，入库前 `round(x, 2)`，统计时 `ROUND(SUM(...), 2)`，显示用 `f"{x:,.2f}"`。浮点数累加会有 `300.00000000000006` 这种尾巴，这三步能把它收干净。
- **数据库连接每次用完就关**（`db.py` 里的 `connect()`），不做全局缓存。缓存的连接会一直占着文件句柄，想删库重来就删不掉了。
- **不要用 `use_container_width` 参数**。它已弃用，官方原定 2025-12-31 后移除。直接用 `width="stretch"`，或者不传（默认就是撑满）。
- **`app.py` 里四个标签页的顺序不要随意调整**。Streamlit 每次交互都会把整个脚本从头跑到尾，四个标签的代码都会执行。顺序决定了"写操作"和"读操作"谁先谁后。

---

## 暂时没做的功能

编辑已有账目、记录收入算结余、导出 CSV、自定义分类、预算提醒、多用户。

这些都不难加，结构上留好位置了。

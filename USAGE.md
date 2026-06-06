# 项目使用说明 — marshal 稳定性测试套件

**第 15 小组** · 软件测试期末大作业
**仓库地址：** https://github.com/Xu-ziang13/marshal-stability-tests

---

## 一、项目简介

这是一个针对 Python `marshal` 模块的**黑盒 + 白盒测试套件**，回答核心问题：
> **同样的输入是否总是产生 hash 完全一致的输出？**

测试套件包含 **654 个测试用例**，覆盖：
- 等价类划分、边界值分析
- 浮点特殊值（NaN/Inf/-0.0）
- 跨进程确定性（PYTHONHASHSEED）
- 循环引用、深度极限
- 白盒类型码覆盖（marshal.c 中的 `TYPE_*` 分支）
- 模糊测试（随机生成对象）

**核心发现：** 字符串 set/frozenset 在不同进程中产生**不同字节**（F1），但整数 set 稳定（F2）。这是由 Python 的 hash 随机化（PYTHONHASHSEED）引起的。

---

## 二、环境要求

- **Python 3.6+**（建议 3.9+，项目在 CPython 3.9.6 上测试）
- **操作系统：** macOS / Linux / Windows（跨平台，但主要在 macOS 上验证）
- **依赖：** 只需 `pytest`（核心依赖），`hypothesis`（可选，用于更强的模糊测试）

---

## 三、快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/Xu-ziang13/marshal-stability-tests.git
cd marshal-stability-tests
```

### 2. 安装依赖

**最小安装（只需 pytest）：**
```bash
pip3 install pytest
```

**完整安装（含 hypothesis 模糊测试库）：**
```bash
pip3 install -r requirements.txt
```

> 💡 如果没有 `hypothesis`，`test_fuzz.py` 会自动退回到内置的确定性随机生成器，不影响运行。

### 3. 运行全部测试

```bash
python3 -m pytest -q
```

**预期输出：**
```
........................................................................ [ 11%]
........................................................................ [ 22%]
...（省略）...
........................................................................ [ 99%]
......                                                                   [100%]
654 passed in 0.53s
```

> ✅ `654 passed` = 所有测试通过
> ⚠️ 如果看到 `FAILED`，说明你的 Python 版本或环境与预期行为不同（这本身也是有价值的发现）。

---

## 四、查看测试结果的不同方式

### 方式 1：运行单个测试模块（了解具体内容）

```bash
# 只运行确定性测试（F1/F2 发现所在）
python3 -m pytest tests/test_determinism.py -v

# 只运行浮点边界值测试
python3 -m pytest tests/test_floats.py -v

# 只运行模糊测试
python3 -m pytest tests/test_fuzz.py -v
```

`-v` 参数会显示每个测试的名字和结果，方便看懂在测什么。

### 方式 2：生成详细的测试报告

```bash
python3 -m pytest --tb=short -v > test_results.txt
cat test_results.txt
```

这会把所有测试名称和通过/失败信息保存到文件，可以提交或分享。

### 方式 3：查看代码覆盖率（可选，需要安装 coverage）

```bash
pip3 install pytest-cov
python3 -m pytest --cov=src --cov-report=html
open htmlcov/index.html   # macOS 打开浏览器查看覆盖率报告
```

> ⚠️ 注意：marshal 本身是 C 扩展，我们只能覆盖测试辅助代码（`src/marshal_testkit.py`），而不是 CPython 核心。白盒覆盖是通过**手动识别类型码分支**实现的（见 `tests/test_typecodes.py`）。

---

## 五、重现关键发现（F1 ~ F9）

我们提供了**独立脚本**来演示 9 个核心发现，无需运行全部测试套件。

### 运行所有发现的证据脚本

```bash
python3 findings/run_all_findings.py
```

**输出示例：**
```
interpreter : CPython 3.9.6 on Darwin
marshal.version (default) : 4

============================================================
F1/F2  set ordering vs PYTHONHASHSEED
============================================================
  string-set distinct digests over 6 seeds: 6 (NON-DETERMINISTIC)
  int-set    distinct digests over 6 seeds: 1 (stable)

============================================================
F3  dict insertion-order sensitivity
============================================================
  {1,2} == {2,1} (logical): True
  bytes equal: False

...（F4 ~ F9 的具体证据）...
```

### 单独重现 F1（最重要的发现）

```bash
python3 findings/f1_set_hashseed.py
```

**输出：**
```
PYTHONHASHSEED  string-set digest   int-set digest
----------------------------------------------------
0               affb5aec9ee10e09   7b9d4189b59f309e
1               ea027e95c060ee7f   7b9d4189b59f309e
2               71539a927df1c723   7b9d4189b59f309e
...（6 个不同的 string-set 摘要，int-set 摘要全部相同）...
----------------------------------------------------
distinct string-set digests: 6 -> NON-DETERMINISTIC
distinct int-set digests:    1 -> STABLE
```

这就是**核心 bug 类**：字符串集合的序列化输出依赖于进程启动时的随机种子。

---

## 六、项目结构说明

```
.
├── README.md                   # 项目总览
├── report/report.md            # 最终报告（策略、矩阵、发现、局限）
├── requirements.txt            # 依赖列表
├── pytest.ini                  # pytest 配置
├── conftest.py                 # 测试启动配置（把 src 加到路径）
│
├── src/
│   └── marshal_testkit.py      # 共享工具：digest()、稳定性检查、语料库
│
├── tests/                      # 测试套件主体（654 个测试）
│   ├── test_determinism.py     # F1/F2/F3：进程内外稳定性、set/dict 顺序
│   ├── test_roundtrip.py       # 正确性：loads(dumps(x)) == x
│   ├── test_floats.py          # F4/F5：浮点边界、特殊值、bit-exact
│   ├── test_collections.py     # 空/大集合、类型区分
│   ├── test_recursive.py       # F6/F7：循环引用、FLAG_REF、深度
│   ├── test_versions.py        # F8：跨版本格式稳定性
│   ├── test_typecodes.py       # 白盒：每个 TYPE_* 分支一个用例
│   └── test_fuzz.py            # F9：随机对象模糊测试
│
└── findings/                   # 独立脚本，重现 9 个发现
    ├── f1_set_hashseed.py      # 演示 F1（字符串 set 非确定性）
    └── run_all_findings.py     # 一键输出所有发现的证据
```

---

## 七、常见问题

### Q1：我运行测试时看到一些测试失败了，怎么办？

**A：** 这可能是正常的！原因：
- 如果你的 Python 版本不是 3.9，marshal 格式版本可能不同（比如 Python 3.11 可能是 version 5）
- 我们的测试 **故意硬编码了观察到的行为**（比如 F8 断言 v3/v4 输出相同），如果 CPython 改了实现，测试会捕获到
- 失败本身也是有价值的测试结果 —— 说明不同环境下行为确实有差异

### Q2：我没有 pytest，能不能直接运行 Python 文件？

**A：** 不行。测试用例使用了 pytest 的 `@pytest.mark.parametrize` 等特性，必须通过 pytest 运行。安装很简单：
```bash
pip3 install pytest
```

### Q3：报告在哪里？需要导出 PDF 吗？

**A：** 报告在 `report/report.md`（Markdown 格式）。如果作业要求 PDF：
- macOS: 用 Typora / MacDown 打开后导出 PDF
- 在线工具：https://www.markdowntopdf.com/
- 命令行（需要 pandoc）：
  ```bash
  pandoc report/report.md -o report.pdf
  ```

### Q4：如何验证代码符合 PEP 8 规范？

```bash
pip3 install pycodestyle
python3 -m pycodestyle --max-line-length=79 src tests findings conftest.py
```

如果没有输出 = 全部符合规范（我们的代码已经验证过了）。

### Q5：我想修改测试或添加新用例，怎么做？

1. 编辑对应的 `tests/test_*.py` 文件
2. 运行 `python3 -m pytest tests/test_你修改的文件.py -v` 验证
3. 提交前确保全部测试通过：`python3 -m pytest -q`

---

## 八、给组员的检查清单

运行以下命令，确认项目在你的环境正常：

```bash
# 1. 克隆仓库
git clone https://github.com/Xu-ziang13/marshal-stability-tests.git
cd marshal-stability-tests

# 2. 安装依赖
pip3 install pytest

# 3. 运行全部测试（应该看到 654 passed）
python3 -m pytest -q

# 4. 重现关键发现（F1 非确定性）
python3 findings/f1_set_hashseed.py

# 5. 查看报告
cat report/report.md   # 或用 Markdown 阅读器打开

# 6. 验证 PEP 8（可选）
pip3 install pycodestyle
python3 -m pycodestyle --max-line-length=79 src tests findings conftest.py
```

全部通过 = 你的环境没问题。

---

## 九、汇报/演示时的重点

如果需要演示这个项目（答辩/演讲），可以强调：

1. **真实发现，不是编的**：用 `findings/f1_set_hashseed.py` 现场跑，6 个种子产生 6 个不同摘要 → 非确定性的直接证据
2. **测试技术多样性**：EP、BVA、fuzzing、differential testing、白盒类型码覆盖 → 展示 `tests/` 里不同模块的职责
3. **可复现**：代码在 GitHub 公开，任何人克隆下来都能跑出 654 passed
4. **工程质量**：PEP 8 干净、清晰的模块结构、独立的 findings 脚本、完整的报告

**演示流程（3 分钟）：**
```bash
# 1. 显示测试通过
python3 -m pytest -q   # 654 passed

# 2. 演示关键发现
python3 findings/f1_set_hashseed.py   # 6 个不同摘要

# 3. 解释一个测试用例
cat tests/test_determinism.py   # 拉到 test_string_set_nondeterministic_across_hashseeds
```

---

## 联系方式

如果有任何问题，联系组长 **Wang Chengyi** 或任一组员。

**祝答辩顺利！🎉**

# 回归检查与示例

在仓库根目录运行 `python3 tests/test_coverage.py`，使用 Git 与 Python 3.8 或更新版本。脚本在系统临时目录创建自用 Git 仓库，测试固定版本、逐行对账、错误与边界处理，并输出结果和临时目录位置。

[日历示例](fixtures/calendar/README.md) 是专供审查试用的小型虚构产品。它有产品约定、命令入口、已有单测和一个规划中的功能。可在独立审查区使用该示例练习验收，再查看[实际试用记录](../验证记录.md)和[同一时刻的时区比较](evidence/calendar-comparison.json)。已有单测与产品契约各自能证明什么，可以在示例中亲自对照。

复演“选 B，交给原开发 AI”时，保留一份原日历作为基线。在另一个独立副本中应用[本轮修复与回归测试](calendar-round.patch)，再用相同输入运行两份产品的命令入口。[复验数据与实际结果](evidence/roundtrip-results.json)记录了固定版本、样例、预期、实际结果及退出码。

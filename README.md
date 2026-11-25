# AI Development OS V3.2

给 Codex 和 Claude Code 使用的通用研发质量工作流。给它一个产品仓库的链接，可以从逐文件盘点开始，连续审查适用环节，也可以只做一次专项或接着上次的进度。开发中的产品、已完成的产品和已有目录较乱的项目都可以接入。

## 平时怎么用

1. 把[完整提示词](ai-development-os/给原开发AI的提示词.txt)发给当前产品的开发 AI。它会更新对应仓库，或在确实没有仓库时新建私有库，并核实远端的产品版本。
2. 在能读到此 Skill 和产品仓库的新聊天里，发回执顶部的启动句或整份归档回执。接收者自动打开 16 个模块，核验固定版本，遇到项目特有任务继续加查。
3. 读聊天中的 16 行看板和完整产品报告，每一项有结论、证据与具体改法。按建议的先后顺序挑一批，选 A 只要建议、B 给原开发 AI 一张任务单、C 由当前 Codex 直接开发。
4. 选 B 时，整批只需把开发者生成的一个复验块转发回来。审查者对比原版与候选，逐条关闭、返工或保留待证。选 C 时由当前 Codex 接续。[批次任务单和返回格式](ai-development-os/templates/DEVELOPMENT_ROUND.md)

## 项目导航

| 想做什么 | 从这里开始 |
| --- | --- |
| 获取可移植包，或在另一台电脑配置 | [下载 V3.2 ZIP](AI-Development-OS-V3.2.zip) · [使用说明](ai-development-os/README.md) |
| 查阅工作流和选择专项 | [SKILL.md 与全部模块](ai-development-os/SKILL.md) |
| 独立复制提示词与使用模板 | [16 个模块](ai-development-os/references/) · [22 份可选模板](ai-development-os/templates/) |
| 核对仓库的阅读覆盖 | [本地清单工具](ai-development-os/scripts/repo_coverage.py) |
| 对账每一项审查并生成离线 HTML 看板 | [报告模板](ai-development-os/templates/AUDIT_REPORT.md) · [看板工具](ai-development-os/scripts/check_audit.py) |
| 查看交付依据或复跑示例 | [验证记录](验证记录.md) · [回归检查与示例](tests/README.md) |

工作流保存在本仓库。各产品继续使用自己的源码、文档、素材和 README。个人级安装供同一台电脑上的 Codex 项目复用。

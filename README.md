# AI Development OS V3.1

给 Codex 和 Claude Code 使用的通用研发质量工作流。给它一个产品仓库的链接，可以从逐文件盘点开始，连续审查适用环节，也可以只做一次专项或接着上次的进度。开发中的产品、已完成的产品和已有目录较乱的项目都可以接入。

## 平时怎么用

1. 把[完整提示词](ai-development-os/给原开发AI的提示词.txt)发给当前产品的开发 AI。它会更新对应仓库，或在确实没有仓库时新建私有库，并核实远端的产品版本。
2. 复制它回复顶部以 `$ai-development-os` 开头的一行。在安装了此 Skill 且能访问产品仓库的本机 Codex 新聊天中粘贴发送。其中的链接应指向你要审的产品提交。
3. 读首审报告，选 A 只要建议、B 生成给原开发 AI 的任务单，或 C 由当前 Codex 直接开发。可指定要改的问题。
4. 选 B 时，把原开发 AI 改完后给你的复验块转发回来。Codex 按原任务对比两个版本，逐项验证并给出结果。选 C 时，这段衔接由当前 Codex 完成。[任务单和返回格式](ai-development-os/templates/DEVELOPMENT_ROUND.md)

## 项目导航

| 想做什么 | 从这里开始 |
| --- | --- |
| 获取可移植包，或在另一台电脑配置 | [下载 ZIP](AI-Development-OS-V3.1.zip) · [使用说明](ai-development-os/README.md) |
| 查阅工作流和选择专项 | [SKILL.md 与全部模块](ai-development-os/SKILL.md) |
| 独立复制提示词与使用模板 | [16 个模块](ai-development-os/references/) · [22 份可选模板](ai-development-os/templates/) |
| 核对仓库的阅读覆盖 | [本地清单工具](ai-development-os/scripts/repo_coverage.py) |
| 查看交付依据或复跑示例 | [验证记录](验证记录.md) · [回归检查与示例](tests/README.md) |

工作流保存在本仓库。各产品继续使用自己的源码、文档、素材和 README。个人级安装供同一台电脑上的 Codex 项目复用。

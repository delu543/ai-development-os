# 参与 AI Development OS

最有帮助的贡献通常来自一次真实的使用摩擦。一个宣传“已修复”的候选仍会丢数据、一份报告把没测的内容写成通过、某个入口让新用户无法继续，都可以用来改进这个工作流。请把案例缩减为可公开的合成输入。[提交普通问题或改进建议](https://github.com/delu543/ai-development-os/issues/new/choose)

## 提交反馈

写明 Skill 版本、宿主工具、你给的请求、期待的结果和实际结果。能定位到模块编号、稳定的测试输入或脱敏后的报告行，会更容易复核。涉及凭据、隐私或可能影响使用者安全的问题，请使用私密入口。[安全报告说明](SECURITY.md)

## 提交修改

1. 从自己的分支或 fork 修改。总入口在 `ai-development-os/SKILL.md`，专项说明在 `references/`，公共表单在 `templates/`，可执行工具在 `scripts/`。这三个目录都位于 `ai-development-os/` 内。
2. 改提示词时，说明哪类用户输入原来会导致什么错误，改后应出现什么可观察的结果。涉及验收和报告格式时，提供一个应该通过以及一个应该被拦下的最小示例。
3. 从仓库根目录运行以下检查。在 PR 中写明运行环境、结果和剩余边界。仅改文案时，至少核对受影响的链接和用法。

```sh
python3 tests/test_coverage.py
python3 tests/test_audit_report.py
python3 scripts/check_distribution.py
```

许可证、发布包和示例也受检查。发布包只收录 Git 已跟踪的 Skill 文件，含与根目录相同的许可证。在干净的发布提交下运行下面的命令，可得到安装 ZIP、离线示例和二者的 SHA-256 清单。已有同名文件且内容不同时，请选择新的输出目录。[版本记录](CHANGELOG.md)

```sh
python3 scripts/check_distribution.py --output-dir dist
```

请提交你有权按本项目 MIT 条款分享的内容。引入第三方材料时，请在 PR 中提供来源、版本、许可证及需要保留的声明。这里接受中文或英文 Issue 和 PR。[MIT 许可证](LICENSE) · [社区行为准则](CODE_OF_CONDUCT.md)

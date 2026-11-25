"""Regression tests for review completeness, evidence links and the HTML snapshot."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ai-development-os/scripts/check_audit.py"
spec = importlib.util.spec_from_file_location("audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def md_table(headers, data):
    return "\n".join("| " + " | ".join(r) + " |" for r in [headers, ["---"] * len(headers), *data])


def report(rows, extra=None):
    head = ["编号", "模块", "执行状态", "验收结论", "实际检查与观察", "证据编号", "下一步"]
    extras = md_table(head, extra) if extra else "产品只有本地输入输出，已有专项覆盖该承诺。依据 E-01。"
    return "\n\n".join([
        "# 示例", "## 16 项核验", md_table(head, rows),
        "## 核心用户旅程和专项", md_table(["用户", "维度", "入口", "实测", "判定"],
                                         [["操作者", "输出", "本地", "从正常入口读回一行", "通过，E-01"]]),
        "## 项目追加专项", extras, "## 问题、优化机会与待查问题", "已选用例无新增问题。保留输入与输出。",
        "## 证据索引", md_table(["编号","位置","事实"], [["E-01","固定候选的本地日志","输入一行，读回一行"]]),
        "## 收口", "覆盖结论以固定候选及本地结果为界。"])


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.rows = [[f"{i:02d}", name, "已执行", "通过", "从入口读回测试结果", "E-01", "保留用例"]
                     for i, name in enumerate(audit.MODULES)]

    def test_all_modules_present(self):
        self.assertEqual(len(audit.review(report(self.rows))[1]), 16)

    def test_missing_duplicate_out_of_order_and_swapped_names(self):
        for rows in [self.rows[1:], self.rows + [self.rows[-1]],
                     [self.rows[1], self.rows[0], *self.rows[2:]]]:
            with self.assertRaises(ValueError):
                audit.review(report(rows))
        self.rows[0][1] = self.rows[1][1]
        with self.assertRaises(ValueError):
            audit.review(report(self.rows))

    def test_evidence_placeholder_and_inconsistent_status(self):
        for col, value in [(5, "E-99"), (4, "〔待填写〕"), (2, "待做"), (2, "不适用"), (2, "部分执行")]:
            with self.subTest(col=col, value=value):
                rows = [list(r) for r in self.rows]
                rows[7][col] = value
                with self.assertRaises(ValueError):
                    audit.review(report(rows))

    def test_not_applicable_requires_support_and_future_condition(self):
        self.rows[3][2:] = ["不适用", "不适用", "该版本只提供离线接口", "E-01", "增加界面后重启"]
        audit.review(report(self.rows))
        self.rows[3][-1] = "无"
        with self.assertRaises(ValueError):
            audit.review(report(self.rows))

    def test_empty_template_and_archive_only_fail_as_full_report(self):
        for body in [(ROOT / "ai-development-os/templates/AUDIT_REPORT.md").read_text(), "三个文件已对账，测试通过。"]:
            with self.assertRaises(ValueError):
                audit.review(body)

    def test_safe_offline_cards_and_evidence_anchors(self):
        parts, ledger = audit.review(report(self.rows))
        rendered = audit.dashboard(parts, ledger)
        self.assertEqual(rendered.count("<article "), 16)
        self.assertIn('href="#proof-E-01"', rendered)
        self.assertIn('id="proof-E-01"', rendered)
        self.assertNotIn("javascript:", audit.inline("[x](javascript:alert)"))
        self.assertIn("&lt;script&gt;", audit.inline("<script>"))

    def test_extra_scope_and_its_open_state_reach_cli(self):
        extra = [["X01","用户特有承诺","受阻","未验证","缺目标设备","待取证","取得测试设备后验证"]]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source, dest = base/"review.md", base/"result.html"
            source.write_text(report(self.rows, extra))
            res = subprocess.run([sys.executable, str(SCRIPT), str(source), "--html", str(dest)],
                                 capture_output=True, text=True)
            self.assertEqual(res.returncode, 1, res.stderr)
            self.assertIn('"open": ["X01"]', res.stdout)
            self.assertIn("用户特有承诺", dest.read_text())
            orig = dest.read_bytes()
            repeat = subprocess.run([sys.executable, str(SCRIPT), str(source), "--html", str(dest)], capture_output=True)
            self.assertEqual(repeat.returncode, 2)
            self.assertEqual(dest.read_bytes(), orig)
        extra[0][0] = "X03"
        with self.assertRaises(ValueError):
            audit.review(report(self.rows, extra))


if __name__ == "__main__":
    unittest.main()

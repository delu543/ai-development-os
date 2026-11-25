"""Check a full review's module ledger and render a local self-contained dashboard."""
import argparse
from collections import Counter
import html
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit


STATES = ("已执行", "部分执行", "受阻", "待做", "不适用", "后续阶段")
RESULTS = ("通过", "未通过", "部分通过", "未验证", "不适用")
PENDING = {"部分执行", "受阻", "待做"}
LEDGER = "16 项核验"
EXTRA = "项目追加专项"
EVIDENCE = "证据索引"
EID = r"E-[0-9]+"
MODULES = ("仓库接入", "研发总控", "产品全维度审计", "UI/UX", "算法与核心技术", "验收契约",
           "基线与需求追踪", "工程门禁", "AI Evals", "安全与隐私", "兜底 V1", "兜底 V2",
           "GitHub 交接", "跨模型核验", "发布运维与回滚", "真实用户价值")


def sections(body):
    result = {"": []}
    current = ""
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            if current in result:
                raise ValueError("章节重复 " + current)
            result[current] = []
        else:
            result[current].append(line)
    return result


def cells(line):
    return [v.strip().replace(r"\|", "|") for v in re.split(r"(?<!\\)\|", line.strip()[1:-1])]


def table(lines):
    return [cells(s) for s in lines if s.strip().startswith("|") and s.strip().endswith("|")]


def filled(row):
    return all(value and value not in {"-", "…", "无记录"} and "〔" not in value for value in row)


def review(body):
    parts = sections(body)
    for key in (LEDGER, EXTRA, "核心用户旅程和专项", "问题、优化机会与待查问题", EVIDENCE, "收口"):
        if key not in parts:
            raise ValueError("缺少章节 " + key)
    records = table(parts[EVIDENCE])[2:]
    sources = set()
    for row in records:
        if len(row) != 3 or not re.fullmatch(EID, row[0]) or not filled(row) or row[0] in sources:
            raise ValueError("证据索引须有唯一编号、可复核位置与事实")
        sources.add(row[0])
    ledger = table(parts[LEDGER])[2:]
    if [r[0] for r in ledger] != ["%02d" % i for i in range(16)]:
        raise ValueError("全流程报告须按 00 至 15 顺序逐项登记，缺号、重复或乱序均须改正")
    if any(len(r) < 2 or r[1] != MODULES[i] for i, r in enumerate(ledger)):
        raise ValueError("模块名称与 00 至 15 的编号不对应")
    extra = table(parts[EXTRA])[2:]
    if [r[0] for r in extra] != ["X%02d" % i for i in range(1, len(extra) + 1)]:
        raise ValueError("项目追加专项使用 X01 起的连续编号")
    if not extra:
        reason = " ".join(s.strip() for s in parts[EXTRA] if not s.startswith("|")).strip()
        if not reason or "〔" in reason or not (set(re.findall(EID, reason)) & sources):
            raise ValueError("无追加专项时写明范围依据并引用证据")
    for row in ledger + extra:
        if len(row) != 7 or not filled(row):
            raise ValueError(row[0] + " 缺少实际动作、结论、证据或下一步")
        idx, _, state, result, _, refs, followup = row
        if state not in STATES or result not in RESULTS:
            raise ValueError(idx + " 执行状态或验收结论无效")
        no_test = state in {"受阻", "待做", "后续阶段"}
        if (no_test and result != "未验证") or (state == "不适用") != (result == "不适用"):
            raise ValueError(idx + " 执行状态与验收结论冲突")
        if state == "部分执行" and result == "通过":
            raise ValueError(idx + " 仍有缺口时不能把整项判为通过")
        if idx in {"00", "01", "02"} and state in {"不适用", "后续阶段"}:
            raise ValueError(idx + " 是全流程首审的必要环节")
        if state != "已执行" and followup in {"无", "无缺口", "无后续"}:
            raise ValueError(idx + " 需要具体边界、补证或重新评估条件")
        if state in {"待做", "受阻"} and refs == "待取证":
            continue
        ids = re.findall(EID, refs)
        if not ids or set(ids) - sources or re.sub(EID, "", refs).strip(" ,，、/"):
            raise ValueError(idx + " 证据编号缺失、格式错误或无法在证据索引定位")
    journeys = table(parts["核心用户旅程和专项"])[2:]
    if not journeys or not all(len(r) == 5 and filled(r) for r in journeys):
        raise ValueError("请逐一填写核心旅程的实际证据，未测的写明缺口")
    for key in ("问题、优化机会与待查问题", "收口"):
        content = "\n".join(parts[key]).strip()
        if not content or "〔" in content or not any(s.strip() and not s.startswith("|") for s in parts[key]):
            raise ValueError("请填写实际结果或明确写出零项及其范围 " + key)
    return parts, ledger


def inline(value):
    """Render plain text and safe Markdown evidence links only."""
    chunks = []
    end = 0
    for match in re.finditer(r"\[([^\]\n]+)\]\(([^)\s]+)\)", value):
        chunks.append(html.escape(value[end:match.start()]))
        label, url = match.groups()
        parts = urlsplit(url)
        safe = parts.scheme == "https" or (not parts.scheme and not url.startswith(("/", "\\")) and "\\" not in url)
        if safe:
            chunks.append('<a href="{}">{}</a>'.format(html.escape(url, quote=True), html.escape(label)))
        else:
            chunks.append(html.escape(label))
        end = match.end()
    chunks.append(html.escape(value[end:]))
    return "".join(chunks)


def prose(lines):
    output = []
    in_table = False
    for s in lines + [""]:
        if s.startswith("|") and s.rstrip().endswith("|"):
            row = cells(s)
            if all(re.fullmatch(r":?-{3,}:?", v) for v in row):
                continue
            cell = "td" if in_table else "th"
            if not in_table:
                output.append('<div class="scroll"><table>')
                in_table = True
            anchor = ' id="proof-{}"'.format(row[0]) if re.fullmatch(EID, row[0]) else ""
            output.append("<tr" + anchor + ">" + "".join("<{0}>{1}</{0}>".format(cell, inline(v)) for v in row) + "</tr>")
        else:
            if in_table:
                output.append("</table></div>")
                in_table = False
            if s.strip() and not s.startswith("# "):
                output.append("<p>" + inline(s.strip()) + "</p>")
    return "".join(output)


def dashboard(parts, ledger):
    title = next((s[2:].strip() for s in parts[""] if s.startswith("# ")), "产品审查")
    tone = {"未通过": "bad", "部分通过": "part", "通过": "good", "未验证": "unknown", "不适用": "quiet"}
    cards = []
    for idx, name, state, verdict, finding, refs, next_step in ledger:
        refs_html = re.sub(EID, lambda m: '<a href="#proof-{0}">{0}</a>'.format(m[0]), html.escape(refs))
        cards.append('<article class="{}"><header><small>{} · {}</small><b>{}</b></header><h3>{}</h3>'
                     '<p>{}</p><p><strong>下一步</strong> {}</p><footer>证据 {}</footer></article>'.format(
                         tone[verdict], idx, html.escape(state), verdict, html.escape(name),
                         inline(finding), inline(next_step), refs_html))
    groups = []
    for heading, lines in parts.items():
        if heading and heading != LEDGER:
            groups.append('<section><h2>{}</h2>{}</section>'.format(html.escape(heading), prose(lines)))
    style = """
    :root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f7f7f3;color:#1b2925;
    font:16px/1.6 Inter,'PingFang SC','Microsoft YaHei',system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:32px 22px 64px}
    h1{font-size:clamp(26px,4vw,42px);line-height:1.25}h2{margin:32px 0 12px}h3,p{margin:8px 0}
    p,h1,h2,h3,footer{overflow-wrap:anywhere}
    nav{display:flex;gap:16px;flex-wrap:wrap}a{color:#175a63;text-underline-offset:3px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,285px),1fr));gap:12px}
    article{border:1px solid #ccd5d0;border-top:4px solid var(--ink);padding:16px;border-radius:6px;background:white}
    header{display:flex;align-items:center;justify-content:space-between;gap:6px}header b{color:var(--ink)}
    .bad{--ink:#9c342a}.part{--ink:#855100}.good{--ink:#236449}.unknown{--ink:#435c85}.quiet{--ink:#5a6260}
    footer,small{color:#46534f}footer{margin-top:14px;font-size:13px}.scroll{overflow-x:auto}
    table{width:100%;border-collapse:collapse;background:#fff}th,td{text-align:left;vertical-align:top;padding:8px 12px;
    border-bottom:1px solid #d5ddd8;min-width:72px}th{background:#e8efea}button{font:inherit}
    @media print{main{padding:0}.grid{display:block}article{break-inside:avoid;margin:8px}nav{display:none}}
    """
    nav = '<nav><a href="#modules">看 16 项</a><a href="#detail">看旅程、发现与证据</a></nav>'
    return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" '
            'content="width=device-width,initial-scale=1"><title>{t}</title><style>{css}</style>'
            '<main><h1>{t}</h1>{intro}{nav}<h2 id="modules">16 项核验</h2><div class="grid">{cards}</div>'
            '<div id="detail">{groups}</div></main></html>').format(t=html.escape(title), css=style,
                intro=prose(parts[""]), nav=nav, cards="".join(cards), groups="".join(groups))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("report", type=Path, help="Markdown report based on templates/AUDIT_REPORT.md")
    cli.add_argument("--html", type=Path, help="create a new offline HTML file if the ledger is valid")
    args = cli.parse_args()
    try:
        parts, ledger = review(args.report.read_text(encoding="utf-8"))
        if args.html:
            page = dashboard(parts, ledger)
            with args.html.open("x", encoding="utf-8") as f:
                f.write(page)
        extra = table(parts[EXTRA])[2:]
        counts = Counter(r[2] for r in ledger + extra)
        pending = [r[0] for r in ledger + extra if r[2] in PENDING]
        print(json.dumps({"modules": len(ledger), "additional": len(extra), "states": counts, "open": pending}, ensure_ascii=False))
        return int(bool(pending))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

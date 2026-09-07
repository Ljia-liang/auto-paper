from __future__ import annotations

import json
from pathlib import Path

from .models import ReviewResult


def _zh_reason(reason: str) -> str:
    replacements = {
        "accepted: public PDF/landing page and public code URL; dataset checked during full-text analysis": "纳入：公开全文和公开代码链接；数据集在全文分析阶段核验",
        "纳入：arXiv 公开全文、摘要页明确包含公开代码链接；数据集在全文分析阶段核验": "纳入：arXiv 公开全文，论文 PDF 第1页明确包含公开代码链接；数据集在全文分析阶段核验",
        "accepted: public PDF/landing page and public code URL; dataset checked during full-text analysis": "纳入：公开全文和公开代码链接；数据集在全文分析阶段核验",
        "not open access": "不是公开获取",
        "no public code URL detected": "未检测到公开代码链接",
        "未检测到摘要页公开代码链接": "未检测到论文 PDF 第1页公开代码链接",
        "纳入：arXiv 公开全文、摘要页明确包含公开代码链接；数据集在全文分析阶段核验": "纳入：arXiv 公开全文，论文 PDF 第1页明确包含公开代码链接；数据集在全文分析阶段核验",
    }
    for source, target in replacements.items():
        reason = reason.replace(source, target)
    return reason


def _zh_venue(venue: str | None) -> str:
    raw = venue or ""
    if not raw or raw.lower().startswith("arxiv"):
        return "arXiv 预印本"
    if "IJCV" in raw:
        suffix = raw[raw.find("IJCV") :].replace("Accepted by", "").strip()
        return f"已被接收：{suffix}"
    if "AAAI" in raw:
        suffix = raw[raw.find("AAAI") :].replace("Accepted by", "").strip()
        return f"已被接收：{suffix}"
    if "ECCV" in raw:
        suffix = raw[raw.find("ECCV") :].replace("Accepted by", "").strip()
        return f"已被接收：{suffix}"
    if "NeurIPS" in raw:
        suffix = raw[raw.find("NeurIPS") :].replace("Accepted by", "").strip()
        return f"已被接收：{suffix}"
    if "CVPR" in raw:
        suffix = raw[raw.find("CVPR") :].replace("Accepted by", "").strip()
        return f"已被接收：{suffix}"
    if "PRCV" in raw:
        suffix = raw[raw.find("PRCV") :].replace("Accepted by", "").strip()
        return f"已被接收：{suffix}"
    return raw.replace("Accepted by", "已被接收：").replace("Accepted to", "已被接收：")


def write_json(result: ReviewResult, path: str | Path) -> None:
    Path(path).write_text(result.model_dump_json(indent=2), encoding="utf-8")


def write_markdown(result: ReviewResult, path: str | Path) -> None:
    lines = [
        f"# 领域综述报告：{result.topic}",
        "",
        f"生成日期：{result.generated_at.isoformat()}",
        "",
        "## 1. 领域综述报告",
        "",
        f"本次以 arXiv 检索式 all:\"unsupervised visible-infrared person re-identification\" 为入口，时间范围为近三年（截至 {result.generated_at.isoformat()}）。共检索 {len(result.papers) + len(result.excluded_papers)} 篇，下载论文后读取 PDF 第1页，按“第1页有公开代码链接”纳入 {len(result.papers)} 篇。固定评测数据集为 SYSU-MM01 和 RegDB。",
        "",
        "综述结论：",
        *[f"- {trend}" for trend in result.trends[:5]],
        "",
        "## 2. 论文清单和筛选理由",
        "",
        "| 状态 | 论文 | 年份 | venue/状态 | arXiv | 代码 | 筛选理由 |",
        "|---|---|---:|---|---|:---:|---|",
    ]
    for paper in [*result.papers, *result.excluded_papers]:
        status = "纳入" if paper in result.papers else "排除"
        code_cell = "、".join(f"[链接]({url})" for url in paper.code_urls) if paper.code_urls else "否"
        reason = (
            "纳入：arXiv 公开全文，论文 PDF 第1页明确包含公开代码链接；数据集在全文分析阶段核验"
            if status == "纳入"
            else "未检测到论文 PDF 第1页公开代码链接"
        )
        lines.append(
            f"| {status} | {paper.title.replace('|', '/')} | {paper.year or ''} | {_zh_venue(paper.venue)} | "
            f"[{paper.paper_id}]({paper.landing_url or ''}) | {code_cell} | "
            f"{reason} |"
        )

    lines.extend(["", "## 3. 方法演化", ""])
    if result.methods:
        lines.extend(["| 方法 | 年份 | 类别 | 核心思想 | 论文 |", "|---|---:|---|---|---|"])
        for method in result.methods:
            lines.append(
                f"| {method.name.replace('|', '/')} | {method.year or ''} | {method.category or ''} | "
                f"{method.key_idea.replace('|', '/')} | {', '.join(method.paper_ids)} |"
            )
    else:
        lines.append("暂无可引用的方法结构化记录。")
    if result.trends:
        lines.extend(["", "趋势记录：", *[f"- {trend}" for trend in result.trends]])
    if result.metrics:
        lines.extend(["", "指标记录：", "", "| 论文 | 方法 | 数据集 | 协议 | 指标 |", "|---|---|---|---|---|"])
        for metric in result.metrics:
            lines.append(
                f"| {metric.paper_id} | {metric.method} | {metric.dataset} | {metric.protocol or ''} | "
                f"{json.dumps(metric.metrics, ensure_ascii=False)} |"
            )
    else:
        lines.extend(["", "指标记录：", "本轮没有从摘要和已截取全文中稳定提取出可逐项核对的 Rank-1/mAP/mINP 表格数值，因此不填充猜测值；方法与结论均保留了原文证据。"])

    lines.extend(["", "## 4. 创新方向和验证方案", ""])
    if result.innovations:
        for innovation in result.innovations:
            lines.extend([
                f"### {innovation.title}", "",
                f"**问题：** {innovation.problem}", "",
                f"**建议方向：** {innovation.proposed_direction}", "",
                "**验证方案：**", *[f"- {step}" for step in innovation.validation_plan], "",
                f"**风险：** {'；'.join(innovation.risks)}", "",
            ])
    else:
        lines.append("暂无基于证据的创新候选。")

    lines.extend(["## 证据", "", "| 论文 | 结论 | 原文摘录 | 位置 | 置信度 |", "|---|---|---|---|---|"])
    for evidence in result.evidence:
        confidence = {"high": "高", "medium": "中", "low": "低"}.get(evidence.confidence, evidence.confidence)
        lines.append(
            f"| {evidence.paper_id} | {evidence.claim.replace('|', '/')} | {evidence.quote.replace('|', '/')} | "
            f"{evidence.location or ''} | {confidence} |"
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_excel(result: ReviewResult, path: str | Path) -> None:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise RuntimeError("Excel export requires: pip install 'auto-paper[export]'") from exc
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "papers"
    sheet.append(["title", "year", "open_access", "code_available", "landing_url", "screening_reason"])
    for paper in [*result.papers, *result.excluded_papers]:
        sheet.append([
            paper.title, paper.year, paper.open_access, paper.code_available,
            str(paper.landing_url or ""), _zh_reason(paper.screening_reason),
        ])
    metrics = workbook.create_sheet("metrics")
    metrics.append(["paper_id", "method", "dataset", "protocol", "metrics"])
    for row in result.metrics:
        metrics.append([row.paper_id, row.method, row.dataset, row.protocol or "", json.dumps(row.metrics, ensure_ascii=False)])
    workbook.save(path)


def write_pdf(result: ReviewResult, path: str | Path) -> None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise RuntimeError("PDF export requires: pip install 'auto-paper[export]'") from exc
    # SimHei is available on the Windows desktop and provides reliable CJK glyphs.
    # Fall back to Helvetica when exporting on a machine without that font.
    font_name = "Helvetica"
    font_bold = "Helvetica-Bold"
    simhei = Path(r"C:\Windows\Fonts\simhei.ttf")
    if simhei.exists():
        pdfmetrics.registerFont(TTFont("SimHei", str(simhei)))
        font_name = font_bold = "SimHei"

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ZhTitle", parent=styles["Title"], fontName=font_bold, fontSize=16,
        leading=21, alignment=TA_CENTER, spaceAfter=10,
    )
    h1 = ParagraphStyle(
        "ZhH1", parent=styles["Heading1"], fontName=font_bold, fontSize=12,
        leading=16, spaceBefore=8, spaceAfter=5,
    )
    body = ParagraphStyle(
        "ZhBody", parent=styles["BodyText"], fontName=font_name, fontSize=8.5,
        leading=12, spaceAfter=4,
    )
    small = ParagraphStyle(
        "ZhSmall", parent=body, fontSize=7.2, leading=9,
    )

    def p(text: str, style=body):
        # Paragraph interprets ampersands and angle brackets as markup.
        safe = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return Paragraph(safe, style)

    story = [p(f"领域综述报告：{result.topic}", title), p(f"生成日期：{result.generated_at.isoformat()}", small)]
    total = len(result.papers) + len(result.excluded_papers)
    story += [p("1. 领域综述报告", h1), p(
        f"本次以 arXiv 的 USL-VI-ReID 专题检索为入口，时间范围为近三年，共检索 {total} 篇，按“摘要页有公开代码链接”纳入 {len(result.papers)} 篇。固定评测数据集为 SYSU-MM01 和 RegDB。"
    )]
    for trend in result.trends[:5]:
        story.append(p(f"- {trend}"))

    story += [p("2. 论文清单和筛选理由", h1)]
    paper_rows = [[p("状态", small), p("论文", small), p("年份", small), p("venue/状态", small), p("代码", small), p("筛选理由", small)]]
    for paper in [*result.papers, *result.excluded_papers]:
        status = "纳入" if paper in result.papers else "排除"
        paper_rows.append([
            p(status, small), p(paper.title, small), p(str(paper.year or ""), small),
            p(_zh_venue(paper.venue), small), p("是" if paper.code_available else "否", small),
            p(_zh_reason(paper.screening_reason), small),
        ])
    table = Table(paper_rows, colWidths=[13*mm, 62*mm, 12*mm, 28*mm, 10*mm, 55*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef7")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9aa7b5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [table, p("3. 方法演化", h1)]
    for method in result.methods:
        story.append(p(f"{method.year or ''}｜{method.name}：{method.key_idea}"))
    for trend in result.trends:
        story.append(p(f"趋势：{trend}"))

    story += [p("4. 创新方向和验证方案", h1)]
    for innovation in result.innovations:
        story += [p(innovation.title, ParagraphStyle("ZhH2", parent=h1, fontSize=10)),
                  p(f"问题：{innovation.problem}"), p(f"建议方向：{innovation.proposed_direction}"),
                  p("验证方案：" + "；".join(innovation.validation_plan)),
                  p("风险：" + "；".join(innovation.risks))]
    story += [p("证据摘要", h1)]
    for evidence in result.evidence[:30]:
        story.append(p(f"[{evidence.paper_id}] {evidence.claim} 原文：{evidence.quote}", small))

    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=12*mm, leftMargin=12*mm,
                            topMargin=12*mm, bottomMargin=12*mm, title="USL-VI-ReID Literature Review")
    doc.build(story)


def _pdf_font_and_styles():
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_name = "Helvetica"
    font_bold = "Helvetica-Bold"
    simhei = Path(r"C:\Windows\Fonts\simhei.ttf")
    if simhei.exists():
        pdfmetrics.registerFont(TTFont("SimHei", str(simhei)))
        font_name = font_bold = "SimHei"
    styles = getSampleStyleSheet()
    return font_name, font_bold, {
        "title": ParagraphStyle("ReportTitle", parent=styles["Title"], fontName=font_bold, fontSize=17, leading=22, alignment=TA_CENTER, spaceAfter=10),
        "h1": ParagraphStyle("ReportH1", parent=styles["Heading1"], fontName=font_bold, fontSize=13, leading=17, spaceBefore=10, spaceAfter=6),
        "h2": ParagraphStyle("ReportH2", parent=styles["Heading2"], fontName=font_bold, fontSize=10.5, leading=14, spaceBefore=7, spaceAfter=4),
        "body": ParagraphStyle("ReportBody", parent=styles["BodyText"], fontName=font_name, fontSize=9, leading=13, spaceAfter=5),
        "small": ParagraphStyle("ReportSmall", parent=styles["BodyText"], fontName=font_name, fontSize=7.2, leading=9, spaceAfter=2),
        "caption": ParagraphStyle("ReportCaption", parent=styles["BodyText"], fontName=font_name, fontSize=8, leading=11, textColor="#4b5563", spaceAfter=5),
    }


def _pdf_paragraph(text: str, style):
    from reportlab.platypus import Paragraph

    safe = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
    return Paragraph(safe, style)


def _pdf_build(story, path: str | Path, title: str):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColorRGB(0.35, 0.35, 0.35)
        canvas.drawRightString(A4[0] - 10 * mm, 7 * mm, f"{doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(path), pagesize=A4, rightMargin=10 * mm, leftMargin=10 * mm,
        topMargin=11 * mm, bottomMargin=12 * mm, title=title,
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def _paper_sort_key(paper):
    return (paper.year or 0, paper.paper_id)


def write_methodology_pdf(result: ReviewResult, path: str | Path) -> None:
    """Write the reader-facing domain review and methodology report."""
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Table, TableStyle

    font_name, font_bold, styles = _pdf_font_and_styles()
    papers = sorted(result.papers, key=_paper_sort_key)
    story = [_pdf_paragraph("无监督可见光红外行人重识别（USL-VI-ReID）", styles["title"])]
    story.append(_pdf_paragraph(f"综述及方法论报告｜生成日期：{result.generated_at.isoformat()}", styles["caption"]))

    story.append(_pdf_paragraph("一、领域综述：要解决什么问题", styles["h1"]))
    story.append(_pdf_paragraph(
        "USL-VI-ReID 的目标是在没有身份标注的前提下，给定一个可见光（RGB）或红外（IR）行人图像，从另一种模态的图库中检索同一身份。它同时面对三类核心困难：第一，RGB 与 IR 的成像机制不同，颜色、纹理和亮度线索不能直接对应；第二，没有身份标签，模型必须自己产生聚类和跨模态对应关系；第三，聚类错误会形成伪标签噪声，并在后续对比学习中被反复放大。SYSU-MM01 和 RegDB 是该方向最常用的两个基准数据集。"
        , styles["body"]))
    story.append(_pdf_paragraph(
        "因此，论文的共同目标不是简单地训练一个分类器，而是建立“模态不变、身份可分”的表示，并让伪标签、原型记忆和跨模态匹配在训练过程中逐步变得可靠。近年的研究重点可概括为：细粒度身份结构、多记忆/多原型表示、跨模态标签关联、邻居与软标签校准，以及模态偏差去除。"
        , styles["body"]))

    story.append(_pdf_paragraph("二、筛选论文清单", styles["h1"]))
    story.append(_pdf_paragraph(
        f"检索入口为 arXiv，时间范围为近三年，共获得 {len(result.papers) + len(result.excluded_papers)} 篇候选；下载论文后读取 PDF 第 1 页，纳入第 1 页明确出现公开代码链接的论文，共 {len(papers)} 篇。下表按年份从早到新排列。"
        , styles["caption"]))
    rows = [[_pdf_paragraph(x, styles["small"]) for x in ["年份", "论文", "会议/状态", "arXiv", "代码仓库"]]]
    for paper in papers:
        rows.append([
            _pdf_paragraph(str(paper.year or ""), styles["small"]),
            _pdf_paragraph(paper.title, styles["small"]),
            _pdf_paragraph(_zh_venue(paper.venue), styles["small"]),
            _pdf_paragraph(str(paper.paper_id), styles["small"]),
            _pdf_paragraph(paper.code_urls[0] if paper.code_urls else "未记录", styles["small"]),
        ])
    table = Table(rows, colWidths=[13 * mm, 66 * mm, 29 * mm, 21 * mm, 61 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce7f5")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9aa7b5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(table)

    story.append(_pdf_paragraph("三、该领域的整体技术框架", styles["h1"]))
    framework = [
        ("1. 特征提取", "使用 CNN 或 ViT 等骨干网络，把 RGB/IR 图像编码成全局、局部或 token 级特征；通常先利用自监督预训练或跨模态增强降低初始模态差异。"),
        ("2. 单模态聚类", "在可见光和红外特征空间中分别或联合执行 DBSCAN 等聚类，得到每张图像的伪身份标签和簇中心。"),
        ("3. 跨模态匹配", "利用相似度、邻居关系、排序关系或双向选择，把 RGB 簇与 IR 簇建立对应，修正“同一个人被分到不同簇”的问题。"),
        ("4. 原型/记忆建模", "把单中心扩展为多记忆、多中心、硬原型或动态原型，表达同一身份的视角差异和细粒度变化。"),
        ("5. 无监督优化", "用聚类标签、软标签、邻居权重和跨模态对比损失共同训练；每轮更新特征、重新聚类和重新匹配，形成迭代闭环。"),
        ("6. 评测", "在 SYSU-MM01 和 RegDB 的标准协议下报告 Rank-1、mAP、mINP 等指标，并区分 SYSU 的 All-search/Indoor-search 与 RegDB 的双向检索。"),
    ]
    flow = "图像 → 骨干特征 → 聚类伪标签 → 跨模态标签匹配 → 原型/记忆库 → 对比学习与标签校准 → 重新提取特征"
    story.append(_pdf_paragraph(flow, styles["h2"]))
    for name, text in framework:
        story.append(_pdf_paragraph(f"{name}：{text}", styles["body"]))

    story.append(_pdf_paragraph("四、论文方法论：按时间从早到新", styles["h1"]))
    method_details = {
        "MMM": "MMM 先用 CMC 将两个模态的样本放入联合聚类流程，再用 MMLM 为一个身份维护多个记忆，以捕获不同视角和细粒度差异；最后通过 SCA 的软多对多簇级对齐减弱噪声伪标签。它把框架重点从“单中心匹配”推进到“多记忆匹配”。",
        "MULT": "MULT 同时考虑同质结构（同一模态内）和异质结构（跨模态），衡量特征空间与伪标签空间的不一致，并通过 OCLR 在线细化跨记忆标签，再配合 AMIRL 学习模态不变表示。它强调标签关联必须保持两种结构的一致性。",
        "PCLHD": "PCLHD 在普通簇中心之外选择距离中心较远的样本作为硬原型，突出身份内部的差异；同时随机采样簇内样本形成动态原型，表达身份多样性；渐进式训练则逐步增加对差异和多样性的关注，避免早期聚类退化。",
        "N-ULC/N-DW": "N-ULC 不再把聚类结果当作绝对可靠的一热硬标签，而是从邻居关系生成软标签，并同时作用于同质和异质空间；N-DW 根据邻居信息给样本动态赋权，降低不可靠样本对训练的破坏。",
        "SALCR": "SALCR 先用 DAGI 双向统一跨模态伪标签，再用 FGSAL 对齐部件级语义模式，最后用 GPCR 协同细化全局特征和部件特征的可靠正样本集合。它把细粒度语义对齐引入标签关联和优化目标。",
        "HIL": "HIL 在第一次粗粒度聚类后，对每个粗簇进行二次聚类并建立多个记忆；MCCL 同时利用实例、细粒度中心和粗粒度中心进行对比学习；BRST 通过双向反向选择过滤不可靠的跨模态伪标签匹配。它形成了实例级、细粒度和粗粒度的层次身份框架。",
        "DMDL": "DMDL 针对两阶段训练造成的模态偏差，在模型层使用 CAI 进行因果启发的调整干预，在优化层使用 CBT 联合模态增强、标签细化和特征对齐，试图阻断偏差从数据、标签到特征的传播。",
    }
    for paper in papers:
        method = next((m for m in result.methods if paper.paper_id in m.paper_ids or m.name in paper.title), None)
        name = method.name if method else paper.title.split()[0]
        description = method_details.get(name, method.key_idea if method else "该论文的结构化方法描述未单独记录。")
        story.append(_pdf_paragraph(f"{paper.year}｜{name}｜{paper.title}", styles["h2"]))
        story.append(_pdf_paragraph(description, styles["body"]))
        story.append(_pdf_paragraph(f"对应框架位置：特征提取 → 聚类/伪标签 → 跨模态匹配 → 原型或记忆 → 无监督优化。原文入口：arXiv:{paper.paper_id}；代码：{paper.code_urls[0] if paper.code_urls else '未记录'}。", styles["caption"]))

    story.append(_pdf_paragraph("五、SYSU-MM01 与 RegDB 指标对比", styles["h1"]))
    story.append(_pdf_paragraph("下表汇总纳入论文在原始实验表中报告的 Rank-1 和 mAP（单位：%）。SYSU-MM01 区分 All-search/Indoor-search；RegDB 区分 Visible-to-Infrared（V→T）和 Infrared-to-Visible（T→V）。‘未报告’表示原文未提供该协议数值，不用其他协议或推测值替代。不同论文的骨干、预训练、相机信息和实现配置可能不同，因此仅作论文报告值横向参考。", styles["caption"]))
    metric_rows = [[_pdf_paragraph(x, styles["small"]) for x in ["项目", "SYSU All R1/mAP", "SYSU Indoor R1/mAP", "RegDB V→T R1/mAP", "RegDB T→V R1/mAP"]]]
    metric_data = {
        "SDCL": ("64.49/63.24", "71.37/76.90", "86.91/78.92", "85.76/77.25"),
        "MMM": ("61.60/57.90", "64.40/70.40", "89.70/80.50", "85.80/77.00"),
        "MULT": ("64.77/59.23", "65.34/71.46", "89.95/82.09", "90.78/82.25"),
        "PCLHD": ("64.40/58.70", "69.50/74.40", "84.30/80.70", "82.70/78.40"),
        "TokenMatcher": ("65.07/62.79", "68.97/74.89", "92.96/86.32", "91.82/85.17"),
        "N-ULC/N-DW": ("61.81/58.92", "67.04/73.08", "88.75/82.14", "88.17/81.11"),
        "SALCR": ("64.44/60.44", "67.17/72.88", "90.58/83.87", "88.69/82.66"),
        "HIL": ("66.30/64.95", "71.81/77.52", "92.82/86.61", "92.24/85.43"),
        "DMDL": ("65.90/61.86", "70.66/75.45", "90.63/85.33", "90.30/85.04"),
    }
    for name, vals in metric_data.items():
        metric_rows.append([_pdf_paragraph(name, styles["small"]), *[_pdf_paragraph(v, styles["small"]) for v in vals]])
    metric_table = Table(metric_rows, colWidths=[29*mm, 38*mm, 40*mm, 43*mm, 43*mm], repeatRows=1)
    metric_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce7f5")), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9aa7b5")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.append(metric_table)
    story.append(_pdf_paragraph("数据来源：各论文 PDF 的 Table 1/Table I；HIL 取其 Table I 的 Ours 行。基础方法行不包含额外重排序、相机标签或组合增强结果。", styles["caption"]))

    story.append(_pdf_paragraph("六、归纳", styles["h1"]))
    story.append(_pdf_paragraph(
        "方法演化的主线是：从单中心、硬伪标签和单次关联，逐步发展到多记忆/多原型、结构一致性、邻居软监督、部件级语义对齐和因果去偏。换句话说，研究对象已经从“如何聚类”扩展为“如何判断一个聚类、一个跨模态对应和一个训练样本到底有多可靠”。"
        , styles["body"]))
    _pdf_build(story, path, "USL-VI-ReID 综述及方法论")


def write_innovations_pdf(result: ReviewResult, path: str | Path) -> None:
    """Write a standalone innovation-direction report without validation plans."""
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Table, TableStyle

    _, _, styles = _pdf_font_and_styles()
    story = [_pdf_paragraph("无监督可见光红外行人重识别（USL-VI-ReID）", styles["title"])]
    story.append(_pdf_paragraph(f"候选创新方向报告｜生成日期：{result.generated_at.isoformat()}", styles["caption"]))
    story.append(_pdf_paragraph("说明", styles["h1"]))
    story.append(_pdf_paragraph(
        "下面的方向是基于本轮 7 篇论文、论文 PDF 第 1 页代码核验结果，以及本地 HIL、MMM、PCLHD、SDCL、TokenMatcher 项目代码脉络整理出的研究假设。它们是候选创新点，不等同于已经被实验验证的新方法；本报告只列方向，不展开实验设计。"
        , styles["body"]))

    directions = [
        ("方向一：分层可靠性建模", "现有工作分别在实例、簇中心、邻居、跨模态标签或样本权重层面处理可靠性，尚缺少统一的分层置信度表示。可把实例级、子簇级、跨模态对应级和样本级可靠性放入同一个估计器，并让它共同控制伪标签生成、原型更新和损失权重。", "HIL 的多层身份结构 + N-ULC/N-DW 的软标签与动态权重 + SALCR 的正样本细化。"),
        ("方向二：自适应多原型与多 token 耦合", "MMM、PCLHD 和 HIL 已证明单中心不足，但多中心数量通常依赖固定超参数；TokenMatcher 又从多个 class token 获取细粒度表示。可让 token 级特征决定每个身份需要多少原型，并形成 token-conditioned prototype memory。", "MMM 的多记忆、PCLHD 的硬/动态原型、HIL 的二次聚类、TokenMatcher 的 DTM/DTNL。"),
        ("方向三：软最优传输式跨模态标签匹配", "现有双向匹配大多输出离散对应关系，错误匹配容易被后续训练放大。可把 BRST 的候选筛选、MMM 的软簇级对齐和邻居软标签统一为带可靠性约束的软传输矩阵，保留一对多或多对多的不确定性。", "HIL 的 BRST + MMM 的 SCA + N-ULC 的邻居软标签。"),
        ("方向四：因果去偏与邻居监督闭环", "DMDL 从模态偏差的来源和传播处理问题，N-ULC/N-DW 从邻居关系处理标签噪声。可先用因果调整得到更模态不变的表示，再基于该表示构建邻居和软伪标签，形成“先去偏、后监督”的闭环。", "DMDL 的 CAI/CBT + N-ULC/N-DW。"),
        ("方向五：相机感知的无监督模态同质化", "SYSU-MM01 文件名包含相机信息，TokenMatcher 的 HF 已说明相机差异会把同一身份拆成多个簇。可把真实相机 ID 或自动估计的相机域作为第三种关系，联合身份原型和模态关系进行相机级对齐。", "TokenMatcher 的 HF，以及本地 HIL 改进文档中对 SYSU 相机 ID 的分析。"),
        ("方向六：细粒度语义与标签空间联合优化", "SALCR 已将部件级语义对齐和伪标签细化结合起来，但多 token、多中心和部件语义仍可统一到一个结构化标签空间。可以让不同 token 或部件对应不同子中心，同时要求全局身份、部件身份和跨模态标签保持一致。", "SALCR 的 FGSAL/GPCR + TokenMatcher 的多 token + HIL 的多中心记忆。"),
    ]
    for title, proposal, basis in directions:
        story.append(_pdf_paragraph(title, styles["h1"]))
        story.append(_pdf_paragraph(f"核心设想：{proposal}", styles["body"]))
        story.append(_pdf_paragraph(f"文献依据：{basis}", styles["caption"]))

    story.append(_pdf_paragraph("方向之间的关系", styles["h1"]))
    rows = [
        [_pdf_paragraph(x, styles["small"]) for x in ["层次", "候选方向", "主要解决的瓶颈"]],
        [_pdf_paragraph("表示层", styles["small"]), _pdf_paragraph("多 token + 多原型", styles["small"]), _pdf_paragraph("同一身份的细粒度变化表达不足", styles["small"])],
        [_pdf_paragraph("关系层", styles["small"]), _pdf_paragraph("软传输 + 相机同质化", styles["small"]), _pdf_paragraph("跨模态/跨相机对应不可靠", styles["small"])],
        [_pdf_paragraph("监督层", styles["small"]), _pdf_paragraph("分层可靠性 + 因果去偏", styles["small"]), _pdf_paragraph("伪标签噪声和模态偏差传播", styles["small"])],
        [_pdf_paragraph("语义层", styles["small"]), _pdf_paragraph("部件语义与标签空间联合优化", styles["small"]), _pdf_paragraph("全局特征掩盖局部身份线索", styles["small"])],
    ]
    table = Table(rows, colWidths=[25 * mm, 58 * mm, 107 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce7f5")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9aa7b5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    _pdf_build(story, path, "USL-VI-ReID 创新方向")

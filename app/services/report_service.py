"""Report generation service — exports analytics data as CSV, JSON, or PDF."""
import csv
import io
import json
from datetime import datetime
from typing import Any

from app.utils.logger import logger

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
        HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not available — PDF export disabled.")


# Indigo color palette for PDF
INDIGO_DARK = colors.HexColor("#312E81")
INDIGO_MID = colors.HexColor("#4F46E5")
INDIGO_LIGHT = colors.HexColor("#C7D2FE")
WHITE = colors.white
GRAY_LIGHT = colors.HexColor("#F3F4F6")
GRAY_TEXT = colors.HexColor("#6B7280")


class ReportService:
    """Generates downloadable analytics reports in CSV, JSON, and PDF formats."""

    def to_csv(self, data: dict) -> bytes:
        """
        Generate a CSV report from analytics data.

        Structure:
          - Metric/Value rows for top-level metrics
          - Blank row separator
          - Top posts table (if available)
          - Insights section

        Args:
            data: Analysis result dict (post or profile).

        Returns:
            UTF-8 encoded CSV bytes.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        platform = data.get("platform", "unknown").upper()
        report_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        writer.writerow(["SocialPulse Intelligence — Analytics Report"])
        writer.writerow([f"Platform: {platform}", f"Generated: {report_time}"])
        writer.writerow([])

        # Determine URL / username
        url = data.get("url") or data.get("username", "N/A")
        writer.writerow(["Subject", url])
        writer.writerow([])

        # Main metrics
        writer.writerow(["Metric", "Value"])
        metrics = data.get("metrics", {})
        for key, value in metrics.items():
            label = key.replace("_", " ").title()
            writer.writerow([label, value])

        writer.writerow([])

        # Top posts
        top_posts = data.get("top_posts", [])
        if top_posts:
            writer.writerow(["Top Posts"])
            writer.writerow(["URL", "Title", "Views", "Likes", "Comments", "Shares", "ER%", "Virality"])
            for post in top_posts:
                writer.writerow([
                    post.get("url", ""),
                    post.get("title", ""),
                    post.get("views", 0),
                    post.get("likes", 0),
                    post.get("comments", 0),
                    post.get("shares", 0),
                    f"{post.get('engagement_rate', 0):.2f}",
                    f"{post.get('virality_score', 0):.2f}",
                ])
            writer.writerow([])

        # Hashtags
        hashtags = data.get("hashtags", [])
        if hashtags:
            writer.writerow(["Top Hashtags"])
            writer.writerow([", ".join(f"#{h}" for h in hashtags[:20])])
            writer.writerow([])

        # Insights
        insights = data.get("insights", [])
        if insights:
            writer.writerow(["Insights"])
            for insight in insights:
                # Strip emoji for clean CSV
                clean = insight.encode("ascii", "ignore").decode("ascii").strip()
                writer.writerow([clean])

        return output.getvalue().encode("utf-8-sig")  # BOM for Excel compatibility

    def to_json(self, data: dict) -> bytes:
        """
        Generate a pretty-printed JSON report.

        Args:
            data: Analysis result dict.

        Returns:
            UTF-8 encoded JSON bytes.
        """
        payload = {
            "report": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": "SocialPulse Intelligence API",
                "version": "1.0.0",
            },
            "data": data,
        }
        return json.dumps(payload, indent=2, default=str, ensure_ascii=False).encode("utf-8")

    def to_pdf(self, data: dict) -> bytes:
        """
        Generate a styled PDF analytics report using ReportLab.

        Args:
            data: Analysis result dict.

        Returns:
            PDF file bytes.

        Raises:
            RuntimeError: If reportlab is not installed.
        """
        if not _REPORTLAB_AVAILABLE:
            raise RuntimeError(
                "PDF export is unavailable. Install reportlab: pip install reportlab"
            )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=1 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()
        story = []

        # --- Header ---
        header_style = ParagraphStyle(
            "Header",
            parent=styles["Title"],
            textColor=INDIGO_DARK,
            fontSize=22,
            spaceAfter=4,
            alignment=TA_CENTER,
        )
        sub_style = ParagraphStyle(
            "SubHeader",
            parent=styles["Normal"],
            textColor=GRAY_TEXT,
            fontSize=10,
            spaceAfter=12,
            alignment=TA_CENTER,
        )
        section_style = ParagraphStyle(
            "Section",
            parent=styles["Heading2"],
            textColor=INDIGO_DARK,
            fontSize=13,
            spaceBefore=16,
            spaceAfter=8,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#1F2937"),
            leading=16,
        )

        platform = data.get("platform", "Unknown").upper()
        subject = data.get("url") or data.get("username", "N/A")
        report_time = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")

        story.append(Paragraph("SocialPulse Intelligence", header_style))
        story.append(Paragraph(f"Analytics Report — {platform}", sub_style))
        story.append(Paragraph(f"Generated: {report_time}", sub_style))
        story.append(HRFlowable(width="100%", thickness=2, color=INDIGO_MID))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"<b>Subject:</b> {subject}", body_style))
        story.append(Spacer(1, 16))

        # --- Metrics table ---
        story.append(Paragraph("Engagement Metrics", section_style))
        metrics = data.get("metrics", {})
        metric_rows = [["Metric", "Value"]]
        for key, value in metrics.items():
            label = key.replace("_", " ").title()
            if isinstance(value, float):
                display = f"{value:.4f}"
            else:
                display = str(value) if value is not None else "N/A"
            metric_rows.append([label, display])

        metrics_table = Table(metric_rows, colWidths=[3.5 * inch, 2.5 * inch])
        metrics_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), INDIGO_MID),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ])
        )
        story.append(metrics_table)

        # --- Top posts ---
        top_posts = data.get("top_posts", [])
        if top_posts:
            story.append(Spacer(1, 12))
            story.append(Paragraph("Top Performing Posts", section_style))

            post_rows = [["Title", "Views", "Likes", "Comments", "ER%", "Virality"]]
            for post in top_posts[:10]:
                title = (post.get("title") or post.get("url", ""))[:40]
                post_rows.append([
                    title,
                    f"{post.get('views', 0):,}",
                    f"{post.get('likes', 0):,}",
                    f"{post.get('comments', 0):,}",
                    f"{post.get('engagement_rate', 0):.2f}%",
                    f"{post.get('virality_score', 0):.1f}",
                ])

            posts_table = Table(
                post_rows,
                colWidths=[2.5 * inch, 0.9 * inch, 0.8 * inch, 0.9 * inch, 0.7 * inch, 0.7 * inch],
            )
            posts_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), INDIGO_MID),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ])
            )
            story.append(posts_table)

        # --- Hashtags ---
        hashtags = data.get("hashtags", [])
        if hashtags:
            story.append(Spacer(1, 12))
            story.append(Paragraph("Top Hashtags", section_style))
            hashtag_str = "  ".join(f"#{h}" for h in hashtags[:20])
            story.append(Paragraph(hashtag_str, body_style))

        # --- Insights ---
        insights = data.get("insights", [])
        if insights:
            story.append(Spacer(1, 12))
            story.append(Paragraph("AI-Generated Insights", section_style))
            for idx, insight in enumerate(insights, start=1):
                clean = insight.encode("ascii", "ignore").decode("ascii").strip()
                story.append(Paragraph(f"{idx}. {clean}", body_style))
                story.append(Spacer(1, 4))

        # --- Footer ---
        story.append(Spacer(1, 24))
        story.append(HRFlowable(width="100%", thickness=1, color=INDIGO_LIGHT))
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            textColor=GRAY_TEXT,
            fontSize=8,
            alignment=TA_CENTER,
        )
        story.append(
            Paragraph(
                "Generated by SocialPulse Intelligence | socialpulse.ai",
                footer_style,
            )
        )

        doc.build(story)
        return buffer.getvalue()


# Singleton instance
report_service = ReportService()

__all__ = ["ReportService", "report_service"]

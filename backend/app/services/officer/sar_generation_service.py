"""
SAR (Suspicious Activity Report) Generation Service

Generates professional PDF SAR reports with:
- TrustVault header/logo
- Case/Alert details
- Risk scores
- Timeline
- Evidence
- Recommendations
- Regulatory filing support
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import json
from pathlib import Path
import pandas as pd
import asyncio
import math
import re

from app.core.runtime_context import get_runtime_session_id
from app.core import storage_paths
from app.services.cases.case_repository import case_repository
from app.services.alerts.alert_storage_service import read_csv
from app.db.file_storage import log_report
from app.services.transaction.audit_service import log_officer_action
from app.realtime.transaction_memory_store import publish_event
from app.utils.file_utils import ensure_parent_dir
from app.services.officer.sar_context_service import sar_context_service

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        HRFlowable,
        KeepTogether,
        ListFlowable,
        ListItem,
        PageBreak,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image,
    )
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


SAR_REPORTS_DIR = storage_paths.PROCESSED_DIR / "reports" / "sar"
SAR_METADATA_FILE = storage_paths.PROCESSED_DIR / "reports" / "sar_metadata.csv"

SAR_METADATA_COLUMNS = [
    "sar_id",
    "case_id",
    "alert_id",
    "user_id",
    "generated_by",
    "generated_at",
    "status",
    "pdf_filename",
    "filing_type",
    "runtime_session_id"
]


def _ensure_sar_storage() -> None:
    ensure_parent_dir(SAR_REPORTS_DIR)
    ensure_parent_dir(SAR_METADATA_FILE)
    if not SAR_METADATA_FILE.exists():
        df = pd.DataFrame(columns=SAR_METADATA_COLUMNS)
        df.to_csv(SAR_METADATA_FILE, index=False)


def _generate_sar_id() -> str:
    """Generate unique SAR ID"""
    from uuid import uuid4
    return f"SAR-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6].upper()}"


def _atomic_write_csv(df: pd.DataFrame, path: Path) -> None:
    ensure_parent_dir(path)
    tmp_path = path.with_suffix(".tmp")
    df.to_csv(tmp_path, index=False)
    tmp_path.replace(path)


def _publish_sar_event(payload: Dict[str, Any]) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    try:
        loop.create_task(publish_event(payload))
    except Exception:
        pass


class SARGenerationService:
    """Handles SAR report generation"""

    def __init__(self):
        self.runtime_session_id = get_runtime_session_id()
        _ensure_sar_storage()

    def generate_sar_from_case(
        self,
        case_id: str,
        generated_by: str,
        officer_notes: str = "",
        filing_type: str = "INTERNAL"  # INTERNAL or STR (for regulatory filing)
    ) -> Dict[str, Any]:
        """Generate SAR from case"""
        case = case_repository.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        # Generate SAR
        sar_id = _generate_sar_id()
        pdf_filename = f"SAR_{case_id}_{sar_id}.pdf"
        pdf_path = SAR_REPORTS_DIR / pdf_filename

        # Prepare SAR data
        sar_content = sar_context_service.build_sar_context(
            case_id=case_id,
            generated_by=generated_by,
            officer_notes=officer_notes,
            filing_type=filing_type,
            sar_id=sar_id,
        )

        # Generate PDF
        if HAS_REPORTLAB:
            try:
                self._generate_pdf(sar_content, pdf_path)
                generated_successfully = True
            except Exception as e:
                print(f"PDF generation error: {e}")
                generated_successfully = False
        else:
            # Fallback: generate a minimal PDF without ReportLab
            self._generate_fallback_pdf(sar_content, pdf_path)
            generated_successfully = True

        # Record SAR metadata
        sar_record = {
            "sar_id": sar_id,
            "case_id": case_id,
            "alert_id": case.get("source_alert_id", ""),
            "user_id": case.get("user_id", ""),
            "generated_by": generated_by,
            "generated_at": _now(),
            "status": "GENERATED" if generated_successfully else "PENDING",
            "pdf_filename": pdf_filename,
            "pdf_path": str(pdf_path),
            "filing_type": filing_type,
            "runtime_session_id": self.runtime_session_id
        }

        self._record_sar(sar_record)

        log_officer_action(
            officer_id=generated_by,
            action="SAR_GENERATED",
            case_id=case_id,
            alert_id=sar_record.get("alert_id") or None,
            old_state=str(case.get("status", "")),
            new_state="SAR_FILED",
            reason=f"SAR generated for case {case_id}",
            notes=officer_notes,
            metadata={"filing_type": filing_type},
        )

        # Log report
        log_report({
            "report_type": "SAR",
            "report_id": sar_id,
            "case_id": case_id,
            "user_id": case.get("user_id", ""),
            "generated_by": generated_by,
            "timestamp": _now(),
            "runtime_session_id": self.runtime_session_id
        })

        # Publish SSE event
        _publish_sar_event({
            "type": "SAR_GENERATED",
            "sar_id": sar_id,
            "case_id": case_id,
            "generated_by": generated_by,
            "timestamp": _now(),
            "runtime_session_id": self.runtime_session_id
        })

        return {
            "status": "SUCCESS",
            "sar_id": sar_id,
            "case_id": case_id,
            "pdf_filename": pdf_filename,
            "pdf_path": str(pdf_path),
            "download_url": f"/api/v1/sar/{case_id}/download",
            "filing_type": filing_type
        }

    def generate_sar_from_alert(
        self,
        alert_id: str,
        generated_by: str,
        officer_notes: str = "",
        alert_type: str = "transaction",
        filing_type: str = "INTERNAL"
    ) -> Dict[str, Any]:
        """Generate SAR directly from alert"""
        alert = None
        try:
            alerts = read_csv(f"{alert_type}_alerts")
            for a in alerts:
                if str(a.get("alert_id", "")) == str(alert_id):
                    alert = a
                    break
        except Exception:
            pass

        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Generate SAR
        sar_id = _generate_sar_id()
        pdf_filename = f"SAR_ALERT_{alert_id}_{sar_id}.pdf"
        pdf_path = SAR_REPORTS_DIR / pdf_filename

        # Prepare SAR data
        sar_content = sar_context_service.build_sar_context(
            alert_id=alert_id,
            generated_by=generated_by,
            officer_notes=officer_notes,
            filing_type=filing_type,
            sar_id=sar_id,
        )

        # Generate PDF
        if HAS_REPORTLAB:
            try:
                self._generate_pdf(sar_content, pdf_path)
                generated_successfully = True
            except Exception as e:
                print(f"PDF generation error: {e}")
                generated_successfully = False
        else:
            self._generate_fallback_pdf(sar_content, pdf_path)
            generated_successfully = True

        # Record SAR metadata
        sar_record = {
            "sar_id": sar_id,
            "case_id": "",
            "alert_id": alert_id,
            "user_id": alert.get("user_id", ""),
            "generated_by": generated_by,
            "generated_at": _now(),
            "status": "GENERATED" if generated_successfully else "PENDING",
            "pdf_filename": pdf_filename,
            "pdf_path": str(pdf_path),
            "filing_type": filing_type,
            "runtime_session_id": self.runtime_session_id
        }

        self._record_sar(sar_record)

        log_officer_action(
            officer_id=generated_by,
            action="SAR_GENERATED",
            case_id=None,
            alert_id=alert_id,
            old_state=str(alert.get("state", "")),
            new_state="SAR_FILED",
            reason=f"SAR generated for alert {alert_id}",
            notes=officer_notes,
            metadata={"filing_type": filing_type, "alert_type": alert_type},
        )

        # Log report
        log_report({
            "report_type": "SAR",
            "report_id": sar_id,
            "alert_id": alert_id,
            "user_id": alert.get("user_id", ""),
            "generated_by": generated_by,
            "timestamp": _now(),
            "runtime_session_id": self.runtime_session_id
        })

        # Publish SSE event
        _publish_sar_event({
            "type": "SAR_GENERATED",
            "sar_id": sar_id,
            "alert_id": alert_id,
            "generated_by": generated_by,
            "timestamp": _now(),
            "runtime_session_id": self.runtime_session_id
        })

        return {
            "status": "SUCCESS",
            "sar_id": sar_id,
            "alert_id": alert_id,
            "pdf_filename": pdf_filename,
            "pdf_path": str(pdf_path),
            "download_url": f"/api/v1/sar/{alert_id}/download",
            "filing_type": filing_type
        }

    def _prepare_sar_content(self, case: Dict[str, Any], officer_notes: str, generated_by: str) -> Dict[str, Any]:
        """Prepare SAR content from case"""
        return sar_context_service.build_sar_context(
            case_id=case.get("case_id", ""),
            alert_id=case.get("source_alert_id", ""),
            generated_by=generated_by,
            officer_notes=officer_notes,
            sar_id=_generate_sar_id(),
        )

    def _prepare_sar_content_from_alert(
        self,
        alert: Dict[str, Any],
        officer_notes: str,
        generated_by: str,
        alert_type: str
    ) -> Dict[str, Any]:
        """Prepare SAR content from alert"""
        return sar_context_service.build_sar_context(
            alert_id=alert.get("alert_id", ""),
            generated_by=generated_by,
            officer_notes=officer_notes,
            sar_id=_generate_sar_id(),
        )

    def _safe_text(self, value: Any, fallback: str = "Not Available") -> str:
        if value is None:
            return fallback
        if isinstance(value, float) and math.isnan(value):
            return fallback
        text = str(value).strip()
        if not text or text.lower() in {"none", "nan", "null", "[]"}:
            return fallback
        return text

    def _safe_number(self, value: Any, default: float | None = None) -> float | None:
        try:
            if value in (None, ""):
                return default
            number = float(value)
            if math.isnan(number):
                return default
            return number
        except Exception:
            return default

    def _safe_datetime_text(self, value: Any) -> str:
        text = self._safe_text(value, fallback="")
        if not text:
            return "Not Available"
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return parsed.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return text

    def _as_bullets(self, value: Any) -> list[str]:
        if value in (None, "", [], {}):
            return []
        if isinstance(value, list):
            return [self._safe_text(item, fallback="").strip() for item in value if self._safe_text(item, fallback="").strip()]
        text = str(value).strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [self._safe_text(item, fallback="").strip() for item in parsed if self._safe_text(item, fallback="").strip()]
        except Exception:
            pass
        chunks = [chunk.strip() for chunk in re.split(r"\n+|\r+|;", text) if chunk.strip()]
        if len(chunks) > 1:
            return chunks
        if text.startswith("[") and text.endswith("]"):
            return [text.strip("[] ")]
        return [text]

    def _section_title(self, text: str, styles: Dict[str, ParagraphStyle]) -> Paragraph:
        return Paragraph(text, styles["SectionHeader"])

    def _kv_table(self, rows: list[tuple[str, Any]], styles: Dict[str, ParagraphStyle], widths: list[float] | None = None) -> Table:
        table_rows = []
        for label, value in rows:
            table_rows.append([
                Paragraph(f"<b>{label}</b>", styles["LabelCell"]),
                Paragraph(self._safe_text(value), styles["ValueCell"]),
            ])

        table = Table(table_rows, colWidths=widths or [2.2 * inch, 4.95 * inch], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#F8FAFC"), colors.HexColor("#EEF2F7")]),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return table

    def _summary_box(self, report_id: str, generated_on: str, generated_by: str, runtime_session: str, styles: Dict[str, ParagraphStyle]) -> Table:
        rows = [
            [Paragraph("<b>Report ID</b>", styles["LabelCell"]), Paragraph(self._safe_text(report_id), styles["ValueCell"])],
            [Paragraph("<b>Generated On</b>", styles["LabelCell"]), Paragraph(self._safe_text(generated_on), styles["ValueCell"])],
            [Paragraph("<b>Generated By</b>", styles["LabelCell"]), Paragraph(self._safe_text(generated_by), styles["ValueCell"])],
            [Paragraph("<b>Runtime Session</b>", styles["LabelCell"]), Paragraph(self._safe_text(runtime_session), styles["ValueCell"])],
        ]
        table = Table(rows, colWidths=[1.6 * inch, 5.5 * inch], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor("#1E293B")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        return table

    def _risk_bar(self, risk_score: float, styles: Dict[str, ParagraphStyle]) -> Table:
        score = max(0.0, min(100.0, self._safe_number(risk_score, 0.0) or 0.0))
        filled = max(1, min(20, int(round(score / 5.0))))
        empty = 20 - filled
        color = colors.HexColor("#16A34A") if score <= 30 else colors.HexColor("#F59E0B") if score <= 70 else colors.HexColor("#DC2626")
        bar = Paragraph(
            f'<font color="#FFFFFF">{"█" * filled}</font><font color="#CBD5E1">{"░" * empty}</font>',
            styles["RiskBar"],
        )
        score_chip = Paragraph(
            f'<para align="center"><b>{score:.0f}%</b></para>',
            styles["DecisionBadgeWhite"],
        )
        table = Table([[bar, score_chip]], colWidths=[5.5 * inch, 0.95 * inch], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), color),
            ("BACKGROUND", (1, 0), (1, 0), color),
            ("BOX", (0, 0), (-1, -1), 0.8, color),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return table

    def _decision_badge(self, decision: str, styles: Dict[str, ParagraphStyle]) -> Table:
        normalized = self._safe_text(decision, fallback="PENDING INVESTIGATION").upper()
        badge_color = {
            "ALLOW": colors.HexColor("#16A34A"),
            "REVIEW": colors.HexColor("#D97706"),
            "SUSPICIOUS": colors.HexColor("#DC2626"),
            "BLOCK": colors.HexColor("#991B1B"),
        }.get(normalized, colors.HexColor("#475569"))
        table = Table([[Paragraph(f"<para align='center'><b>{normalized}</b></para>", styles["DecisionBadgeWhite"])]], colWidths=[1.4 * inch], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), badge_color),
            ("BOX", (0, 0), (-1, -1), 0.8, badge_color),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return table

    def _bullet_paragraphs(self, values: Any, styles: Dict[str, ParagraphStyle]) -> list[Any]:
        items = self._as_bullets(values)
        if not items:
            return [Paragraph("No Evidence Attached", styles["Body"])]
        bullet_items = [ListItem(Paragraph(self._safe_text(item, fallback=""), styles["BulletItem"]), leftIndent=6) for item in items]
        return [ListFlowable(bullet_items, bulletType="bullet", start="•", leftIndent=10, bulletFontName="Helvetica", bulletFontSize=9)]

    def _make_styles(self) -> Dict[str, ParagraphStyle]:
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=2,
        ))
        styles.add(ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1D4ED8"),
            spaceAfter=8,
        ))
        styles.add(ParagraphStyle(
            name="SectionHeader",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=colors.white,
            alignment=TA_LEFT,
            backColor=colors.HexColor("#334155"),
            borderPadding=(6, 8, 6),
            spaceBefore=10,
            spaceAfter=6,
        ))
        styles.add(ParagraphStyle(
            name="Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12,
            textColor=colors.HexColor("#0F172A"),
        ))
        styles.add(ParagraphStyle(
            name="LabelCell",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.9,
            leading=11,
            textColor=colors.HexColor("#334155"),
        ))
        styles.add(ParagraphStyle(
            name="ValueCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.9,
            leading=11,
            textColor=colors.HexColor("#0F172A"),
        ))
        styles.add(ParagraphStyle(
            name="BulletItem",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0F172A"),
        ))
        styles.add(ParagraphStyle(
            name="TableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.6,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.white,
        ))
        styles.add(ParagraphStyle(
            name="SmallBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.4,
            leading=10,
            textColor=colors.HexColor("#0F172A"),
        ))
        styles.add(ParagraphStyle(
            name="DecisionBadgeWhite",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.white,
        ))
        styles.add(ParagraphStyle(
            name="RiskBar",
            parent=styles["BodyText"],
            fontName="Courier-Bold",
            fontSize=8.8,
            leading=10,
            alignment=TA_LEFT,
            textColor=colors.white,
        ))
        return styles

    def _build_action_rows(self, sar_content: Dict[str, Any]) -> list[list[Any]]:
        generated_on = self._safe_datetime_text(sar_content.get("generated_at"))
        created_at = self._safe_datetime_text(sar_content.get("created_at"))
        updated_at = self._safe_datetime_text(sar_content.get("updated_at"))
        rows = [
            ["Generated", self._safe_text(sar_content.get("generated_by")), generated_on, self._safe_text(sar_content.get("status"), "Pending Investigation")],
        ]
        if created_at != "Not Available":
            rows.append(["Case Created", self._safe_text(sar_content.get("assigned_officer"), "Pending Investigation"), created_at, self._safe_text(sar_content.get("status"), "Pending Investigation")])
        if updated_at != "Not Available":
            rows.append(["Last Updated", self._safe_text(sar_content.get("generated_by")), updated_at, self._safe_text(sar_content.get("status"), "Pending Investigation")])
        return rows

    def _build_audit_rows(self, sar_content: Dict[str, Any]) -> list[list[Any]]:
        generated_on = self._safe_datetime_text(sar_content.get("generated_at"))
        created_at = self._safe_datetime_text(sar_content.get("created_at"))
        updated_at = self._safe_datetime_text(sar_content.get("updated_at"))
        rows = [
            [generated_on, "SAR Generated", self._safe_text(sar_content.get("generated_by"), "System"), self._safe_text(sar_content.get("resolution"), "No officer remarks available.")],
            [created_at, "Case Created", self._safe_text(sar_content.get("assigned_officer"), "Pending Investigation"), self._safe_text(sar_content.get("reason"), "No Evidence Attached")],
        ]
        if updated_at != "Not Available":
            rows.append([updated_at, self._safe_text(sar_content.get("status"), "Status Updated"), self._safe_text(sar_content.get("generated_by"), "System"), self._safe_text(sar_content.get("officer_notes"), "No officer remarks available.")])
        return rows

    def _render_header_footer(self, canvas: canvas.Canvas, doc: Any) -> None:
        canvas.saveState()
        width, height = letter
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setFillColor(colors.HexColor("#0F172A"))
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawCentredString(width / 2.0, height - 32, "TRUSTVAULT AML SYSTEM")
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(colors.HexColor("#1D4ED8"))
        canvas.drawCentredString(width / 2.0, height - 46, "Suspicious Activity Report (SAR)")
        canvas.setStrokeColor(colors.HexColor("#334155"))
        canvas.setLineWidth(0.7)
        canvas.line(doc.leftMargin, height - 56, width - doc.rightMargin, height - 56)

        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.6)
        canvas.line(doc.leftMargin, 44, width - doc.rightMargin, 44)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawCentredString(width / 2.0, 33, "TrustVault AML Compliance Platform")
        canvas.drawCentredString(width / 2.0, 24, "Confidential Document")
        canvas.drawCentredString(width / 2.0, 15, "Generated automatically by TrustVault AML Engine")
        canvas.restoreState()

    def _generate_pdf(self, sar_content: Dict[str, Any], output_path: Path) -> None:
        """Generate PDF using ReportLab"""
        if not HAS_REPORTLAB:
            raise ImportError("reportlab not installed")

        ensure_parent_dir(output_path)
        styles = self._make_styles()
        story: list[Any] = []

        class _NumberedCanvas(canvas.Canvas):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._saved_page_states: list[dict[str, Any]] = []

            def showPage(self):
                self._saved_page_states.append(dict(self.__dict__))
                self._startPage()

            def save(self):
                page_count = len(self._saved_page_states)
                for page_state in self._saved_page_states:
                    self.__dict__.update(page_state)
                    self.setFont("Helvetica", 7.5)
                    self.setFillColor(colors.HexColor("#475569"))
                    self.drawRightString(letter[0] - 0.72 * inch, 15, f"Page {self._pageNumber} of {page_count}")
                    super().showPage()
                super().save()

        report_id = self._safe_text(sar_content.get("sar_id"), fallback="Not Available")
        generated_on = self._safe_datetime_text(sar_content.get("generated_at"))
        generated_by = self._safe_text(sar_content.get("generated_by"), fallback="Not Available")
        runtime_session = self._safe_text(get_runtime_session_id(), fallback="Not Available")

        story.append(Spacer(1, 0.35 * inch))
        story.append(Paragraph("TRUSTVAULT AML SYSTEM", styles["ReportTitle"]))
        story.append(Paragraph("Suspicious Activity Report (SAR)", styles["ReportSubtitle"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#334155"), spaceBefore=4, spaceAfter=8))

        story.append(KeepTogether([
            self._summary_box(report_id, generated_on, generated_by, runtime_session, styles),
            Spacer(1, 0.12 * inch),
        ]))

        section_order = [
            ("CASE INFORMATION", self._kv_table([
                ("Case ID", sar_content.get("case_id")),
                ("Alert ID", sar_content.get("alert_id")),
                ("Transaction ID", sar_content.get("transaction_id")),
                ("Status", sar_content.get("status")),
                ("Priority", sar_content.get("priority")),
                ("Queue", sar_content.get("assigned_queue", sar_content.get("queue"))),
            ], styles)),
            ("CUSTOMER INFORMATION", self._kv_table([
                ("User ID", sar_content.get("user_id")),
                ("Account ID", sar_content.get("account_id")),
                ("Risk Band", sar_content.get("risk_band")),
                ("Account Age", sar_content.get("account_age")),
                ("Identity Trust Score", sar_content.get("identity_trust_score")),
                ("Device Trust Score", sar_content.get("device_trust_score")),
            ], styles)),
            ("TRANSACTION DETAILS", self._kv_table([
                ("Sender", sar_content.get("sender_id", sar_content.get("user_id"))),
                ("Receiver", sar_content.get("receiver_id")),
                ("Amount", sar_content.get("amount")),
                ("Currency", sar_content.get("currency")),
                ("Channel", sar_content.get("channel")),
                ("Location", sar_content.get("location")),
                ("Timestamp", sar_content.get("timestamp", sar_content.get("created_at"))),
                ("Scenario", sar_content.get("scenario")),
                ("Scenario Variant", sar_content.get("scenario_variant")),
            ], styles)),
        ]

        for title_text, block in section_order:
            story.append(self._section_title(title_text, styles))
            story.append(block)
            story.append(Spacer(1, 0.09 * inch))

        story.append(self._section_title("AI RISK ANALYSIS", styles))
        risk_score = self._safe_number(sar_content.get("risk_score"), 0.0) or 0.0
        story.append(self._risk_bar(risk_score, styles))
        risk_rows = [
            ("Overall Risk Score", f"{risk_score:.2f}"),
            ("Behavior Score", sar_content.get("behavior_score")),
            ("Sequence Score", sar_content.get("sequence_score")),
            ("Velocity Score", sar_content.get("velocity_score", sar_content.get("transaction_velocity_score"))),
            ("Graph Score", sar_content.get("graph_score")),
            ("Confidence Score", sar_content.get("confidence_score", sar_content.get("confidence"))),
        ]
        story.append(Spacer(1, 0.08 * inch))
        story.append(self._kv_table(risk_rows, styles))
        story.append(Spacer(1, 0.08 * inch))
        story.append(self._decision_badge(sar_content.get("decision", sar_content.get("final_decision", "PENDING INVESTIGATION")), styles))

        story.append(self._section_title("NETWORK INTELLIGENCE", styles))
        story.append(self._kv_table([
            ("Hop Distance", sar_content.get("hop_distance")),
            ("Known Fraud Connections", sar_content.get("known_fraud_connections")),
            ("Cluster Size", sar_content.get("cluster_size")),
            ("Community Risk", sar_content.get("community_risk")),
            ("Network Role", sar_content.get("network_role")),
        ], styles))

        story.append(self._section_title("RISK EXPLANATION", styles))
        story.extend(self._bullet_paragraphs(sar_content.get("reasons") or sar_content.get("reason") or sar_content.get("metadata", {}).get("reasons"), styles))

        story.append(self._section_title("OFFICER NOTES", styles))
        officer_rows = [
            ("Assigned Officer", sar_content.get("assigned_officer")),
            ("Officer Remarks", sar_content.get("officer_notes")),
            ("Investigation Summary", sar_content.get("resolution", sar_content.get("summary"))),
        ]
        story.append(self._kv_table(officer_rows, styles))
        story.append(Paragraph(self._safe_text(sar_content.get("officer_notes"), fallback="No officer remarks available."), styles["Body"]))

        story.append(self._section_title("ACTION TAKEN", styles))
        action_rows = self._build_action_rows(sar_content)
        action_table = Table([
            [Paragraph("<b>Action</b>", styles["TableHeader"]), Paragraph("<b>Officer</b>", styles["TableHeader"]), Paragraph("<b>Timestamp</b>", styles["TableHeader"]), Paragraph("<b>Status</b>", styles["TableHeader"])],
            *[[Paragraph(self._safe_text(row[0]), styles["SmallBody"]), Paragraph(self._safe_text(row[1]), styles["SmallBody"]), Paragraph(self._safe_text(row[2]), styles["SmallBody"]), Paragraph(self._safe_text(row[3]), styles["SmallBody"])] for row in action_rows],
        ], colWidths=[1.65 * inch, 1.65 * inch, 2.0 * inch, 1.45 * inch], hAlign="LEFT")
        action_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(action_table)

        story.append(self._section_title("AUDIT TRAIL", styles))
        audit_rows = self._build_audit_rows(sar_content)
        audit_table = Table([
            [Paragraph("<b>Timestamp</b>", styles["TableHeader"]), Paragraph("<b>Action</b>", styles["TableHeader"]), Paragraph("<b>Performed By</b>", styles["TableHeader"]), Paragraph("<b>Remarks</b>", styles["TableHeader"])],
            *[[Paragraph(self._safe_text(row[0]), styles["SmallBody"]), Paragraph(self._safe_text(row[1]), styles["SmallBody"]), Paragraph(self._safe_text(row[2]), styles["SmallBody"]), Paragraph(self._safe_text(row[3]), styles["SmallBody"])] for row in audit_rows],
        ], colWidths=[1.55 * inch, 1.45 * inch, 1.45 * inch, 2.3 * inch], hAlign="LEFT")
        audit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(audit_table)

        story.append(Spacer(1, 0.12 * inch))
        story.append(Paragraph("TrustVault AML Compliance Platform · Confidential Document · Generated automatically by TrustVault AML Engine", styles["SmallBody"]))

        frame = Frame(
            letter[0] * 0 + 0.72 * inch,
            0.78 * inch,
            letter[0] - 1.44 * inch,
            letter[1] - 1.75 * inch,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
            id="normal",
        )
        doc = BaseDocTemplate(
            str(output_path),
            pagesize=letter,
            leftMargin=0.72 * inch,
            rightMargin=0.72 * inch,
            topMargin=0.92 * inch,
            bottomMargin=0.78 * inch,
            title="TrustVault AML Suspicious Activity Report",
            author="TrustVault AML Engine",
        )
        doc.addPageTemplates([PageTemplate(id="sar", frames=[frame], onPage=self._render_header_footer)])
        doc.build(story, canvasmaker=_NumberedCanvas)

    def _generate_fallback_pdf(self, sar_content: Dict[str, Any], output_path: Path) -> None:
        """Generate a minimal PDF SAR when ReportLab is unavailable."""
        ensure_parent_dir(output_path)
        lines = [
            "TRUSTVAULT AML SYSTEM",
            "Suspicious Activity Report (SAR)",
            "",
            f"Report ID: {self._safe_text(sar_content.get('sar_id'))}",
            f"Generated On: {self._safe_datetime_text(sar_content.get('generated_at'))}",
            f"Generated By: {self._safe_text(sar_content.get('generated_by'))}",
            f"Runtime Session: {self._safe_text(get_runtime_session_id())}",
            "",
            "CASE INFORMATION",
            f"Case ID: {self._safe_text(sar_content.get('case_id'))}",
            f"Alert ID: {self._safe_text(sar_content.get('alert_id'))}",
            f"Transaction ID: {self._safe_text(sar_content.get('transaction_id'))}",
            f"Status: {self._safe_text(sar_content.get('status'))}",
            f"Priority: {self._safe_text(sar_content.get('priority'))}",
            f"Queue: {self._safe_text(sar_content.get('assigned_queue', sar_content.get('queue')))}",
            "",
            "CUSTOMER INFORMATION",
            f"User ID: {self._safe_text(sar_content.get('user_id'))}",
            f"Account ID: {self._safe_text(sar_content.get('account_id'))}",
            f"Risk Band: {self._safe_text(sar_content.get('risk_band'))}",
            f"Account Age: {self._safe_text(sar_content.get('account_age'))}",
            f"Identity Trust Score: {self._safe_text(sar_content.get('identity_trust_score'))}",
            f"Device Trust Score: {self._safe_text(sar_content.get('device_trust_score'))}",
            "",
            "TRANSACTION DETAILS",
            f"Sender: {self._safe_text(sar_content.get('sender_id', sar_content.get('user_id')))}",
            f"Receiver: {self._safe_text(sar_content.get('receiver_id'))}",
            f"Amount: {self._safe_text(sar_content.get('amount'))}",
            f"Currency: {self._safe_text(sar_content.get('currency'))}",
            f"Channel: {self._safe_text(sar_content.get('channel'))}",
            f"Location: {self._safe_text(sar_content.get('location'))}",
            f"Timestamp: {self._safe_datetime_text(sar_content.get('timestamp', sar_content.get('created_at')))}",
            f"Scenario: {self._safe_text(sar_content.get('scenario'))}",
            f"Scenario Variant: {self._safe_text(sar_content.get('scenario_variant'))}",
            "",
            "AI RISK ANALYSIS",
            f"Overall Risk Score: {self._safe_text(sar_content.get('risk_score'))}",
            f"Behavior Score: {self._safe_text(sar_content.get('behavior_score'))}",
            f"Sequence Score: {self._safe_text(sar_content.get('sequence_score'))}",
            f"Velocity Score: {self._safe_text(sar_content.get('velocity_score', sar_content.get('transaction_velocity_score')))}",
            f"Graph Score: {self._safe_text(sar_content.get('graph_score'))}",
            f"Confidence Score: {self._safe_text(sar_content.get('confidence_score', sar_content.get('confidence')))}",
            f"Final Decision: {self._safe_text(sar_content.get('decision', sar_content.get('final_decision')))}",
            "",
            "NETWORK INTELLIGENCE",
            f"Hop Distance: {self._safe_text(sar_content.get('hop_distance'))}",
            f"Known Fraud Connections: {self._safe_text(sar_content.get('known_fraud_connections'))}",
            f"Cluster Size: {self._safe_text(sar_content.get('cluster_size'))}",
            f"Community Risk: {self._safe_text(sar_content.get('community_risk'))}",
            f"Network Role: {self._safe_text(sar_content.get('network_role'))}",
            "",
            "RISK EXPLANATION",
        ]
        bullets = self._as_bullets(sar_content.get("reasons") or sar_content.get("reason") or [])
        if bullets:
            lines.extend([f"• {bullet}" for bullet in bullets])
        else:
            lines.append("• No Evidence Attached")
        lines.extend([
            "",
            "OFFICER NOTES",
            f"Assigned Officer: {self._safe_text(sar_content.get('assigned_officer'))}",
            f"Officer Remarks: {self._safe_text(sar_content.get('officer_notes'), 'No officer remarks available.')}",
            f"Investigation Summary: {self._safe_text(sar_content.get('resolution'), 'Pending Investigation')}",
            "",
            "ACTION TAKEN",
            f"Acknowledged: {self._safe_text(sar_content.get('generated_by'))}",
            f"Escalated: {self._safe_text(sar_content.get('escalated_by'))}",
            f"Debit Freeze: {self._safe_text(sar_content.get('freeze_status'))}",
            f"EDD Requested: {self._safe_text(sar_content.get('edd_status'))}",
            f"SAR Generated: {self._safe_text(sar_content.get('generated_by'))}",
            f"Case Closed: {self._safe_text(sar_content.get('status'))}",
            "",
            "AUDIT TRAIL",
            f"Timestamp: {self._safe_datetime_text(sar_content.get('generated_at'))} | Action: SAR Generated | Performed By: {self._safe_text(sar_content.get('generated_by'))}",
            f"Timestamp: {self._safe_datetime_text(sar_content.get('updated_at'))} | Action: Case Updated | Performed By: {self._safe_text(sar_content.get('assigned_officer'))}",
            "",
            "TrustVault AML Compliance Platform",
            "Confidential Document",
            "Generated automatically by TrustVault AML Engine",
        ])

        def _escape_pdf_text(text: str) -> str:
            return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        content_lines = ["BT", "/F1 11 Tf", "72 760 Td"]
        for index, line in enumerate(lines):
            safe_line = _escape_pdf_text(line)
            if index == 0:
                content_lines.append(f"({safe_line}) Tj")
            else:
                content_lines.append(f"0 -13 Td ({safe_line}) Tj")
        content_lines.append("ET")
        stream = "\n".join(content_lines).encode("latin-1", errors="replace")

        objects: list[bytes] = []
        objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
        objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
        objects.append(
            b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
        )
        objects.append(
            f"4 0 obj<< /Length {len(stream)} >>stream\n".encode("latin-1") + stream + b"\nendstream\nendobj\n"
        )
        objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for obj in objects:
            offsets.append(len(pdf))
            pdf.extend(obj)
        xref_start = len(pdf)
        pdf.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
        pdf.extend(
            b"trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n"
            + str(xref_start).encode("latin-1")
            + b"\n%%EOF\n"
        )

        with open(output_path, "wb") as f:
            f.write(pdf)

    def _record_sar(self, sar_record: Dict[str, Any]) -> None:
        """Record SAR metadata"""
        try:
            _ensure_sar_storage()
            df = pd.read_csv(SAR_METADATA_FILE)
        except Exception:
            df = pd.DataFrame(columns=SAR_METADATA_COLUMNS)

        df = pd.concat([df, pd.DataFrame([sar_record])], ignore_index=True)
        _atomic_write_csv(df, SAR_METADATA_FILE)

    def get_sar_reports(self) -> list:
        """Get all SAR reports"""
        try:
            _ensure_sar_storage()
            df = pd.read_csv(SAR_METADATA_FILE)
            return df.to_dict("records")
        except Exception:
            return []

    def get_sar_report(self, sar_id: str) -> Optional[Dict[str, Any]]:
        """Get specific SAR report"""
        try:
            reports = self.get_sar_reports()
            for report in reports:
                if str(report.get("sar_id", "")) == str(sar_id):
                    return report
        except Exception:
            pass
        return None


# Global instance
sar_generation_service = SARGenerationService()

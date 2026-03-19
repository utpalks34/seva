# complaints/report_service.py
"""
PDF Report Generation Service for SCFMS.
Uses ReportLab to generate professional government-grade PDF reports.
"""
import io
import logging
from datetime import date, timedelta

from django.utils import timezone
from django.db.models import Count, Avg, Q

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

logger = logging.getLogger(__name__)

# ── Brand colours ──────────────────────────────────────────
TEAL    = colors.HexColor('#0f766e')
CYAN    = colors.HexColor('#06b6d4')
AMBER   = colors.HexColor('#f59e0b')
GREEN   = colors.HexColor('#10b981')
RED     = colors.HexColor('#ef4444')
INDIGO  = colors.HexColor('#6366f1')
SLATE   = colors.HexColor('#475569')
LIGHT   = colors.HexColor('#f1f5f9')
WHITE   = colors.white
BLACK   = colors.HexColor('#0f172a')

STATUS_NAMES   = {'P': 'Pending', 'I': 'In Progress', 'R': 'Resolved'}
CATEGORY_NAMES = {
    'RO': 'Roads/Potholes',
    'GA': 'Garbage/Waste',
    'UT': 'Utilities',
    'PB': 'Public Behavior',
    'OT': 'Other',
}


def _styles():
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('rpt_title',
            fontName='Helvetica-Bold', fontSize=22,
            textColor=TEAL, spaceAfter=4, alignment=TA_CENTER),
        'subtitle': ParagraphStyle('rpt_sub',
            fontName='Helvetica', fontSize=11,
            textColor=SLATE, spaceAfter=2, alignment=TA_CENTER),
        'section': ParagraphStyle('rpt_section',
            fontName='Helvetica-Bold', fontSize=13,
            textColor=TEAL, spaceBefore=14, spaceAfter=6),
        'body': ParagraphStyle('rpt_body',
            fontName='Helvetica', fontSize=9,
            textColor=BLACK, leading=14),
        'small': ParagraphStyle('rpt_small',
            fontName='Helvetica', fontSize=8,
            textColor=SLATE, leading=12),
        'footer': ParagraphStyle('rpt_footer',
            fontName='Helvetica', fontSize=8,
            textColor=SLATE, alignment=TA_CENTER),
    }


# ── Table helpers ──────────────────────────────────────────
def _header_table(styles, period_label: str, generated_by: str):
    """Top banner with title + meta."""
    now = timezone.now()
    data = [
        [Paragraph('🏛️ Smart Civic Feedback Management System', styles['title'])],
        [Paragraph('Government Complaint Analytics Report', styles['subtitle'])],
        [Paragraph(
            f'Period: {period_label} &nbsp;|&nbsp; '
            f'Generated: {now.strftime("%d %b %Y, %I:%M %p")} &nbsp;|&nbsp; '
            f'By: {generated_by}',
            styles['small']
        )],
    ]
    t = Table(data, colWidths=[17 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT),
        ('ROUNDEDCORNERS', [6]),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    return t


def _kpi_row(kpis: list):
    """Row of KPI boxes: [(label, value, color), ...]"""
    cell_data = []
    for label, value, color in kpis:
        cell_data.append(
            Paragraph(
                f'<font size="22" color="{color.hexval()}">'
                f'<b>{value}</b></font><br/>'
                f'<font size="8" color="#475569">{label}</font>',
                ParagraphStyle('kpi', alignment=TA_CENTER, leading=26)
            )
        )
    col_w = 17 * cm / len(kpis)
    t = Table([cell_data], colWidths=[col_w] * len(kpis))
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


def _data_table(headers, rows, col_widths=None):
    """Standard striped data table."""
    data = [headers] + rows
    if col_widths is None:
        col_widths = [17 * cm / len(headers)] * len(headers)
    t = Table(data, colWidths=col_widths)
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), TEAL),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#f8fafc')]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]
    t.setStyle(TableStyle(style))
    return t


# ── Mini bar chart (pure ReportLab, no matplotlib) ────────
def _bar_chart(labels, values, title, width=17*cm, height=5*cm):
    if not values or max(values, default=0) == 0:
        return None

    drawing = Drawing(width, height + 1.5 * cm)
    chart = VerticalBarChart()
    chart.x = 40
    chart.y = 20
    chart.width = float(width) - 60
    chart.height = float(height) - 10

    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.angle = 20
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.dy = -6
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(values) + max(1, max(values) // 5)
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = TEAL

    drawing.add(chart)
    return drawing


# ── Main report builder ────────────────────────────────────
class ReportService:

    @staticmethod
    def generate_pdf(period: str = 'monthly', generated_by: str = 'Government Official') -> bytes:
        """
        Generate a PDF analytics report.

        Args:
            period: 'weekly' | 'monthly' | 'quarterly' | 'all'
            generated_by: name or email of the requesting GO

        Returns:
            Raw PDF bytes
        """
        from .models import Complaint, Department, DepartmentAssignment

        # ── Date range ────────────────────────────────────
        today = timezone.now().date()
        if period == 'weekly':
            start = today - timedelta(days=7)
            period_label = f'Last 7 days ({start} → {today})'
        elif period == 'quarterly':
            start = today - timedelta(days=90)
            period_label = f'Last 90 days ({start} → {today})'
        elif period == 'monthly':
            start = today - timedelta(days=30)
            period_label = f'Last 30 days ({start} → {today})'
        else:  # 'all'
            start = None
            period_label = 'All Time'

        qs = Complaint.objects.all()
        if start:
            qs = qs.filter(created_at__date__gte=start)

        # ── Aggregate data ────────────────────────────────
        total       = qs.count()
        pending     = qs.filter(status='P').count()
        in_progress = qs.filter(status='I').count()
        resolved    = qs.filter(status='R').count()
        duplicates  = qs.filter(is_duplicate=True).count()
        high_prio   = qs.filter(severity_score__gte=70).count()
        res_rate    = round(resolved / total * 100, 1) if total else 0

        by_category = list(
            qs.values('category')
              .annotate(cnt=Count('id'))
              .order_by('-cnt')
        )
        by_dept = list(
            DepartmentAssignment.objects
              .filter(complaint__in=qs)
              .values('department__department_name', 'department__category')
              .annotate(total=Count('id'), resolved=Count('id', filter=Q(resolved_at__isnull=False)))
              .order_by('-total')
        )

        recent_complaints = list(
            qs.select_related('user')
              .order_by('-created_at')[:10]
        )

        # ── Build PDF ─────────────────────────────────────
        buf    = io.BytesIO()
        styles = _styles()

        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            title='SCFMS Analytics Report',
            author='SCFMS System',
        )

        story = []

        # Header
        story.append(_header_table(styles, period_label, generated_by))
        story.append(Spacer(1, 0.4 * cm))
        story.append(HRFlowable(width='100%', thickness=2, color=TEAL))
        story.append(Spacer(1, 0.4 * cm))

        # ── KPI boxes ─────────────────────────────────────
        story.append(Paragraph('📊 Key Metrics', styles['section']))
        story.append(_kpi_row([
            ('Total Complaints', total, INDIGO),
            ('Pending',          pending, AMBER),
            ('In Progress',      in_progress, CYAN),
            ('Resolved',         resolved, GREEN),
        ]))
        story.append(Spacer(1, 0.3 * cm))
        story.append(_kpi_row([
            ('Resolution Rate', f'{res_rate}%', GREEN),
            ('High Priority',   high_prio, RED),
            ('Duplicates',      duplicates, SLATE),
            ('Period',          period_label.split('(')[0].strip(), TEAL),
        ]))
        story.append(Spacer(1, 0.5 * cm))

        # ── Category breakdown ────────────────────────────
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0')))
        story.append(Paragraph('🗂️ Complaints by Category', styles['section']))

        if by_category:
            cat_labels = [CATEGORY_NAMES.get(r['category'], r['category']) for r in by_category]
            cat_values = [r['cnt'] for r in by_category]

            chart = _bar_chart(cat_labels, cat_values, 'By Category')
            if chart:
                story.append(chart)
                story.append(Spacer(1, 0.2 * cm))

            cat_rows = [
                [CATEGORY_NAMES.get(r['category'], r['category']),
                 str(r['cnt']),
                 f"{round(r['cnt']/total*100, 1)}%" if total else '0%']
                for r in by_category
            ]
            story.append(_data_table(
                ['Category', 'Count', '% of Total'],
                cat_rows,
                col_widths=[9*cm, 4*cm, 4*cm]
            ))
        else:
            story.append(Paragraph('No data for this period.', styles['body']))

        story.append(Spacer(1, 0.5 * cm))

        # ── Status breakdown ──────────────────────────────
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0')))
        story.append(Paragraph('📈 Status Distribution', styles['section']))

        status_data = [
            ['Status', 'Count', '%'],
            ['Pending',     str(pending),     f"{round(pending/total*100,1) if total else 0}%"],
            ['In Progress', str(in_progress), f"{round(in_progress/total*100,1) if total else 0}%"],
            ['Resolved',    str(resolved),    f"{round(resolved/total*100,1) if total else 0}%"],
        ]
        t = Table(status_data, colWidths=[8*cm, 4.5*cm, 4.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), TEAL),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#fef9c3')),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#e0f2fe')),
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#dcfce7')),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5 * cm))

        # ── Department performance ────────────────────────
        if by_dept:
            story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0')))
            story.append(Paragraph('🏢 Department Performance', styles['section']))
            dept_rows = []
            for d in by_dept:
                rate = round(d['resolved'] / d['total'] * 100, 1) if d['total'] else 0
                dept_rows.append([
                    d['department__department_name'],
                    CATEGORY_NAMES.get(d['department__category'], '-'),
                    str(d['total']),
                    str(d['resolved']),
                    f'{rate}%',
                ])
            story.append(_data_table(
                ['Department', 'Category', 'Assigned', 'Resolved', 'Rate'],
                dept_rows,
                col_widths=[5*cm, 4*cm, 2.5*cm, 2.5*cm, 3*cm]
            ))
            story.append(Spacer(1, 0.5 * cm))

        # ── Recent complaints ─────────────────────────────
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0')))
        story.append(Paragraph('📋 Recent Complaints (Top 10)', styles['section']))
        if recent_complaints:
            rc_rows = []
            for c in recent_complaints:
                rc_rows.append([
                    str(c.id),
                    c.title[:40] + ('…' if len(c.title) > 40 else ''),
                    CATEGORY_NAMES.get(c.category, c.category),
                    STATUS_NAMES.get(c.status, c.status),
                    str(int(c.severity_score)) + '%',
                    c.created_at.strftime('%d %b %y'),
                ])
            story.append(_data_table(
                ['ID', 'Title', 'Category', 'Status', 'Severity', 'Filed'],
                rc_rows,
                col_widths=[1.2*cm, 6*cm, 3*cm, 2.5*cm, 2*cm, 2.3*cm]
            ))
        else:
            story.append(Paragraph('No complaints in this period.', styles['body']))

        story.append(Spacer(1, 0.8 * cm))

        # ── Footer ────────────────────────────────────────
        story.append(HRFlowable(width='100%', thickness=1, color=TEAL))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            f'SCFMS — Smart Civic Feedback Management System &nbsp;|&nbsp; '
            f'Confidential Government Report &nbsp;|&nbsp; '
            f'Generated on {timezone.now().strftime("%d %b %Y")}',
            styles['footer']
        ))

        doc.build(story)
        buf.seek(0)
        return buf.read()

from pathlib import Path
from html import escape
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'analysis-report.md'
OUTPUT = ROOT / 'output' / 'pdf' / 'cryptagent-evaluation-report.pdf'
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='CoverTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=24, leading=29, textColor=colors.HexColor('#173b65'), spaceAfter=10))
styles.add(ParagraphStyle(name='H1x', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor('#173b65'), spaceBefore=18, spaceAfter=9, keepWithNext=True))
styles.add(ParagraphStyle(name='H2x', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=13.5, leading=17, textColor=colors.HexColor('#24537a'), spaceBefore=14, spaceAfter=7, keepWithNext=True))
styles.add(ParagraphStyle(name='Bodyx', parent=styles['BodyText'], fontName='Helvetica', fontSize=9.1, leading=13.1, textColor=colors.HexColor('#273747'), spaceAfter=7))
styles.add(ParagraphStyle(name='Smallx', parent=styles['BodyText'], fontName='Helvetica', fontSize=7.5, leading=10, textColor=colors.HexColor('#586b7d'), spaceAfter=5))
styles.add(ParagraphStyle(name='Quote', parent=styles['BodyText'], fontName='Helvetica-Oblique', fontSize=9, leading=13, textColor=colors.HexColor('#5a4525'), leftIndent=11, rightIndent=11, borderWidth=0.6, borderColor=colors.HexColor('#d2a45b'), borderPadding=8, backColor=colors.HexColor('#fff8ec'), spaceAfter=9))
styles.add(ParagraphStyle(name='CodeBlock', fontName='Courier', fontSize=7.2, leading=9, textColor=colors.HexColor('#173b65'), backColor=colors.HexColor('#f2f6fa'), borderColor=colors.HexColor('#dbe5ef'), borderWidth=0.4, borderPadding=7, spaceAfter=9))

def inline(text):
    text = escape(text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'<font name="Courier">\1</font>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    return text

def parse_table(rows):
    cells = [[cell.strip() for cell in row.strip().split('|')[1:-1]] for row in rows]
    cells = [cells[0]] + cells[2:]
    data = [[Paragraph(inline(cell), styles['Smallx']) for cell in row] for row in cells]
    widths = [168*mm / len(data[0])] * len(data[0])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eaf1f8')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#173b65')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#d9e2ec')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 5), ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    return table

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#d8e1ea'))
    canvas.line(doc.leftMargin, 14*mm, A4[0]-doc.rightMargin, 14*mm)
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(colors.HexColor('#60758b'))
    canvas.drawString(doc.leftMargin, 9*mm, 'CRYPTAGENT - Evaluation report')
    canvas.drawRightString(A4[0]-doc.rightMargin, 9*mm, 'Page %d' % doc.page)
    canvas.restoreState()

lines = SOURCE.read_text(encoding='utf-8').splitlines()
story = []
i = 0
first_title = True
while i < len(lines):
    line = lines[i]
    if not line.strip(): i += 1; continue
    if line.startswith('```'):
        code = []; i += 1
        while i < len(lines) and not lines[i].startswith('```'): code.append(lines[i]); i += 1
        story.append(Preformatted('\n'.join(code), styles['CodeBlock'])); i += 1; continue
    if line.startswith('|'):
        table_lines = []
        while i < len(lines) and lines[i].startswith('|'): table_lines.append(lines[i]); i += 1
        story.extend([parse_table(table_lines), Spacer(1, 5)]); continue
    if line.startswith('# '):
        story.append(Paragraph(inline(line[2:]), styles['CoverTitle'] if first_title else styles['H1x'])); first_title = False; i += 1; continue
    if line.startswith('## '): story.append(Paragraph(inline(line[3:]), styles['H1x'])); i += 1; continue
    if line.startswith('### '): story.append(Paragraph(inline(line[4:]), styles['H2x'])); i += 1; continue
    if line.startswith('> '): story.append(Paragraph(inline(line[2:]), styles['Quote'])); i += 1; continue
    if re.match(r'^\d+\. ', line): story.append(Paragraph(inline(line), styles['Bodyx'])); i += 1; continue
    if line.startswith('- '): story.append(Paragraph('• ' + inline(line[2:]), styles['Bodyx'])); i += 1; continue
    paragraph = [line]; i += 1
    while i < len(lines) and lines[i].strip() and not re.match(r'^(#|```|\||> |- |\d+\. )', lines[i]): paragraph.append(lines[i]); i += 1
    story.append(Paragraph('<br/>'.join(inline(p) for p in paragraph), styles['Bodyx']))

doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=21*mm, rightMargin=21*mm, topMargin=19*mm, bottomMargin=21*mm, title='Cryptagent Evaluation Report', author='Cryptagent')
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT)

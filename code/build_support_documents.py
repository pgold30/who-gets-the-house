"""Readable PDFs from the release's editable README and author disclosure."""
from pathlib import Path
import re,html
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Preformatted,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
ROOT=Path(__file__).resolve().parents[1]
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyRelease',fontName='Times-Roman',fontSize=10.5,leading=14,spaceAfter=8,splitLongWords=True))
styles.add(ParagraphStyle(name='HeadingRelease',fontName='Helvetica-Bold',fontSize=13,leading=17,spaceBefore=12,spaceAfter=7,keepWithNext=True))
styles.add(ParagraphStyle(name='TitleRelease',fontName='Helvetica-Bold',fontSize=20,leading=24,spaceAfter=16))
styles.add(ParagraphStyle(name='CodeRelease',fontName='Courier',fontSize=7.5,leading=10,spaceAfter=9))
def footer(c,doc):
    c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#555555'));c.drawString(54,32,'WGTH-2026-09-10-JHE-S1');c.drawRightString(558,32,str(doc.page))
def build(src,dest):
    story=[];buf=[];code=False;codebuf=[]
    def flush():
        if buf:story.append(Paragraph(html.escape(' '.join(buf)),styles['BodyRelease']));buf.clear()
    for line in src.read_text().splitlines():
        if line.startswith('```'):
            flush()
            if code:
                story.append(Preformatted('\n'.join(codebuf),styles['CodeRelease'],maxLineLength=106));codebuf=[]
            code=not code;continue
        if code:codebuf.append(line);continue
        if not line.strip():flush();continue
        if line.startswith('# '):flush();story.append(Paragraph(html.escape(line[2:]),styles['TitleRelease']));continue
        if line.startswith('## '):flush();story.append(Paragraph(html.escape(line[3:]),styles['HeadingRelease']));continue
        if line.startswith('- '):flush();story.append(Paragraph('&#8226; '+html.escape(line[2:]),styles['BodyRelease']));continue
        buf.append(line)
    flush()
    SimpleDocTemplate(str(dest),pagesize=(612,792),leftMargin=54,rightMargin=54,topMargin=48,bottomMargin=48,title=src.stem,author='Pablo Loschi').build(story,onFirstPage=footer,onLaterPages=footer)
if __name__=='__main__':
    build(ROOT/'README.md',ROOT/'README.pdf')
    build(ROOT/'paper/disclosure.md',ROOT/'paper/disclosure.pdf')
    print('Built README.pdf and author disclosure.pdf.')

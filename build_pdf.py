"""Render the same paper content with ReportLab when native TeX is unavailable.

This is a Python-rendered PDF, not a claim of a successful LaTeX compilation.
The paper.tex source and logo asset remain available for a TeX-capable editor.
"""
import html
import re
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT/'output'/'pdf'
OUTPUT.mkdir(parents=True,exist_ok=True)
styles = {
    'body': ParagraphStyle('body',fontName='Times-Roman',fontSize=11,leading=14,
                           alignment=TA_JUSTIFY,spaceAfter=7),
    'h1': ParagraphStyle('h1',fontName='Times-Bold',fontSize=13,leading=16,spaceBefore=6,spaceAfter=8),
    'h2': ParagraphStyle('h2',fontName='Times-Bold',fontSize=11,leading=14,spaceBefore=4,spaceAfter=5),
    'title': ParagraphStyle('title',fontName='Times-Bold',fontSize=21,leading=27,alignment=TA_CENTER,spaceAfter=12),
    'subtitle': ParagraphStyle('subtitle',fontName='Times-Roman',fontSize=12,leading=15,alignment=TA_CENTER,spaceAfter=8),
    'center': ParagraphStyle('center',fontName='Times-Roman',fontSize=10.5,leading=13,alignment=TA_CENTER,spaceAfter=3),
    'small': ParagraphStyle('small',fontName='Times-Roman',fontSize=9.5,leading=12,spaceAfter=3),
    'ref': ParagraphStyle('ref',fontName='Times-Roman',fontSize=9.5,leading=12,spaceAfter=7),
}
citations = {'ostep':'1','cornell':'2','osc':'3','sklearn':'4','lykouris':'5'}

def clean(text):
    text = re.sub(r'\s+',' ',text.strip())
    text = re.sub(r'\\cite\{([^}]+)\}',lambda m:'['+', '.join(citations[k.strip()] for k in m[1].split(','))+']',text)
    text = re.sub(r'Table~\\ref\{[^}]+\}','Table 1',text)
    text = re.sub(r'Figure~\\ref\{[^}]+\}','Figure 1',text)
    text = re.sub(r'\\url\{([^}]+)\}',lambda m:'URLLINKSTART'+m[1]+'URLLINKEND',text)
    text = re.sub(r'\\(?:texttt|emph)\{([^}]+)\}',r'\1',text)
    text = text.replace(r'\times',' x ').replace('$','').replace(r'\%','%').replace(r'\_','_')
    text = text.replace('---',' - ').replace('--','-').replace('~',' ')
    text = html.escape(text).replace('&lt;br/&gt;','<br/>')
    text = re.sub(r'URLLINKSTART(.*?)URLLINKEND',lambda m:f'<link href="{m[1]}" color="black">{m[1]}</link>',text)
    return text

def p(text, style='body'):
    return Paragraph(clean(text),styles[style])

def make_table(rows, widths):
    rows=[[p(cell,'small') for cell in row] for row in rows]
    t=Table(rows,colWidths=widths,hAlign='CENTER')
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,-1),colors.white),
                          ('GRID',(0,0),(-1,-1),.6,colors.black),('LEFTPADDING',(0,0),(-1,-1),6),
                          ('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),
                          ('BOTTOMPADDING',(0,0),(-1,-1),3)]))
    return t

def source_table(token):
    contents=token.split(r'\hline',1)[1].split(r'\end{tabular}',1)[0]
    lines=[]
    for row in contents.split(r'\\'):
        row=row.replace(r'\hline','').strip()
        if '&' in row:
            lines.append([cell.strip() for cell in row.split('&')])
    n=len(lines[0])
    if n==5:
        widths=[65,103,103,103,103]
    elif n==3:
        widths=[120,170,170]
    elif lines[0][0]=='Policy':
        widths=[65,412]
    else:
        widths=[145,332]
    return make_table(lines,widths)

source=(ROOT/'paper.tex').read_text(encoding='utf-8').split(r'\begin{document}',1)[1].split(r'\end{document}',1)[0]
# Remove only the first title block; later centered tables are preserved.
title_end=source.index(r'\end{center}')+len(r'\end{center}')
source=source[title_end:]
source=source.replace(r'\setcounter{page}{1}','')
pages=source.split(r'\newpage')
assert len(pages)==6
story=[]
section_number=0
table_number=0
for page_index,page in enumerate(pages):
    if page_index:
        story.append(PageBreak())
    else:
        logo=Image(str(ROOT/'assets'/'mist-logo.png'))
        logo_ratio=logo.imageHeight/logo.imageWidth
        logo.drawWidth=84
        logo.drawHeight=84*logo_ratio
        story.extend([Spacer(1,15),logo,
                      Spacer(1,10),p('MIST','title'),
                      p('Department of Computer Science and Engineering','center'),Spacer(1,42),
                      p('CSE-307: Operating Systems','subtitle'),
                      p('TERM PAPER - PART B, TRACK 1','center'),Spacer(1,40),
                      p('Page Replacement under a<br/>Changing Access Pattern','title'),
                      p('A Comparison of FIFO, LRU, Optimal,<br/>and a Simple Learned Policy','subtitle'),
                      Spacer(1,36),make_table([
                          ['Submitted by','Fahim Azmul Hasan'],['Student ID','202414014'],
                          ['Section','A'],['Level and term','Level 3, Term 1'],
                          ['Submitted to','Lecturer Khaled Hasan Irfan'],
                          ['Submission date','3 October 2026']], [120,300])])
    tokens=re.split(r'(\\section\{[^}]+\}|\\subsection\{[^}]+\}|\\begin\{abstract\}|\\end\{abstract\}|'
                    r'\\begin\{center\}.*?\\end\{center\}|\\begin\{table\}.*?\\end\{table\}|'
                    r'\\begin\{figure\}.*?\\end\{figure\}|\\begin\{thebibliography\}.*?\\end\{thebibliography\})',page,flags=re.S)
    subsection_number=0
    for token in tokens:
        token=token.strip()
        if not token:
            continue
        if token.startswith(r'\section{'):
            section_number+=1; subsection_number=0
            story.append(p(f'{section_number}. '+re.search(r'\{(.*?)\}',token)[1],'h1'))
        elif token.startswith(r'\subsection{'):
            subsection_number+=1
            story.append(p(f'{section_number}.{subsection_number} '+re.search(r'\{(.*?)\}',token)[1],'h2'))
        elif token==r'\begin{abstract}':
            story.append(p('Abstract','h2'))
        elif token==r'\end{abstract}':
            pass
        elif token.startswith(r'\begin{center}'):
            if r'\begin{tabular}' in token:
                story.append(source_table(token))
            else:
                contents=token.replace(r'\begin{center}','').replace(r'\end{center}','')
                story.append(p(contents,'center'))
            story.append(Spacer(1,7))
        elif token.startswith(r'\begin{table}'):
            table_number+=1
            caption=re.search(r'\\caption\{([^}]+)\}',token)[1]
            story.append(p(f'Table {table_number}. '+caption,'small'))
            story.append(source_table(token));story.append(Spacer(1,8))
        elif token.startswith(r'\begin{figure}'):
            story.append(Image(str(ROOT/'results'/'capacity.png'),width=477,height=172))
            story.append(p('Figure 1. Average hit ratios after the change at four frame counts.','small'))
        elif token.startswith(r'\begin{thebibliography}'):
            refs=re.split(r'\\bibitem\{([^}]+)\}',token)[1:]
            for i in range(0,len(refs),2):
                text=refs[i+1].replace(r'\end{thebibliography}','')
                story.append(p('['+citations[refs[i]]+'] '+text,'ref'))
        else:
            for paragraph in re.split(r'\n\s*\n',token):
                if paragraph.strip():
                    story.append(p(paragraph))

def footer(canvas,doc):
    if doc.page==1:
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(.8)
        canvas.rect(35,35,A4[0]-70,A4[1]-70)
        return
    canvas.setFont('Times-Roman',8)
    canvas.setFillColor(colors.HexColor('#555555'))
    canvas.drawString(48,25,'CSE-307 | Page Replacement | Fahim Azmul Hasan')
    canvas.drawRightString(A4[0]-48,25,str(doc.page-1))

doc=SimpleDocTemplate(str(OUTPUT/'CSE307_Track1_Term_Paper.pdf'),pagesize=A4,
                      rightMargin=48,leftMargin=48,topMargin=43,bottomMargin=42,
                      title='Page Replacement under a Changing Access Pattern',author='Fahim Azmul Hasan')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print('Generated Python-rendered PDF:',OUTPUT/'CSE307_Track1_Term_Paper.pdf')

"""Render the same paper content with ReportLab when native TeX is unavailable.

This is a Python-rendered PDF, not a claim of a successful LaTeX compilation.
The standalone paper.tex remains available for a TeX-capable editor.
"""
import csv
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
    'body': ParagraphStyle('body',fontName='Times-Roman',fontSize=10.5,leading=13.1,
                           alignment=TA_JUSTIFY,spaceAfter=6),
    'h1': ParagraphStyle('h1',fontName='Times-Bold',fontSize=13,leading=16,spaceBefore=6,spaceAfter=8),
    'h2': ParagraphStyle('h2',fontName='Times-Bold',fontSize=11,leading=14,spaceBefore=4,spaceAfter=5),
    'title': ParagraphStyle('title',fontName='Times-Bold',fontSize=17,leading=20,alignment=TA_CENTER,spaceAfter=5),
    'subtitle': ParagraphStyle('subtitle',fontName='Times-Roman',fontSize=12,leading=15,alignment=TA_CENTER,spaceAfter=8),
    'center': ParagraphStyle('center',fontName='Times-Roman',fontSize=10.5,leading=13,alignment=TA_CENTER,spaceAfter=3),
    'small': ParagraphStyle('small',fontName='Times-Roman',fontSize=9,leading=11,spaceAfter=5),
    'ref': ParagraphStyle('ref',fontName='Times-Roman',fontSize=8.7,leading=10.5,spaceAfter=4),
}
citations = {'ostep':'1','cornell':'2','sklearn':'3','lykouris':'4'}

def clean(text):
    text = re.sub(r'\s+',' ',text.strip())
    text = re.sub(r'\\cite\{([^}]+)\}',lambda m:'['+citations[m[1]]+']',text)
    text = re.sub(r'Table~\\ref\{[^}]+\}','Table 1',text)
    text = re.sub(r'Figure~\\ref\{[^}]+\}','Figure 1',text)
    text = re.sub(r'\\url\{([^}]+)\}',lambda m:'URLLINKSTART'+m[1]+'URLLINKEND',text)
    text = re.sub(r'\\(?:texttt|emph)\{([^}]+)\}',r'\1',text)
    text = text.replace(r'\times',' x ').replace('$','').replace(r'\%','%').replace(r'\_','_')
    text = text.replace('---',' - ').replace('--','-').replace('~',' ')
    text = html.escape(text)
    text = re.sub(r'URLLINKSTART(.*?)URLLINKEND',lambda m:f'<link href="{m[1]}" color="#254d78">{m[1]}</link>',text)
    return text

def p(text, style='body'):
    return Paragraph(clean(text),styles[style])

def table_main():
    summary=list(csv.DictReader((ROOT/'results'/'summary.csv').open()))
    rows=[['Scenario','Policy','Before faults','Before hit %','After faults','After hit %','After SD pp']]
    for scenario in ['random','bursty']:
        for policy in ['FIFO','LRU','OPT','Learned']:
            a=next(r for r in summary if (r['scenario'],r['frames'],r['policy'],r['phase'])==(scenario,'16',policy,'before'))
            b=next(r for r in summary if (r['scenario'],r['frames'],r['policy'],r['phase'])==(scenario,'16',policy,'after'))
            rows.append([scenario.title(),policy,f"{float(a['mean_faults']):.1f}",f"{100*float(a['mean_hit']):.2f}",
                         f"{float(b['mean_faults']):.1f}",f"{100*float(b['mean_hit']):.2f}",f"{100*float(b['sd_hit']):.2f}"])
    return make_table(rows,[55,47,75,74,69,72,68])

def make_table(rows, widths):
    rows=[[p(cell,'small') for cell in row] for row in rows]
    t=Table(rows,colWidths=widths,hAlign='CENTER')
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9eef2')),
                          ('LINEABOVE',(0,0),(-1,0),.7,colors.black),('LINEBELOW',(0,0),(-1,0),.5,colors.black),
                          ('LINEBELOW',(0,-1),(-1,-1),.7,colors.black),('LEFTPADDING',(0,0),(-1,-1),4),
                          ('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),3),
                          ('BOTTOMPADDING',(0,0),(-1,-1),1)]))
    return t

source=(ROOT/'paper.tex').read_text(encoding='utf-8').split(r'\begin{document}',1)[1].split(r'\end{document}',1)[0]
# Remove only the first title block; later centered tables are preserved.
title_end=source.index(r'\end{center}')+len(r'\end{center}')
source=source[title_end:]
pages=source.split(r'\newpage')
assert len(pages)==6
story=[]
section_number=0
for page_index,page in enumerate(pages):
    if page_index:
        story.append(PageBreak())
    else:
        story.extend([p('Learned Page Replacement under a Workload Shift','title'),
                      p("A Comparison with FIFO, LRU, and Belady's Optimal Policy",'subtitle'),
                      p('CSE-307: Operating Systems - Part B, Track 1','center'),
                      p('Fahim Azmul Hasan | Student ID: 2024-14014','center'),
                      p('Section A | Level 3, Term 1','center'),
                      p('Submitted to Lecturer Khaled Hasan Irfan','center'),
                      p('3 October 2026','center'),Spacer(1,9)])
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
            contents=token.split(r'\midrule',1)[1].split(r'\bottomrule',1)[0]
            lines=[]
            for line in contents.split(r'\\'):
                if '&' in line:
                    lines.append([x.strip() for x in line.strip().split('&')])
            if 'Recency' in contents:
                story.append(make_table([['Feature','Definition before current access']]+lines,[100,370]))
            else:
                story.append(make_table([['Setting','Value']]+lines,[200,270]))
            story.append(Spacer(1,7))
        elif token.startswith(r'\begin{table}'):
            story.append(p('Table 1. Measured results with 16 frames; 3,000 references per phase and ten seeds.','small'))
            story.append(table_main());story.append(Spacer(1,8))
        elif token.startswith(r'\begin{figure}'):
            story.append(Image(str(ROOT/'results'/'capacity.png'),width=477,height=172))
            story.append(p('Figure 1. After-shift mean hit ratio versus frame capacity, across ten traces. '
                           'The two panels share the same page universe and first-half generator.','small'))
        elif token.startswith(r'\begin{thebibliography}'):
            story.append(p('References','h2'))
            refs=re.split(r'\\bibitem\{([^}]+)\}',token)[1:]
            for i in range(0,len(refs),2):
                text=refs[i+1].replace(r'\end{thebibliography}','')
                story.append(p('['+citations[refs[i]]+'] '+text,'ref'))
        else:
            for paragraph in re.split(r'\n\s*\n',token):
                if paragraph.strip():
                    story.append(p(paragraph))

def footer(canvas,doc):
    canvas.setFont('Times-Roman',8)
    canvas.setFillColor(colors.HexColor('#555555'))
    canvas.drawString(45,25,'CSE-307 | Learned Page Replacement | Fahim Azmul Hasan')
    canvas.drawRightString(A4[0]-45,25,str(doc.page))

doc=SimpleDocTemplate(str(OUTPUT/'CSE307_Track1_Term_Paper.pdf'),pagesize=A4,
                      rightMargin=45,leftMargin=45,topMargin=39,bottomMargin=40,
                      title='Learned Page Replacement under a Workload Shift',author='Fahim Azmul Hasan')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print('Generated Python-rendered PDF:',OUTPUT/'CSE307_Track1_Term_Paper.pdf')

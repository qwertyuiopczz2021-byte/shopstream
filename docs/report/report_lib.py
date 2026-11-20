
# -*- coding: utf-8 -*-
"""Builder helpers for the ShopStream project report."""
import os
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether,
                                PageBreak, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

REPO = r"D:\projects\shopstream"
FIG = os.path.join(REPO, "docs", "report", "figures")

INK = colors.HexColor("#1b1c1e")
MUTED = colors.HexColor("#5f6368")
ACCENT = colors.HexColor("#1a4f8a")
RULE = colors.HexColor("#c9ced6")
CODE_BG = colors.HexColor("#f4f5f7")
CODE_EDGE = colors.HexColor("#d8dbe0")

pdfmetrics.registerFont(TTFont("Segoe", r"C:\Windows\Fonts\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("Segoe-Bold", r"C:\Windows\Fonts\segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("Segoe-Italic", r"C:\Windows\Fonts\segoeuii.ttf"))
pdfmetrics.registerFont(TTFont("Consola", r"C:\Windows\Fonts\consola.ttf"))
pdfmetrics.registerFont(TTFont("Consola-Bold", r"C:\Windows\Fonts\consolab.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("Segoe", normal="Segoe", bold="Segoe-Bold", italic="Segoe-Italic", boldItalic="Segoe-Bold")
registerFontFamily("Consola", normal="Consola", bold="Consola-Bold", italic="Consola", boldItalic="Consola-Bold")

BODY = ParagraphStyle("Body", fontName="Segoe", fontSize=10.2, leading=15.6,
                      textColor=INK, alignment=TA_JUSTIFY, spaceAfter=7)
BULLET = ParagraphStyle("Bullet", parent=BODY, leftIndent=14, bulletIndent=4,
                        spaceAfter=4.5, alignment=TA_LEFT)
H1 = ParagraphStyle("H1", fontName="Segoe-Bold", fontSize=18, leading=22,
                    textColor=ACCENT, spaceBefore=6, spaceAfter=12)
H2 = ParagraphStyle("H2", fontName="Segoe-Bold", fontSize=12.6, leading=16,
                    textColor=INK, spaceBefore=15, spaceAfter=6)
H3 = ParagraphStyle("H3", fontName="Segoe-Bold", fontSize=10.6, leading=14,
                    textColor=INK, spaceBefore=10, spaceAfter=3)
CAPTION = ParagraphStyle("Caption", fontName="Segoe", fontSize=8.6, leading=11.5,
                         textColor=MUTED, alignment=TA_CENTER, spaceBefore=4, spaceAfter=10)
CODEFILE = ParagraphStyle("CodeFile", fontName="Consola", fontSize=8, leading=10,
                          textColor=MUTED, spaceBefore=6, spaceAfter=2)
NOTE = ParagraphStyle("Note", parent=BODY, fontSize=9.4, leading=13.5,
                      leftIndent=10, rightIndent=6, borderPadding=2)
TCELL = ParagraphStyle("TCell", fontName="Segoe", fontSize=8.6, leading=11.4, textColor=INK)
THEAD = ParagraphStyle("THead", fontName="Segoe-Bold", fontSize=8.6, leading=11.4, textColor=colors.white)


def P(text):
    return Paragraph(text, BODY)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Builder:
    def __init__(self, story):
        self.story = story
        self.fig_n = 0
        self.tab_n = 0

    # ---------------------------------------------------------------- headings
    def h1(self, text):
        self.story.append(PageBreak())
        self.story.append(Paragraph(text, H1))

    def h2(self, text):
        self.story.append(Paragraph(text, H2))

    def h3(self, text):
        self.story.append(Paragraph(text, H3))

    def p(self, text):
        self.story.append(P(text))

    def bullets(self, items):
        for it in items:
            self.story.append(Paragraph(it, BULLET, bulletText="\u2022"))
        self.story.append(Spacer(1, 3))

    def note(self, text):
        t = Table([[Paragraph(text, NOTE)]], colWidths=[16.4 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef3f9")),
            ("LINEBEFORE", (0, 0), (0, -1), 2.2, ACCENT),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        self.story.append(t)
        self.story.append(Spacer(1, 8))

    # ------------------------------------------------------------------- code
    def code(self, relpath, first=None, last=None, caption=None, size=7.4):
        path = os.path.join(REPO, relpath)
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        first = first or 1
        last = last or len(lines)
        chunk = lines[first - 1:last]
        width = int(16.4 * cm / (size * 0.60))
        out = []
        for l in chunk:
            l = l.expandtabs(4)
            while len(l) > width:
                cut = l.rfind(" ", 0, width)
                if cut < width * 0.6:
                    cut = width
                out.append(l[:cut].rstrip())
                l = "    " + l[cut:].lstrip()
            out.append(l)
        text = "\n".join(out)
        label = relpath.replace("\\", "/")
        if caption:
            label = label + "  \u2014  " + caption
        cell = [Paragraph(esc(label), CODEFILE)]
        body = Paragraph(text.replace(" ", "&nbsp;").replace("\n", "<br/>")
                         .replace("&nbsp;&nbsp;&nbsp;&nbsp;", "&nbsp;&nbsp;&nbsp;&nbsp;"),
                         ParagraphStyle("code", fontName="Consola", fontSize=size,
                                        leading=size * 1.36, textColor=colors.HexColor("#22262b")))
        t = Table([[body]], colWidths=[16.9 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, CODE_EDGE),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        self.story.append(KeepTogether(cell + [t, Spacer(1, 9)]))

    # ----------------------------------------------------------------- figure
    def fig(self, name, caption, width_cm=15.6):
        path = name if os.path.isabs(name) else os.path.join(FIG, name)
        from reportlab.lib.utils import ImageReader
        iw, ih = ImageReader(path).getSize()
        w = width_cm * cm
        h = w * ih / iw
        max_h = 20.5 * cm
        if h > max_h:
            h = max_h
            w = h * iw / ih
        img = Image(path, width=w, height=h)
        self.fig_n += 1
        cap = "Figure %d. %s" % (self.fig_n, caption)
        block = [Spacer(1, 4), img, Paragraph(cap, CAPTION)]
        if h < 12 * cm:
            self.story.append(KeepTogether(block))
        else:
            self.story.append(block[0])
            self.story.append(block[1])
            self.story.append(block[2])

    # ------------------------------------------------------------------ table
    def table(self, header, rows, widths, caption=None, size=8.4, first_col_mono=False):
        data = [[Paragraph(esc(h), THEAD) for h in header]]
        for r in rows:
            data.append([Paragraph(c if c.startswith("<") else esc(c), TCELL) for c in r])
        t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, RULE),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f6f7f9")))
        t.setStyle(TableStyle(style))
        self.tab_n += 1
        cap = Paragraph("Table %d. %s" % (self.tab_n, caption or ""), CAPTION)
        if len(data) < 14:
            self.story.append(KeepTogether([Spacer(1, 3), t, cap]))
        else:
            # a long table may split across pages, so it cannot be kept together
            # with its caption; append the flowables exactly once
            self.story.append(Spacer(1, 3))
            self.story.append(t)
            self.story.append(Spacer(1, 2))
            self.story.append(cap)


class ReportDoc(BaseDocTemplate):
    def __init__(self, filename, **kw):
        BaseDocTemplate.__init__(self, filename, pagesize=A4,
                                 leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                                 topMargin=2.4 * cm, bottomMargin=2.0 * cm,
                                 title="ShopStream - Development of Distributed Web Applications",
                                 author="Chen Zizheng", **kw)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        cover = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="cover")
        self.addPageTemplates([
            PageTemplate(id="Cover", frames=[cover], onPage=self._cover),
            PageTemplate(id="Body", frames=[frame], onPage=self._decorate),
        ])

    def _cover(self, canv, doc):
        canv.saveState()
        canv.setFillColor(ACCENT)
        canv.rect(0, A4[1] - 1.6 * cm, A4[0], 1.6 * cm, stroke=0, fill=1)
        canv.setFillColor(RULE)
        canv.rect(0, 0, A4[0], 0.8 * cm, stroke=0, fill=1)
        canv.restoreState()

    def _decorate(self, canv, doc):
        canv.saveState()
        canv.setFont("Segoe", 7.8)
        canv.setFillColor(MUTED)
        canv.drawString(2.2 * cm, A4[1] - 1.35 * cm, "ShopStream \u2014 Design and Implementation Report")
        canv.drawRightString(A4[0] - 2.2 * cm, A4[1] - 1.35 * cm, "Chen Zizheng")
        canv.setStrokeColor(RULE)
        canv.setLineWidth(0.5)
        canv.line(2.2 * cm, A4[1] - 1.55 * cm, A4[0] - 2.2 * cm, A4[1] - 1.55 * cm)
        canv.line(2.2 * cm, 1.5 * cm, A4[0] - 2.2 * cm, 1.5 * cm)
        canv.drawCentredString(A4[0] / 2, 1.05 * cm, str(doc.page))
        canv.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            name = flowable.style.name
            if name in ("H1", "H2"):
                level = 0 if name == "H1" else 1
                text = flowable.getPlainText()
                key = "h" + str(self.seq.nextf("heading"))
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text[:110], key, level=level, closed=(level == 0))
                self.notify("TOCEntry", (level, text, self.page, key))


def make_toc():
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOC1", fontName="Segoe-Bold", fontSize=10.2, leading=17,
                       textColor=INK, leftIndent=0, firstLineIndent=0, spaceBefore=4),
        ParagraphStyle("TOC2", fontName="Segoe", fontSize=9.4, leading=14,
                       textColor=colors.HexColor("#33383d"), leftIndent=16, firstLineIndent=0),
    ]
    toc.dotsMinLevel = 0
    return toc

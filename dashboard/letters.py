from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, Spacer, Frame, KeepTogether, Flowable, NextPageTemplate, PageBreak, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import textobject, canvas
from reportlab.pdfbase import pdfmetrics  
from reportlab.pdfbase.ttfonts import TTFont  
from reportlab.lib.colors import CMYKColor
from reportlab.lib.enums import TA_JUSTIFY
import os, datetime
from dashboard.models import Signature

PAPER_SIZE = letter
black = CMYKColor(0, 0, 0, 1)
media_path = os.path.join('external', 'sfu')

from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate

class LetterPageTemplate(PageTemplate):
    def __init__(self, pagesize, *args, **kwargs):
        self._set_margins(pagesize)
        kwargs['frames'] = [self._create_frame(pagesize)]
        kwargs['pagesize'] = pagesize
        PageTemplate.__init__(self, *args, **kwargs)
    
    def _set_margins(self, pagesize):
        self.pg_w, self.pg_h = pagesize
        self.lr_margin = 0.75*inch
        self.top_margin = 0.5*inch
        self.para_width = self.pg_w - 2*self.lr_margin

    def _create_frame(self, pagesize):
        frame = Frame(self.lr_margin, inch, self.para_width, self.pg_h-2*inch)
        return frame

    def _drawStringLeading(self, canvas, x, y, text, charspace=0, mode=None):
        """
        Draws a string in the current text styles.
        
        Duplicate of Canvas.drawString, but passing charspace in when the string is drawn.
        """
        t = textobject.PDFTextObject(canvas, x, y)
        t.setCharSpace(charspace)
        if mode is not None: t.setTextRenderMode(mode)
        t.textLine(text)
        t.setCharSpace(0)
        canvas.drawText(t)

    def _put_lines(self, doc, canvas, lines, x, y, width, style, font_size, leading):
        """
        Place these lines, with given leading
        """
        ypos = y
        for line in lines:
            line = unicode(line).translate(doc.digit_trans)
            p = Paragraph(line, style)
            _,h = p.wrap(width, 1*inch)
            p.drawOn(canvas, x, ypos-h)
            ypos -= h + leading

    def beforeDrawPage(self, c, doc):
        "Draw the letterhead before anything else"
        # non-first pages only get the footer, not the header
        self._draw_footer(c, doc)

    def _draw_footer(self, c, doc):
        """
        Draw the bottom-of-page part of the letterhead (used on all pages)
        """
        c.setFont('Helvetica', 12)
        c.setFillColor(doc.sfu_red)
        self._drawStringLeading(c, self.lr_margin + 6, 0.5*inch, u'Simon Fraser University'.translate(doc.sc_trans_bembo), charspace=1.4)
        c.setFont('Helvetica', 6)
        c.setFillColor(doc.sfu_grey)
        self._drawStringLeading(c, 3.15*inch, 0.5*inch, u'Engaging the World'.upper(), charspace=2)
        

class LetterheadTemplate(LetterPageTemplate):
    def __init__(self, unit, *args, **kwargs):
        LetterPageTemplate.__init__(self, *args, **kwargs)
        self.unit = unit
    
    def beforeDrawPage(self, c, doc):
        "Draw the letterhead before anything else"
        self._draw_header(c, doc)
        self._draw_footer(c, doc)

    def _create_frame(self, pagesize):
        frame = Frame(self.lr_margin, inch, self.para_width, self.pg_h-3*inch)
        return frame

    def _draw_header(self, c, doc):
        """
        Draw the top-of-page part of the letterhead (used only on first page of letter)
        """
        # SFU logo
        c.drawImage(doc.logofile, x=self.lr_margin + 6, y=self.pg_h-self.top_margin-0.5*inch, width=1*inch, height=0.5*inch)

        # unit text
        c.setFont('Helvetica', 12)
        c.setFillColor(doc.sfu_blue)
        parent = self.unit.parent
        if parent.label == 'UNIV':
            # faculty-level unit: just the unit name
            self._drawStringLeading(c, 2*inch, self.pg_h - self.top_margin - 0.375*inch, self.unit.name.translate(doc.sc_trans_bembo), charspace=1.2)
        else:
            # department with faculty above it: display both
            self._drawStringLeading(c, 2*inch, self.pg_h - self.top_margin - 0.325*inch, self.unit.name.translate(doc.sc_trans_bembo), charspace=1.2)
            c.setFillColor(doc.sfu_grey)
            c.setFont('Helvetica', 8.5)
            self._drawStringLeading(c, 2*inch, self.pg_h - self.top_margin - 0.48*inch, parent.name, charspace=0.3)

        # address block
        addr_style = ParagraphStyle(name='Normal',
                                      fontName='Helvetica',
                                      fontSize=10,
                                      leading=10,
                                      textColor=doc.sfu_grey)
        self._put_lines(doc, c, self.unit.address(), 2*inch, self.pg_h - self.top_margin - 0.75*inch, 2.25*inch, addr_style, 8, 1.5)

        # phone numbers block
        lines = [u'Tel'.translate(doc.sc_trans_bembo) + ' ' + self.unit.tel().replace('-', '.')]
        if self.unit.fax():
            lines.append(u'Fax'.translate(doc.sc_trans_bembo) + ' ' + self.unit.fax().replace('-', '.'))
        self._put_lines(doc, c, lines, 4.5*inch, self.pg_h - self.top_margin - 0.75*inch, 1.5*inch, addr_style, 8, 1.5)

        # web and email block
        lines = []
        if self.unit.email():
            lines.append(self.unit.email())
        web = self.unit.web()
        if web.startswith("http://"):
            web = web[7:]
        if web.endswith("/"):
            web = web[:-1]
        lines.append(web)
        self._put_lines(doc, c, lines, 6.25*inch, self.pg_h - self.top_margin - 0.75*inch, 1.5*inch, addr_style, 8, 1.5)
        


class OfficialLetter(BaseDocTemplate):
    """
    Template for a letter on letterhead.
    
    Implements "2009" version of letterhead in SFU graphic design specs: http://www.sfu.ca/clf/downloads.html
    """
    def __init__(self, filename, unit, pagesize=PAPER_SIZE, *args, **kwargs):
        self._media_setup()
        kwargs['pagesize'] = pagesize
        kwargs['pageTemplates'] = [LetterheadTemplate(pagesize=pagesize, unit=unit), LetterPageTemplate(pagesize=pagesize)]
        BaseDocTemplate.__init__(self, filename, *args, **kwargs)
        self.contents = [] # to be a list of Flowables
    
    def add_letter(self, letter):
        "Add the given LetterContents object to this document"
        self.contents.extend(letter._contents(self))
    
    def write(self):
        "Write the PDF contents out"
        self.build(self.contents)

    def _media_setup(self):
        "Get all of the media needed for the letterhead"
        # fonts and logo
        ttfFile = os.path.join(media_path, 'Helvetica.ttf')
        #pdfmetrics.registerFont(TTFont("Helvetica", ttfFile))  
        ttfFile = os.path.join(media_path, 'Helvetica.ttf')
        #pdfmetrics.registerFont(TTFont("Helvetica", ttfFile))  
        self.logofile = os.path.join(media_path, 'logo.png')
        
        # graphic standards colours
        self.sfu_red = CMYKColor(0, 1, 0.79, 0.2)
        self.sfu_grey = CMYKColor(0, 0, 0.15, 0.82)
        self.sfu_blue = CMYKColor(1, 0.68, 0, 0.12)
        
        # translate digits to old-style numerals (in their Bembo character positions)
        self.digit_trans = {}
        for d in range(10):
            self.digit_trans[48+d] = unichr(0xF643 + d)
        
        self.sc_trans_bembo = {}
        # translate letters to smallcaps characters (in their [strange] Bembo character positions)
        for d in range(26):
            if d<3: # A-C
                offset = d
            elif d<4: # D
                offset = d+2
            elif d<21: # E-U
                offset = d+3
            else: # V-Z
                offset = d+4
            self.sc_trans_bembo[65+d] = unichr(0xE004 + offset)
            self.sc_trans_bembo[97+d] = unichr(0xE004 + offset)


class LetterContents(object):
    """
    Contents of a single letter.
    
    to_addr_lines: the lines of the recipient's address (list of strings)
    from_name_lines: the sender's name (and title, etc) (list of strings)
    date: sending date of the letter (datetime.date object)
    saluations: letter's salutation (string)
    closing: letter's closing (string)
    signer: person signing the letter, if knows (a coredata.models.Person)
    """
    def __init__(self, to_addr_lines, from_name_lines, date=None, salutation="To whom it may concern",
                 closing="Yours truly", signer=None, paragraphs=None):
        self.date = date or datetime.date.today()
        self.salutation = salutation
        self.closing = closing
        self.flowables = []
        self.to_addr_lines = to_addr_lines
        self.from_name_lines = from_name_lines
        self.signer = signer
        if paragraphs:
            self.add_paragraphs(paragraphs)
        
        # styles
        self.line_height = 13
        self.content_style = ParagraphStyle(name='Normal',
                                      fontName='BemboMTPro',
                                      fontSize=12,
                                      leading=self.line_height,
                                      allowWidows=0,
                                      allowOrphans=0,
                                      alignment=TA_JUSTIFY,
                                      textColor=black)
        
    def add_paragraph(self, text):
        "Add a paragraph (represented as a string) to the letter: used by OfficialLetter.add_letter"
        self.flowables.append(Paragraph(text, self.content_style))

    def add_paragraphs(self, paragraphs):
        "Add a list of paragraphs (strings) to the letter"
        self.flowables.extend([Paragraph(text, self.content_style) for text in paragraphs])
    
    def _contents(self, letter):
        "Builds of contents that can be added to a letter"
        contents = []
        space_height = self.line_height
        style = self.content_style

        contents.append(Paragraph(self.date.strftime('%B %d, %Y').replace(' 0', ' '), style))
        contents.append(Spacer(1, space_height))
        contents.append(NextPageTemplate(1)) # switch to non-letterhead on next page
        
        for line in self.to_addr_lines:
            contents.append(Paragraph(line, style))
        contents.append(Spacer(1, 2*space_height))
        contents.append(Paragraph(self.salutation+",", style))
        contents.append(Spacer(1, space_height))
        
        for f in self.flowables[:-1]:
            # last paragraph is put in the KeepTogether below, to prevent bad page break
            contents.append(f)
            contents.append(Spacer(1, space_height))
        
        # closing block (kept together on one page)
        close = []
        close.append(self.flowables[-1])
        close.append(Spacer(1, 2*space_height))
        close.append(Paragraph(self.closing+",", style))
        # signature
        if self.signer:
            import PIL
            try:
                sig = Signature.objects.get(user=self.signer)
                sig.sig.open()
                img = PIL.Image.open(sig.sig)
                width, height = img.size
                wid = width / float(sig.resolution) * inch
                hei = height / float(sig.resolution) * inch
                sig.sig.open()
                img = Image(sig.sig, width=wid, height=hei)
                img.hAlign = 'LEFT'
                close.append(Spacer(1, space_height))
                close.append(img)
            except Signature.DoesNotExist:
                close.append(Spacer(1, 4*space_height))
        else:
            close.append(Spacer(1, 4*space_height))
        
        for line in self.from_name_lines:
            close.append(Paragraph(line, style))
        
        contents.append(KeepTogether(close))
        contents.append(NextPageTemplate(0)) # next letter starts on letterhead again
        contents.append(PageBreak())
        
        return contents


class RAForm(object):
    BOX_OFFSET = 0.078125*inch # how far boxes are from the edges (i.e. from the larger box)
    ENTRY_SIZE = 0.375*inch # height of a data entry box
    ENTRY_HEIGHT = ENTRY_SIZE + BOX_OFFSET # height difference for adjacent entry boxes
    LABEL_OFFSET = 2 # right offset of a label from the box position
    LABEL_HEIGHT = 8 # height of a label (i.e. offset of top of box)
    DATA_BUMP = 4 # how far to move data up from bottom of box
    MAIN_WIDTH = 7.5*inch # size of the main box
    MAIN_HEIGHT = 7.5*inch # size of the main box
    CHECK_SIZE = 0.125*inch # checkbox size

    def __init__(self, ra):
        self.ra = ra
    
    def _draw_box_right(self, x, y, label, content, width=MAIN_WIDTH-BOX_OFFSET):
        self._draw_box_left(x=self.MAIN_WIDTH - x - width - self.BOX_OFFSET, y=y, label=label, content=content, width=width)
        
    def _draw_box_left(self, x, y, label, content, width=MAIN_WIDTH-BOX_OFFSET):
        """
        Draw one text entry box with the above parameters.
        
        "width" parameter should include one BOX_OFFSET
        """
        # box
        self.c.setLineWidth(2)
        self.c.rect(x + self.BOX_OFFSET, y - self.BOX_OFFSET - self.ENTRY_SIZE, width - self.BOX_OFFSET, self.ENTRY_SIZE)

        # label
        self.c.setFont("Helvetica", 6)
        self.c.drawString(x + self.BOX_OFFSET + self.LABEL_OFFSET, y - self.BOX_OFFSET - self.LABEL_HEIGHT, label)
        
        # content
        self.c.setFont("Helvetica", 12)
        self.c.drawString(x + self.BOX_OFFSET + 2*self.LABEL_OFFSET, y - self.BOX_OFFSET - self.ENTRY_SIZE + self.DATA_BUMP, content)
    
    def _rule(self, height):
        self.c.setLineWidth(2)
        self.c.line(0, height, self.MAIN_WIDTH, height)
    
    def draw_pdf(self, outfile):
        """
        Generates PDF in the file object (which could be a Django HttpResponse).
        """
        c = canvas.Canvas(outfile, pagesize=letter)
        self.c = c
        self.c.setStrokeColor(black)

        # draw form
        c.translate(0.5*inch, 2.25*inch) # origin = lower-left of the main box
    
        c.setStrokeColor(black)
        c.setLineWidth(2)
        c.rect(0, 0, self.MAIN_WIDTH, self.MAIN_HEIGHT)
        
        c.setFont("Helvetica", 10)
        c.drawCentredString(4*inch, 8.125*inch, "SIMON FRASER UNIVERSITY")
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(4*inch, 7.875*inch, "Student, Research & Other Non-Union")
        c.drawCentredString(4*inch, 7.625*inch, "Appointments")
        
        # SIN
        sin = "%09i" % (self.ra.sin)
        sin = sin[:3] + '-' + sin[3:6] + '-' + sin[6:]
        self._draw_box_left(0, self.MAIN_HEIGHT, width=3.125*inch, label="SOCIAL INSURANCE NUMBER (SIN)", content=sin)

        # emplid
        emplid = unicode(self.ra.person.emplid)
        emplid = emplid[:5] + '-' + emplid[5:]
        self._draw_box_right(0, self.MAIN_HEIGHT, width=3.375*inch, label="SFU ID #", content=emplid)
        
        # names
        self._draw_box_left(0, self.MAIN_HEIGHT - self.ENTRY_HEIGHT, label="LAST OR FAMILY NAME", content=self.ra.person.last_name)
        self._draw_box_left(0, self.MAIN_HEIGHT - 2*self.ENTRY_HEIGHT, label="FIRST NAME", content=self.ra.person.first_name)
        
        height = self.MAIN_HEIGHT - 3*self.ENTRY_HEIGHT - self.BOX_OFFSET
        self._rule(height)
        
        # position
        self._draw_box_left(0, height, width=3.125*inch, label="POSITION NUMBER", content=unicode(self.ra.account.position_number))
        self._draw_box_right(0, height, width=3.75*inch, label="POSITION TITLE", content=unicode(self.ra.account.title))
        
        # department
        self._draw_box_left(0, height - self.ENTRY_HEIGHT, width=3.125*inch, label="DEPARTMENT", content=self.ra.unit.name)
        
        # fund/project/account
        self._draw_box_right(0, height - self.ENTRY_HEIGHT, width=3.75*inch, label="FUND (2)", content='XX...')
        
        height = height - 2*self.ENTRY_HEIGHT - self.BOX_OFFSET
        self._rule(height)
        
        # dates
        self._draw_box_left(0, height, width=2.125*inch, label="START DATE (yyyy/mm/dd)", content=unicode(self.ra.start_date))
        self._draw_box_left(3*inch, height, width=1.5*inch, label="END DATE (yyyy/mm/dd)", content=unicode(self.ra.end_date))

        # health benefit check boxes        
        self.c.setLineWidth(1)
        self.c.setFont("Helvetica", 6)
        if self.ra.medical_benefits:
            fills = [1, 0]
        else:
            fills = [0, 1]
        self.c.rect(5*inch, height - self.BOX_OFFSET - self.CHECK_SIZE, self.CHECK_SIZE, self.CHECK_SIZE, fill=fills[0])
        self.c.drawString(5*inch + 1.5*self.CHECK_SIZE, height - self.BOX_OFFSET - 0.5*self.CHECK_SIZE - 3, "Yes, Eligible for Health Benefits")
        self.c.rect(5*inch, height - self.BOX_OFFSET - 2.5*self.CHECK_SIZE, self.CHECK_SIZE, self.CHECK_SIZE, fill=fills[1])
        self.c.drawString(5*inch + 1.5*self.CHECK_SIZE, height - self.BOX_OFFSET - 2*self.CHECK_SIZE - 3, "Not Eligible for Health Benefits")
        
        # pay
        self._draw_box_left(0, height - self.ENTRY_HEIGHT, width=2.125*inch, label="HOURLY", content="$  " + unicode(self.ra.hourly_pay))
        self._draw_box_left(3*inch, height - self.ENTRY_HEIGHT, width=1.5*inch, label="BI-WEEKLY", content="$  " + unicode(self.ra.biweekly_pay))
        self._draw_box_right(0, height - self.ENTRY_HEIGHT, width=2.25*inch, label="LUMP SUM ADJUSTMENT", content="$  " + unicode(self.ra.lump_sum_pay))
        
        self._draw_box_left(3*inch, height - 2*self.ENTRY_HEIGHT, width=1.5*inch, label="BI-WEEKLY", content="HH:MM")
        self._draw_box_left(self.MAIN_WIDTH - self.BOX_OFFSET - 2.25*inch, height - 2*self.ENTRY_HEIGHT, width=1*inch, label="LUMP SUM", content="HH:MM")
        
        height = height - 3*self.ENTRY_HEIGHT - self.BOX_OFFSET
        self._rule(height)
        
        # appointment type checkboxes
        if self.ra.hiring_category == 'U':
            fills = [0,0,1,0]
        elif self.ra.hiring_category == 'E':
            fills = [0,1,0,0]
        elif self.ra.hiring_category == 'N':
            fills = [0,0,0,1]
        elif self.ra.hiring_category == 'S':
            fills = [1,0,0,0]
        else:
            fills = [0,0,0,0]
        
        self.c.setLineWidth(1)
        self.c.setFont("Helvetica", 6)
        self.c.rect(0.75*inch, height - self.BOX_OFFSET - self.CHECK_SIZE, self.CHECK_SIZE, self.CHECK_SIZE, fill=fills[0])
        self.c.drawString(0.75*inch + 1.5*self.CHECK_SIZE, height - self.BOX_OFFSET - 0.5*self.CHECK_SIZE - 3, "GRAD STUDENT RESEARCH ASSISTANT (SCHOLARSHIP INCOME)")
        self.c.rect(4*inch, height - self.BOX_OFFSET - self.CHECK_SIZE, self.CHECK_SIZE, self.CHECK_SIZE, fill=fills[1])
        self.c.drawString(4*inch + 1.5*self.CHECK_SIZE, height - self.BOX_OFFSET - 0.5*self.CHECK_SIZE - 3, "GRAD STUDENT RESEARCH ASSISTANT (EMPLOYMENT INCOME)")
        self.c.rect(4*inch, height - self.BOX_OFFSET - 3*self.CHECK_SIZE, self.CHECK_SIZE, self.CHECK_SIZE, fill=fills[2])
        self.c.drawString(4*inch + 1.5*self.CHECK_SIZE, height - self.BOX_OFFSET - 2.5*self.CHECK_SIZE - 3, "UNDERGRAD STUDENT")
        self.c.rect(4*inch, height - self.BOX_OFFSET - 5*self.CHECK_SIZE, self.CHECK_SIZE, self.CHECK_SIZE, fill=fills[3])
        self.c.drawString(4*inch + 1.5*self.CHECK_SIZE, height - self.BOX_OFFSET - 4.5*self.CHECK_SIZE - 3, "NON STUDENT")
        
        height = height - 7*self.CHECK_SIZE
        self._rule(height)
        
        
        c.showPage()
        c.save()


def ra_form(ra, outfile):
    """
    Generate FPP4 form for this RAAppointment.
    """
    form = RAForm(ra)
    return form.draw_pdf(outfile)


class TAForm(object):
    BOX_HEIGHT = 0.25*inch
    LABEL_RIGHT = 2
    LABEL_UP = 2
    CONTENT_RIGHT = 4
    CONTENT_UP = 4
    LABEL_SIZE = 6

    def __init__(self, contract):
        self.contract = contract
    
    def _draw_box(self, x, y, width, label='', label_size=LABEL_SIZE, content=''):
        height = self.BOX_HEIGHT
        self.c.setLineWidth(1)
        self.c.rect(x, y, width, height)
        
        if label:
            self.c.setFont("Helvetica", label_size)
            self.c.drawString(x + self.LABEL_RIGHT, y + height + self.LABEL_UP, label)
        
        if content:
            self.c.setFont("Helvetica", 12)
            self.c.drawString(x + self.CONTENT_RIGHT, y + self.CONTENT_UP, content)

    def draw_pdf(self, outfile):
        """
        Generates PDF in the file object (which could be a Django HttpResponse).
        """
        c = canvas.Canvas(outfile, pagesize=letter)
        self.c = c
        self.c.setStrokeColor(black)

        # draw form
        c.translate(0.625*inch, 1.25*inch) # origin = lower-left of the main box
        
        # main outline
        c.setStrokeColor(black)
        c.setLineWidth(2)
        p = c.beginPath()
        p.moveTo(0,0)
        p.lineTo(0, 8.875*inch)
        p.lineTo(43*mm, 8.875*inch)
        p.lineTo(43*mm, 8.625*inch)
        p.lineTo(7.25*inch, 8.625*inch)
        p.lineTo(7.25*inch, 0)
        p.close()
        c.drawPath(p, stroke=1, fill=0)
        
        # personal info
        self._draw_box(0, 8.625*inch, 43*mm, label="SFU ID #", content=unicode(self.contract.application.person.emplid))
        self._draw_box(0, 210*mm, 43*mm, label="CANADA SOCIAL INSURANCE NO.", content=unicode(self.contract.application.sin))
        self._draw_box(46*mm, 210*mm, 74*mm, label="LAST OR FAMILY NAME", content=unicode(self.contract.application.person.last_name))
        self._draw_box(125*mm, 210*mm, 50*mm, label="FIRST NAME", content=unicode(self.contract.application.person.first_name))
        self._draw_box(15*mm, 202*mm, 160*mm) # HOME ADDRESS
        c.setFont("Helvetica", self.LABEL_SIZE)
        c.drawString(2, 206*mm, "HOME")
        c.drawString(2, 203*mm, "ADDRESS")
        
        # appointment basic info
        c.drawString(2, 194*mm, "DEPARTMENT")
        self._draw_box(20*mm, 193*mm, 78*mm, content=unicode(self.contract.application.posting.unit.name)) # DEPARTMENT
        self._draw_box(102*mm, 193*mm, 32*mm, label="APPOINTMENT START DATE", content=unicode(self.contract.pay_start))
        self._draw_box(139*mm, 193*mm, 32*mm, label="APPOINTMENT END DATE", content=unicode(self.contract.pay_end))
        
        # initial appointment boxes
        c.rect(14*mm, 185*mm, 5*mm, 5*mm, fill=1)
        c.rect(14*mm, 176*mm, 5*mm, 5*mm, fill=0)
        c.setFont("Helvetica", self.LABEL_SIZE)
        c.drawString(21*mm, 188*mm, "INITIAL APPOINTMENT TO")
        c.drawString(21*mm, 186*mm, "THIS POSITION NUMBER")
        c.setFont("Helvetica", 5)
        c.drawString(21*mm, 179*mm, "REAPPOINTMENT TO SAME POSITION")
        c.drawString(21*mm, 177*mm, "NUMBER OR REVISION TO APPOINTMENT")

        # position info
        self._draw_box(60*mm, 176*mm, 37*mm, label="POSITION NUMBER", content=unicode(self.contract.position_number.position_number))
        self._draw_box(102*mm, 176*mm, 32*mm, label="PAYROLL START DATE", content=unicode(self.contract.pay_start))
        self._draw_box(139*mm, 176*mm, 32*mm, label="PAYROLL END DATE", content=unicode(self.contract.pay_end))
        
        

        c.showPage()
        c.save()

def ta_form(contract, outfile):
    """
    Generate TA Appointment Form for this TAContract.
    """
    form = TAForm(contract)
    return form.draw_pdf(outfile)


from pathlib import Path
import textwrap


OUT = Path("HR_System_UI_Design_Test_Evaluation_Form.pdf")


class Pdf:
    def __init__(self):
        self.objects = []
        self.pages = []
        self.font_obj = self.add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        self.bold_font_obj = self.add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    def add_object(self, body):
        self.objects.append(body)
        return len(self.objects)

    def add_page(self, stream, width=612, height=792):
        stream_obj = self.add_object(f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream")
        page_obj = self.add_object(
            f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {width} {height}] "
            f"/Resources << /Font << /F1 {self.font_obj} 0 R /F2 {self.bold_font_obj} 0 R >> >> "
            f"/Contents {stream_obj} 0 R >>"
        )
        self.pages.append(page_obj)

    def save(self, path):
        kids = " ".join(f"{obj} 0 R" for obj in self.pages)
        pages_obj = self.add_object(f"<< /Type /Pages /Kids [{kids}] /Count {len(self.pages)} >>")
        for page_obj in self.pages:
            self.objects[page_obj - 1] = self.objects[page_obj - 1].replace("/Parent 0 0 R", f"/Parent {pages_obj} 0 R")
        catalog_obj = self.add_object(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>")

        parts = ["%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
        offsets = [0]
        for index, body in enumerate(self.objects, start=1):
            offsets.append(sum(len(part.encode("latin-1")) for part in parts))
            parts.append(f"{index} 0 obj\n{body}\nendobj\n")
        xref_start = sum(len(part.encode("latin-1")) for part in parts)
        parts.append(f"xref\n0 {len(self.objects) + 1}\n")
        parts.append("0000000000 65535 f \n")
        for offset in offsets[1:]:
            parts.append(f"{offset:010d} 00000 n \n")
        parts.append(
            f"trailer\n<< /Size {len(self.objects) + 1} /Root {catalog_obj} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        )
        path.write_bytes("".join(parts).encode("latin-1"))


def esc(text):
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class Canvas:
    def __init__(self):
        self.ops = []

    def text(self, x, y, value, size=10, bold=False):
        font = "F2" if bold else "F1"
        self.ops.append(f"BT /{font} {size} Tf {x} {y} Td ({esc(value)}) Tj ET")

    def line(self, x1, y1, x2, y2, width=0.8):
        self.ops.append(f"{width} w {x1} {y1} m {x2} {y2} l S")

    def rect(self, x, y, w, h, width=0.8):
        self.ops.append(f"{width} w {x} {y} {w} {h} re S")

    def checkbox(self, x, y, label, size=9):
        self.rect(x, y, 9, 9)
        self.text(x + 14, y + 1, label, size=size)

    def wrapped(self, x, y, value, chars=96, size=9, leading=11, bold=False):
        for line in textwrap.wrap(value, width=chars):
            self.text(x, y, line, size=size, bold=bold)
            y -= leading
        return y

    def field_line(self, x, y, label, line_x, end_x):
        self.text(x, y, label, size=9.5, bold=True)
        self.line(line_x, y - 2, end_x, y - 2)

    def multiline_box(self, x, y, w, h, label):
        self.text(x, y + h + 8, label, size=9.5, bold=True)
        self.rect(x, y, w, h)
        line_y = y + h - 18
        while line_y > y + 8:
            self.line(x + 8, line_y, x + w - 8, line_y, width=0.35)
            line_y -= 18

    def stream(self):
        return "\n".join(self.ops)


def rating_row(c, x, y):
    c.text(x, y, "Rating:", size=9, bold=True)
    labels = ["1 Poor", "2 Fair", "3 Good", "4 Very Good", "5 Excellent"]
    pos = x + 50
    for label in labels:
        c.checkbox(pos, y - 2, label, size=8.5)
        pos += 84


def checklist(c, x, y, items):
    for item in items:
        c.checkbox(x, y, item, size=8.8)
        y -= 16
    return y


def add_section(c, title, description, y, checklist_items):
    c.text(42, y, title, size=11, bold=True)
    y -= 14
    y = c.wrapped(42, y, description, chars=96, size=8.8, leading=11)
    y -= 5
    rating_row(c, 42, y)
    y -= 23
    c.text(42, y, "Items to verify:", size=9, bold=True)
    y -= 15
    y = checklist(c, 52, y, checklist_items)
    y -= 8
    c.multiline_box(42, y - 52, 528, 52, "HR comments, findings, or required improvements:")
    return y - 72


def header(c, title, copy_label):
    c = Canvas()
    c.text(42, 754, "Applicant Tracking System", size=16, bold=True)
    c.text(42, 735, title, size=13, bold=True)
    c.text(438, 754, copy_label, size=9, bold=True)
    c.line(42, 724, 570, 724)
    return c


def make_page_one():
    c = header(c=None, title="HR System Test Evaluation Form - UI and Design Test", copy_label="Page 1 of 2")

    c.field_line(42, 700, "HR Evaluator Name:", 165, 365)
    c.field_line(385, 700, "Test Date:", 445, 570)
    c.field_line(42, 678, "Position/Role:", 130, 365)
    c.field_line(385, 678, "Department:", 465, 570)
    c.field_line(42, 656, "System/Module Reviewed:", 180, 570)

    c.text(42, 628, "Purpose", size=10.5, bold=True)
    c.wrapped(
        42,
        613,
        "This evaluation verifies whether the system interface and design qualify with the company's design standards "
        "and employee standards. HR should review visual consistency, professional presentation, employee usability, "
        "and suitability for daily recruitment and HR-related work.",
        chars=104,
        size=9,
        leading=11,
    )

    y = 568
    y = add_section(
        c,
        "Company Design Standards",
        "Check whether the system follows the expected company look, layout discipline, branding, and professional presentation.",
        y,
        [
            "Colors, typography, spacing, and layout are consistent.",
            "Buttons, forms, tables, and menus follow a uniform style.",
            "The interface looks professional and appropriate for company use.",
            "Labels, headings, and messages are clear and properly presented.",
        ],
    )
    add_section(
        c,
        "Employee Standards",
        "Check whether the system supports employee expectations for clarity, accessibility, ease of use, and reliable work output.",
        y,
        [
            "Employees can understand the screen purpose without confusion.",
            "Important actions are easy to find and complete.",
            "The design supports accurate and efficient work.",
            "The system is appropriate for both HR users and employee-facing use.",
        ],
    )
    c.text(42, 44, "Continue to Page 2 for UI/design qualification and final HR recommendation.", size=8.5, bold=True)
    return c.stream()


def make_page_two():
    c = header(c=None, title="HR System Test Evaluation Form - UI and Design Test", copy_label="Page 2 of 2")

    c.field_line(42, 700, "HR Evaluator Name:", 165, 365)
    c.field_line(385, 700, "Test Date:", 445, 570)
    c.field_line(42, 678, "System/Module Reviewed:", 180, 570)

    c.text(42, 642, "Evaluation Continuation", size=10.5, bold=True)
    c.wrapped(
        42,
        627,
        "Use this page to decide whether the system's interface and design are qualified for employee use, "
        "based on the company's design standards and employee standards.",
        chars=104,
        size=9,
        leading=11,
    )

    y = 582
    y = add_section(
        c,
        "UI and Design Qualification",
        "Decide whether the system's user interface is ready for use, needs minor changes, or requires major design revision.",
        y,
        [
            "Screens are organized and not visually crowded.",
            "Error messages, alerts, and confirmations are readable.",
            "The design works well for repeated daily use.",
            "The overall interface is ready for user testing or deployment.",
        ],
    )

    c.multiline_box(42, y - 34, 528, 34, "Additional HR observations:")
    y -= 58
    c.text(42, y + 2, "Final HR Recommendation", size=10.5, bold=True)
    c.checkbox(42, y - 17, "Qualified based on company and employee standards", size=8.8)
    c.checkbox(310, y - 17, "Qualified with minor design changes", size=8.8)
    c.checkbox(42, y - 35, "Not yet qualified; major UI/design changes required", size=8.8)
    c.multiline_box(42, y - 112, 528, 54, "Summary opinion and approval notes:")
    c.field_line(42, 44, "HR Evaluator Signature:", 175, 330)
    c.field_line(350, 44, "Date Signed:", 430, 570)
    return c.stream()


pdf = Pdf()
pdf.add_page(make_page_one())
pdf.add_page(make_page_two())
pdf.save(OUT)
print(OUT.resolve())

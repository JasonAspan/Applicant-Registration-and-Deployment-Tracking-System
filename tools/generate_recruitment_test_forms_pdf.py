from pathlib import Path
import textwrap


OUT = Path("Recruitment_System_Test_Evaluation_Forms.pdf")


testers = [
    {
        "name": "Jomar Tesorrio",
        "role": "Recruitment Manager",
        "focus": "Functionality Test and Overall User Experience Test",
    },
    {
        "name": "Eliza Pacheco",
        "role": "Recruitment SV",
        "focus": "Overall User Experience Test",
    },
    {
        "name": "Brian Basabas",
        "role": "Branch Manager",
        "focus": "Overall User Experience Test",
    },
    {
        "name": "Lanie Quijano",
        "role": "Recruitment Officer",
        "focus": "Functionality Test",
    },
    {
        "name": "Angel Balite",
        "role": "Recruitment Officer",
        "focus": "Functionality Test",
    },
    {
        "name": "Kristine Macatangay",
        "role": "Recruitment Officer",
        "focus": "Usability Test",
    },
    {
        "name": "Bong Bermundo",
        "role": "Recruitment Officer",
        "focus": "Usability Test",
    },
]


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

    def checkbox(self, x, y, label, size=10):
        self.rect(x, y, 9, 9)
        self.text(x + 14, y + 1, label, size=size)

    def wrapped(self, x, y, value, chars=96, size=9.5, leading=12, bold=False):
        for line in textwrap.wrap(value, width=chars):
            self.text(x, y, line, size=size, bold=bold)
            y -= leading
        return y

    def field_line(self, x, y, label, line_x=150, end_x=560):
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


def add_section(c, title, description, y):
    c.text(42, y, title, size=11, bold=True)
    y -= 14
    y = c.wrapped(42, y, description, chars=96, size=8.8, leading=11)
    y -= 5
    rating_row(c, 42, y)
    y -= 34
    c.multiline_box(42, y - 66, 528, 66, "Comments, observations, and issues found:")
    return y - 88


def make_page(tester, page_no):
    c = Canvas()
    c.text(42, 754, "Applicant Tracking System", size=16, bold=True)
    c.text(42, 735, "Recruitment System Test Evaluation Form", size=13, bold=True)
    c.text(445, 754, f"Tester Copy {page_no}", size=9, bold=True)
    c.line(42, 724, 570, 724)

    c.field_line(42, 700, "Tester Name:", 130, 365)
    c.text(134, 701, tester["name"], size=10)
    c.field_line(385, 700, "Test Date:", 445, 570)
    c.field_line(42, 678, "Position/Role:", 130, 365)
    if tester["role"]:
        c.text(134, 679, tester["role"], size=10)
    c.field_line(385, 678, "Department:", 465, 570)
    c.field_line(42, 656, "Assigned Test Focus:", 160, 570)
    if tester["focus"]:
        c.text(164, 657, tester["focus"], size=10)

    c.text(42, 628, "Instructions", size=10.5, bold=True)
    c.wrapped(
        42,
        613,
        "Please test the recruitment workflow in the Applicant Tracking System based on the areas below. "
        "Select a rating and write clear opinions, concerns, defects, and recommended improvements.",
        chars=104,
        size=9,
        leading=11,
    )

    y = 575
    y = add_section(
        c,
        "Overall User Experience Test",
        "Evaluate whether the system feels clear, efficient, and suitable for recruitment users from start to finish.",
        y,
    )
    y = add_section(
        c,
        "Functionality Test",
        "Verify that recruitment features work as expected, including applicant records, job postings, screening steps, status updates, and related actions.",
        y,
    )
    y = add_section(
        c,
        "Usability Test",
        "Assess whether the system is easy to understand, navigate, and use with minimal confusion or extra effort.",
        y,
    )

    c.text(42, y + 2, "Final Recommendation", size=10.5, bold=True)
    c.checkbox(42, y - 17, "Fit for user use", size=9)
    c.checkbox(180, y - 17, "Fit with minor changes", size=9)
    c.checkbox(360, y - 17, "Needs major changes before use", size=9)
    c.multiline_box(42, y - 98, 528, 54, "Summary opinion and recommended changes:")
    c.field_line(42, 44, "Tester Signature:", 150, 330)
    c.field_line(350, 44, "Date Signed:", 430, 570)
    return c.stream()


pdf = Pdf()
for idx, tester in enumerate(testers, start=1):
    pdf.add_page(make_page(tester, idx))
pdf.save(OUT)
print(OUT.resolve())

from pathlib import Path
import textwrap


OUT = Path("Operations_Manager_System_UI_Design_Test_Evaluation_Form.pdf")


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


def header(title, page_label):
    c = Canvas()
    c.text(42, 754, "Applicant Tracking System", size=16, bold=True)
    c.text(42, 735, title, size=13, bold=True)
    c.text(455, 754, page_label, size=9, bold=True)
    c.line(42, 724, 570, 724)
    return c


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
    c.multiline_box(42, y - 52, 528, 52, "Operations Manager comments, findings, or required improvements:")
    return y - 72


def make_page_one():
    c = header("Operations Manager System Test Evaluation Form - UI and Design Test", "Page 1 of 2")
    c.field_line(42, 700, "Operations Manager Name:", 195, 365)
    c.field_line(385, 700, "Test Date:", 445, 570)
    c.field_line(42, 678, "Position/Role:", 130, 365)
    c.field_line(385, 678, "Department:", 465, 570)
    c.field_line(42, 656, "System/Module Reviewed:", 180, 570)

    c.text(42, 628, "Purpose", size=10.5, bold=True)
    c.wrapped(
        42,
        613,
        "This evaluation helps the Operations Manager verify whether the system qualifies with company design standards, "
        "employee standards, and operational needs. The review should consider whether the system can support smooth "
        "daily operations, reliable coordination, and long-term business benefit.",
        chars=104,
        size=9,
        leading=11,
    )

    y = 568
    y = add_section(
        c,
        "Company Design Standards",
        "Review whether the system interface is professional, consistent, and suitable for company-wide operational use.",
        y,
        [
            "Interface design is clean, organized, and company-appropriate.",
            "Visual elements, forms, tables, buttons, and labels are consistent.",
            "Screens are clear enough for operational monitoring and review.",
            "The design supports formal recruitment and operational workflows.",
        ],
    )
    add_section(
        c,
        "Employee and Operational Standards",
        "Review whether the system supports employees, supervisors, HR, and operations users in completing work accurately.",
        y,
        [
            "Users can follow the workflow without unnecessary confusion.",
            "The system supports accurate records and process visibility.",
            "The interface reduces manual work, delays, or repeated follow-ups.",
            "The system is practical for daily operational use.",
        ],
    )
    c.text(42, 44, "Continue to Page 2 for long-term operational benefit and final recommendation.", size=8.5, bold=True)
    return c.stream()


def make_page_two():
    c = header("Operations Manager System Test Evaluation Form - UI and Design Test", "Page 2 of 2")
    c.field_line(42, 700, "Operations Manager Name:", 195, 365)
    c.field_line(385, 700, "Test Date:", 445, 570)
    c.field_line(42, 678, "System/Module Reviewed:", 180, 570)

    c.text(42, 642, "Evaluation Continuation", size=10.5, bold=True)
    c.wrapped(
        42,
        627,
        "Use this page to assess whether the system will provide long-term operational value and whether it should be "
        "recommended for continued improvement, user testing, or deployment.",
        chars=104,
        size=9,
        leading=11,
    )

    y = 582
    y = add_section(
        c,
        "Long-Term Operational Benefit",
        "Assess whether the system can improve operational control, recruitment coordination, process tracking, and business efficiency over time.",
        y,
        [
            "The system can improve process monitoring and accountability.",
            "The system can reduce manual coordination and process errors.",
            "The system can support branch, HR, and operations alignment.",
            "The long-term operational benefit justifies continued use or improvement.",
        ],
    )
    y = add_section(
        c,
        "Overall UI and Operational Qualification",
        "Decide whether the system interface and design are acceptable from an operations management perspective.",
        y,
        [
            "The system is visually acceptable for company operations.",
            "The system is practical for employees, HR, and management users.",
            "The design supports reliable tracking, reporting, and decision-making.",
            "The system is ready for user testing, rollout, or further revision.",
        ],
    )

    c.text(42, y + 2, "Final Operations Manager Recommendation", size=10.5, bold=True)
    c.checkbox(42, y - 17, "Qualified and beneficial for long-term operational use", size=8.8)
    c.checkbox(320, y - 17, "Qualified with minor improvements", size=8.8)
    c.checkbox(42, y - 35, "Needs major improvements before operational use", size=8.8)
    c.multiline_box(42, y - 112, 528, 54, "Summary opinion and recommendation:")
    c.field_line(42, 44, "Operations Manager Signature:", 205, 330)
    c.field_line(350, 44, "Date Signed:", 430, 570)
    return c.stream()


pdf = Pdf()
pdf.add_page(make_page_one())
pdf.add_page(make_page_two())
pdf.save(OUT)
print(OUT.resolve())

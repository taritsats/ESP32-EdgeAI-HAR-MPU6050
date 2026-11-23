"""Build a Word version from the matching Markdown source using Pandoc."""

import argparse
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, RGBColor

ROOT = Path(__file__).resolve().parent


def format_document(path, is_guide):
    doc = Document(path)
    for name in ("Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3"):
        style = doc.styles[name]
        style.font.color.rgb = RGBColor(0, 0, 0)
        border = style.element.get_or_add_pPr().find(qn("w:pBdr"))
        if border is not None:
            border.getparent().remove(border)
    for shape in doc.inline_shapes:
        if shape.height > Inches(2.6):
            width = round(shape.width * Inches(2.6) / shape.height)
            shape.width, shape.height = width, Inches(2.6)
    for table in doc.tables:
        if is_guide:
            section = doc.sections[0]
            width = section.page_width - section.left_margin - section.right_margin
            table.autofit = False
            for column, fraction in zip(table.columns, (0.31, 0.69)):
                column.width = round(width * fraction)
                for cell in column.cells:
                    cell.width = column.width
        properties = table._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
            border = OxmlElement(f"w:{side}")
            border.set(qn("w:val"), "single")
            border.set(qn("w:sz"), "4")
            border.set(qn("w:color"), "D9D9D9")
            borders.append(border)
        properties.insert_element_before(borders, "w:shd", "w:tblLayout", "w:tblLook")
        last_row = len(table.rows) - 1
        for index, row in enumerate(table.rows):
            row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
            for cell in row.cells:
                if index == 0:
                    shade = OxmlElement("w:shd")
                    shade.set(qn("w:fill"), "E7EDF3")
                    cell._tc.get_or_add_tcPr().append(shade)
                if is_guide:
                    for paragraph in cell.paragraphs:
                        paragraph.paragraph_format.keep_with_next = index != last_row
    doc.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guide", action="store_true", help="Build the experiment guide.")
    parser.add_argument("--pandoc", default="pandoc", help="Path to the Pandoc binary.")
    args = parser.parse_args()
    stem = ("PANDUAN_STEP_BY_STEP_PERCOBAAN" if args.guide
            else "Laporan_Pengujian_Klasifikasi_Aktivitas_ESP32")
    source = ROOT / f"{stem}.md"
    target = source.with_suffix(".docx")
    title, _, body = source.read_text(encoding="utf-8").partition("\n")

    with TemporaryDirectory(dir=ROOT) as directory:
        output = Path(directory) / target.name
        command = [
            args.pandoc, "--from", "gfm", "--to", "docx", "--standalone",
            "--metadata", f"title={title.removeprefix('# ')}",
            "--metadata", "lang=id", "--output", str(output),
        ]
        if target.exists():
            command.extend(["--reference-doc", str(target)])
        subprocess.run(command, input=body.encode("utf-8"), cwd=ROOT, check=True)
        format_document(output, args.guide)
        output.replace(target)


if __name__ == "__main__":
    main()

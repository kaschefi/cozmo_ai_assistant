"""
Convert docs/HLD.md into a beautifully styled Word document (docs/HLD.docx).
Replaces Mermaid text code blocks with the high-resolution rendered diagrams:
- Diagram 1 slot in HLD -> diagram2.png
- Diagram 2 slot in HLD -> diagram3.png
- Diagram 3 slot in HLD -> diagram4.png
- Diagram 4 slot in HLD -> diagram5.png
- Diagram 5 slot in HLD -> diagram6.png
Wide diagrams are placed onto dedicated full-page Landscape sections with 0.5" margins,
ensuring text and flowcharts remain crystal clear, sharp, and easily readable.
"""

import os
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION, WD_ORIENTATION
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn
from PIL import Image

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_background(cell, hex_color):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_table_borders(table, color="D3D3D3", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>\n'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:left w:val="none"/>\n'
        f'  <w:right w:val="none"/>\n'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:insideV w:val="none"/>\n'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def add_styled_paragraph(doc, text="", style='Normal', space_before=0, space_after=4, line_spacing=1.15):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    return p

def format_inline_text(paragraph, text, base_font_size=10.5, font_name="Calibri", base_color=None):
    pattern = re.compile(
        r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*|`.*?`|\[.*?\]\(.*?\))'
    )
    tokens = pattern.split(text)
    for token in tokens:
        if not token:
            continue
        run = paragraph.add_run()
        run.font.name = font_name
        run.font.size = Pt(base_font_size)
        if base_color:
            run.font.color.rgb = base_color

        if token.startswith('***') and token.endswith('***'):
            run.text = token[3:-3]
            run.bold = True
            run.italic = True
        elif token.startswith('**') and token.endswith('**'):
            run.text = token[2:-2]
            run.bold = True
        elif token.startswith('*') and token.endswith('*'):
            run.text = token[1:-1]
            run.italic = True
        elif token.startswith('`') and token.endswith('`'):
            run.text = token[1:-1]
            run.font.name = "Consolas"
            run.font.size = Pt(base_font_size * 0.9)
            run.font.color.rgb = RGBColor(199, 37, 78)
        elif token.startswith('[') and '](' in token and token.endswith(')'):
            m = re.match(r'\[(.*?)\]\((.*?)\)', token)
            if m:
                label = m.group(1)
                run.text = label
                run.font.color.rgb = RGBColor(26, 115, 232)
                run.underline = True
            else:
                run.text = token
        else:
            clean_text = token.replace('$', '')
            run.text = clean_text

def render_table(doc, lines):
    header_line = lines[0]
    headers = [c.strip() for c in header_line.strip('|').split('|')]
    
    rows = []
    for line in lines[2:]:
        cols = [c.strip() for c in line.strip('|').split('|')]
        if len(cols) < len(headers):
            cols += [''] * (len(headers) - len(cols))
        rows.append(cols[:len(headers)])

    num_cols = len(headers)
    table = doc.add_table(rows=len(rows) + 1, cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table, color="D3D3D3", sz="4")

    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = ""
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        format_inline_text(p, title, base_font_size=9.5, base_color=RGBColor(255, 255, 255))
        for r in p.runs:
            r.bold = True
        set_cell_background(hdr_cells[i], "1A365D")
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=160, right=160)

    for r_idx, row_data in enumerate(rows):
        row_cells = table.rows[r_idx + 1].cells
        bg_color = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, cell_value in enumerate(row_data):
            row_cells[c_idx].text = ""
            p = row_cells[c_idx].paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            format_inline_text(p, cell_value, base_font_size=9)
            set_cell_background(row_cells[c_idx], bg_color)
            set_cell_margins(row_cells[c_idx], top=100, bottom=100, left=160, right=160)

    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(0)
    p_spacer.paragraph_format.space_after = Pt(6)

def add_fullpage_landscape_diagram(doc, img_path, caption=None):
    """
    Creates a dedicated Landscape section for maximum diagram width and crisp text readability.
    Switches back to Portrait afterwards.
    """
    im = Image.open(img_path)
    img_w, img_h = im.size
    aspect_ratio = img_h / img_w

    # Switch to Landscape section
    sec = doc.add_section(WD_SECTION.NEW_PAGE)
    sec.orientation = WD_ORIENTATION.LANDSCAPE
    sec.page_width = Inches(11.0)
    sec.page_height = Inches(8.5)
    sec.top_margin = Inches(0.4)
    sec.bottom_margin = Inches(0.4)
    sec.left_margin = Inches(0.5)
    sec.right_margin = Inches(0.5)

    max_w = 10.0
    max_h = 7.1

    target_w = max_w
    target_h = target_w * aspect_ratio
    if target_h > max_h:
        target_h = max_h
        target_w = target_h / aspect_ratio

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(img_path, width=Inches(target_w), height=Inches(target_h))

    if caption:
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(2)
        p_cap.paragraph_format.space_after = Pt(4)
        run_cap = p_cap.add_run(caption)
        run_cap.font.name = "Calibri"
        run_cap.font.size = Pt(10)
        run_cap.font.bold = True
        run_cap.font.color.rgb = RGBColor(71, 85, 105)

    # Return to Portrait section for standard reading
    sec_back = doc.add_section(WD_SECTION.NEW_PAGE)
    sec_back.orientation = WD_ORIENTATION.PORTRAIT
    sec_back.page_width = Inches(8.5)
    sec_back.page_height = Inches(11.0)
    sec_back.top_margin = Inches(1.0)
    sec_back.bottom_margin = Inches(1.0)
    sec_back.left_margin = Inches(1.0)
    sec_back.right_margin = Inches(1.0)

def markdown_to_docx(md_path, docx_path, images_dir):
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    doc = Document()

    # Standard Portrait margins for first section
    s0 = doc.sections[0]
    s0.orientation = WD_ORIENTATION.PORTRAIT
    s0.page_width = Inches(8.5)
    s0.page_height = Inches(11.0)
    s0.top_margin = Inches(1.0)
    s0.bottom_margin = Inches(1.0)
    s0.left_margin = Inches(1.0)
    s0.right_margin = Inches(1.0)

    lines = md_text.splitlines()
    i = 0
    in_code_block = False
    code_block_lines = []
    code_block_lang = ""

    in_table = False
    table_lines = []
    diagram_counter = 0

    # User mapping:
    # Diagram 1 in doc -> diagram2.png
    # Diagram 2 in doc -> diagram3.png
    # Diagram 3 in doc -> diagram4.png
    # Diagram 4 in doc -> diagram5.png
    # Diagram 5 in doc -> diagram6.png
    diagram_image_map = {
        1: "diagram2.png",
        2: "diagram3.png",
        3: "diagram4.png",
        4: "diagram5.png",
        5: "diagram6.png"
    }

    diagram_captions = {
        1: "Figure 1: Ecosystem Context & Architecture Boundaries (Diagram 1)",
        2: "Figure 2: Component Interaction & Subsystem Decomposition (Diagram 2)",
        3: "Figure 3: Multimodal End-to-End Streaming Data Flow (Diagram 3)",
        4: "Figure 4: Two-Tier Routing Decision Tree & Benchmark Pipeline (Diagram 4)",
        5: "Figure 5: Autonomous Vision & Cyber-Physical Motion Control Loop (Diagram 5)",
    }

    while i < len(lines):
        line = lines[i]

        # Handle Code Block
        if line.strip().startswith('```'):
            if in_code_block:
                if code_block_lang.lower() == 'mermaid':
                    diagram_counter += 1
                    target_image_name = diagram_image_map.get(diagram_counter, f"diagram{diagram_counter + 1}.png")
                    png_file = os.path.join(images_dir, target_image_name)
                    caption = diagram_captions.get(diagram_counter, f"Figure {diagram_counter}: Architecture Diagram")
                    if os.path.exists(png_file):
                        add_fullpage_landscape_diagram(doc, png_file, caption=caption)
                    else:
                        p = doc.add_paragraph(f"[Diagram not found at {png_file}]")
                        p.paragraph_format.space_after = Pt(6)
                else:
                    table = doc.add_table(rows=1, cols=1)
                    table.alignment = WD_TABLE_ALIGNMENT.CENTER
                    cell = table.cell(0, 0)
                    set_cell_background(cell, "F1F5F9")
                    set_cell_margins(cell, top=140, bottom=140, left=180, right=180)
                    set_table_borders(table, color="CBD5E1", sz="4")

                    cell.text = ""
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(0)
                    p.paragraph_format.line_spacing = 1.05

                    code_content = "\n".join(code_block_lines)
                    run = p.add_run(code_content)
                    run.font.name = "Consolas"
                    run.font.size = Pt(8.5)
                    run.font.color.rgb = RGBColor(30, 41, 59)

                    p_spacer = doc.add_paragraph()
                    p_spacer.paragraph_format.space_before = Pt(0)
                    p_spacer.paragraph_format.space_after = Pt(6)

                in_code_block = False
                code_block_lines = []
                code_block_lang = ""
            else:
                in_code_block = True
                code_block_lang = line.strip()[3:].strip()
                code_block_lines = []
            i += 1
            continue

        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue

        # Handle Markdown Table
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            if not in_table:
                in_table = True
                table_lines = [line]
            else:
                table_lines.append(line)
            i += 1
            continue
        else:
            if in_table:
                render_table(doc, table_lines)
                in_table = False
                table_lines = []

        if not stripped:
            i += 1
            continue

        # Horizontal Rule
        if stripped in ('---', '***', '___'):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            pPr = p._p.get_or_add_pPr()
            pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="6" w:space="1" w:color="CBD5E1"/></w:pBdr>')
            pPr.append(pBdr)
            i += 1
            continue

        # Headings
        if stripped.startswith('# '):
            p = add_styled_paragraph(doc, "", space_before=16, space_after=8)
            format_inline_text(p, stripped[2:], base_font_size=20, base_color=RGBColor(15, 23, 42))
            for r in p.runs:
                r.bold = True
        elif stripped.startswith('## '):
            p = add_styled_paragraph(doc, "", space_before=14, space_after=6)
            format_inline_text(p, stripped[3:], base_font_size=15, base_color=RGBColor(30, 58, 138))
            for r in p.runs:
                r.bold = True
        elif stripped.startswith('### '):
            p = add_styled_paragraph(doc, "", space_before=10, space_after=4)
            format_inline_text(p, stripped[4:], base_font_size=12.5, base_color=RGBColor(51, 65, 85))
            for r in p.runs:
                r.bold = True
        elif stripped.startswith('#### '):
            p = add_styled_paragraph(doc, "", space_before=8, space_after=3)
            format_inline_text(p, stripped[5:], base_font_size=11, base_color=RGBColor(71, 85, 105))
            for r in p.runs:
                r.bold = True
        # Bullet list
        elif stripped.startswith(('* ', '- ', '+ ')):
            indent_level = (len(line) - len(line.lstrip())) // 2
            p = add_styled_paragraph(doc, "", space_before=1, space_after=2)
            p.paragraph_format.left_indent = Inches(0.25 * (indent_level + 1))
            run_bullet = p.add_run("•  ")
            run_bullet.bold = True
            run_bullet.font.color.rgb = RGBColor(59, 130, 246)
            format_inline_text(p, stripped[2:], base_font_size=10)
        # Numbered list
        elif re.match(r'^\d+\.\s', stripped):
            m = re.match(r'^(\d+\.)\s(.*)', stripped)
            num_label = m.group(1)
            content = m.group(2)
            p = add_styled_paragraph(doc, "", space_before=2, space_after=2)
            p.paragraph_format.left_indent = Inches(0.25)
            run_num = p.add_run(num_label + " ")
            run_num.bold = True
            run_num.font.color.rgb = RGBColor(30, 58, 138)
            format_inline_text(p, content, base_font_size=10)
        # Blockquote
        elif stripped.startswith('> '):
            table = doc.add_table(rows=1, cols=1)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cell = table.cell(0, 0)
            set_cell_background(cell, "F8FAFC")
            set_cell_margins(cell, top=80, bottom=80, left=160, right=160)
            tblPr = table._tbl.tblPr
            borders = parse_xml(
                f'<w:tblBorders {nsdecls("w")}>\n'
                f'  <w:left w:val="single" w:sz="18" w:space="0" w:color="3B82F6"/>\n'
                f'  <w:top w:val="none"/>\n'
                f'  <w:bottom w:val="none"/>\n'
                f'  <w:right w:val="none"/>\n'
                f'</w:tblBorders>'
            )
            tblPr.append(borders)
            p = cell.paragraphs[0]
            format_inline_text(p, stripped[2:], base_font_size=9.5, base_color=RGBColor(71, 85, 105))
            for r in p.runs:
                r.italic = True
        else:
            p = add_styled_paragraph(doc, "", space_before=2, space_after=5)
            format_inline_text(p, stripped, base_font_size=10)

        i += 1

    if in_table:
        render_table(doc, table_lines)

    doc.save(docx_path)
    print(f"Successfully generated: {docx_path}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    md_file = os.path.join(current_dir, "HLD.md")
    docx_file = os.path.join(current_dir, "HLD.docx")
    images_folder = os.path.join(current_dir, "images")
    markdown_to_docx(md_file, docx_file, images_folder)

import streamlit as st
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
from typing import List
from io import BytesIO
import base64

def labeller(label_type: str, label_txt_list: List[str], skiprows: int):
    if label_type not in ['circle', 'rect']:
        raise ValueError("label_type must be either 'circle' or 'rect'")
    
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('app/templates/template.html')
    
    row = 5 if label_type == 'rect' else 12
    skipped_labels = ['' for _ in range(skiprows * row)]
    labels = skipped_labels + label_txt_list
    
    max_chars = [10, 13, 15, 13, 10]
    base_font_size = 6.5

    def adjust_font_size(line: str, index: int) -> str:
        if len(line) > max_chars[index]:
            new_font_size = base_font_size * (max_chars[index] / len(line))
            return f'<span style="font-size: {new_font_size}px">{line}</span>'
        return line

    def split_long_lines(lines: List[str]) -> List[str]:
        new_lines = []
        for line in lines:
            if len(line) > 12:
                words = line.split(' ')
                temp_line = words[0]
                for word in words[1:]:
                    if len(temp_line) + len(word) + 1 <= 12:
                        temp_line += ' ' + word
                    else:
                        new_lines.append(temp_line)
                        temp_line = word
                new_lines.append(temp_line)
            else:
                new_lines.append(line)
        return new_lines

    def adjust_for_label(label: str) -> str:
        lines = split_long_lines(label.split('<br>'))
        return '<br>'.join([adjust_font_size(line, i) for i, line in enumerate(lines[:5])])
    
    records = [{'sample': adjust_for_label(label)} for label in labels]
    rendered_html = template.render(records=records)
    
    buffer = BytesIO()
    # HTML(string=rendered_html).write_pdf(f"labels/{output_file}.pdf", stylesheets=[f"app/templates/{label_type}.css"])
    HTML(string=rendered_html).write_pdf(buffer, stylesheets=[f"app/templates/{label_type}.css"])
    buffer.seek(0)  # Move to the beginning of the buffer
    
    base64_pdf = base64.b64encode(buffer.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    return pdf_display

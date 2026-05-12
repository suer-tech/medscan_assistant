"""PDF generation using WeasyPrint"""
from typing import Optional
from datetime import datetime
import tempfile
import os
import secrets
import string

# Optional nanoid import
try:
    from nanoid import generate
    NANOID_AVAILABLE = True
except ImportError:
    NANOID_AVAILABLE = False
    # Fallback function if nanoid is not available
    def generate(size=21):
        alphabet = string.ascii_letters + string.digits + '-_'
        return ''.join(secrets.choice(alphabet) for _ in range(size))

# Try to import WeasyPrint, but don't fail if it's not available
WEASYPRINT_AVAILABLE = False
HTML = None
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    # WeasyPrint requires system libraries on Windows
    WEASYPRINT_AVAILABLE = False
    HTML = None


STUDY_TYPE_LABELS = {
    "retinal_scan": "Сканирование сетчатки",
    "optic_nerve": "Анализ зрительного нерва",
    "macular_analysis": "Анализ макулярной области",
}


def _generate_html(
    title: str,
    study_type: str,
    created_at: datetime,
    analysis_result: str,
    image_url: Optional[str] = None
) -> str:
    """Generate HTML for PDF"""
    study_type_label = STUDY_TYPE_LABELS.get(study_type, study_type)
    formatted_date = created_at.strftime("%d %B %Y")
    
    image_section = ""
    if image_url:
        image_section = f"""
  <div class="image-section">
    <img src="{image_url}" alt="Рентгеновский снимок" />
  </div>
"""

    paragraphs = "".join(f'<p>{para}</p>' for para in analysis_result.replace('\\n', '\n').split('\n') if para.strip())

    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    @page {{
      size: A4;
      margin: 2cm;
    }}
    body {{
      font-family: 'Arial', sans-serif;
      line-height: 1.6;
      color: #1e293b;
      font-size: 12pt;
    }}
    .header {{
      text-align: center;
      margin-bottom: 30px;
      padding-bottom: 20px;
      border-bottom: 2px solid #2563eb;
    }}
    .header h1 {{
      color: #2563eb;
      margin: 0 0 10px 0;
      font-size: 24pt;
    }}
    .header .meta {{
      color: #64748b;
      font-size: 11pt;
    }}
    .image-section {{
      text-align: center;
      margin: 30px 0;
    }}
    .image-section img {{
      max-width: 100%;
      height: auto;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
    }}
    .content {{
      margin-top: 30px;
    }}
    .content h2 {{
      color: #2563eb;
      font-size: 16pt;
      margin-top: 25px;
      margin-bottom: 15px;
    }}
    .content p {{
      margin: 10px 0;
      text-align: justify;
    }}
    .footer {{
      margin-top: 50px;
      padding-top: 20px;
      border-top: 1px solid #e2e8f0;
      text-align: center;
      color: #64748b;
      font-size: 10pt;
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>{title}</h1>
    <div class="meta">
      <p><strong>Тип исследования:</strong> {study_type_label}</p>
      <p><strong>Дата:</strong> {formatted_date}</p>
    </div>
  </div>
  
  {image_section}
  
  <div class="content">
    <h2>Результаты анализа</h2>
    {paragraphs}
  </div>
  
  <div class="footer">
    <p>Документ создан автоматически системой МедСкан</p>
  </div>
</body>
</html>
    """.strip()
    
    return html


async def generate_pdf(
    title: str,
    study_type: str,
    created_at: datetime,
    analysis_result: str,
    image_url: Optional[str] = None
) -> bytes:
    """Generate PDF from study data"""
    if not WEASYPRINT_AVAILABLE:
        raise ValueError("WeasyPrint is not available. Please install required dependencies for PDF generation.")
    
    html_content = _generate_html(title, study_type, created_at, analysis_result, image_url)
    temp_id = generate()
    
    # Use temporary file for HTML
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as html_file:
        html_path = html_file.name
        html_file.write(html_content)
    
    try:
        # Generate PDF using WeasyPrint
        pdf_bytes = HTML(filename=html_path).write_pdf()
        
        # Clean up
        os.unlink(html_path)
        
        return pdf_bytes
    except Exception as error:
        # Clean up on error
        if os.path.exists(html_path):
            os.unlink(html_path)
        print(f"Error generating PDF: {error}")
        raise ValueError("Failed to generate PDF")


"""Synthetic PDF safety and rendering checks; no patient data or AI calls."""

import asyncio
import base64
from datetime import datetime
from io import BytesIO
import json
import random
import unittest
from unittest.mock import patch

from PIL import Image
from pypdf import PdfReader

from server.pdf import MAX_ANALYSIS_CHARS, MAX_PDF_BYTES, _decode_raster_image, _escaped_text, generate_pdf


def synthetic_image() -> str:
    buffer = BytesIO()
    Image.new("RGB", (160, 100), color=(215, 230, 245)).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


class PdfSafetyTests(unittest.TestCase):
    def test_escapes_all_user_markup(self):
        self.assertEqual(_escaped_text('<b>А & Б</b>'), '&lt;b&gt;А &amp; Б&lt;/b&gt;')

    def test_external_file_and_svg_images_are_rejected_without_fetching(self):
        urls = [
            "https://example.invalid/patient.png", "http://127.0.0.1/private",
            "file:///etc/passwd", "C:/private.png", "//example.invalid/image.png",
            "data:image/svg+xml;base64,PHN2Zy8+", "data:text/html;base64,PHN2Zy8+",
            "data:image/png;base64,PHN2Zy8+", "data:image/png;base64,!!!!",
        ]
        with patch("urllib.request.urlopen", side_effect=AssertionError("Network is forbidden")):
            for url in urls:
                with self.subTest(url=url), self.assertRaises(ValueError):
                    _decode_raster_image(url)

    def test_raster_mime_must_match_decoded_content(self):
        with self.assertRaises(ValueError):
            _decode_raster_image(synthetic_image().replace("image/png", "image/jpeg"))

    def test_valid_raster_remains_printable(self):
        with Image.open(_decode_raster_image(synthetic_image())) as result:
            self.assertEqual(result.size, (160, 100))
            self.assertEqual(result.format, "JPEG")

    def test_text_and_image_limits(self):
        with self.assertRaises(ValueError):
            asyncio.run(generate_pdf("А" * 1001, "retinal_scan", datetime(2026, 9, 11), "Тест"))
        with self.assertRaisesRegex(ValueError, "Слишком большой текст"):
            asyncio.run(generate_pdf("Тест", "retinal_scan", datetime(2026, 9, 11), "А" * (MAX_ANALYSIS_CHARS + 1)))
        with patch("server.pdf.MAX_IMAGE_PIXELS", 1), self.assertRaises(ValueError):
            _decode_raster_image(synthetic_image())
        with patch("server.pdf.MAX_IMAGE_BYTES", 1), self.assertRaises(ValueError):
            _decode_raster_image(synthetic_image())


class PdfRenderingTests(unittest.TestCase):
    def test_large_synthetic_raster_fits_vercel_response_budget(self):
        # Seeded RGB noise is deliberately difficult to compress. The original
        # PNG is under 10 MB but larger than the 1600 px PDF viewing copy.
        size = (1700, 1700)
        original = BytesIO()
        Image.frombytes("RGB", size, random.Random(42).randbytes(size[0] * size[1] * 3)).save(original, format="PNG")
        image_url = "data:image/png;base64," + base64.b64encode(original.getvalue()).decode("ascii")
        with Image.open(_decode_raster_image(image_url)) as preview:
            self.assertEqual(preview.size, (1600, 1600))
        output = asyncio.run(generate_pdf("Тест большого изображения", "retinal_scan", datetime(2026, 9, 11), "Синтетические данные.", image_url))
        self.assertLess(len(output), MAX_PDF_BYTES)
        response = json.dumps({"pdf": base64.b64encode(output).decode("ascii"), "filename": "тест.pdf"}).encode("utf-8")
        self.assertLess(len(response), 4_500_000)
        text = " ".join(" ".join(p.extract_text().split()) for p in PdfReader(BytesIO(output)).pages)
        self.assertIn("уменьшенная копия для просмотра", text)
        self.assertIn("Оригинал доступен в исследовании.", text)

    def test_pdf_output_limit_reports_an_actionable_error(self):
        with patch("server.pdf.MAX_PDF_BYTES", 1), self.assertRaisesRegex(ValueError, "Сократите текст протокола"):
            asyncio.run(generate_pdf("Тест", "retinal_scan", datetime(2026, 9, 11), "Только синтетические данные."))

    def test_cyrillic_multipage_pdf_keeps_text_without_active_markup(self):
        title = 'Тестовый протокол <img src="file:///private">'
        analysis = (
            "Только синтетические данные. Врач: тестовый специалист.\\n"
            "<link href=\"https://example.invalid\">Ссылка не активна</link>\n\n"
            + "\n".join(f"Строка {index:03d}: проверка кириллицы, переносов и сохранения протокола." for index in range(100))
            + "\nКонец тестового протокола."
        )
        with patch("urllib.request.urlopen", side_effect=AssertionError("Network is forbidden")):
            output = asyncio.run(generate_pdf(title, "retinal_scan", datetime(2026, 9, 11), analysis, synthetic_image()))
        self.assertTrue(output.startswith(b"%PDF-"))
        reader = PdfReader(BytesIO(output))
        self.assertGreaterEqual(len(reader.pages), 3)
        text = "\n".join(page.extract_text() for page in reader.pages)
        normalized_text = " ".join(text.split())
        for expected in [title, "Сканирование сетчатки", "11.09.2026", "Врач: тестовый специалист", "Строка 099", "Конец тестового протокола."]:
            self.assertIn(expected, normalized_text)
        self.assertEqual(reader.metadata.title, title)
        self.assertTrue(any(page.images for page in reader.pages))
        self.assertFalse(any(page.get("/Annots") for page in reader.pages))
        self.assertNotIn("/JavaScript", reader.trailer["/Root"])


if __name__ == "__main__":
    unittest.main()

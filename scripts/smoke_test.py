"""Exercise a deployed MedScan with synthetic data; never print credentials.

--ai makes two real provider requests and must only be used with owner approval.
Only the synthetic study created by this run is deleted, including on failure.
"""
import argparse
import base64
import io
import json
from pathlib import Path
import uuid

import httpx
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://medscan-assistant.vercel.app")
    parser.add_argument("--ai", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    access = json.loads((root / ".private" / "medscan-access.json").read_text(encoding="utf-8"))
    image = Image.new("RGB", (400, 180), "white")
    ImageDraw.Draw(image).text((20, 50), "SYNTHETIC TEST 123 - NOT PATIENT DATA", fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    png = buffer.getvalue()
    study_id = None
    with httpx.Client(base_url=args.url.rstrip("/"), timeout=115.0, follow_redirects=False) as client:
        def check(method, path, expected=200, **kwargs):
            response = client.request(method, path, **kwargs)
            if response.status_code != expected:
                # Status and path are safe; never dump bodies/cookies/login data.
                raise RuntimeError(f"{method} {path}: HTTP {response.status_code}, expected {expected}")
            return response

        health = check("GET", "/api/health").json()
        assert health["database"] == "postgres" and health["persistent"] and health["authConfigured"]
        print("PASS health: PostgreSQL, persistent storage, configured auth", flush=True)
        check("GET", "/api/studies", 401)
        check("POST", "/api/auth/login", 401, json={"email": access["email"], "password": "definitely-not-the-owner-password"})
        check("POST", "/api/auth/login", json={"email": access["email"], "password": access["password"]})
        assert check("GET", "/api/auth/me").json()["email"] == access["email"]
        print("PASS unauthorized access, login and session", flush=True)
        try:
            study_id = check("POST", "/api/studies", json={
                "title": "Synthetic deployment check " + uuid.uuid4().hex[:10], "studyType": "free_query",
            }).json()["id"]
            image_data = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
            uploaded = check("POST", f"/api/studies/{study_id}/images", json={
                "imageData": image_data, "filename": "synthetic-test.png", "mimeType": "image/png",
            }).json()
            study = check("GET", f"/api/studies/{study_id}").json()
            assert len(study["images"]) == 1 and not study["images"][0]["url"].startswith("data:")
            assert check("GET", uploaded["url"]).content == png
            check("PATCH", f"/api/studies/{study_id}", json={"title": "Synthetic verified", "analysisResult": "Синтетическая проверка. Не медицинское заключение."})
            assert check("GET", f"/api/studies/{study_id}").json()["title"] == "Synthetic verified"
            print("PASS create, original image upload/download, persistence and edit", flush=True)
            if args.ai:
                assert health["aiConfigured"], "AI is not configured"
                analysis = check("POST", f"/api/studies/{study_id}/analyze", json={
                    "userQuery": "Это синтетическая тестовая картинка, не медицинский снимок. Прочитай текст на ней одним предложением. Не делай медицинских выводов.",
                }).json()
                assert analysis["success"] and analysis["analysisResult"]
                check("POST", f"/api/studies/{study_id}/messages", json={
                    "message": "Подтверди одним коротким предложением, что это синтетическая проверка, не данные пациента.",
                })
                messages = check("GET", f"/api/studies/{study_id}/messages").json()
                assert len(messages) >= 2
                print("PASS live AI image analysis and chat (synthetic data only)", flush=True)
            exported = check("GET", f"/api/studies/{study_id}/pdf").json()
            pdf = base64.b64decode(exported["pdf"], validate=True)
            assert pdf.startswith(b"%PDF-") and len(pdf) < 3 * 1024 * 1024
            print(f"PASS PDF export ({len(pdf)} bytes)", flush=True)
        finally:
            if study_id is not None:
                check("DELETE", f"/api/studies/{study_id}")
                check("GET", f"/api/studies/{study_id}", 404)
                print("CLEANUP removed this run's synthetic study and attachments", flush=True)
        check("POST", "/api/auth/logout")
        check("GET", "/api/studies", 401)
        print("PASS logout", flush=True)


if __name__ == "__main__":
    main()

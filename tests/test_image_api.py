"""Image route tests with synthetic rasters and a fake in-memory repository."""
import ast
import base64
import binascii
import io
import json
from pathlib import Path
import struct
import unittest
import warnings
import zlib

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field


ROUTERS_PATH = Path(__file__).resolve().parents[1] / "server" / "routers.py"
MAX_BYTES = 3 * 1024 * 1024


def synthetic_image(image_format="PNG"):
    with io.BytesIO() as buffer:
        Image.new("RGB", (2, 2), (0, 128, 255)).save(buffer, format=image_format)
        return buffer.getvalue()


def png_at_limit():
    """Add a valid inert PNG text chunk so the test file is exactly 3 MiB."""
    original = synthetic_image()
    key = b"synthetic\0"
    payload = key + b"a" * (MAX_BYTES - len(original) - len(key) - 12)
    chunk_type = b"tEXt"
    chunk = struct.pack(">I", len(payload)) + chunk_type + payload
    chunk += struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    return original[:-12] + chunk + original[-12:]


def upload_payload(content, mime="image/png"):
    return {"imageData": f"data:{mime};base64," + base64.b64encode(content).decode("ascii"),
            "filename": "synthetic-image", "mimeType": mime}


class FakeDB:
    def __init__(self):
        self.studies = {
            1: {"id": 1, "userId": 1, "title": "Synthetic study", "studyType": "lab_blood", "analysisResult": None},
            2: {"id": 2, "userId": 2, "title": "Other synthetic study", "studyType": "lab_blood", "analysisResult": None},
        }
        self.images = []

    async def get_study_by_id(self, study_id):
        return self.studies.get(study_id)

    async def get_study_images(self, study_id):
        return [item.copy() for item in self.images if item["studyId"] == study_id]

    async def create_study_image(self, data):
        image_id = len(self.images) + 1
        self.images.append({"id": image_id, **data, "createdAt": "2026-01-01T00:00:00+00:00"})
        return image_id


async def require_synthetic_user(request: Request):
    user_id = request.headers.get("x-synthetic-user")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"id": int(user_id)}


def image_test_app(db):
    # Load only these route definitions, excluding env, real storage, auth and AI.
    names = {"StudyUploadImageInput", "MAX_IMAGE_BYTES", "IMAGE_FORMAT_MIMES",
             "validate_study_image", "study_image_metadata", "studies_get",
             "studies_upload_image", "studies_get_image"}
    tree = ast.parse(ROUTERS_PATH.read_text(encoding="utf-8-sig"))
    selected = []
    for node in tree.body:
        if getattr(node, "name", None) in names:
            selected.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in names for target in node.targets):
            selected.append(node)
    namespace = {
        "router": APIRouter(), "db": db, "base64": base64, "binascii": binascii,
        "io": io, "warnings": warnings, "Image": Image, "UnidentifiedImageError": UnidentifiedImageError,
        "Depends": Depends, "require_user": require_synthetic_user, "HTTPException": HTTPException,
        "Response": Response, "JSONResponse": JSONResponse, "BaseModel": BaseModel,
        "Field": Field, "generate": lambda: "synthetic-id",
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(ROUTERS_PATH), "exec"), namespace)
    app = FastAPI()
    app.include_router(namespace["router"])
    return app


class ImageAPITests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.client = TestClient(image_test_app(self.db))
        self.headers = {"x-synthetic-user": "1"}

    def tearDown(self):
        self.client.close()

    def upload(self, payload, headers=None):
        return self.client.post("/api/studies/1/images", json=payload, headers=self.headers if headers is None else headers)

    def test_all_four_formats_round_trip_without_reencoding(self):
        for format_name, mime in (("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp"), ("GIF", "image/gif")):
            with self.subTest(format=format_name):
                original = synthetic_image(format_name)
                response = self.upload(upload_payload(original, mime))
                self.assertEqual(response.status_code, 200)
                image_url = response.json()["url"]
                self.assertTrue(image_url.startswith("/api/studies/1/images/"))
                self.assertLess(len(response.content), 256)
                downloaded = self.client.get(image_url, headers=self.headers)
                self.assertEqual(downloaded.status_code, 200)
                self.assertEqual(downloaded.content, original)
                self.assertEqual(downloaded.headers["content-type"], mime)
                self.assertEqual(downloaded.headers["cache-control"], "private, no-store")
                self.assertEqual(downloaded.headers["x-content-type-options"], "nosniff")
                self.assertEqual(self.db.images[-1]["fileSize"], len(original))
                self.assertEqual(self.db.images[-1]["url"], upload_payload(original, mime)["imageData"])

    def test_three_mib_original_fits_request_and_binary_response(self):
        original = png_at_limit()
        self.assertEqual(len(original), MAX_BYTES)
        payload = upload_payload(original)
        self.assertLess(len(json.dumps(payload).encode()), 4_500_000)
        response = self.upload(payload)
        self.assertEqual(response.status_code, 200)
        downloaded = self.client.get(response.json()["url"], headers=self.headers)
        self.assertEqual(downloaded.status_code, 200)
        self.assertTrue(downloaded.content == original)
        self.assertEqual(len(downloaded.content), MAX_BYTES)

    def test_oversized_original_is_rejected_before_storage(self):
        response = self.upload(upload_payload(b"a" * (MAX_BYTES + 1)))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.db.images, [])

    def test_invalid_data_urls_and_mime_spoofing_are_rejected(self):
        invalid = [
            {"imageData": "https://invalid.example/image.png", "filename": "synthetic", "mimeType": "image/png"},
            {"imageData": "data:image/png;base64,%%%%", "filename": "synthetic", "mimeType": "image/png"},
            upload_payload(b""),
            upload_payload(b"not a raster"),
            upload_payload(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/svg+xml"),
            upload_payload(synthetic_image(), "image/jpeg"),
        ]
        for payload in invalid:
            with self.subTest(mime=payload["mimeType"]):
                self.assertEqual(self.upload(payload).status_code, 400)
        self.assertEqual(self.db.images, [])

    def test_study_json_contains_metadata_not_image_base64(self):
        response = self.upload(upload_payload(synthetic_image()))
        original_data_url = self.db.images[0]["url"]
        for number in range(2, 17):
            self.db.images.append({**self.db.images[0], "id": number, "url": original_data_url * 40_000})
        details = self.client.get("/api/studies/1", headers=self.headers)
        self.assertEqual(details.status_code, 200)
        self.assertLess(len(details.content), 16_384)
        self.assertEqual(len(details.json()["images"]), 16)
        self.assertNotIn("base64", details.text)
        self.assertEqual(details.json()["images"][0]["url"], response.json()["url"])
        self.assertEqual(self.db.images[0]["url"], original_data_url)

    def test_image_requires_auth_and_study_ownership(self):
        response = self.upload(upload_payload(synthetic_image()))
        image_url = response.json()["url"]
        self.assertEqual(self.client.get(image_url).status_code, 401)
        self.assertEqual(self.client.get(image_url, headers={"x-synthetic-user": "2"}).status_code, 403)
        self.assertEqual(self.client.get("/api/studies/1/images/999", headers=self.headers).status_code, 404)
        self.assertEqual(self.client.get("/api/studies/2/images/1", headers={"x-synthetic-user": "2"}).status_code, 404)
        self.assertEqual(self.upload(upload_payload(synthetic_image()), headers={}).status_code, 401)


if __name__ == "__main__":
    unittest.main()

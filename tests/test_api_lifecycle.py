"""Full offline API lifecycle with synthetic data, SQLite, and mocked AI only."""
import asyncio
import base64
from contextlib import ExitStack
import importlib
import importlib.util
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from passlib.hash import pbkdf2_sha256
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_EMAIL = "owner@example.test"
FIXTURE_PASSWORD = "synthetic-only password with spaces "
FIXTURE_JWT_SECRET = "synthetic-only-jwt-secret-not-for-deployment-123456"


def synthetic_upload():
    output = BytesIO()
    Image.new("RGB", (4, 3), (37, 99, 235)).save(output, format="PNG")
    original = output.getvalue()
    return original, {
        "imageData": "data:image/png;base64," + base64.b64encode(original).decode("ascii"),
        "filename": "synthetic.png", "mimeType": "image/png",
    }


class APILifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_hash = pbkdf2_sha256.using(rounds=1_000).hash(FIXTURE_PASSWORD)

    def setUp(self):
        self.resources = ExitStack()
        self.addCleanup(self.resources.close)
        directory = self.resources.enter_context(tempfile.TemporaryDirectory(prefix="medscan-api-test-"))
        self.database_path = Path(directory) / "synthetic.sqlite"
        self.resources.enter_context(patch.dict(os.environ, {
            "NODE_ENV": "test", "BACKEND_ONLY": "true", "MEDSCAN_STORAGE": "postgres",
            "DATABASE_URL": "sqlite:///" + self.database_path.as_posix(),
            "MEDSCAN_ADMIN_EMAIL": FIXTURE_EMAIL, "MEDSCAN_ADMIN_PASSWORD_HASH": self.fixture_hash,
            "JWT_SECRET": FIXTURE_JWT_SECRET, "BUILT_IN_FORGE_API_KEY": "",
            "OAUTH_SERVER_URL": "", "VITE_APP_ID": "synthetic-app",
        }, clear=True))
        # Even if a developer has local configuration, the tests must not load it.
        self.resources.enter_context(patch("dotenv.load_dotenv", return_value=False))
        self.resources.enter_context(patch("httpx.AsyncClient.request", side_effect=AssertionError("External HTTP is forbidden in API tests")))
        self.resources.enter_context(patch("urllib.request.urlopen", side_effect=AssertionError("External HTTP is forbidden in API tests")))
        self.routes = importlib.import_module("server.routers")
        self.store = importlib.import_module("server.postgres_storage")
        if self.store._engine is not None:
            self.store._engine.dispose()
            self.store._engine = None
        self.resources.callback(self.reset_engine)
        # Guarantee the real persistent adapter even if another test imported
        # routers in local-JSON mode earlier in the same process.
        self.resources.enter_context(patch.object(self.routes, "db", self.store))
        self.app = importlib.import_module("server._core.main").app
        self.client = self.resources.enter_context(TestClient(self.app, base_url="https://medscan.example.test"))
        self.fake_analysis = self.resources.enter_context(patch.object(
            self.routes, "analyze_xray_image", new=AsyncMock(return_value="Синтетический результат: требуется проверка специалистом.")))
        self.fake_template = self.resources.enter_context(patch.object(
            self.routes, "analyze_template_form", new=AsyncMock(return_value="Синтетический шаблон.")))
        self.fake_chat = self.resources.enter_context(patch(
            "server._core.llm.invoke_llm", new=AsyncMock(return_value={
                "choices": [{"message": {"content": "Синтетический ответ помощника."}}],
            })))

    def reset_engine(self):
        if self.store._engine is not None:
            self.store._engine.dispose()
            self.store._engine = None

    def login(self):
        response = self.client.post("/api/auth/login", json={"email": " OWNER@EXAMPLE.TEST ", "password": FIXTURE_PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        return response

    def create(self, title="Синтетическое исследование"):
        response = self.client.post("/api/studies", json={"title": title, "studyType": "lab_blood"})
        self.assertEqual(response.status_code, 200)
        return response.json()["id"]

    def test_auth_me_login_logout_and_unauthorized_routes(self):
        self.assertIsNone(self.client.get("/api/auth/me").json())
        _, upload = synthetic_upload()
        requests = [
            ("GET", "/api/studies", None), ("GET", "/api/studies/1", None),
            ("POST", "/api/studies", {"title": "Synthetic", "studyType": "lab_blood"}),
            ("POST", "/api/studies/1/images", upload), ("GET", "/api/studies/1/images/1", None),
            ("POST", "/api/studies/1/analyze", {}), ("PATCH", "/api/studies/1", {"title": "Synthetic"}),
            ("GET", "/api/studies/1/pdf", None), ("GET", "/api/studies/1/messages", None),
            ("POST", "/api/studies/1/messages", {"message": "Synthetic question"}),
            ("DELETE", "/api/studies/1", None),
        ]
        for method, path, body in requests:
            with self.subTest(method=method, path=path):
                self.assertEqual(self.client.request(method, path, json=body).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json={"email": FIXTURE_EMAIL, "password": "wrong"}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json={"email": FIXTURE_EMAIL, "password": FIXTURE_PASSWORD.rstrip()}).status_code, 401)
        response = self.login()
        cookie = response.headers["set-cookie"].lower()
        for option in ("httponly", "secure", "samesite=lax", "path=/"):
            self.assertIn(option, cookie)
        self.assertNotIn("domain=", cookie)
        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], FIXTURE_EMAIL)
        self.assertNotIn("passwordHash", me.json())
        self.assertNotIn(FIXTURE_PASSWORD, me.text)
        self.assertEqual(self.client.get("/api/studies").json(), [])
        logout = self.client.post("/api/auth/logout")
        self.assertEqual(logout.status_code, 200)
        self.assertIn("max-age=0", logout.headers["set-cookie"].lower())
        self.assertEqual(self.client.get("/api/studies").status_code, 401)
        self.assertIsNone(self.client.get("/api/auth/me").json())

    def test_full_study_image_analysis_edit_pdf_chat_restart_delete(self):
        self.login()
        study_id = self.create()
        path = f"/api/studies/{study_id}"
        self.assertEqual(self.client.get(path + "/pdf").status_code, 400)
        self.assertEqual(self.client.post(path + "/analyze", json={}).status_code, 400)
        original, upload = synthetic_upload()
        uploaded = self.client.post(path + "/images", json=upload)
        self.assertEqual(uploaded.status_code, 200)
        image_url = uploaded.json()["url"]
        self.assertEqual(self.client.get(image_url).content, original)
        details = self.client.get(path).json()
        self.assertEqual(details["images"][0]["url"], image_url)
        self.assertNotIn("base64", json.dumps(details))
        analysis = self.client.post(path + "/analyze", json={"userQuery": "Синтетический вопрос"})
        self.assertEqual(analysis.status_code, 200)
        self.fake_analysis.assert_awaited_once_with(upload["imageData"], "lab_blood", user_query="Синтетический вопрос")
        self.assertEqual(self.client.get(path).json()["status"], "completed")
        edited = "Синтетический отредактированный протокол.\nПроверка специалистом обязательна."
        changed = self.client.patch(path, json={"title": "Синтетический итог", "analysisResult": edited})
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(self.client.get(path).json()["analysisResult"], edited)
        pdf = self.client.get(path + "/pdf")
        self.assertEqual(pdf.status_code, 200)
        pdf_bytes = base64.b64decode(pdf.json()["pdf"], validate=True)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 1_000)
        self.assertEqual(pdf.json()["filename"], "Синтетический итог.pdf")
        chat = self.client.post(path + "/messages", json={"message": "Синтетический вопрос в чате"})
        self.assertEqual(chat.status_code, 200)
        self.assertEqual(chat.json()["message"], "Синтетический ответ помощника.")
        self.fake_chat.assert_awaited_once()
        sent_messages = self.fake_chat.await_args.kwargs["messages"]
        self.assertIn(edited, sent_messages[0]["content"])
        self.assertEqual(sent_messages[-1], {"role": "user", "content": "Синтетический вопрос в чате"})
        history = self.client.get(path + "/messages").json()
        self.assertEqual([message["role"] for message in history], ["user", "assistant"])
        self.reset_engine()
        self.assertEqual(self.client.get(path).json()["analysisResult"], edited)
        self.assertEqual(self.client.get(image_url).content, original)
        self.assertEqual(self.client.get(path + "/messages").json(), history)
        self.assertEqual(self.client.delete(path).status_code, 200)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get(image_url).status_code, 404)
        self.assertEqual(self.client.get("/api/studies").json(), [])
        self.assertEqual(asyncio.run(self.store.get_study_images(study_id)), [])
        self.assertEqual(asyncio.run(self.store.get_chat_messages(study_id)), [])

    def test_other_owner_records_cannot_be_read_or_modified(self):
        self.login()
        other_id = asyncio.run(self.store.create_study({"userId": 2, "title": "Other synthetic owner", "studyType": "lab_blood"}))
        path = f"/api/studies/{other_id}"
        _, upload = synthetic_upload()
        for method, suffix, body in [
            ("GET", "", None), ("GET", "/images/1", None), ("POST", "/images", upload),
            ("POST", "/analyze", {}), ("PATCH", "", {"title": "Blocked synthetic change"}),
            ("GET", "/pdf", None), ("GET", "/messages", None),
            ("POST", "/messages", {"message": "Blocked synthetic question"}), ("DELETE", "", None),
        ]:
            with self.subTest(method=method, suffix=suffix):
                self.assertEqual(self.client.request(method, path + suffix, json=body).status_code, 403)
        self.assertEqual(self.client.get("/api/studies").json(), [])
        self.assertEqual(asyncio.run(self.store.get_study_by_id(other_id))["title"], "Other synthetic owner")
        self.fake_analysis.assert_not_awaited()
        self.fake_chat.assert_not_awaited()

    def test_ai_failures_are_sanitized_and_leave_recoverable_study(self):
        self.login()
        study_id = self.create()
        path = f"/api/studies/{study_id}"
        self.client.post(path + "/images", json=synthetic_upload()[1])
        self.fake_analysis.side_effect = RuntimeError("synthetic-private-input-must-not-leak")
        response = self.client.post(path + "/analyze", json={})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("synthetic-private-input", response.text)
        self.assertEqual(self.client.get(path).json()["status"], "error")
        self.fake_chat.side_effect = RuntimeError("synthetic-private-input-must-not-leak")
        response = self.client.post(path + "/messages", json={"message": "Synthetic retryable question"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("synthetic-private-input", response.text)
        self.assertEqual(len(self.client.get(path + "/messages").json()), 1)

    def test_template_analysis_and_public_health_have_no_secrets(self):
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {"ok": True, "database": "sqlite", "persistent": True, "aiConfigured": False, "authConfigured": True})
        for sensitive in (FIXTURE_EMAIL, FIXTURE_PASSWORD, self.fixture_hash, FIXTURE_JWT_SECRET, str(self.database_path)):
            self.assertNotIn(sensitive, health.text)
        self.login()
        study_id = self.create()
        upload = synthetic_upload()[1]
        self.client.post(f"/api/studies/{study_id}/images", json=upload)
        template = [{"name": "Synthetic field", "value": "Synthetic value", "included": True}]
        response = self.client.post(f"/api/studies/{study_id}/analyze", json={"template": template})
        self.assertEqual(response.status_code, 200)
        self.fake_template.assert_awaited_once_with(upload["imageData"], template)
        self.fake_analysis.assert_not_awaited()

    def test_serverless_entrypoint_import_is_lazy_and_enforces_signing_key(self):
        entrypoint_path = ROOT / "api" / "index.py"
        with patch.dict(os.environ, {"VERCEL": "1", "NODE_ENV": "production", "DATABASE_URL": "postgresql://synthetic:dummy@example.invalid/medscan"}):
            with patch.object(self.store, "create_engine", side_effect=AssertionError("Serverless import must not connect to storage")) as create_engine:
                spec = importlib.util.spec_from_file_location("synthetic_medscan_entrypoint", entrypoint_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.assertIs(module.app, self.app)
                self.assertEqual(os.getenv("BACKEND_ONLY"), "true")
                self.assertEqual(os.getenv("MEDSCAN_STORAGE"), "postgres")
                create_engine.assert_not_called()
            with patch.dict(os.environ, {"JWT_SECRET": ""}):
                spec = importlib.util.spec_from_file_location("invalid_medscan_entrypoint", entrypoint_path)
                module = importlib.util.module_from_spec(spec)
                with self.assertRaisesRegex(RuntimeError, "JWT_SECRET"):
                    spec.loader.exec_module(module)


class DeploymentConfigurationTests(unittest.TestCase):
    def test_frontend_output_api_rewrite_and_private_exclusions(self):
        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(config["outputDirectory"], "dist/public")
        self.assertEqual(config["buildCommand"], "npm run build")
        self.assertEqual(config["rewrites"][0], {"source": "/api/:path*", "destination": "/api/index.py"})
        exclusions = set((ROOT / ".vercelignore").read_text(encoding="utf-8-sig").splitlines())
        self.assertTrue({".private", ".git", "data", "dataset", "server/.env", ".env*"}.issubset(exclusions))


if __name__ == "__main__":
    unittest.main()

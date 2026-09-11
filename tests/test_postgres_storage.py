"""Storage contract tests: temporary SQLite only, no production config or data."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "server" / "postgres_storage.py"


class StorageContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="medscan-storage-test-")
        self.path = Path(self.temp.name) / "test.sqlite"
        self.environment = patch.dict(os.environ, {
            "DATABASE_URL": "sqlite:///" + self.path.as_posix(),
            "POSTGRES_URL": "", "VERCEL": "", "NODE_ENV": "test",
        })
        self.environment.start()
        spec = importlib.util.spec_from_file_location("isolated_postgres_storage", MODULE_PATH)
        self.store = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.store)

    def tearDown(self):
        if self.store._engine is not None:
            self.store._engine.dispose()
        self.environment.stop()
        self.temp.cleanup()

    def run_async(self, coroutine):
        return asyncio.run(coroutine)

    def create(self, user_id=1, title="Synthetic study"):
        return self.run_async(self.store.create_study({
            "userId": user_id, "title": title, "studyType": "lab_blood",
        }))

    def test_lazy_schema_does_not_create_or_read_data_at_import(self):
        self.assertFalse(self.path.exists())
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("CREATE TABLE unrelated_table (value TEXT)")
            connection.execute("INSERT INTO unrelated_table VALUES ('untouched')")
        self.assertEqual(self.run_async(self.store.health_check()), {"database": "sqlite", "persistent": True})
        self.run_async(self.store.health_check())
        with closing(sqlite3.connect(self.path)) as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(connection.execute("SELECT value FROM unrelated_table").fetchone()[0], "untouched")
        self.assertEqual(tables - {"unrelated_table", "sqlite_sequence"}, {
            "medscan_studies", "medscan_images", "medscan_messages",
        })

    def test_study_crud_json_compatibility_and_user_filter(self):
        study_id = self.create(title="Синтетическое исследование")
        other_id = self.create(user_id=2)
        record = self.run_async(self.store.get_study_by_id(study_id))
        self.assertEqual(set(record), {"id", "userId", "title", "studyType", "status", "analysisResult", "createdAt", "updatedAt"})
        self.assertEqual(record["status"], "draft")
        self.assertIsNone(record["analysisResult"])
        self.assertIsNotNone(datetime.fromisoformat(record["createdAt"]).tzinfo)
        json.dumps(record)
        self.run_async(self.store.update_study(study_id, {"title": "Updated", "status": "completed", "analysisResult": "Synthetic result"}))
        updated = self.run_async(self.store.get_study_by_id(study_id))
        self.assertEqual(updated["createdAt"], record["createdAt"])
        self.assertGreaterEqual(updated["updatedAt"], record["updatedAt"])
        self.assertEqual(updated["analysisResult"], "Synthetic result")
        self.assertEqual([r["id"] for r in self.run_async(self.store.get_studies_by_user_id(1))], [study_id])
        self.assertIsNotNone(self.run_async(self.store.get_study_by_id(other_id)))
        with self.assertRaises(ValueError):
            self.run_async(self.store.update_study(999, {"title": "missing"}))
        with self.assertRaises(ValueError):
            self.run_async(self.store.update_study(study_id, {"userId": 2}))

    def test_images_messages_and_delete_cascade(self):
        study_id = self.create()
        image = {"studyId": study_id, "fileKey": "synthetic/image", "url": "data:image/png;base64,dGVzdA==", "filename": "synthetic.png", "mimeType": "image/png", "fileSize": 4}
        image_id = self.run_async(self.store.create_study_image(image))
        loaded = self.run_async(self.store.get_study_images(study_id))
        self.assertEqual(loaded[0]["id"], image_id)
        for key, value in image.items():
            self.assertEqual(loaded[0][key], value)
        first = self.run_async(self.store.create_chat_message({"studyId": study_id, "role": "user", "content": "Synthetic question"}))
        second = self.run_async(self.store.create_chat_message({"studyId": study_id, "role": "assistant", "content": "Synthetic response"}))
        self.assertEqual([m["id"] for m in self.run_async(self.store.get_chat_messages(study_id))], [first, second])
        self.run_async(self.store.delete_study(study_id))
        self.assertIsNone(self.run_async(self.store.get_study_by_id(study_id)))
        self.assertEqual(self.run_async(self.store.get_study_images(study_id)), [])
        self.assertEqual(self.run_async(self.store.get_chat_messages(study_id)), [])
        self.run_async(self.store.delete_study(study_id))
        self.assertGreater(self.create(), study_id)

    def test_foreign_key_failure_does_not_persist_or_echo_input(self):
        sensitive = "synthetic-sensitive-content"
        with self.assertRaises(RuntimeError) as error:
            self.run_async(self.store.create_chat_message({"studyId": 999, "role": "user", "content": sensitive}))
        self.assertNotIn(sensitive, str(error.exception))
        self.assertEqual(self.run_async(self.store.get_chat_messages(999)), [])

    def test_concurrent_first_writes_have_distinct_ids(self):
        with ThreadPoolExecutor(max_workers=6) as executor:
            ids = list(executor.map(lambda n: self.create(title=f"Synthetic {n}"), range(12)))
        self.assertEqual(len(set(ids)), 12)
        self.assertEqual(len(self.run_async(self.store.get_studies_by_user_id(1))), 12)

    def test_persistence_after_engine_restart(self):
        study_id = self.create()
        self.store._engine.dispose()
        self.store._engine = None
        self.assertEqual(self.run_async(self.store.get_study_by_id(study_id))["id"], study_id)

    def test_postgres_url_aliases_without_connecting(self):
        for scheme in ("postgres", "postgresql", "postgresql+psycopg"):
            with patch.dict(os.environ, {"DATABASE_URL": f"{scheme}://synthetic:dummy@example.invalid/test?sslmode=require"}):
                url = self.store._database_url()
                self.assertEqual(url.drivername, "postgresql+psycopg")
                self.assertEqual(url.query["sslmode"], "require")
        with patch.dict(os.environ, {"DATABASE_URL": "", "POSTGRES_URL": "postgres://example.invalid/test"}):
            self.assertEqual(self.store._database_url().drivername, "postgresql+psycopg")

    def test_missing_config_and_production_sqlite_fail_closed(self):
        with patch.dict(os.environ, {"DATABASE_URL": "", "POSTGRES_URL": ""}):
            with self.assertRaises(RuntimeError):
                self.run_async(self.store.health_check())
        self.create()
        for setting in ({"VERCEL": "1"}, {"NODE_ENV": "production"}):
            with patch.dict(os.environ, setting):
                with self.assertRaisesRegex(RuntimeError, "PostgreSQL is required"):
                    self.run_async(self.store.health_check())


if __name__ == "__main__":
    unittest.main()

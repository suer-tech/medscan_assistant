"""Offline authentication tests. All credentials below are synthetic fixtures."""
import contextlib
import io
import os
import unittest
import warnings
from unittest.mock import patch

from fastapi import Request
from passlib.hash import pbkdf2_sha256

from server._core.cookies import get_session_cookie_options
from server._core.env import ENV
from server._core import simple_auth


class OwnerAuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_hash = pbkdf2_sha256.using(rounds=1_000).hash("synthetic password with spaces ")

    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "MEDSCAN_ADMIN_EMAIL": "owner@example.test",
            "MEDSCAN_ADMIN_PASSWORD_HASH": self.fixture_hash,
        }, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        simple_auth._last_signed_in.clear()

    def test_correct_hash_and_normalized_email(self):
        self.assertTrue(simple_auth.verify_simple_password(
            " OWNER@EXAMPLE.TEST ", "synthetic password with spaces "))
        self.assertFalse(simple_auth.verify_simple_password(
            "owner@example.test", "synthetic password with spaces"))
        self.assertFalse(simple_auth.verify_simple_password("other@example.test", "wrong"))

    def test_missing_credentials_disable_users_and_login(self):
        for key in ("MEDSCAN_ADMIN_EMAIL", "MEDSCAN_ADMIN_PASSWORD_HASH"):
            with self.subTest(key=key), patch.dict(os.environ, {key: ""}):
                self.assertFalse(simple_auth.verify_simple_password("owner@example.test", "wrong"))
                self.assertIsNone(simple_auth.get_simple_user("owner@example.test"))
                self.assertIsNone(simple_auth.get_user_by_open_id("local_example_at_mail.ru"))

    def test_invalid_hash_fails_closed(self):
        for invalid_hash in ("plaintext", "$pbkdf2-sha256$broken", "$2b$broken"):
            with self.subTest(hash_format=invalid_hash.split("$")[1:2]), patch.dict(
                os.environ, {"MEDSCAN_ADMIN_PASSWORD_HASH": invalid_hash}
            ):
                self.assertFalse(simple_auth.verify_simple_password("owner@example.test", "wrong"))
                self.assertIsNone(simple_auth.get_simple_user("owner@example.test"))

    def test_identity_lookup_does_not_expose_hash(self):
        user = simple_auth.get_simple_user(" OWNER@EXAMPLE.TEST ")
        self.assertEqual(user["id"], 1)
        self.assertEqual(user["email"], "owner@example.test")
        self.assertNotIn("passwordHash", user)
        self.assertLessEqual(len(user["openId"]), 64)
        self.assertEqual(simple_auth.get_user_by_open_id(user["openId"]), user)
        self.assertIsNone(simple_auth.get_user_by_open_id("unknown"))

    def test_password_rotation_invalidates_old_identity(self):
        old_id = simple_auth.get_simple_user("owner@example.test")["openId"]
        rotated_hash = pbkdf2_sha256.using(rounds=1_000).hash("another synthetic password")
        with patch.dict(os.environ, {"MEDSCAN_ADMIN_PASSWORD_HASH": rotated_hash}):
            self.assertIsNone(simple_auth.get_user_by_open_id(old_id))

    def test_last_signed_in_and_no_credential_output(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            simple_auth.verify_simple_password("owner@example.test", "wrong")
            simple_auth.verify_simple_password("owner@example.test", "synthetic password with spaces ")
            simple_auth.update_last_signed_in(" OWNER@EXAMPLE.TEST ")
        self.assertIsNotNone(simple_auth.get_simple_user("owner@example.test")["lastSignedIn"])
        self.assertEqual(output.getvalue(), "")


class SessionSecretTests(unittest.TestCase):
    def test_development_secret_is_process_instance_local(self):
        with patch.dict(os.environ, {}, clear=True):
            first, second = ENV(), ENV()
            self.assertGreaterEqual(len(first.cookie_secret), 32)
            self.assertEqual(first.cookie_secret, first.cookie_secret)
            self.assertNotEqual(first.cookie_secret, second.cookie_secret)

    def test_production_and_vercel_require_secret(self):
        for marker in ({"NODE_ENV": "production"}, {"VERCEL": "1"}, {"VERCEL_ENV": "preview"}):
            for secret in ("", "short", " " * 32):
                with self.subTest(marker=marker, length=len(secret)), patch.dict(
                    os.environ, {**marker, "JWT_SECRET": secret}, clear=True
                ):
                    with self.assertRaisesRegex(RuntimeError, "JWT_SECRET"):
                        _ = ENV().cookie_secret

    def test_configured_secret_is_used_without_changing_it(self):
        with patch.dict(os.environ, {"NODE_ENV": "production", "JWT_SECRET": "test-only-not-a-real-secret-123456789"}, clear=True):
            self.assertEqual(ENV().cookie_secret, "test-only-not-a-real-secret-123456789")


class SessionIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        fixture_hash = pbkdf2_sha256.using(rounds=1_000).hash("synthetic-session-password")
        self.environment = patch.dict(os.environ, {
            "NODE_ENV": "production",
            "JWT_SECRET": "synthetic-session-test-only-secret-123456789",
            "MEDSCAN_ADMIN_EMAIL": "owner@example.test",
            "MEDSCAN_ADMIN_PASSWORD_HASH": fixture_hash,
        }, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        from server._core.sdk import sdk
        self.sdk = sdk
        self.network_guard = patch("httpx.AsyncClient.request", side_effect=AssertionError("Network is forbidden in auth tests"))
        self.network_guard.start()
        self.addCleanup(self.network_guard.stop)

    async def test_signed_owner_session_resolves_in_request_without_logs(self):
        from server._core.const import COOKIE_NAME
        from server._core.dependencies import get_current_user

        output = io.StringIO()
        with warnings.catch_warnings(), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            warnings.simplefilter("ignore", DeprecationWarning)
            token = await simple_auth.create_session_for_user(" OWNER@EXAMPLE.TEST ")
            session = await self.sdk.verify_session(token)
            request = Request({"type": "http", "scheme": "https", "method": "GET", "path": "/api/auth/me", "headers": [(b"cookie", f"{COOKIE_NAME}={token}".encode())]})
            user = await get_current_user(request)
        self.assertEqual(session.openId, user["openId"])
        self.assertEqual(user["email"], "owner@example.test")
        self.assertEqual(output.getvalue(), "")

    async def test_tampered_and_expired_sessions_rejected(self):
        token = await simple_auth.create_session_for_user("owner@example.test")
        header, payload, signature = token.split(".")
        forged = f"{header}.{payload}.{'A' if signature[0] != 'A' else 'B'}{signature[1:]}"
        self.assertIsNone(await self.sdk.verify_session(forged))
        expired = await self.sdk.create_session_token("synthetic-owner", {"expiresInMs": -1_000})
        self.assertIsNone(await self.sdk.verify_session(expired))

    async def test_unconfigured_identity_cannot_create_session(self):
        with patch.dict(os.environ, {"MEDSCAN_ADMIN_PASSWORD_HASH": ""}):
            with self.assertRaisesRegex(ValueError, "User not found"):
                await simple_auth.create_session_for_user("owner@example.test")

    async def test_sdk_refuses_missing_production_signing_key(self):
        with patch.dict(os.environ, {"JWT_SECRET": ""}):
            with self.assertRaisesRegex(RuntimeError, "JWT_SECRET"):
                await self.sdk.create_session_token("synthetic-owner")


class CookieSecurityTests(unittest.TestCase):
    def request(self, scheme, headers=()):
        return Request({"type": "http", "scheme": scheme, "method": "GET", "path": "/api/auth/me", "headers": headers, "server": ("example.test", 443)})

    def test_https_is_secure_same_site_host_only(self):
        options = get_session_cookie_options(self.request("https"))
        self.assertEqual(options, {"httponly": True, "path": "/", "samesite": "lax", "secure": True})

    def test_proxy_https_and_local_http(self):
        self.assertTrue(get_session_cookie_options(self.request(
            "http", [(b"x-forwarded-proto", b"https")]))["secure"])
        self.assertFalse(get_session_cookie_options(self.request("http"))["secure"])

    def test_no_customer_domain_override(self):
        self.assertFalse(get_session_cookie_options(self.request(
            "http", [(b"host", b"medscan.krmu.edu.kz")]))["secure"])


if __name__ == "__main__":
    unittest.main()

"""Exercise logging with synthetic values; never import the live app/env/storage."""
import ast
import asyncio
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SENSITIVE = "synthetic-sensitive-value-do-not-log"


def load_definition(relative_path, name, namespace=None):
    """Load only a function/class, excluding imports with runtime side effects."""
    path = ROOT / relative_path
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    definition = next(node for node in tree.body if getattr(node, "name", None) == name)
    definition.decorator_list = []
    module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), definition],
        type_ignores=[],
    )
    values = dict(namespace or {})
    exec(compile(ast.fix_missing_locations(module), str(path), "exec"), values)
    return values[name]


class LoggingPrivacyTests(unittest.TestCase):
    def test_middleware_does_not_read_or_log_request_body(self):
        middleware_class = load_definition(
            "server/_core/main.py", "LoggingMiddleware", {"BaseHTTPMiddleware": object}
        )

        class Request:
            method = "POST"
            url = SimpleNamespace(path="/api/auth/login")
            body_reads = 0

            async def body(self):
                self.body_reads += 1
                return json.dumps({"password": SENSITIVE}).encode()

        request = Request()

        async def handler(received):
            self.assertIs(received, request)
            self.assertEqual(received.body_reads, 0)
            self.assertIn(SENSITIVE.encode(), await received.body())
            return SimpleNamespace(status_code=200)

        captured = io.StringIO()
        with redirect_stdout(captured):
            result = asyncio.run(middleware_class().dispatch(request, handler))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(request.body_reads, 1)
        self.assertNotIn(SENSITIVE, captured.getvalue())

    def run_llm(self, response=None, transport_error=False):
        invoke = load_definition("server/_core/llm.py", "invoke_llm", {
            "env": SimpleNamespace(llm_model="test-model", forge_api_key=SENSITIVE),
            "_assert_api_key": lambda: None,
            "_resolve_api_url": lambda: "https://invalid.example/" + SENSITIVE,
            "_normalize_message": lambda message: message,
        })

        class HTTPError(Exception):
            pass

        class Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def post(self, url, **kwargs):
                if transport_error:
                    raise HTTPError(SENSITIVE)
                return response

        captured = io.StringIO()
        error = None
        result = None
        with patch.dict("sys.modules", {"httpx": SimpleNamespace(AsyncClient=Client, HTTPError=HTTPError)}):
            with redirect_stdout(captured):
                try:
                    result = asyncio.run(invoke([{"role": "user", "content": SENSITIVE}]))
                except ValueError as exc:
                    error = exc
        self.assertNotIn(SENSITIVE, captured.getvalue())
        if error:
            self.assertNotIn(SENSITIVE, str(error))
        return result, error

    def test_llm_success_returns_content_without_logging_it(self):
        payload = {"choices": [{"message": {"content": SENSITIVE}}]}
        result, error = self.run_llm(SimpleNamespace(is_success=True, json=lambda: payload))
        self.assertIsNone(error)
        self.assertEqual(result, payload)

    def test_llm_provider_error_does_not_echo_provider_body(self):
        class Response:
            is_success = False
            status_code = 401
            reason_phrase = SENSITIVE

            async def aread(self):
                return SENSITIVE.encode()

        _, error = self.run_llm(Response())
        self.assertIsInstance(error, ValueError)
        self.assertIn("401", str(error))

    def test_llm_transport_error_does_not_echo_sensitive_url(self):
        _, error = self.run_llm(transport_error=True)
        self.assertIsInstance(error, ValueError)

    def test_template_parse_failure_does_not_log_medical_response(self):
        async def invoke(*args, **kwargs):
            return {"choices": [{"message": {"content": SENSITIVE}}]}

        analyze = load_definition("server/openai.py", "analyze_template_form", {
            "json": json, "re": re, "invoke_llm": invoke,
        })
        captured = io.StringIO()
        with redirect_stdout(captured):
            with self.assertRaises(ValueError) as raised:
                asyncio.run(analyze("data:image/png;base64," + SENSITIVE, [
                    {"name": "test_field", "value": "", "included": True}
                ]))
        self.assertNotIn(SENSITIVE, captured.getvalue())
        self.assertNotIn(SENSITIVE, str(raised.exception))

    def test_login_prints_do_not_reference_credentials_or_cookie(self):
        tree = ast.parse((ROOT / "server/routers.py").read_text(encoding="utf-8-sig"))
        login = next(node for node in tree.body if getattr(node, "name", None) == "auth_login")
        forbidden = {"email", "password", "login_data", "session_token", "response_obj", "set_cookie_header"}
        for node in ast.walk(login):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                referenced = {part.id for part in ast.walk(node) if isinstance(part, ast.Name)}
                self.assertFalse(forbidden & referenced, f"Sensitive login log at line {node.lineno}")


if __name__ == "__main__":
    unittest.main()

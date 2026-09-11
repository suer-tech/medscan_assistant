"""RouterAI endpoint/vision contract tests: no real env, credentials or network."""
import ast
import asyncio
from contextlib import redirect_stderr, redirect_stdout
import copy
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "server" / "_core" / "llm.py"
ROUTERAI_ENDPOINT = "https://routerai.ru/api/v1/chat/completions"
ROUTERAI_MODEL = "google/gemini-2.5-flash-lite"
SYNTHETIC_KEY = "synthetic-routerai-key-never-used-on-network"
SYNTHETIC_PROMPT = "synthetic-private-vision-prompt"
SYNTHETIC_ANSWER = "synthetic-private-model-response"
# A synthetic one-pixel PNG fixture, never a patient image.
SYNTHETIC_IMAGE = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6uX8AAAAASUVORK5CYII="
)


def load_llm(api_url="https://routerai.ru/api/v1", api_key=SYNTHETIC_KEY):
    """Execute actual LLM code with its deployment-env import replaced by a fixture."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom) and node.module == "server._core.env"
    )]
    namespace = {"env": SimpleNamespace(
        forge_api_url=api_url, forge_api_key=api_key, llm_model=ROUTERAI_MODEL,
    )}
    exec(compile(tree, str(SOURCE), "exec"), namespace)
    return namespace


class EndpointResolutionTests(unittest.TestCase):
    def test_routerai_versioned_base_and_whitespace(self):
        for base in (
            "https://routerai.ru/api/v1", "https://routerai.ru/api/v1/",
            "  https://routerai.ru/api/v1  ", "\t https://routerai.ru/api/v1/ \n",
        ):
            with self.subTest(base=base):
                actual = load_llm(base)["_resolve_api_url"]()
                self.assertEqual(actual, ROUTERAI_ENDPOINT)
                self.assertNotIn("/v1/v1/", actual)

    def test_legacy_api_base_gains_exactly_one_version(self):
        for base, expected in (
            ("https://routerai.ru/api", ROUTERAI_ENDPOINT),
            (" https://routerai.ru/api/ ", ROUTERAI_ENDPOINT),
            ("https://openrouter.ai/api", "https://openrouter.ai/api/v1/chat/completions"),
            (" https://openrouter.ai/api/ ", "https://openrouter.ai/api/v1/chat/completions"),
        ):
            with self.subTest(base=base):
                self.assertEqual(load_llm(base)["_resolve_api_url"](), expected)

    def test_full_chat_completions_url_is_not_appended_again(self):
        for endpoint in (ROUTERAI_ENDPOINT, "https://openrouter.ai/api/v1/chat/completions"):
            for base in (endpoint, endpoint + "/", "  " + endpoint + "/ \t"):
                with self.subTest(base=base):
                    self.assertEqual(load_llm(base)["_resolve_api_url"](), endpoint)

    def test_blank_base_uses_routerai_default(self):
        for base in ("", "  \n\t", None):
            with self.subTest(base=base):
                self.assertEqual(load_llm(base)["_resolve_api_url"](), ROUTERAI_ENDPOINT)


class RouterAIRequestTests(unittest.TestCase):
    def invoke_mocked(self, messages, *, base="https://routerai.ru/api/v1", key=SYNTHETIC_KEY, status=200, transport_error=False, **kwargs):
        llm = load_llm(base, key)
        calls = []

        class HTTPError(Exception):
            pass

        class MockResponse:
            is_success = 200 <= status < 300
            status_code = status
            text = SYNTHETIC_KEY + SYNTHETIC_PROMPT + SYNTHETIC_IMAGE

            def json(self):
                return {"choices": [{"message": {"content": SYNTHETIC_ANSWER}}]}

        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def post(self, url, **options):
                calls.append({"url": url, **copy.deepcopy(options)})
                if transport_error:
                    raise HTTPError(SYNTHETIC_KEY + SYNTHETIC_PROMPT)
                return MockResponse()

        output = io.StringIO()
        result, error = None, None
        # Replacing the whole HTTP module guarantees no network request escapes.
        with patch.dict("sys.modules", {"httpx": SimpleNamespace(AsyncClient=MockClient, HTTPError=HTTPError)}):
            with redirect_stdout(output), redirect_stderr(output):
                try:
                    result = asyncio.run(llm["invoke_llm"](messages=messages, **kwargs))
                except ValueError as exc:
                    error = exc
        for sensitive in (SYNTHETIC_KEY, SYNTHETIC_PROMPT, SYNTHETIC_ANSWER, SYNTHETIC_IMAGE):
            self.assertNotIn(sensitive, output.getvalue())
            if error is not None:
                self.assertNotIn(sensitive, str(error))
        return calls, result, error

    def test_exact_routerai_auth_model_and_unmodified_vision_payload(self):
        messages = [
            {"role": "system", "content": "Synthetic system instruction"},
            {"role": "user", "content": [
                {"type": "text", "text": SYNTHETIC_PROMPT},
                {"type": "image_url", "image_url": {"url": SYNTHETIC_IMAGE, "detail": "high"}},
            ]},
        ]
        original = copy.deepcopy(messages)
        calls, result, error = self.invoke_mocked(messages, base=" https://routerai.ru/api/v1/ ", max_tokens=512)
        self.assertIsNone(error)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["url"], ROUTERAI_ENDPOINT)
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer " + SYNTHETIC_KEY)
        self.assertEqual(calls[0]["headers"]["Content-Type"], "application/json")
        self.assertEqual(calls[0]["json"], {"model": ROUTERAI_MODEL, "messages": original, "max_tokens": 512})
        self.assertEqual(messages, original)
        self.assertEqual(result["choices"][0]["message"]["content"], SYNTHETIC_ANSWER)

    def test_text_chat_uses_same_endpoint_and_normalizes_text_part(self):
        messages = [{"role": "user", "content": [{"type": "text", "text": SYNTHETIC_PROMPT}]}]
        calls, _, error = self.invoke_mocked(messages)
        self.assertIsNone(error)
        self.assertEqual(calls[0]["url"], ROUTERAI_ENDPOINT)
        self.assertEqual(calls[0]["json"]["model"], ROUTERAI_MODEL)
        self.assertEqual(calls[0]["json"]["messages"], [{"role": "user", "content": SYNTHETIC_PROMPT}])

    def test_missing_key_prevents_any_http_call(self):
        calls, result, error = self.invoke_mocked([{"role": "user", "content": SYNTHETIC_PROMPT}], key="")
        self.assertEqual(calls, [])
        self.assertIsNone(result)
        self.assertIsInstance(error, ValueError)

    def test_provider_and_transport_errors_do_not_leak_credentials_or_prompt(self):
        for options in ({"status": 401}, {"transport_error": True}):
            with self.subTest(options=options):
                calls, result, error = self.invoke_mocked([{"role": "user", "content": SYNTHETIC_PROMPT}], **options)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0]["url"], ROUTERAI_ENDPOINT)
                self.assertIsNone(result)
                self.assertIsInstance(error, ValueError)


if __name__ == "__main__":
    unittest.main()

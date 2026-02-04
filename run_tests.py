import os
import json
from types import SimpleNamespace

from analyze_ticket import triage_ticket

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


SAMPLES = {
    "Billing": "Payment failed when attempting to checkout. I was charged twice and need a refund. The invoice number is INV-12345.",
    "Bug": "The web app returns Error 500 when I try to save my profile. The page just crashes every time and I'm seeing 'internal server error' in the console.",
    "General": "How do I update my account email? I don't see an option in settings. Is there documentation?",
}


def run_live_tests(client, model="gpt-4"):
    print("=== Running tests (V1 triage) ===")
    for name, text in SAMPLES.items():
        print(f"\n--- Sample: {name} ---")
        final_payload = triage_ticket(text, client, model=model)
        print("Final payload:")
        print(json.dumps(final_payload, indent=2))


def test_empty_string(client=None):
    print("\n=== Test: empty string ===")
    final_payload = triage_ticket(
        "",
        llm_client=client if client is not None else _FakeValidClient(),
        model="gpt-4",
    )
    print("Expected: stable payload returned, needs_human_review=True, confidence=0.0, error='empty_ticket_text'")
    print(json.dumps(final_payload, indent=2))


def test_invalid_json_return():
    print("\n=== Test: simulated LLM returns invalid JSON ===")

    class FakeResp:
        def __init__(self, content):
            self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]

    class FakeCompletions:
        def __init__(self, content):
            self.content = content

        def create(self, *args, **kwargs):
            return FakeResp(self.content)

    class FakeChat:
        def __init__(self, content):
            self.completions = FakeCompletions(content)

    class FakeClient:
        def __init__(self, content):
            self.chat = FakeChat(content)

    fake_client = FakeClient("This is not JSON at all. Just plain text.")
    final_payload = triage_ticket(SAMPLES["Bug"], fake_client, model="gpt-4")
    print("Expected: stable payload returned, needs_human_review=True, confidence=0.0, error starts with 'invalid_json:'")
    print(json.dumps(final_payload, indent=2))


class _FakeValidClient:
    """
    Returns a minimal valid JSON response that will pass validations.
    This is only to prove the pipeline doesn't crash without an API key.
    """
    def __init__(self):
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda *args, **kwargs: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({
                        "summary": [
                            "Simulated summary bullet 1.",
                            "Simulated summary bullet 2.",
                            "Simulated summary bullet 3."
                        ],
                        "priority": "Medium",
                        "category": "General"
                    })))],
                )
            )
        )


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        print("Note: OPENAI_API_KEY not set or OpenAI SDK not available. Live LLM tests will be skipped.")
        print("Running with a simulated valid client (no network).")
        client = _FakeValidClient()
    else:
        client = OpenAI()
        print("OpenAI client created; running live tests with model 'gpt-4'.")

    run_live_tests(client, model="gpt-4")
    test_empty_string(client)
    test_invalid_json_return()

    print("\nAll tests completed. Pipeline did not crash.")


if __name__ == "__main__":
    main()

import argparse

from .client import LLMClient
from .config import load_config
from .errors import LLMError
from .models import ChatMessage


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify an OpenAI-compatible LLM connection")
    parser.add_argument("prompt", nargs="?", default="Reply with a short greeting.")
    args = parser.parse_args(argv)
    try:
        result = LLMClient(load_config()).chat([ChatMessage("user", args.prompt)])
    except (LLMError, RuntimeError) as exc:
        print("LLM verification failed: " + str(exc))
        return 1
    print(result.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

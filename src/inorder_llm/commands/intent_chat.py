from ..infrastructure.llm import LLMClient, load_config
from ..graph.intent import build_intent_graph
from ..intent.resolver import LLMIntentModel
from ..cli.app import IntentCli


def main(argv=None):
    IntentCli(graph=build_intent_graph(LLMIntentModel(LLMClient(load_config())))).run()
    return 0

__all__ = ["main"]

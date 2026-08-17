from ..infrastructure.llm import LLMClient, load_config
from ..graph.intent import build_intent_graph
from ..graph.order import build_order_processing_graph
from ..intent.resolver import LLMIntentModel
from ..rewrite import OrderRewriteModel
from ..extract import EntityExtractor
from ..cli.app import IntentCli


def main(argv=None):
    client = LLMClient(load_config(), on_content=lambda content: print("\n[LLM content]\n" + content + "\n[/LLM content]"))
    intent_graph = build_intent_graph(LLMIntentModel(client))
    order_graph = build_order_processing_graph(OrderRewriteModel(client), EntityExtractor(client))
    IntentCli(intent_graph=intent_graph, order_graph=order_graph).run()
    return 0

__all__ = ["main"]

from ..infrastructure.llm import LLMClient, load_config
from ..graph.intent import build_intent_graph
from ..graph.order import build_order_processing_graph
from ..intent.resolver import LLMIntentModel
from ..rewrite import OrderRewriteModel
from ..extract import EntityExtractor, LangExtractEntityExtractor
from ..cargo_profile import CargoProfileResolver
from ..cli.app import IntentCli


def main(argv=None):
    config = load_config()
    client = LLMClient(config, on_content=lambda content: print("\n[LLM content]\n" + content + "\n[/LLM content]"))
    intent_graph = build_intent_graph(LLMIntentModel(client))
    extractor = (
        LangExtractEntityExtractor(config)
        if config.extractor_backend == "langextract"
        else EntityExtractor(client)
    )
    order_graph = build_order_processing_graph(OrderRewriteModel(client), extractor, CargoProfileResolver(client))
    IntentCli(intent_graph=intent_graph, order_graph=order_graph).run()
    return 0

__all__ = ["main"]

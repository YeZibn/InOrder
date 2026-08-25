"""Run the local InOrder SSE API."""

import uvicorn

from ..cargo_profile import CargoProfileResolver
from ..extract import EntityExtractor, LangExtractEntityExtractor
from ..graph.main import build_main_graph_from_models
from ..infrastructure.llm import LLMClient, load_config
from ..intent.resolver import LLMIntentModel
from ..rewrite import OrderRewriteModel
from ..vehicle_resolution import VehicleResolutionResolver
from ..workflow.api import create_app


def build_app():
    config = load_config()
    client = LLMClient(config)
    extractor = LangExtractEntityExtractor(config) if config.extractor_backend == "langextract" else EntityExtractor(client)
    graph = build_main_graph_from_models(LLMIntentModel(client), OrderRewriteModel(client), extractor, CargoProfileResolver(client), VehicleResolutionResolver(client))
    return create_app(main_graph=graph)


app = build_app()


def main():
    uvicorn.run("inorder_llm.commands.api_server:app", host="0.0.0.0", port=8000, reload=False)


__all__ = ["app", "main"]

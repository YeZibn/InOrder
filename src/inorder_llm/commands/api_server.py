"""Run the local InOrder SSE API."""

import uvicorn

from ..cargo_profile import CargoProfileResolver
from ..extract import EntityExtractor, LangExtractEntityExtractor
from ..graph.main import build_main_graph_from_models
from ..infrastructure.llm import LLMClient, load_config
from ..intent.resolver import LLMIntentModel
from ..rewrite import OrderRewriteModel
from ..vehicle_resolution import VehicleResolutionResolver
from ..catalog import CachedVehicleCatalogProvider, LocalVehicleCatalogProvider, RpcVehicleCatalogProvider
import os
from ..workflow.api import create_app
from ..workflow.runtime import WorkflowRuntimeConfig
from ..workflow.capacity import WorkerCapacity


def build_app():
    config = load_config()
    runtime_config = WorkflowRuntimeConfig.from_environ()
    capacity = WorkerCapacity(runtime_config)
    client = LLMClient(config, llm_gate=capacity.llm)
    extractor = LangExtractEntityExtractor(config) if config.extractor_backend == "langextract" else EntityExtractor(client)
    local_catalog = LocalVehicleCatalogProvider()
    endpoint = os.getenv("VEHICLE_CATALOG_RPC_URL")
    remote = RpcVehicleCatalogProvider(endpoint, float(os.getenv("VEHICLE_CATALOG_RPC_TIMEOUT", "0.8"))) if endpoint else local_catalog
    catalog = CachedVehicleCatalogProvider(remote, local_catalog, float(os.getenv("VEHICLE_CATALOG_CACHE_TTL", "300")))
    graph = build_main_graph_from_models(LLMIntentModel(client), OrderRewriteModel(client), extractor, CargoProfileResolver(client), VehicleResolutionResolver(client, catalog_provider=catalog), capacity=capacity)
    return create_app(main_graph=graph, runtime_config=runtime_config, capacity=capacity, shutdown_callback=client.aclose)


app = build_app()


def main():
    uvicorn.run("inorder_llm.commands.api_server:app", host="0.0.0.0", port=8000, reload=False)


__all__ = ["app", "main"]

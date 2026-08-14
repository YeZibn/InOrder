from inorder_llm.infrastructure.llm.client import LLMClient as NewLLMClient
from inorder_llm.intent.models import IntentPlan
from inorder_llm.intent.models import IntentPlan
from inorder_llm.cli.app import IntentCli as NewIntentCli


def test_new_modules_are_source_of_truth():
    assert NewLLMClient.__module__ == "inorder_llm.infrastructure.llm.client"
    assert IntentPlan.__module__ == "inorder_llm.intent.models"
    assert NewIntentCli.__module__ == "inorder_llm.cli.app"

"""LangExtract OpenAI provider implemented with the Responses API."""

from typing import Any


class ResponsesLanguageModel:
    """Small LangExtract BaseLanguageModel adapter for Responses API."""

    def __new__(cls, *args, **kwargs):
        try:
            from langextract.providers.openai import OpenAILanguageModel
        except ImportError as exc:
            raise RuntimeError("langextract is required") from exc

        class _Provider(OpenAILanguageModel):
            def _build_responses_params(self, prompt: str, config: dict) -> dict:
                params: dict[str, Any] = {
                    "model": self.model_id,
                    "input": [{"role": "user", "content": prompt}],
                }
                if self.format_type.name == "JSON":
                    params["input"].insert(0, {
                        "role": "system",
                        "content": "You are a helpful assistant that responds in JSON format.",
                    })
                if config.get("reasoning_effort") is not None:
                    params["reasoning"] = {"effort": config["reasoning_effort"]}
                response_format = config.get("response_format")
                if response_format and response_format.get("type") == "json_schema":
                    schema = response_format.get("json_schema", {})
                    params["text"] = {"format": {
                        "type": "json_schema",
                        "name": schema.get("name", "langextract_extractions"),
                        "schema": schema.get("schema", {}),
                        "strict": schema.get("strict", True),
                    }}
                elif self.format_type.name == "JSON":
                    params["text"] = {"format": {"type": "json_object"}}
                return params

            def _process_single_prompt(self, prompt: str, config: dict):
                from langextract.core import exceptions, types
                try:
                    response = self._client.responses.create(
                        **self._build_responses_params(prompt, config)
                    )
                    return types.ScoredOutput(score=1.0, output=getattr(response, "output_text", "") or "")
                except exceptions.InferenceConfigError:
                    raise
                except Exception as exc:
                    raise exceptions.InferenceRuntimeError(
                        f"OpenAI Responses API error: {exc}", original=exc
                    ) from exc

        instance = object.__new__(_Provider)
        _Provider.__init__(instance, *args, **kwargs)
        return instance


__all__ = ["ResponsesLanguageModel"]

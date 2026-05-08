"""Registry of mmore commands surfaced by the TUI.

Mirrors `mmore.cli` 1:1. Each entry exposes:
  - label: shown in the menu
  - description: shown in the right pane
  - import_path: dotted path "module:callable" — imported lazily because
    mmore's run_* modules pull in heavy ML deps.
  - dataclass_path: dotted path "module:Class" of the top-level config dataclass,
    or None when the command has no introspectable config (e.g. postprocess).
  - call_kind: how to call the resolved callable. One of:
      "config_only"  -> fn(config_path)
      "config_input" -> fn(config_path, input_data)
      "ragcli"       -> RagCLI(config_path).launch_cli() handled specially
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CommandSpec:
    name: str
    label: str
    description: str
    import_path: str
    dataclass_path: Optional[str]
    call_kind: str = "config_only"


COMMANDS: list[CommandSpec] = [
    CommandSpec(
        name="process",
        label="process",
        description=(
            "Extract and dispatch raw documents (PDF, video, spreadsheets, …) "
            "into a normalized JSONL dataset.\n\n"
            "Config: ProcessInference (data_path, dispatcher_config, …)."
        ),
        import_path="mmore.run_process:process",
        dataclass_path="mmore.run_process:ProcessInference",
    ),
    CommandSpec(
        name="postprocess",
        label="postprocess",
        description=(
            "Apply post-processors (chunkers, cleaners, taggers) to a JSONL "
            "produced by `process`.\n\n"
            "Note: takes both a config file AND an input JSONL path."
        ),
        import_path="mmore.run_postprocess:postprocess",
        dataclass_path=None,
        call_kind="config_input",
    ),
    CommandSpec(
        name="index",
        label="index",
        description=(
            "Index a (post)processed JSONL into the vector store.\n\n"
            "Config: IndexConfig (indexer, collection_name, documents_path)."
        ),
        import_path="mmore.run_index:index",
        dataclass_path="mmore.run_index:IndexConfig",
    ),
    CommandSpec(
        name="rag",
        label="rag",
        description=(
            "Run the RAG inference pipeline in batch (read queries from a "
            "JSONL, write answers) or as an HTTP endpoint.\n\n"
            "Config: RAGInferenceConfig."
        ),
        import_path="mmore.run_rag:rag",
        dataclass_path="mmore.run_rag:RAGInferenceConfig",
    ),
    CommandSpec(
        name="ragcli",
        label="ragcli (chat)",
        description="Interactive RAG chat against an indexed collection.",
        import_path="mmore.run_ragcli:RagCLI",
        dataclass_path=None,
        call_kind="ragcli",
    ),
    CommandSpec(
        name="retrieve",
        label="retrieve",
        description="Run the retriever standalone over a JSONL of queries.",
        import_path="mmore.run_retriever:retrieve",
        dataclass_path=None,
    ),
    CommandSpec(
        name="live_retrieval",
        label="live_retrieval",
        description="Serve the retriever as an HTTP endpoint.",
        import_path="mmore.run_live_retrieval:live_retrieval",
        dataclass_path=None,
    ),
    CommandSpec(
        name="index_api",
        label="index_api",
        description="Serve the indexer as an HTTP endpoint.",
        import_path="mmore.run_index_api:index_api",
        dataclass_path=None,
    ),
    CommandSpec(
        name="websearch",
        label="websearch",
        description="Run the web-search-augmented RAG pipeline.",
        import_path="mmore.run_websearch:websearch",
        dataclass_path=None,
    ),
]


def get_command(name: str) -> CommandSpec:
    for c in COMMANDS:
        if c.name == name:
            return c
    raise KeyError(name)


def resolve(spec: CommandSpec):
    """Lazy-import the callable referenced by spec.import_path."""
    module_name, attr = spec.import_path.split(":")
    import importlib

    module = importlib.import_module(module_name)
    return getattr(module, attr)


def resolve_dataclass(spec: CommandSpec):
    if spec.dataclass_path is None:
        return None
    module_name, attr = spec.dataclass_path.split(":")
    import importlib

    module = importlib.import_module(module_name)
    return getattr(module, attr)

"""The util module contains the functionality required for the script runner."""

import argparse
import functools
import importlib
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast

if sys.version_info >= (3, 10):
    from types import NoneType
else:
    NoneType = type(None)

from hera.shared._pydantic import _PYDANTIC_VERSION
from hera.shared._type_util import (
    get_workflow_annotation,
    origin_type_issubtype,
    unwrap_annotation,
)
from hera.shared.serialization import serialize
from hera.workflows import Artifact
from hera.workflows._runner.script_annotations_util import (
    _map_argo_inputs_to_function,
    _save_annotated_return_outputs,
    _save_dummy_outputs,
)
from hera.workflows.artifact import ArtifactLoader
from hera.workflows.io.v1 import (
    Output as OutputV1,
)
from hera.workflows.script import _extract_return_annotation_output

if _PYDANTIC_VERSION == 2:
    from pydantic.type_adapter import TypeAdapter  # type: ignore
    from pydantic.v1 import parse_obj_as  # type: ignore

    from hera.workflows.io.v2 import (  # type: ignore
        Output as OutputV2,
    )
else:
    from pydantic import parse_obj_as

    from hera.workflows.io.v1 import (  # type: ignore
        Output as OutputV2,
    )


def _ignore_unmatched_kwargs(f: Callable) -> Callable:
    """Make function ignore unmatched kwargs.

    If the function already has the catch all **kwargs, do nothing.
    """
    if _contains_var_kwarg(f):
        return f

    @functools.wraps(f)
    def inner(**kwargs):
        # filter out kwargs that are not part of the function signature
        # and transform them to the correct type
        filtered_kwargs = {key: _parse(value, key, f) for key, value in kwargs.items() if _is_kwarg_of(key, f)}
        return f(**filtered_kwargs)

    return inner


def _contains_var_kwarg(f: Callable) -> bool:
    """Tells whether the given callable contains a keyword argument."""
    return any(param.kind == inspect.Parameter.VAR_KEYWORD for param in inspect.signature(f).parameters.values())


def _is_kwarg_of(key: str, f: Callable) -> bool:
    """Tells whether the given `key` identifies a keyword argument of the given callable."""
    param = inspect.signature(f).parameters.get(key)
    return param is not None and (
        param.kind is inspect.Parameter.KEYWORD_ONLY or param.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    )


def _parse(value: str, key: str, f: Callable) -> Any:
    """Parse a value to the correct type.

    Args:
        value: The value to parse.
        key: The name of the kwarg.
        f: The function to parse the value for.

    Returns:
        The parsed value.

    """
    if _is_str_kwarg_of(key, f) or _is_artifact_loaded(key, f) or _is_output_kwarg(key, f):
        return value
    try:
        type_ = _get_unannotated_type(key, f)
        loaded_json_value = json.loads(value)

        if not type_:
            return loaded_json_value

        _pydantic_mode = int(os.environ.get("hera__pydantic_mode", _PYDANTIC_VERSION))
        if _pydantic_mode == 1:
            return parse_obj_as(type_, loaded_json_value)
        else:
            return TypeAdapter(type_).validate_python(loaded_json_value)
    except (json.JSONDecodeError, TypeError):
        return value


def _get_function_param_annotation(key: str, f: Callable) -> Optional[type]:
    func_param_annotation = inspect.signature(f).parameters[key].annotation
    if func_param_annotation is inspect.Parameter.empty:
        return None
    return func_param_annotation


def _get_unannotated_type(key: str, f: Callable) -> Optional[type]:
    """Get the type of function param without the 'Annotated' outer type."""
    type_ = _get_function_param_annotation(key, f)
    if type_ is None:
        return None
    return unwrap_annotation(type_)


def _is_str_kwarg_of(key: str, f: Callable) -> bool:
    """Check if param `key` of function `f` has a type annotation that can be interpreted as a subclass of str."""
    if func_param_annotation := _get_function_param_annotation(key, f):
        return origin_type_issubtype(func_param_annotation, (str, NoneType))
    return False


def _is_artifact_loaded(key: str, f: Callable) -> bool:
    """Check if param `key` of function `f` is actually an Artifact that has already been loaded."""
    if param_annotation := _get_function_param_annotation(key, f):
        if (artifact := get_workflow_annotation(param_annotation)) and isinstance(artifact, Artifact):
            return artifact.loader == ArtifactLoader.json.value
    return False


def _is_output_kwarg(key: str, f: Callable) -> bool:
    """Check if param `key` of function `f` is an output Artifact/Parameter."""
    if param_annotation := _get_function_param_annotation(key, f):
        if param_or_artifact := get_workflow_annotation(param_annotation):
            return bool(param_or_artifact.output)
    return False


def _runner(entrypoint: str, kwargs_list: List) -> Any:
    """Run the function defined by the entrypoint with the given list of kwargs.

    Args:
        entrypoint: The module path to the script within the container to execute. "package.submodule:function"
        kwargs_list: A list of dicts with "name" and "value" keys, representing the kwargs of the function.

    Returns:
        The result of the function or `None` if the outputs are to be saved.
    """
    # import the module and get the function
    module, function_name = entrypoint.split(":")
    function: Callable = getattr(importlib.import_module(module), function_name)
    # if the function is wrapped, unwrap it
    # this may happen if the function is decorated with @script
    if hasattr(function, "wrapped_function"):
        function = function.wrapped_function
    # convert the kwargs list to a dict
    kwargs: Dict[str, str] = {}
    for kwarg in kwargs_list:
        if "name" not in kwarg or "value" not in kwarg:
            continue
        # sanitize the key for python
        key = cast(str, serialize(kwarg["name"]))
        value = kwarg["value"]
        kwargs[key] = value

    kwargs = _map_argo_inputs_to_function(function, kwargs)

    # The imported validate_arguments uses smart union by default just in case clients do not rely on it. This means that if a function uses a union
    # type for any of its inputs, then this will at least try to map those types correctly if the input object is
    # not a pydantic model with smart_union enabled
    _pydantic_mode = int(os.environ.get("hera__pydantic_mode", _PYDANTIC_VERSION))
    if _pydantic_mode == 2:
        from pydantic import validate_call  # type: ignore

        function = validate_call(function)
    else:
        if _PYDANTIC_VERSION == 1:
            from pydantic import validate_arguments
        else:
            from pydantic.v1 import validate_arguments  # type: ignore
        function = validate_arguments(function, config=dict(smart_union=True, arbitrary_types_allowed=True))  # type: ignore

    function = _ignore_unmatched_kwargs(function)

    output_annotations = _extract_return_annotation_output(function)

    if output_annotations:
        # This will save outputs returned from the function only. Any function parameters/artifacts marked as
        # outputs should be written to within the function itself.
        try:
            output = _save_annotated_return_outputs(function(**kwargs), output_annotations)
        except Exception as e:
            _save_dummy_outputs(output_annotations)
            raise e
        return output or None

    return function(**kwargs)


def _parse_args() -> argparse.Namespace:
    """Creates an argparse for the runner function.

    The returned argparse takes a module and function name as flags and a path to a json file as an argument.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--entrypoint", "-e", type=str, required=True)
    parser.add_argument("args_path", type=Path)
    return parser.parse_args()


def _run() -> None:
    """Runs a function from a specific path using parsed arguments from Argo.

    Note that this prints the result of the function to stdout, which is the normal mode of operation for Argo. Any
    output of a Python function submitted via a `Script.source` field results in outputs sent to stdout.
    """
    args = _parse_args()
    # 1. Protect against trying to json.loads on empty files with inner `or r"[]`
    # 2. Protect against files containing `null` as text with outer `or []` (as a result of using
    #    `{{inputs.parameters}}` where the parameters key doesn't exist in `inputs`)
    kwargs_list = json.loads(args.args_path.read_text() or r"[]") or []
    assert isinstance(kwargs_list, List)
    result = _runner(args.entrypoint, kwargs_list)
    if not result:
        return

    if isinstance(result, (OutputV1, OutputV2)):
        print(serialize(result.result))
        exit(result.exit_code)

    print(serialize(result))

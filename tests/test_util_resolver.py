"""Test suite for prance.util.resolver ."""

__author__ = "Jens Finkhaeuser"
__copyright__ = "Copyright (c) 2016-2021 Jens Finkhaeuser"
__license__ = "MIT"
__all__ = ()


import pytest
from unittest.mock import patch

from prance.util import fs
from prance.util import resolver
from prance.util.url import ResolutionError

from . import none_of


def get_specs(fname):
    specs = fs.read_file(fname)

    from prance.util import formats

    specs = formats.parse_spec(specs, fname)

    return specs


def mock_get_petstore(*args, **kwargs):
    from .mock_response import MockResponse, PETSTORE_YAML

    return MockResponse(text=PETSTORE_YAML)


def recursion_limit_handler_none(limit, refstring, recursions):
    return None


@pytest.fixture
def externals_file():
    return get_specs("tests/specs/with_externals.yaml")


@pytest.fixture
def recursive_objs_file():
    return get_specs("tests/specs/recursive_objs.yaml")


@pytest.fixture
def recursive_files_file():
    return get_specs("tests/specs/recursive_files.yaml")


@pytest.fixture
def recursion_limit_file():
    return get_specs("tests/specs/recursion_limit.yaml")


@pytest.fixture
def recursion_limit_files_file():
    return get_specs("tests/specs/recursion_limit_files.yaml")


@pytest.fixture
def missing_file():
    return get_specs("tests/specs/missing_reference.yaml")


def test_resolver_noname(externals_file):
    res = resolver.RefResolver(externals_file)
    # Can't build a fragment URL without reference
    with pytest.raises(ResolutionError):
        res.resolve_references()


@patch("requests.get")
def test_resolver_named(mock_get, externals_file):
    mock_get.side_effect = mock_get_petstore

    import os.path
    from prance.util import fs

    res = resolver.RefResolver(
        externals_file, fs.abspath("tests/specs/with_externals.yaml")
    )
    res.resolve_references()


@patch("requests.get")
def test_resolver_missing_reference(mock_get, missing_file):
    mock_get.side_effect = mock_get_petstore

    import os.path

    res = resolver.RefResolver(
        missing_file, fs.abspath("tests/specs/missing_reference.yaml")
    )
    with pytest.raises(ResolutionError) as exc:
        res.resolve_references()

    assert str(exc.value).startswith("Cannot resolve")


@patch("requests.get")
def test_resolver_recursive_objects(mock_get, recursive_objs_file):
    mock_get.side_effect = mock_get_petstore

    # Recursive references to objects are a problem
    import os.path

    res = resolver.RefResolver(
        recursive_objs_file, fs.abspath("tests/specs/recursive_objs.yaml")
    )
    with pytest.raises(ResolutionError) as exc:
        res.resolve_references()

    assert str(exc.value).startswith("Recursion reached limit")


@patch("requests.get")
def test_resolver_recursive_files(mock_get, recursive_files_file):
    mock_get.side_effect = mock_get_petstore

    # Recursive references to files are not a problem
    import os.path

    res = resolver.RefResolver(
        recursive_files_file, fs.abspath("tests/specs/recursive_files.yaml")
    )
    res.resolve_references()


def test_recursion_limit_do_not_recurse_raise(recursion_limit_file):
    # Expect the default behaviour to raise.
    import os.path

    res = resolver.RefResolver(
        recursion_limit_file, fs.abspath("tests/specs/recursion_limit.yaml")
    )
    with pytest.raises(ResolutionError) as exc:
        res.resolve_references()

    assert str(exc.value).startswith("Recursion reached limit of 1")


def test_recursion_limit_do_not_recurse_ignore(recursion_limit_file):
    # If we overload the handler, we should not get an error but should
    # also simply not have the 'next' field - or it should be None
    import os.path

    res = resolver.RefResolver(
        recursion_limit_file,
        fs.abspath("tests/specs/recursion_limit.yaml"),
        recursion_limit_handler=recursion_limit_handler_none,
    )
    res.resolve_references()

    from prance.util import formats

    contents = formats.serialize_spec(res.specs, "foo.yaml")

    # The effect of returning None on recursion limit should be that
    # despite having recursion, the outermost reference to
    # definitions/Pet should get resolved.
    assert (
        "properties" in res.specs["paths"]["/pets"]["get"]["responses"]["200"]["schema"]
    )

    # However, the 'next' field should not be resolved.
    assert (
        res.specs["paths"]["/pets"]["get"]["responses"]["200"]["schema"]["properties"][
            "next"
        ]["schema"]
        is None
    )


def test_recursion_limit_set_limit_ignore(recursion_limit_file):
    # If we overload the handler, and set the recursion limit higher,
    # we should get nested Pet objects a few levels deep.

    import os.path

    res = resolver.RefResolver(
        recursion_limit_file,
        fs.abspath("tests/specs/recursion_limit.yaml"),
        recursion_limit=2,
        recursion_limit_handler=recursion_limit_handler_none,
    )
    res.resolve_references()

    from prance.util import formats

    contents = formats.serialize_spec(res.specs, "foo.yaml")

    # The effect of returning None on recursion limit should be that
    # despite having recursion, the outermost reference to
    # definitions/Pet should get resolved.
    assert (
        "properties" in res.specs["paths"]["/pets"]["get"]["responses"]["200"]["schema"]
    )

    # However, the 'next' field should be resolved due to the higher recursion limit
    next_field = res.specs["paths"]["/pets"]["get"]["responses"]["200"]["schema"][
        "properties"
    ]["next"]["schema"]
    assert next_field is not None

    # But the 'next' field of the 'next' field should not be resolved.
    assert next_field["properties"]["next"]["schema"] is None


def test_recursion_limit_do_not_recurse_raise_files(recursion_limit_files_file):
    # Expect the default behaviour to raise.
    import os.path

    res = resolver.RefResolver(
        recursion_limit_files_file, fs.abspath("tests/specs/recursion_limit_files.yaml")
    )
    with pytest.raises(ResolutionError) as exc:
        res.resolve_references()

    assert str(exc.value).startswith("Recursion reached limit of 1")


def test_recursion_limit_do_not_recurse_ignore_files(recursion_limit_files_file):
    # If we overload the handler, we should not get an error but should
    # also simply not have the 'next' field - or it should be None
    import os.path

    res = resolver.RefResolver(
        recursion_limit_files_file,
        fs.abspath("tests/specs/recursion_limit_files.yaml"),
        recursion_limit_handler=recursion_limit_handler_none,
    )
    res.resolve_references()

    from prance.util import formats

    contents = formats.serialize_spec(res.specs, "foo.yaml")

    # The effect of returning None on recursion limit should be that
    # despite having recursion, the outermost reference to
    # definitions/Pet should get resolved.
    assert (
        "properties" in res.specs["paths"]["/pets"]["get"]["responses"]["200"]["schema"]
    )

    # However, the 'next' field should not be resolved.
    assert (
        res.specs["paths"]["/pets"]["get"]["responses"]["200"]["schema"]["properties"][
            "next"
        ]["schema"]
        is None
    )


def test_recursion_limit_set_limit_ignore_files(recursion_limit_files_file):
    # If we overload the handler, and set the recursion limit higher,
    # we should get nested Pet objects a few levels deep.

    import os.path

    res = resolver.RefResolver(
        recursion_limit_files_file,
        fs.abspath("tests/specs/recursion_limit_files.yaml"),
        recursion_limit=2,
        recursion_limit_handler=recursion_limit_handler_none,
    )
    res.resolve_references()

    from prance.util import formats

    contents = formats.serialize_spec(res.specs, "foo.yaml")

    # The effect of returning None on recursion limit should be that
    # despite having recursion, the outermost reference to
    # definitions/Pet should get resolved.
    assert (
        "properties" in res.specs["paths"]["/pets"]["get"]["responses"]["200"]["schema"]
    )

    # However, the 'next' field should be resolved due to the higher recursion limit
    next_field = res.specs["paths"]["/pets"]["get"]["responses"]["200"]["schema"][
        "properties"
    ]["next"]["schema"]
    assert next_field is not None

    # But the 'next' field of the 'next' field should not be resolved.
    assert next_field["properties"]["next"]["schema"] is None


@patch("requests.get")
def test_issue_22_empty_path(mock_get, externals_file):
    mock_get.side_effect = mock_get_petstore

    # The raw externals file must have unresolved data
    assert len(externals_file["paths"]["/pets/{petId}"]["get"]["parameters"]) == 1
    param = externals_file["paths"]["/pets/{petId}"]["get"]["parameters"][0]

    assert "overwritten" in param
    assert "$ref" in param

    import os.path
    from prance.util import fs

    res = resolver.RefResolver(
        externals_file, fs.abspath("tests/specs/with_externals.yaml")
    )
    res.resolve_references()

    # The tests should resolve the reference, but the reference overwrites
    # all else.
    assert len(res.specs["paths"]["/pets/{petId}"]["get"]["parameters"]) == 1
    param = res.specs["paths"]["/pets/{petId}"]["get"]["parameters"][0]

    # Dereferenced keys must exist here
    assert "type" in param
    assert "description" in param
    assert "required" in param
    assert "in" in param
    assert "name" in param

    # Previously defined keys must not
    assert "overwritten" not in param
    assert "$ref" not in param


def test_issue_38_tilde_one():
    specs = get_specs("tests/specs/issue_38_a.yaml")
    res = resolver.RefResolver(specs, fs.abspath("tests/specs/issue_38_a.yaml"))
    res.resolve_references()

    path = res.specs["paths"]["/api/v2/vms"]
    assert "get" in path
    assert "operationId" in path["get"]
    assert "description" in path["get"]


@patch("requests.get")
def test_issue_23_partial_resolution_all(mock_get):
    mock_get.side_effect = mock_get_petstore

    specs = get_specs("tests/specs/with_externals.yaml")
    res = resolver.RefResolver(specs, fs.abspath("tests/specs/with_externals.yaml"))
    res.resolve_references()

    # By default, all externals need to be resolved.
    from prance.util.path import path_get

    val = path_get(res.specs, ("paths", "/pets", "get", "responses", "200", "schema"))
    assert "$ref" not in val

    val = path_get(
        res.specs, ("paths", "/pets", "get", "responses", "default", "schema")
    )
    assert "$ref" not in val

    val = path_get(
        res.specs, ("paths", "/pets", "post", "responses", "default", "schema")
    )
    assert "$ref" not in val

    val = path_get(res.specs, ("paths", "/pets/{petId}", "get", "parameters", 0))
    assert "$ref" not in val

    val = path_get(
        res.specs, ("paths", "/pets/{petId}", "get", "responses", "200", "schema")
    )
    assert "$ref" not in val

    val = path_get(
        res.specs, ("paths", "/pets/{petId}", "get", "responses", "203", "schema")
    )
    assert "$ref" not in val

    val = path_get(
        res.specs, ("paths", "/pets/{petId}", "get", "responses", "default", "schema")
    )
    assert "$ref" not in val


def test_issue_23_partial_resolution_internal():
    specs = get_specs("tests/specs/with_externals.yaml")
    res = resolver.RefResolver(
        specs,
        fs.abspath("tests/specs/with_externals.yaml"),
        resolve_types=resolver.RESOLVE_INTERNAL,
    )
    res.resolve_references()

    # By default, all externals need to be resolved.
    from prance.util.path import path_get

    val = path_get(res.specs, ("paths", "/pets", "get", "responses", "200", "schema"))
    assert "$ref" in val

    val = path_get(
        res.specs, ("paths", "/pets", "get", "responses", "default", "schema")
    )
    assert "$ref" in val

    val = path_get(
        res.specs, ("paths", "/pets", "post", "responses", "default", "schema")
    )
    assert "$ref" in val

    val = path_get(res.specs, ("paths", "/pets/{petId}", "get", "parameters", 0))
    assert "$ref" in val

    val = path_get(
        res.specs, ("paths", "/pets/{petId}", "get", "responses", "200", "schema")
    )
    assert "$ref" in val

    val = path_get(
        res.specs, ("paths", "/pets/{petId}", "get", "responses", "203", "schema")
    )
    assert "$ref" in val

    val = path_get(
        res.specs, ("paths", "/pets/{petId}", "get", "responses", "default", "schema")
    )
    assert "$ref" not in val


def test_issue_23_partial_resolution_files():
    specs = get_specs("tests/specs/with_externals.yaml")
    res = resolver.RefResolver(
        specs,
        fs.abspath("tests/specs/with_externals.yaml"),
        resolve_types=resolver.RESOLVE_FILES,
    )
    res.resolve_references()

    # By default, all externals need to be resolved.
    from prance.util.path import path_get

    val = path_get(res.specs, ("paths", "/pets", "get", "responses", "200", "schema"))
    assert "$ref" not in val

    val = path_get(
        res.specs, ("paths", "/pets", "get", "responses", "default", "schema")
    )
    assert "$ref" not in val

    val = path_get(
        res.specs, ("paths", "/pets", "post", "responses", "default", "schema")
    )
    assert "$ref" not in val

    val = path_get(res.specs, ("paths", "/pets/{petId}", "get", "parameters", 0))
    assert "$ref" not in val

    val = path_get(
        res.specs, ("paths", "/pets/{petId}", "get", "responses", "200", "schema")
    )
    assert "$ref" in val

    val = path_get(
        res.specs, ("paths", "/pets/{petId}", "get", "responses", "203", "schema")
    )
    assert "$ref" not in val

    val = path_get(
        res.specs, ("paths", "/pets/{petId}", "get", "responses", "default", "schema")
    )
    assert "$ref" in val


@pytest.mark.skipif(none_of("openapi-spec-validator"), reason="Missing backends")
def test_issue_65_partial_resolution_files():
    specs = """openapi: "3.0.0"
info:
  title: ''
  version: '1.0.0'
paths: {}
components:
    schemas:
        SampleArray:
            type: array
            items:
              $ref: '#/components/schemas/ItemType'

        ItemType:
          type: integer
"""
    from prance.util import formats

    specs = formats.parse_spec(specs, "issue_65.yaml")

    res = resolver.RefResolver(
        specs, fs.abspath("issue_65.yaml"), resolve_types=resolver.RESOLVE_FILES
    )
    res.resolve_references()

    from prance.util.path import path_get

    val = path_get(res.specs, ("components", "schemas", "SampleArray", "items"))
    assert "$ref" in val


@patch("requests.get")
def test_issue_23_partial_resolution_http(mock_get):
    mock_get.side_effect = mock_get_petstore

    specs = get_specs("tests/specs/with_externals.yaml")
    res = resolver.RefResolver(
        specs,
        fs.abspath("tests/specs/with_externals.yaml"),
        resolve_types=resolver.RESOLVE_HTTP,
    )
    res.resolve_references()

    # By default, all externals need to be resolved.
    from prance.util.path import path_get

    val = path_get(res.specs, ("paths", "/pets", "get", "responses", "200", "schema"))
    assert "$ref" in val

    val = path_get(
        res.specs, ("paths", "/pets", "get", "responses", "default", "schema")
    )
    assert "$ref" in val

    val = path_get(
        res.specs, ("paths", "/pets", "post", "responses", "default", "schema")
    )
    assert "$ref" in val

    val = path_get(res.specs, ("paths", "/pets/{petId}", "get", "parameters", 0))
    assert "$ref" in val

    val = path_get(
        res.specs, ("paths", "/pets/{petId}", "get", "responses", "200", "schema")
    )
    assert "$ref" not in val

    val = path_get(
        res.specs, ("paths", "/pets/{petId}", "get", "responses", "203", "schema")
    )
    assert "$ref" in val

    val = path_get(
        res.specs, ("paths", "/pets/{petId}", "get", "responses", "default", "schema")
    )
    assert "$ref" in val


def test_issue_23_partial_resolution_invalid_scheme():
    specs = {"$ref": "foo://cannot-do-anything"}
    res = resolver.RefResolver(specs, fs.abspath("tests/specs/with_externals.yaml"))

    with pytest.raises(ValueError):
        res.resolve_references()


def test_issue_69_urlparse_error():
    # XXX depending on python version, the error may not actually come from
    #     parsing the URL, but from trying to load a local file that does
    #     not exist. See test_issue_72_* for a test case that specifically
    #     tries for a nonexistent file url.
    specs = {"$ref": "file://a\u2100b/bad/netloc"}
    res = resolver.RefResolver(specs, fs.abspath("tests/specs/with_externals.yaml"))

    with pytest.raises(ResolutionError) as exinfo:
        res.resolve_references()

    assert "bad/netloc" in str(exinfo.value)


def test_issue_72_nonexistent_file_error():
    specs = {"$ref": "file://does/not/exist"}
    res = resolver.RefResolver(specs, fs.abspath("tests/specs/with_externals.yaml"))

    with pytest.raises(ResolutionError) as exinfo:
        res.resolve_references()

    assert "not/exist" in str(exinfo.value)


@pytest.mark.skipif(none_of("openapi-spec-validator"), reason="Missing backends")
def test_issue_78_resolve_internal_bug():
    specs = ""
    with open("tests/specs/issue_78/openapi.json") as fh:
        specs = fh.read()

    from prance.util import formats

    specs = formats.parse_spec(specs, "openapi.json")

    res = resolver.RefResolver(
        specs, fs.abspath("openapi.json"), resolve_types=resolver.RESOLVE_FILES
    )
    res.resolve_references()

    from prance.util.path import path_get

    val = path_get(res.specs, ("paths", "/endpoint", "post", "requestBody", "content"))

    # Reference to file is resolved
    assert "application/json" in val
    # Internal reference within file is NOT resolved
    assert "$ref" in val["application/json"]


@pytest.mark.skipif(none_of("openapi-spec-validator"), reason="Missing backends")
def test_issue_77_translate_external():
    specs = ""
    with open("tests/specs/issue_78/openapi.json") as fh:
        specs = fh.read()

    from prance.util import formats

    specs = formats.parse_spec(specs, "openapi.json")

    res = resolver.RefResolver(
        specs,
        fs.abspath("openapi.json"),
        resolve_types=resolver.RESOLVE_FILES,
        resolve_method=resolver.TRANSLATE_EXTERNAL,
    )
    res.resolve_references()

    from prance.util.path import path_get

    val = path_get(res.specs, ("components", "schemas", "_schemas.json_Body"))

    # Reference to file is translated in components/schemas
    assert "content" in val
    assert "application/json" in val["content"]

    # Reference url is updated
    val = path_get(res.specs, ("paths", "/endpoint", "post", "requestBody", "$ref"))
    assert val == "#/components/schemas/_schemas.json_Body"


@pytest.mark.skipif(none_of("openapi-spec-validator"), reason="Missing backends")
def test_issue_77_translate_external_refs_internal():
    specs = ""
    with open("tests/specs/issue_78/openapi.json") as fh:
        specs = fh.read()

    from prance.util import formats

    specs = formats.parse_spec(specs, "openapi.json")

    res = resolver.RefResolver(
        specs,
        fs.abspath("openapi.json"),
        resolve_types=resolver.RESOLVE_FILES | resolver.RESOLVE_INTERNAL,
        resolve_method=resolver.TRANSLATE_EXTERNAL,
    )
    res.resolve_references()

    from prance.util.path import path_get

    val = path_get(res.specs, ("components", "schemas", "_schemas.json_Body"))

    # Reference to file is translated in components/schemas
    assert "content" in val
    assert "application/json" in val["content"]

    # Internal Reference links updated
    assert (
        "#/components/schemas/_schemas.json_Something"
        == val["content"]["application/json"]["$ref"]
    )

    # Internal references is copied to components/schemas separately
    val = path_get(res.specs, ("components", "schemas", "_schemas.json_Something"))
    assert "type" in val

    # File reference url is updated as well
    val = path_get(res.specs, ("paths", "/endpoint", "post", "requestBody", "$ref"))
    assert val == "#/components/schemas/_schemas.json_Body"


@pytest.mark.skipif(none_of("openapi-spec-validator"), reason="Missing backends")
def test_issue_77_internal_refs_unresolved():
    specs = ""
    with open("tests/specs/issue_78/openapi.json") as fh:
        specs = fh.read()

    from prance.util import formats

    specs = formats.parse_spec(specs, "openapi.json")

    res = resolver.RefResolver(
        specs,
        fs.abspath("openapi.json"),
        resolve_types=resolver.RESOLVE_FILES,
        resolve_method=resolver.TRANSLATE_EXTERNAL,
    )
    res.resolve_references()

    from prance.util.path import path_get

    val = path_get(res.specs, ("components", "schemas"))

    # File reference resolved
    assert "_schemas.json_Body" in val

    # Internal file reference not resolved
    assert "_schemas.json_Something" not in val


@pytest.mark.xfail(reason="https://github.com/RonnyPfannschmidt/prance/issues/87")
def test_issue_205_swagger_resolution_failure():
    specs = ""
    with open("tests/specs/kubernetes_api_docs.json") as fh:
        specs = fh.read()

    from prance.util import formats

    specs = formats.parse_spec(specs, "kubernetes_api_docs.json")

    res = resolver.RefResolver(
        specs,
        fs.abspath("kubernetes_api_docs.json"),
        resolve_types=resolver.RESOLVE_FILES,
        resolve_method=resolver.TRANSLATE_EXTERNAL,
    )
    # test will raise an exception
    res.resolve_references()


@patch("requests.get")
def test_resolve_package_ref(mock_get):
    mock_get.side_effect = mock_get_petstore

    specs = get_specs("tests/specs/with_externals.yaml")
    res = resolver.RefResolver(
        specs,
        fs.abspath("tests/specs/with_externals.yaml"),
        resolve_types=resolver.RESOLVE_FILES,
    )
    res.resolve_references()

    from prance.util.path import path_get

    val = path_get(
        res.specs, ("paths", "/pets/{petId}", "get", "responses", "203", "schema")
    )
    assert "required" in val


def test_keep_ref_on_recursion():
    specs = get_specs("tests/specs/self_recursive.yaml")
    res = resolver.RefResolver(
        specs,
        fs.abspath("tests/specs/self_recursive.yaml"),
        recursion_limit_handler=resolver.keep_ref_on_recursion,
    )
    res.resolve_references()

    from prance.util.path import path_get

    file_def = path_get(res.specs, ("definitions", "File"))
    # reclimit=1: File is resolved once, the recursive parent inside
    # that resolved copy keeps its $ref
    inner_parent = path_get(file_def, ("properties", "parent", "properties", "parent"))
    assert "$ref" in inner_parent
    assert inner_parent["$ref"] == "#/definitions/File"


def test_permissive_object_on_recursion():
    specs = get_specs("tests/specs/self_recursive.yaml")
    res = resolver.RefResolver(
        specs,
        fs.abspath("tests/specs/self_recursive.yaml"),
        recursion_limit_handler=resolver.permissive_object_on_recursion,
    )
    res.resolve_references()

    from prance.util.path import path_get

    file_def = path_get(res.specs, ("definitions", "File"))
    # reclimit=1: File is resolved once, the recursive parent inside
    # that resolved copy gets the permissive object
    inner_parent = path_get(file_def, ("properties", "parent", "properties", "parent"))
    assert inner_parent["type"] == "object"
    assert inner_parent["additionalProperties"] is True
    assert "x-recursive-ref" in inner_parent


# ---------------------------------------------------------------------------
# OpenAPI 3.1 Reference Object sibling summary/description overrides
# ---------------------------------------------------------------------------

_REF_SIBLINGS_SPEC = """\
openapi: "{version}"
info:
  title: Reference sibling overrides
  version: "1.0.0"
paths:
  /items:
    get:
      operationId: getItems
      parameters:
        - $ref: "#/components/parameters/IdParam"
          description: per-site parameter description
        - $ref: "#/components/parameters/IdParam"
        - $ref: "#/components/parameters/IdParam"
          description: another per-site parameter description
          summary: parameter summary is not a thing yet
      responses:
        "200":
          $ref: "#/components/responses/Ok"
          description: per-site response description
          summary: response summary does not exist in 3.1
    post:
      operationId: createItem
      requestBody:
        $ref: "#/components/requestBodies/Body"
        description: per-site request body description
      responses:
        "200":
          description: direct response
          headers:
            X-Rate:
              $ref: "#/components/headers/Rate"
              description: per-site header description
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Item"
              examples:
                first:
                  $ref: "#/components/examples/Sample"
                  summary: per-site example summary
                  description: per-site example description
          links:
            related:
              $ref: "#/components/links/Related"
              description: per-site link description
              summary: link summary does not exist in 3.1
components:
  parameters:
    IdParam:
      name: id
      in: path
      required: true
      description: shared parameter description
      schema:
        type: string
  requestBodies:
    Body:
      required: true
      description: shared request body description
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/Item"
  responses:
    Ok:
      description: shared response description
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/Item"
  headers:
    Rate:
      description: shared header description
      schema:
        type: integer
  links:
    Related:
      operationId: getItems
      description: shared link description
  examples:
    Sample:
      summary: shared example summary
      description: shared example description
      value:
        id: "7"
  schemas:
    Item:
      type: object
      description: shared schema description
      properties:
        id:
          type: string
    ItemRefWithSiblings:
      $ref: "#/components/schemas/Item"
      description: schema sibling must be ignored
    PlainItemRef:
      $ref: "#/components/schemas/Item"
"""


def _resolve_inline_ref_siblings(version, spec_string=_REF_SIBLINGS_SPEC):
    from prance.util import formats

    spec_string = spec_string.format(version=version)
    specs = formats.parse_spec(spec_string, "ref_siblings_inline.yaml")
    res = resolver.RefResolver(
        specs, fs.abspath("tests/specs/ref_siblings_inline.yaml")
    )
    res.resolve_references()
    return res.specs


def test_openapi31_ref_siblings_override_on_each_object_type():
    specs = _resolve_inline_ref_siblings("3.1.0")
    get_op = specs["paths"]["/items"]["get"]
    post_op = specs["paths"]["/items"]["post"]

    params = get_op["parameters"]
    assert params[0]["description"] == "per-site parameter description"
    assert params[0]["name"] == "id"
    assert "summary" not in params[0]
    assert params[2]["description"] == "another per-site parameter description"
    assert "summary" not in params[2]

    response = get_op["responses"]["200"]
    assert response["description"] == "per-site response description"
    assert "summary" not in response

    body = post_op["requestBody"]
    assert body["description"] == "per-site request body description"
    assert "application/json" in body["content"]

    header = post_op["responses"]["200"]["headers"]["X-Rate"]
    assert header["description"] == "per-site header description"

    link = post_op["responses"]["200"]["links"]["related"]
    assert link["description"] == "per-site link description"
    assert "summary" not in link

    example = post_op["responses"]["200"]["content"]["application/json"]["examples"][
        "first"
    ]
    assert example["summary"] == "per-site example summary"
    assert example["description"] == "per-site example description"
    assert example["value"] == {"id": "7"}


def test_openapi31_ref_siblings_do_not_affect_sites_without_them():
    specs = _resolve_inline_ref_siblings("3.1.0")
    params = specs["paths"]["/items"]["get"]["parameters"]

    # The site without siblings keeps the referenced component's value.
    assert params[1]["description"] == "shared parameter description"

    # And the shared component definition itself is untouched.
    assert (
        specs["components"]["parameters"]["IdParam"]["description"]
        == "shared parameter description"
    )
    assert (
        specs["components"]["responses"]["Ok"]["description"]
        == "shared response description"
    )


def test_openapi31_ref_siblings_isolate_sites_from_each_other():
    specs = _resolve_inline_ref_siblings("3.1.0")
    params = specs["paths"]["/items"]["get"]["parameters"]

    # Override sites get private copies; sites without siblings keep on
    # sharing the single resolved target object.
    assert params[0] is not params[1]
    assert params[0] is not params[2]
    assert params[1] is not params[2]

    # Mutating one override site must not leak into the other sites.
    params[0]["description"] = "locally mutated"
    assert params[1]["description"] == "shared parameter description"
    assert params[2]["description"] == "another per-site parameter description"


def test_openapi30_ref_siblings_are_ignored():
    specs = _resolve_inline_ref_siblings("3.0.3")
    params = specs["paths"]["/items"]["get"]["parameters"]

    # In 3.0 a Reference Object only carries $ref: siblings are dropped
    # and the component's own value survives unchanged.
    assert params[0]["description"] == "shared parameter description"
    assert params[1]["description"] == "shared parameter description"
    assert params[2]["description"] == "shared parameter description"

    response = specs["paths"]["/items"]["get"]["responses"]["200"]
    assert response["description"] == "shared response description"
    assert "summary" not in response


def test_openapi32_ref_sibling_response_summary_takes_effect():
    specs = _resolve_inline_ref_siblings("3.2.0")
    response = specs["paths"]["/items"]["get"]["responses"]["200"]

    # Response gained a summary field in 3.2, so the sibling now applies.
    assert response["summary"] == "response summary does not exist in 3.1"
    assert response["description"] == "per-site response description"

    # Types that still have no summary (parameter/link) keep ignoring it.
    params = specs["paths"]["/items"]["get"]["parameters"]
    assert "summary" not in params[0]
    link = specs["paths"]["/items"]["post"]["responses"]["200"]["links"]["related"]
    assert "summary" not in link


def test_schema_ref_siblings_resolve_as_before():
    specs = _resolve_inline_ref_siblings("3.1.0")
    schemas = specs["components"]["schemas"]

    # A Schema Object with $ref is not a Reference Object: siblings are
    # dropped exactly like ordinary resolution, target fields survive.
    with_siblings = schemas["ItemRefWithSiblings"]
    plain = schemas["PlainItemRef"]
    assert with_siblings["description"] == "shared schema description"
    assert with_siblings["properties"]["id"]["type"] == "string"
    assert plain is with_siblings


_REF_SIBLINGS_EXTERNAL_SPEC = """\
openapi: "3.1.0"
info:
  title: External reference sibling overrides
  version: "1.0.0"
paths:
  /ext:
    get:
      operationId: ext
      parameters:
        - $ref: "ref_siblings_external.yaml#/components/parameters/ExtId"
          description: local override of external parameter
        - $ref: "ref_siblings_external.yaml#/components/parameters/ExtId"
      responses:
        "200":
          $ref: "ref_siblings_external.yaml#/components/responses/ExtOk"
          description: local override of external response
"""


def test_openapi31_ref_siblings_apply_to_external_files():
    from prance.util import formats

    specs = formats.parse_spec(
        _REF_SIBLINGS_EXTERNAL_SPEC, "tests/specs/ref_siblings_inline.yaml"
    )
    res = resolver.RefResolver(
        specs, fs.abspath("tests/specs/ref_siblings_inline.yaml")
    )
    res.resolve_references()

    params = res.specs["paths"]["/ext"]["get"]["parameters"]
    assert params[0]["description"] == "local override of external parameter"
    assert params[0]["name"] == "id"
    assert params[1]["description"] == "external shared parameter description"
    assert params[0] is not params[1]

    response = res.specs["paths"]["/ext"]["get"]["responses"]["200"]
    assert response["description"] == "local override of external response"

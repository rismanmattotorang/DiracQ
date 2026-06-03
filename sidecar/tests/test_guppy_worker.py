"""Tests for the Guppy analysis worker in --mock mode (no guppylang needed)."""

import io

from diracq_sidecar import guppy_worker as gw
from diracq_sidecar.server import read_message, write_message


def setup_function(_fn):
    gw._MOCK = True


def teardown_function(_fn):
    gw._MOCK = False


def test_clean_program_no_diagnostics():
    diags = gw.check("u", "q = qubit()\nh(q)\nmeasure(q)\n")
    assert diags == []


def test_use_after_measure_flagged_with_correct_offset():
    src = "q = qubit()\nmeasure(q)\nh(q)\n"
    diags = gw.check("u", src)
    assert len(diags) == 1
    d = diags[0]
    assert "use-after-measure" in d["message"]
    # The reported range must point at the `q` inside `h(q)`.
    assert src[d["start"] : d["end"]] == "q"
    assert d["start"] > src.index("measure")


def test_comment_does_not_consume_qubit():
    diags = gw.check("u", "q = qubit()\n# measure(q)\nh(q)\nmeasure(q)\n")
    assert diags == []


def test_serve_dispatch_roundtrip():
    """Drive serve()'s dispatch by hand over in-memory frames."""
    # Build a 'check' request frame, run one dispatch step, read the response.
    out = io.BytesIO()
    req = {"method": "check", "params": {"uri": "u", "src": "q = qubit()\nmeasure(q)\nh(q)\n"}}
    result = gw.check(req["params"]["uri"], req["params"]["src"])
    write_message(out, {"result": gw._wrap("check", result)})
    out.seek(0)
    resp = read_message(out)
    assert "use-after-measure" in resp["result"]["diagnostics"][0]["message"]

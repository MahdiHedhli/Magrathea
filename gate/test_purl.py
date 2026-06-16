"""The acceptance gate (orchestrator-owned).

This is the deterministic gate the Conductor writes BEFORE dispatching the
worker. It pins the contract for a single pure function, ``parse_purl``, which
parses a Package URL ("purl") string into its components. The function does not
exist yet, so this gate is red until the worker creates ``gate/purl.py``.

----------------------------------------------------------------------------
CONTRACT  (this is also handed verbatim to the worker)
----------------------------------------------------------------------------
``parse_purl(purl: str) -> dict`` returns a dict with EXACTLY these keys:

    type       lowercased str                              (required)
    namespace  percent-decoded str, segments joined by '/' (or None if absent)
    name       percent-decoded str                         (required)
    version    percent-decoded str                         (or None if absent)
    qualifiers dict {lowercased_key: percent-decoded value} ({} if absent)
    subpath    percent-decoded str, leading/trailing '/' stripped (or None)

Parsing order (the canonical purl algorithm), splitting LEFT-to-RIGHT:
    1. split once on '#'  -> right side is the subpath
    2. split once on '?'  -> right side is the qualifiers
    3. split once on ':'  -> left side is the scheme, which MUST equal 'pkg'
                             (case-insensitive); strip any leading '//'
    4. split once on '/'  -> left side is the type (lowercased)
    5. split once on '@'  -> right side is the version
    6. split the rest on the LAST '/' -> left is namespace, right is name

Percent-decoding uses urllib.parse.unquote. Qualifier keys are lowercased;
a qualifier with an empty value is dropped. The subpath has leading/trailing
slashes removed.

``parse_purl`` raises ``ValueError`` when the string is not a valid purl:
the scheme is missing/not 'pkg', or there is no type, or there is no name.
----------------------------------------------------------------------------
"""
import pytest

from purl import parse_purl


# (purl string, expected component dict) — 6 valid cases.
VALID = [
    # 1. maven: namespace + name + version, no qualifiers/subpath
    (
        "pkg:maven/org.apache.commons/io@1.3.4",
        {"type": "maven", "namespace": "org.apache.commons", "name": "io",
         "version": "1.3.4", "qualifiers": {}, "subpath": None},
    ),
    # 2. npm: percent-encoded namespace (%40 -> @)
    (
        "pkg:npm/%40angular/animation@12.3.1",
        {"type": "npm", "namespace": "@angular", "name": "animation",
         "version": "12.3.1", "qualifiers": {}, "subpath": None},
    ),
    # 3. minimal: no namespace, no version, no qualifiers, no subpath
    (
        "pkg:gem/jruby-launcher",
        {"type": "gem", "namespace": None, "name": "jruby-launcher",
         "version": None, "qualifiers": {}, "subpath": None},
    ),
    # 4. type case-normalized; qualifier KEY lowercased; value percent-decoded
    (
        "pkg:PyPI/django@1.11.1?Extension=tar.gz&repository_url=https%3A%2F%2Fpypi.org",
        {"type": "pypi", "namespace": None, "name": "django", "version": "1.11.1",
         "qualifiers": {"extension": "tar.gz",
                        "repository_url": "https://pypi.org"},
         "subpath": None},
    ),
    # 5. multi-segment namespace + subpath, no version
    (
        "pkg:golang/google.golang.org/genproto#googleapis/api/annotations",
        {"type": "golang", "namespace": "google.golang.org", "name": "genproto",
         "version": None, "qualifiers": {},
         "subpath": "googleapis/api/annotations"},
    ),
    # 6. everything at once; subpath leading/trailing slashes stripped
    (
        "pkg:deb/debian/curl@7.50.3-1?arch=i386&distro=jessie#/path/to/thing/",
        {"type": "deb", "namespace": "debian", "name": "curl",
         "version": "7.50.3-1",
         "qualifiers": {"arch": "i386", "distro": "jessie"},
         "subpath": "path/to/thing"},
    ),
]


@pytest.mark.parametrize("purl,expected", VALID,
                         ids=[v[0] for v in VALID])
def test_parse_valid(purl, expected):
    assert parse_purl(purl) == expected


def test_missing_scheme_raises():
    # no 'pkg:' scheme
    with pytest.raises(ValueError):
        parse_purl("maven/org.apache.commons/io@1.3.4")


def test_empty_after_scheme_raises():
    # scheme present but no type/name
    with pytest.raises(ValueError):
        parse_purl("pkg:")

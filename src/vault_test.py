import vault

config = {"DEFAULT_KEY": "value"}


def test_parse_sources_finds_single_path():
    sources = "target:foo/bar/:key"
    result = vault.parse_sources(sources, config)
    assert result[0]["path"] == "foo/bar/"
    assert result[0]["key"] == "key"
    assert result[0]["target"] == "target"


def test_parse_sources_finds_default_key():
    sources = "target:foo/bar/"
    result = vault.parse_sources(sources, config)
    assert result[0]["target"] == "target"
    assert result[0]["key"] == "value"
    assert result[0]["path"] == "foo/bar/"


def test_parse_sources_finds_multiple_paths():
    sources = "foo/bar/:key,foo2/bar/:key2,target:/foo3/bar/:key3"
    result = vault.parse_sources(sources, config)
    assert result[1]["path"] == "foo2/bar/"
    assert result[1]["key"] == "key2"
    assert result[2]["path"] == "/foo3/bar/"
    assert result[2]["key"] == "key3"


def test_parse_sources_finds_multiple_paths_with_whitespace():
    sources = "   foo/bar/:key,   foo2/bar/:key2,   target:/foo3/bar/:key3   "
    result = vault.parse_sources(sources, config)
    assert result[0]["path"] == "foo/bar/"
    assert result[0]["key"] == "key"
    assert result[1]["path"] == "foo2/bar/"
    assert result[1]["key"] == "key2"
    assert result[2]["path"] == "/foo3/bar/"
    assert result[2]["key"] == "key3"
    assert result[2]["target"] == "target"


def test_parse_sources_finds_prefixs():
    sources = "foo/bar/:key,foo2/bar/:key2"
    result = vault.parse_sources(sources, config)
    assert result[1]["path"] == "foo2/bar/"
    assert result[1]["key"] == "key2"


def test_parse_sources_strips_leading_secret():
    result = vault.parse_sources("/secret/foo:key", config)
    assert result[0]["path"] == "/foo"
    result = vault.parse_sources("secret/foo:key", config)
    assert result[0]["path"] == "/foo"

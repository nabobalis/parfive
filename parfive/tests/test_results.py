from parfive import Results


def make_results(name):
    results = Results([f"{name}.txt"], urls=[f"http://example.com/{name}.txt"])
    results.add_error(f"{name}_failed.txt", f"http://example.com/{name}_failed.txt", ValueError(name))
    return results


def test_add_combines_urls_and_errors():
    a, b = make_results("a"), make_results("b")
    for combined in (a + b, a.__iadd__(b)):
        assert list(combined) == ["a.txt", "b.txt"]
        assert combined.urls == ["http://example.com/a.txt", "http://example.com/b.txt"]
        assert [error.url for error in combined.errors] == [
            "http://example.com/a_failed.txt",
            "http://example.com/b_failed.txt",
        ]
    assert a is a.__iadd__(Results())
    assert list(b) == ["b.txt"]
    assert len(b.urls) == len(b.errors) == 1

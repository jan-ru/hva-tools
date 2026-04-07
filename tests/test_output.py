"""Tests for _print_and_write_table output helper."""

from brightspace_extractor.cli import _print_and_write_table


class TestPrintAndWriteTable:
    """Tests for the shared table output helper."""

    def test_prints_table_to_stdout(self, capsys) -> None:
        items = [
            {"id": "1", "name": "Alpha"},
            {"id": "2", "name": "Beta"},
        ]
        _print_and_write_table(
            items,
            [("ID", "id", 6), ("Name", "name", 20)],
            None,
            "test.md",
            "# Test",
        )
        out = capsys.readouterr().out
        assert "Alpha" in out
        assert "Beta" in out
        assert "2 item(s) found." in out

    def test_writes_markdown_file(self, tmp_path) -> None:
        items = [{"id": "1", "name": "Alpha"}]
        _print_and_write_table(
            items,
            [("ID", "id", 6), ("Name", "name", 20)],
            str(tmp_path),
            "test.md",
            "# Test",
        )
        md = (tmp_path / "test.md").read_text(encoding="utf-8")
        assert md.startswith("# Test\n")
        assert "| ID | Name |" in md
        assert "| 1 | Alpha |" in md

    def test_empty_items_prints_nothing(self, capsys) -> None:
        _print_and_write_table(
            [],
            [("ID", "id", 6)],
            None,
            "test.md",
            "# Test",
        )
        out = capsys.readouterr().out
        assert out == ""

    def test_empty_items_does_not_write_file(self, tmp_path) -> None:
        _print_and_write_table(
            [],
            [("ID", "id", 6)],
            str(tmp_path),
            "test.md",
            "# Test",
        )
        assert not (tmp_path / "test.md").exists()

    def test_creates_output_dir_if_missing(self, tmp_path) -> None:
        out = tmp_path / "nested" / "dir"
        _print_and_write_table(
            [{"id": "1"}],
            [("ID", "id", 6)],
            str(out),
            "test.md",
            "# Test",
        )
        assert (out / "test.md").exists()

    def test_markdown_has_correct_separator(self, tmp_path) -> None:
        items = [{"a": "1", "b": "2", "c": "3"}]
        _print_and_write_table(
            items,
            [("A", "a", 5), ("B", "b", 5), ("C", "c", 5)],
            str(tmp_path),
            "test.md",
            "# Test",
        )
        md = (tmp_path / "test.md").read_text(encoding="utf-8")
        assert "|---|---|---|" in md

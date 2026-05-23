"""Tests for cell_id_mapper."""

import pytest

from cell_id_mapper.mapper import CellLineMapper, load_mapper


@pytest.fixture
def mapper():
    return load_mapper()


class TestExactLookup:
    def test_from_ach_found(self, mapper):
        cl = mapper.from_ach("ACH-000681")
        assert cl is not None
        assert cl.cell_line_name == "A549"

    def test_from_ach_not_found(self, mapper):
        assert mapper.from_ach("ACH-999999") is None

    def test_from_name_case_insensitive(self, mapper):
        cl = mapper.from_name("a549")
        assert cl is not None
        assert cl.depmap_id == "ACH-000681"

    def test_from_name_not_found(self, mapper):
        assert mapper.from_name("nonexistent") is None

    def test_from_cosmic(self, mapper):
        cl = mapper.from_cosmic("905949")
        assert cl is not None
        assert cl.cell_line_name == "A549"

    def test_from_sanger(self, mapper):
        cl = mapper.from_sanger("SIDM00903")
        assert cl is not None
        assert cl.cell_line_name == "A549"


class TestFuzzySearch:
    def test_search_by_name_substring(self, mapper):
        results = mapper.search("A5")
        assert len(results) > 0
        names = [r.cell_line_name for r in results]
        assert "A549" in names

    def test_search_limit(self, mapper):
        results = mapper.search("COLO", limit=3)
        assert len(results) <= 3


class TestFiltering:
    def test_by_lineage(self, mapper):
        lung = mapper.by_lineage("Lung")
        assert len(lung) > 0
        assert all("Lung" in cl.lineage for cl in lung)

    def test_by_disease(self, mapper):
        melanoma = mapper.by_disease("Melanoma")
        assert len(melanoma) > 0


class TestConversion:
    def test_ach_to_name(self, mapper):
        assert mapper.ach_to_name("ACH-000681") == "A549"

    def test_ach_to_cosmic(self, mapper):
        assert mapper.ach_to_cosmic("ACH-000681") == "905949"

    def test_name_to_ach(self, mapper):
        assert mapper.name_to_ach("A549") == "ACH-000681"

    def test_cosmic_to_name(self, mapper):
        assert mapper.cosmic_to_name("905949") == "A549"

    def test_sanger_to_ach(self, mapper):
        assert mapper.sanger_to_ach("SIDM00903") == "ACH-000681"


class TestStats:
    def test_len(self, mapper):
        assert len(mapper) >= 100

    def test_all_returns_copies(self, mapper):
        all_cl = mapper.all()
        assert len(all_cl) == len(mapper)

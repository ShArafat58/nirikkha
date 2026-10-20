from app.ingest.forms import form_of


def test_unknown_accession_falls_back_to_default():
    assert form_of("0000000000-00-000000") == "DEF 14A"
    assert form_of("0000000000-00-000001", default="10-K") == "10-K"
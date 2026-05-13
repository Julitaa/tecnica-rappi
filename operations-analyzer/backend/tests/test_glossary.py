from app.data.glossary import GLOSSARY, get_glossary_entry


def test_glossary_has_all_required_metrics():
    required = {
        "% PRO Users Who Breakeven",
        "% Restaurants Sessions With Optimal Assortment",
        "Gross Profit UE",
        "Lead Penetration",
        "MLTV Top Verticals Adoption",
        "Non-Pro PTC > OP",
        "Perfect Orders",
        "Pro Adoption",
        "Restaurants Markdowns / GMV",
        "Restaurants SS > ATC CVR",
        "Restaurants SST > SS CVR",
        "Retail SST > SS CVR",
        "Turbo Adoption",
    }
    assert required.issubset(set(GLOSSARY.keys()))


def test_each_entry_has_required_fields():
    for name, entry in GLOSSARY.items():
        assert "description" in entry, f"{name} missing description"
        assert "higher_is_better" in entry, f"{name} missing higher_is_better"
        assert "format" in entry, f"{name} missing format"


def test_get_glossary_entry_returns_none_for_unknown():
    assert get_glossary_entry("Nonexistent Metric") is None


def test_get_glossary_entry_returns_dict_for_known():
    entry = get_glossary_entry("Lead Penetration")
    assert entry is not None
    assert entry["higher_is_better"] is True

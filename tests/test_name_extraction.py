from slip_search import extract_name_from_text


def test_extract_name_from_text_combines_name_and_suffix_lines():
    text = """DATA PEGAWAI
MOCHAMAD MAULUDI
S.Pd.I
NIP 198301042005011003
"""

    assert extract_name_from_text(text, "198301042005011003") == "MOCHAMAD MAULUDI, S.Pd.I"

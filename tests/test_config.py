from cognify.config import Settings


def test_blank_credentials_and_file_loading(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','')
    monkeypatch.setenv('OPENAI_API_KEY_FILE','')
    assert Settings.load().api_key==''
    secret=tmp_path/'test-key.txt';secret.write_text('synthetic-unit-test-key\n')
    monkeypatch.setenv('OPENAI_API_KEY_FILE',str(secret))
    assert Settings.load().api_key=='synthetic-unit-test-key'
    assert 'synthetic-unit-test-key' not in repr(Settings.load())
    monkeypatch.setenv('OPENAI_API_KEY','direct-unit-test-key')
    assert Settings.load().api_key=='direct-unit-test-key'
    monkeypatch.setenv('OPENAI_API_KEY','')
    monkeypatch.setenv('OPENAI_API_KEY_FILE',str(tmp_path/'missing'))
    assert Settings.load().credential_error and Settings.load().api_key==''

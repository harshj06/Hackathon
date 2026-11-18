from dataclasses import dataclass, field
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')

@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv('COGNIFY_DATABASE_URL', 'sqlite:///data/cognify.db'))
    api_key: str = field(default='', repr=False)
    model: str = field(default_factory=lambda: os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))
    tts_model: str = field(default_factory=lambda: os.getenv('OPENAI_TTS_MODEL', 'gpt-4o-mini-tts'))
    voice: str = field(default_factory=lambda: os.getenv('OPENAI_TTS_VOICE', 'coral'))
    allow_demo: bool = field(default_factory=lambda: os.getenv('COGNIFY_ALLOW_DEMO', 'true').lower() == 'true')
    credential_error: str = ''

    @classmethod
    def load(cls):
        key = os.getenv('OPENAI_API_KEY', '').strip()
        path = os.getenv('OPENAI_API_KEY_FILE', '').strip()
        error = ''
        if not key and path:
            try:
                file = Path(path).expanduser()
                if file.stat().st_size > 1024:
                    raise ValueError('Credential file too large')
                key = file.read_text(encoding='utf-8').strip()
            except (OSError, ValueError, UnicodeError):
                error = 'Credential file could not be read. Check the server configuration.'
        return cls(api_key=key, credential_error=error)

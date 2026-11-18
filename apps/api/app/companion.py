"""Provider boundary with no default endpoint or implicit network calls."""
import os
import re
from typing import Protocol
import httpx
from pydantic import BaseModel, Field
from .content import Pack
from pathlib import Path

class TutorReply(BaseModel):
    explanation: str = Field(min_length=1, max_length=3000)
    follow_up: str = Field(max_length=300)

class TutorProvider(Protocol):
    def explain(self, topic: str, message: str, lesson: str) -> TutorReply: ...

class CompatibleProvider:
    """Uses an explicitly configured chat-completions-compatible HTTP endpoint."""
    def explain(self, topic: str, message: str, lesson: str) -> TutorReply:
        result = self.structured('tutor', f'Topic: {topic}\nReference lesson: {lesson}\nQuestion: {message}', TutorReply.model_json_schema())
        return TutorReply.model_validate(result)

    def __init__(self):
        self.tokens = 0

    def structured(self, operation: str, message: str, schema: dict) -> dict:
        endpoint = os.environ.get('AI_ENDPOINT','')
        key = os.environ.get('AI_API_KEY','')
        model = os.environ.get('AI_MODEL','')
        if not endpoint or not key or not model:
            raise ValueError('AI is not configured.')
        if not endpoint.startswith('https://'):
            raise ValueError('The AI endpoint must use HTTPS.')
        with httpx.Client(timeout=25, follow_redirects=False) as client:
            prompt = (Path(__file__).with_name('prompts') / (operation+'.txt')).read_text()
            response = client.post(endpoint, headers={'Authorization':f'Bearer {key}'}, json={
                'model':model, 'max_tokens':3500 if operation=='course' else 900, 'response_format':{'type':'json_object'},
                'messages':[{'role':'system','content':prompt+'\nReturn JSON matching this schema: '+__import__('json').dumps(schema)},
                            {'role':'user','content':message}]})
            response.raise_for_status()
            data=response.json()
            self.tokens += int(data.get('usage',{}).get('total_tokens',0))
            return __import__('json').loads(data['choices'][0]['message']['content'])

    def moderate(self, text: str) -> bool:
        endpoint=os.getenv('MODERATION_ENDPOINT','')
        key=os.getenv('MODERATION_API_KEY','')
        if not endpoint.startswith('https://') or not key:
            raise ValueError('A moderation service must be configured before online AI is enabled.')
        with httpx.Client(timeout=15,follow_redirects=False) as client:
            response=client.post(endpoint,headers={'Authorization':f'Bearer {key}'},json={'input':text})
            response.raise_for_status()
            result=response.json()['results']
            if not result or any(type(r.get('flagged')) is not bool for r in result):
                raise ValueError('Invalid moderation result.')
            return not any(r['flagged'] for r in result)

def online_ready() -> bool:
    return os.getenv('AI_ENABLED','false').lower()=='true' and all(os.getenv(k) for k in ['AI_ENDPOINT','AI_API_KEY','AI_MODEL','MODERATION_ENDPOINT','MODERATION_API_KEY'])

def safe_explain(provider: CompatibleProvider, topic: str, message: str, lesson: str) -> TutorReply:
    if not provider.moderate(topic+'\n'+message):
        raise ValueError('Let’s choose a safe learning question instead.')
    result=provider.explain(topic,message,lesson)
    if privacy_check(result.explanation) or not provider.moderate(result.explanation+'\n'+result.follow_up):
        raise ValueError('That reply could not pass the safety check. Try a different learning question.')
    return result

def draft_course(provider: CompatibleProvider, topic: str) -> Pack:
    if not provider.moderate(topic):
        raise ValueError('Choose a safe learning topic.')
    pack=Pack.model_validate(provider.structured('course',topic,Pack.model_json_schema()))
    if not provider.moderate(pack.model_dump_json()):
        raise ValueError('This course draft could not pass the safety check.')
    return pack

def privacy_check(message: str) -> bool:
    return bool(re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b\d[\d -]{8,}\d\b', message))

def guided_reply(pack: Pack, message: str, companion: str, completed: int) -> str:
    """Curated tutoring, explicitly labeled by the API. Never imitates general AI."""
    if privacy_check(message):
        return 'Keep email addresses and phone numbers out of chat. Ask about the idea you want to learn instead.'
    if 'activity' in message.lower() or 'try' in message.lower():
        return pack.activity
    if 'progress' in message.lower():
        return f'You have completed {completed} rounds in this topic. Try explaining the main idea in your own words, then revisit a challenge.'
    return f'{pack.lesson}\n\nWhat part would you like to try? Use “Give me an activity” for a hands-on step. In guided mode I can share this topic’s authored lesson and activity.'

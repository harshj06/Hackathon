from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from sqlalchemy import select,func
from cognify.config import Settings
from cognify.models import Concept,ChatMessage,Mastery
from cognify.services.buddy import BuddyService
from cognify.services.conversation import conversation,send_message,respond,TutorReply
from cognify.services.accounts import register,AccessDenied


def test_offline_conversation_persists_and_is_private(factory,learner):
    u,p=learner
    reply=send_message(factory,Settings(),u.id,p.id,'addition','Show me an example')
    assert reply.source=='Offline guided tutor' and '3 + 2' in reply.reply.answer
    with factory.begin() as s:
        outsider=register(s,'another','long-password','learner')
        assert len(conversation(s,u.id,p.id,'addition'))==2
        with pytest.raises(AccessDenied):
            conversation(s,outsider.id,p.id,'addition')
        assert s.scalar(select(func.count()).select_from(Mastery))==0
    with pytest.raises(ValueError):
        send_message(factory,Settings(),u.id,p.id,'addition',' ')


def test_structured_conversation_success_refusal_failure(factory,learner):
    u,p=learner;p.ai_enabled=True
    client=Mock();service=BuddyService(Settings(api_key='fake-test-key'),client)
    with factory() as s:
        c=s.get(Concept,'addition')
        client.responses.parse.return_value=SimpleNamespace(output_parsed=TutorReply(answer='Combine the groups.',steps=['Count each item once.'],question='What happens with two groups of three?'))
        assert respond(service,c,p,'Help',[]).source=='AI tutor'
        assert client.responses.parse.call_args.kwargs['store'] is False
        client.responses.parse.return_value=SimpleNamespace(output_parsed=None)
        assert 'fallback' in respond(service,c,p,'Help',[]).source
        client.responses.parse.side_effect=TimeoutError('secret')
        assert 'secret' not in respond(service,c,p,'Help',[]).source

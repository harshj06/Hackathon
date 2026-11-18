import pytest
from app.companion import CompatibleProvider, TutorReply, safe_explain, draft_course, online_ready, guided_reply
from app.content import PACKS, Pack

class Provider:
    def __init__(self,allowed=True): self.allowed=allowed
    def moderate(self,text): return self.allowed
    def explain(self,*args): return TutorReply(explanation='A loop repeats steps.',follow_up='What would you repeat?')
    def structured(self,*args): return PACKS['coding'].model_dump()

def test_online_requires_explicit_configuration(monkeypatch):
    monkeypatch.setenv('AI_ENABLED','false')
    assert not online_ready()
    monkeypatch.setenv('AI_ENABLED','true')
    for name in ['AI_API_KEY','AI_ENDPOINT','AI_MODEL','MODERATION_API_KEY','MODERATION_ENDPOINT']:
        monkeypatch.setenv(name,'configured')
    assert online_ready()

def test_provider_does_not_default_to_remote_endpoint(monkeypatch):
    monkeypatch.delenv('AI_ENDPOINT',raising=False)
    with pytest.raises(ValueError): CompatibleProvider().explain('coding','hello','')
    monkeypatch.setenv('AI_ENDPOINT','http://example.test')
    monkeypatch.setenv('AI_API_KEY','fake')
    monkeypatch.setenv('AI_MODEL','fake')
    with pytest.raises(ValueError): CompatibleProvider().explain('coding','hello','')
    with pytest.raises(ValueError): CompatibleProvider().moderate('hello')

def test_safety_and_structure():
    assert safe_explain(Provider(),'coding','explain','').explanation
    with pytest.raises(ValueError): safe_explain(Provider(False),'coding','explain','')
    assert draft_course(Provider(),'coding').id=='coding'
    with pytest.raises(ValueError): draft_course(Provider(False),'coding')
    data=PACKS['coding'].model_dump()
    data['questions'][0]['correct']=3
    with pytest.raises(ValueError): Pack.model_validate(data)

def test_guided_memory_and_privacy():
    pack=PACKS['coding']
    assert 'contact' in guided_reply(pack,'me@example.test','Nova',3)
    assert '3 rounds' in guided_reply(pack,'progress','Nova',3)
    assert 'algorithm' in guided_reply(pack,'explain','Nova',3)

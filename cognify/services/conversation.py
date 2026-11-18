"""Private, concept-scoped conversations. Conversation never writes assessment results."""
import json
from dataclasses import dataclass
from pydantic import BaseModel, Field
from sqlalchemy import select,func
from datetime import timedelta
from cognify.models import Concept,ChatMessage,now
from cognify.services.accounts import require_profile, require_user
from cognify.services.buddy import BuddyService,SYSTEM,log
from cognify.adaptive import EXPERIENCES

class MessageInput(BaseModel):
    text: str = Field(min_length=1,max_length=1000)

class TutorReply(BaseModel):
    answer: str = Field(min_length=1,max_length=1200)
    steps: list[str] = Field(min_length=1,max_length=3)
    question: str = Field(min_length=1,max_length=300)

@dataclass
class ReplyResult:
    reply: TutorReply
    source: str


def conversation(session,user_id,profile_id,concept_id):
    require_profile(session,user_id,profile_id,write=True)
    return list(reversed(list(session.scalars(select(ChatMessage).where(ChatMessage.profile_id==profile_id,
        ChatMessage.concept_id==concept_id).order_by(ChatMessage.id.desc()).limit(12)))))


def respond(service,concept,profile,text,history,demo=False):
    lower=text.casefold()
    lesson=concept.lesson
    if any(word in lower for word in ['example','analogy','interest']):
        answer=lesson['example']
    elif any(word in lower for word in ['try','activity','practice']):
        answer=lesson['activity']
    elif any(word in lower for word in ['visual','draw','picture']):
        answer=lesson['visual']
    else:
        answer=lesson['explanation']
    local=TutorReply(answer=answer,steps=['Try the worked example: '+lesson['example']],
        question='Which part would you like to unpack: the idea, an example, or a practice activity?')
    if demo or not profile.ai_enabled or not service.client:
        return ReplyResult(local,'Offline guided tutor')
    try:
        payload={'concept':concept.title,'reviewed_lesson':lesson,'age_guidance':EXPERIENCES[profile.age_group].instruction,
            'interests':profile.interests,'preference':profile.preference,
            'conversation':[{'role':m.role,'text':m.text[:1800]} for m in history[-6:]],'question':text}
        result=service.client.responses.parse(model=service.settings.model,
            input=[{'role':'system','content':SYSTEM+' Stay within this concept. Keep replies brief. Redirect unrelated requests to learning. Do not request personal information.'},
                   {'role':'user','content':json.dumps(payload)}],text_format=TutorReply,max_output_tokens=1000,store=False)
        if result.output_parsed is None:
            raise ValueError('No structured response')
        reply=TutorReply.model_validate(result.output_parsed)
        if any(len(step)>800 for step in reply.steps):
            raise ValueError('Reply too long')
        return ReplyResult(reply,'AI tutor')
    except Exception as exc:
        log.warning('Tutor request failed (%s)',type(exc).__name__)
        return ReplyResult(local,'Offline fallback — online reply unavailable')


def send_message(factory,settings,user_id,profile_id,concept_id,text,service=None):
    text=MessageInput(text=text.strip()).text
    with factory() as session:
        profile=require_profile(session,user_id,profile_id,write=True)
        user=require_user(session,user_id)
        concept=session.get(Concept,concept_id)
        if not concept:
            raise ValueError('Choose a concept first.')
        recent=session.scalar(select(func.count()).select_from(ChatMessage).where(ChatMessage.profile_id==profile_id,ChatMessage.role=='user',ChatMessage.created_at>=now()-timedelta(minutes=1)))
        if recent>=6:
            raise ValueError('Let’s pause for a moment. You can send up to six messages per minute.')
        messages=conversation(session,user_id,profile_id,concept_id)
    # No DB write transaction is held while waiting on the network.
    result=respond(service or BuddyService(settings),concept,profile,text,messages,demo=user.demo)
    content='\n\n'.join([result.reply.answer,*result.reply.steps,result.reply.question])
    with factory.begin() as session:
        require_profile(session,user_id,profile_id,write=True)
        session.add(ChatMessage(profile_id=profile_id,concept_id=concept_id,role='user',text=text,source=''))
        session.add(ChatMessage(profile_id=profile_id,concept_id=concept_id,role='assistant',text=content,source=result.source))
    return result

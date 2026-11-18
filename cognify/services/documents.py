"""Source-grounded recall. Answers are extracted deterministically, never authored by AI."""
import hashlib
import io
import re
from pathlib import PurePath
from pypdf import PdfReader
from sqlalchemy import select
from cognify.models import Document, DocumentAttempt, Event
from cognify.services.accounts import require_profile

MAX_BYTES = 5 * 1024 * 1024
MAX_CHARS = 80000
MAX_PAGES = 40


def extract_text(filename, data):
    suffix = PurePath(filename).suffix.lower()
    if suffix not in ['.txt', '.pdf']:
        raise ValueError('Upload a PDF or UTF-8 TXT file.')
    if not data or len(data) > MAX_BYTES:
        raise ValueError('Choose a non-empty file no larger than 5 MB.')
    if suffix == '.txt':
        try:
            text = data.decode('utf-8-sig')
        except UnicodeError:
            raise ValueError('TXT files must use UTF-8 encoding.') from None
        if '\x00' in text:
            raise ValueError('This file does not appear to be plain text.')
    else:
        if not data.startswith(b'%PDF-'):
            raise ValueError('The file is not a valid PDF.')
        try:
            reader = PdfReader(io.BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise ValueError('Password-protected PDFs are not supported.')
            if len(reader.pages) > MAX_PAGES:
                raise ValueError('Use a PDF with at most 40 pages.')
            pieces = []
            total = 0
            for page in reader.pages:
                piece = page.extract_text() or ''
                total += len(piece)
                if total > MAX_CHARS:
                    raise ValueError('Use a shorter document (at most 80,000 characters).')
                pieces.append(piece)
            text = '\n'.join(pieces)
        except ValueError:
            raise
        except Exception:
            raise ValueError('The PDF could not be read. Try exporting it again as a text-based PDF.') from None
    text = text.strip()
    if len(text) < 30:
        raise ValueError('No usable text was found. Scanned PDFs need OCR before upload; provide at least 30 characters.')
    if len(text) > MAX_CHARS:
        raise ValueError('Use a shorter document (at most 80,000 characters).')
    return text


def upload_document(session, user_id, profile_id, filename, data):
    require_profile(session, user_id, profile_id, write=True)
    text = extract_text(filename, data)
    digest = hashlib.sha256(data).hexdigest()
    existing = session.scalar(select(Document).where(Document.profile_id == profile_id, Document.digest == digest))
    if existing:
        return existing
    name = filename.replace('\\', '/').split('/')[-1][:120]
    doc = Document(profile_id=profile_id, filename=name, digest=digest, text=text)
    session.add(doc)
    session.add(Event(profile_id=profile_id, kind='Document', detail='Added a document for source-based practice.'))
    session.flush()
    return doc


def get_document(session, user_id, doc_id, write=False):
    doc = session.get(Document, doc_id)
    if not doc:
        raise ValueError('Document not found.')
    # Classroom sharing covers progress only, not private document contents.
    require_profile(session, user_id, doc.profile_id, write=True)
    return doc


def recall_questions(text):
    sentences = re.split(r'(?<=[.!?])\s+|\n+', text[:12000])
    questions = []
    for sentence in sentences:
        if not 30 <= len(sentence) <= 450:
            continue
        words = list(re.finditer(r'\b[A-Za-z]{5,}\b', sentence))
        if not words:
            continue
        word = max(words, key=lambda m: len(m.group()))
        questions.append({'prompt': sentence[:word.start()] + '______' + sentence[word.end():],
                          'answer': word.group(), 'evidence': sentence})
        if len(questions) == 3:
            break
    return questions


def grade_recall(session, user_id, doc_id, responses):
    doc = get_document(session, user_id, doc_id, write=True)
    questions = recall_questions(doc.text)
    if not questions or len(responses) != len(questions) or any(not r.strip() or len(r) > 100 for r in responses):
        raise ValueError('Enter one short answer for each source-recall question.')
    flags = [answer.strip().casefold() == q['answer'].casefold() for answer, q in zip(responses, questions)]
    session.add(DocumentAttempt(document_id=doc_id, profile_id=doc.profile_id, correct=sum(flags), total=len(flags)))
    session.add(Event(profile_id=doc.profile_id, kind='Source recall', detail=f'{sum(flags)}/{len(flags)} exact source words recalled.'))
    from cognify.services.engagement import _award, refresh_badges
    from cognify.models import now
    _award(session,doc.profile_id,f'doc-recall:{doc.id}:{now().date()}','Source recall',5+round(10*sum(flags)/len(flags)))
    refresh_badges(session,user_id,doc.profile_id)
    return flags, questions


def source_summary(text):
    """Extractive summary: only exact source sentences, no fabricated attribution."""
    sentences=re.split(r'(?<=[.!?])\s+|\n+',text[:12000])
    return [s.strip() for s in sentences if 30<=len(s.strip())<=450][:3]


def document_plan(session,user_id,doc_id):
    from cognify.models import DocumentPlan
    doc=get_document(session,user_id,doc_id)
    row=session.get(DocumentPlan,doc_id)
    if not row:
        steps=[{'title':f'Read & explain · part {i+1}','evidence':sentence} for i,sentence in enumerate(source_summary(doc.text))]
        if recall_questions(doc.text):
            steps.append({'title':'Check source recall','evidence':'','kind':'recall'})
        elif not steps:
            steps.append({'title':'Read the source and note a question','evidence':doc.text[:450]})
        row=DocumentPlan(document_id=doc_id,steps=steps,completed=[])
        session.add(row);session.flush()
    return row


def complete_document_step(session,user_id,doc_id,index):
    from cognify.services.engagement import _award,refresh_badges
    plan=document_plan(session,user_id,doc_id)
    doc=get_document(session,user_id,doc_id)
    if type(index) is not int or not 0<=index<len(plan.steps):
        raise ValueError('Unknown source-learning step.')
    if index!=len(plan.completed) and index not in plan.completed:
        raise ValueError('Complete the earlier source steps first.')
    if plan.steps[index].get('kind')=='recall':
        passed=session.scalar(select(DocumentAttempt.id).where(DocumentAttempt.document_id==doc_id,
            DocumentAttempt.correct==DocumentAttempt.total,DocumentAttempt.total>0).limit(1))
        if not passed:
            raise ValueError('Recall all source words correctly to finish this path.')
    if index not in plan.completed:
        plan.completed=plan.completed+[index]
    if len(plan.completed)==len(plan.steps):
        _award(session,doc.profile_id,f'doc-path:{doc_id}','Source mission',15)
        refresh_badges(session,user_id,doc.profile_id)
    return plan

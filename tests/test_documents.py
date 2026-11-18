import io
import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from sqlalchemy import select
from cognify.models import DocumentAttempt
from cognify.services.documents import extract_text, upload_document, recall_questions, grade_recall, MAX_BYTES

TEXT='Photosynthesis converts sunlight into stored chemical energy. Plants absorb water through their roots.'


def pdf_bytes():
    writer=PdfWriter()
    page=writer.add_blank_page(width=400,height=400)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject()
    stream.set_data(f'BT /F1 12 Tf 30 300 Td ({TEXT}) Tj ET'.encode())
    page[NameObject('/Contents')]=writer._add_object(stream)
    out=io.BytesIO(); writer.write(out)
    return out.getvalue()


def test_text_and_pdf_extraction():
    assert extract_text('lesson.txt',TEXT.encode())==TEXT
    assert 'Photosynthesis' in extract_text('lesson.pdf',pdf_bytes())


@pytest.mark.parametrize('name,data',[('x.exe',b'bad'),('x.txt',b''),('x.pdf',b'not pdf'),('x.pdf',b'%PDF-1.4 corrupted'),('x.txt',b'\xff'*40),('x.txt',b'x'*(MAX_BYTES+1)),('x.txt',b'x'*80001),('x.txt',b'x\x00'*40)])
def test_invalid_documents(name,data):
    with pytest.raises(ValueError):
        extract_text(name,data)


def test_empty_encrypted_and_long_pdf():
    for kind in ['empty','encrypted','long']:
        writer=PdfWriter()
        for _ in range(41 if kind=='long' else 1):
            writer.add_blank_page(100,100)
        if kind=='encrypted':
            writer.encrypt('password')
        out=io.BytesIO();writer.write(out)
        with pytest.raises(ValueError):
            extract_text('test.pdf',out.getvalue())


def test_recall_is_source_grounded_and_persisted(factory,learner):
    u,p=learner
    with factory.begin() as s:
        doc=upload_document(s,u.id,p.id,'../../lesson.txt',TEXT.encode())
        duplicate=upload_document(s,u.id,p.id,'same.txt',TEXT.encode())
        assert doc.id==duplicate.id and doc.filename=='lesson.txt'
        qs=recall_questions(doc.text)
        assert qs and all(q['answer'] in q['evidence'] for q in qs)
        flags,_=grade_recall(s,u.id,doc.id,[q['answer'].upper() for q in qs])
        assert all(flags)
    with factory() as s:
        assert s.scalar(select(DocumentAttempt)).correct==len(qs)


def test_extract_summary_and_source_mission(factory,learner):
    from cognify.services.documents import source_summary,document_plan,complete_document_step
    from cognify.services.engagement import snapshot
    u,p=learner
    assert all(s in TEXT for s in source_summary(TEXT))
    with factory.begin() as s:
        doc=upload_document(s,u.id,p.id,'source.txt',TEXT.encode())
        plan=document_plan(s,u.id,doc.id)
        with pytest.raises(ValueError):
            complete_document_step(s,u.id,doc.id,len(plan.steps)-1)
        for index in range(len(plan.steps)-1):
            complete_document_step(s,u.id,doc.id,index)
        with pytest.raises(ValueError,match='Recall'):
            complete_document_step(s,u.id,doc.id,len(plan.steps)-1)
        qs=recall_questions(TEXT)
        grade_recall(s,u.id,doc.id,[q['answer'] for q in qs])
        complete_document_step(s,u.id,doc.id,len(plan.steps)-1)
        total=snapshot(s,u.id,p.id)['total']
        complete_document_step(s,u.id,doc.id,len(plan.steps)-1)
        assert snapshot(s,u.id,p.id)['total']==total==30


def test_non_cloze_source_has_completable_reading_path(factory,learner):
    from cognify.services.documents import document_plan,complete_document_step
    u,p=learner
    with factory.begin() as s:
        doc=upload_document(s,u.id,p.id,'short-words.txt',b'The sun is up. We can see it. It is a big hot sun in the sky.')
        assert not recall_questions(doc.text)
        plan=document_plan(s,u.id,doc.id)
        for i in range(len(plan.steps)):
            complete_document_step(s,u.id,doc.id,i)
        assert len(plan.completed)==len(plan.steps)

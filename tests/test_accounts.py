import pytest
from sqlalchemy import select
from cognify.services.accounts import (register,login,ProfileInput,create_profile,require_profile,
    create_classroom,enroll,leave_classroom,AccessDenied,visible_profiles)
from cognify.models import LoginThrottle
from cognify.services.learning import start_assessment
from cognify.services.documents import upload_document,get_document


def test_login_and_throttle(factory,learner):
    u,p=learner
    with factory.begin() as s:
        assert login(s,'LEARNER_ONE','a-long-password').id==u.id
    for _ in range(5):
        with pytest.raises(ValueError),factory.begin() as s:
            login(s,u.username,'wrong-password')
    with factory() as s:
        assert s.get(LoginThrottle,u.username).failures==5
    with pytest.raises(ValueError,match='Too many'),factory.begin() as s:
        login(s,u.username,'a-long-password')


def test_child_profiles_require_parent(factory):
    data=ProfileInput(nickname='Pip',age_group='5–8',education='School',interests=[],subjects=['Mathematics'],goals='Count',preference='Visual')
    with factory.begin() as s:
        u=register(s,'adult_one','long-password','learner')
        parent=register(s,'parent_one','long-password','parent')
        with pytest.raises(ValueError,match='parent'):
            create_profile(s,u.id,data)
        p=create_profile(s,parent.id,data)
        assert p.owner_id==parent.id


def test_cross_account_and_explicit_classroom_access(factory,learner):
    u,p=learner
    with factory.begin() as s:
        other=register(s,'stranger','long-password','learner')
        teacher=register(s,'teacher','long-password','educator')
        classroom=create_classroom(s,teacher.id,'Science club')
        doc=upload_document(s,u.id,p.id,'lesson.txt',b'Plants require sunlight for photosynthesis. Roots absorb water from the soil.')
        for uid in [other.id,teacher.id]:
            with pytest.raises(AccessDenied):
                require_profile(s,uid,p.id)
        enroll(s,u.id,p.id,classroom.invite)
        assert require_profile(s,teacher.id,p.id).id==p.id
        assert visible_profiles(s,teacher.id)[0].id==p.id
        with pytest.raises(AccessDenied):
            start_assessment(s,teacher.id,p.id,'addition')
        with pytest.raises(AccessDenied):
            get_document(s,teacher.id,doc.id)
        leave_classroom(s,u.id,p.id,classroom.id)
        s.flush()
        with pytest.raises(AccessDenied):
            require_profile(s,teacher.id,p.id)


def test_invalid_registration(factory):
    with factory.begin() as s:
        for username,password,role in [('A !','long-password','learner'),('valid','short','learner'),('valid','long-password','admin')]:
            with pytest.raises(ValueError):
                register(s,username,password,role)


def test_blank_profile_fields_rejected():
    with pytest.raises(ValueError):
        ProfileInput(nickname=' ',age_group='25+',education='Adult',interests=[],subjects=['Science'],goals='Study',preference='Visual')

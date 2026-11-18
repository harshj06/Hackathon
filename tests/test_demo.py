from sqlalchemy import select,func
from cognify.services.demo import create_demo
from cognify.services.accounts import visible_profiles
from cognify.models import Assessment,User


def test_demo_is_persisted_isolated_and_all_ages(factory):
    with factory.begin() as s:
        first=create_demo(s)
        second=create_demo(s)
    with factory() as s:
        a=visible_profiles(s,first.id);b=visible_profiles(s,second.id)
        assert len(a)==len(b)==5
        assert len({p.age_group for p in a})==5
        assert not ({p.id for p in a}&{p.id for p in b})
        assert s.scalar(select(func.count()).select_from(Assessment))==36
        assert s.get(User,first.id).demo

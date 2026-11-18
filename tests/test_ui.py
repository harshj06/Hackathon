"""Exercise actual Streamlit widget flows with an isolated on-disk database."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]


def button(app,label):
    return next(b for b in app.button if b.label==label)


def assert_clean(app):
    assert not app.exception, [e.message for e in app.exception]
    assert not app.error, [e.value for e in app.error]


def test_demo_all_screens_and_assessment(tmp_path,monkeypatch):
    monkeypatch.setenv('COGNIFY_DATABASE_URL','sqlite:///'+str(tmp_path/'ui.db'))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    assert_clean(app)
    button(app,'Explore the demo').click().run()
    assert_clean(app)
    menu=app.sidebar.radio[0]
    for page in ['Learn','Buddy Chat','Games','Achievements','Study plan','Profile','Practice','Progress','Document lab','Settings','Parent space','Educator studio','My learning']:
        app.sidebar.radio[0].set_value(page).run()
        assert_clean(app)
        assert app.session_state['route']==page
    app.sidebar.radio[0].set_value('Practice').run()
    button(app,'Start diagnostic').click().run()
    assert_clean(app)
    for radio in app.radio:
        if radio.label!='Explore':
            radio.set_value(0)
    button(app,'Check my understanding').click().run()
    assert_clean(app)
    assert any('correct' in x.value for x in app.success)
    button(app,'Explain with Buddy').click().run()
    assert_clean(app)
    assert any('Curated offline lesson' in x.value for x in app.caption)
    # Exercise all five age adaptations and ensure private lesson state is cleared.
    app.sidebar.radio[0].set_value('My learning').run()
    for index in range(1,5):
        app.sidebar.selectbox[0].set_value(index+1).run()
        assert_clean(app)
        assert 'lesson' not in app.session_state
    button(app,'Sign out').click().run()
    assert_clean(app)
    assert any(b.label=='Explore the demo' for b in app.button)


def test_registration_onboarding_and_persistence(tmp_path,monkeypatch):
    monkeypatch.setenv('COGNIFY_DATABASE_URL','sqlite:///'+str(tmp_path/'onboarding.db'))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    next(w for w in app.text_input if w.label=='Choose a username').set_value('ui_parent')
    next(w for w in app.text_input if w.label=='Choose a password').set_value('long-enough-password')
    next(w for w in app.selectbox if w.label=='I am joining as').set_value('parent')
    app.checkbox[0].check()
    button(app,'Create account').click().run()
    assert_clean(app)
    next(w for w in app.text_input if w.label=='Learner nickname').set_value('Sunny')
    next(w for w in app.text_input if w.label=='Education level').set_value('Primary school')
    app.text_area[0].set_value('Understand numbers')
    button(app,'Create learning space').click().run()
    assert_clean(app)
    assert any('Sunny' in x.value for x in app.markdown)
    button(app,'Sign out').click().run()
    app.text_input(key='login_username').set_value('ui_parent')
    app.text_input(key='login_password').set_value('long-enough-password')
    button(app,'Sign in').click().run()
    assert_clean(app)
    assert any('Sunny' in x.value for x in app.markdown)


def test_games_chat_and_saved_study_plan(tmp_path,monkeypatch):
    monkeypatch.setenv('COGNIFY_DATABASE_URL','sqlite:///'+str(tmp_path/'engagement.db'))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    button(app,'Explore the demo').click().run()
    button(app,'Find a game').click().run()
    assert app.session_state['route']=='Games'
    app.selectbox(key='game_concept').set_value('fractions').run()
    button(app,'Play match the pairs').click().run()
    answer_map={'Numerator':'Selected equal parts','Denominator':'All equal parts','One half':'1 of 2 equal parts'}
    for label,answer in answer_map.items():
        widget=next(w for w in app.selectbox if w.label==label)
        widget.set_value(widget.options.index(answer))
    button(app,'Check my connections').click().run()
    assert_clean(app)
    assert any('3/3' in msg.value for msg in app.success)
    button(app,'Check what stuck').click().run()
    assert app.session_state['route']=='Practice'
    assert next(w for w in app.selectbox if w.label=='Concept').value=='fractions'
    app.sidebar.radio[0].set_value('Buddy Chat').run()
    button(app,'Show me an example').click().run()
    assert_clean(app)
    assert len(app.chat_message)==2
    assert any('Offline guided tutor' in msg.value for msg in app.caption)
    app.chat_input[0].set_value('Help me picture it').run()
    assert_clean(app)
    assert len(app.chat_message)==4
    app.sidebar.radio[0].set_value('Study plan').run()
    next(w for w in app.slider if w.label=='Daily XP goal').set_value(50)
    next(w for w in app.text_input if 'certification goal' in w.label).set_value('My learning certificate')
    app.text_area[0].set_value('Read syllabus\nPractise basics')
    button(app,'Save study plan').click().run()
    assert_clean(app)
    assert any(w.label=='Read syllabus' for w in app.checkbox)
    app.sidebar.radio[0].set_value('My learning').run()
    assert any('50 XP' in m.value for m in app.markdown)


def test_public_and_protected_routes(tmp_path,monkeypatch):
    monkeypatch.setenv('COGNIFY_DATABASE_URL','sqlite:///'+str(tmp_path/'routes.db'))
    for slug in ['login','signup','games']:
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30)
        app.query_params['page']=slug
        app.run()
        assert_clean(app)
        assert any(b.label=='Sign in' for b in app.button)
        assert not app.sidebar.radio
        if slug in ['login','signup']:
            assert not any(b.label=='Explore the demo' for b in app.button)

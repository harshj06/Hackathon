"""Run with: streamlit run app.py"""
import logging
import time
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from cognify.config import Settings
from cognify.db import make_engine, initialize, session_factory
from cognify.models import User
from cognify.services.accounts import register, login, visible_profiles
from cognify.services.demo import create_demo
from cognify.ui.style import theme, brand, hero, card, mascot
from cognify.ui import views, experience
from cognify.ui.routing import ROUTES, sync_route, route_changed, go
from cognify.adaptive import EXPERIENCES, NAVIGATION

st.set_page_config(page_title='Cognify · Learn with Buddy',page_icon='✦',layout='wide',initial_sidebar_state='expanded')
logging.basicConfig(level=logging.WARNING)

@st.cache_resource
def database(url, schema_revision=2):
    engine = make_engine(url)
    initialize(engine)
    return session_factory(engine)

settings = Settings.load()
factory = database(settings.database_url)
for key,value in [('font_size',17),('contrast',False),('reduce_motion',False)]:
    st.session_state.setdefault(key,value)


page_root = st.empty()

def sign_in(user):
    for key in ['profile_id','attempt_id','quiz_result','lesson','document_lesson','audio_cache','add_profile','game_id','game_celebration','focus_concept','query_seen','route']:
        st.session_state.pop(key,None)
    st.session_state.user_id = user.id
    st.session_state.last_active = time.time()
    page_root.empty()
    st.rerun()


def sign_out():
    st.session_state.clear()
    st.query_params.clear()


def authenticate(mode):
    try:
        with factory.begin() as session:
            if mode == 'login':
                user = login(session,st.session_state.login_username,st.session_state.login_password)
            else:
                if not st.session_state.register_adult:
                    raise ValueError('An adult account holder is required.')
                user = register(session,st.session_state.register_username,st.session_state.register_password,st.session_state.register_role)
        for key in ['profile_id','attempt_id','quiz_result','lesson','document_lesson','audio_cache','add_profile','game_id','game_celebration','focus_concept','query_seen','route']:
            st.session_state.pop(key,None)
        st.session_state.user_id = user.id
        st.session_state.last_active = time.time()
    except ValueError as exc:
        st.session_state.auth_error = str(exc)


def landing():
    theme(st.session_state.font_size,st.session_state.contrast,st.session_state.reduce_motion)
    brand()
    nav=st.columns([4,1,1])
    nav[0].caption('A LITTLE CURIOSITY GOES A LONG WAY')
    nav[1].link_button('Sign in','?page=login',use_container_width=True)
    nav[2].link_button('Get started','?page=signup',use_container_width=True)
    if st.query_params.get('page') not in ['login','signup']:
        left,right = st.columns([2,1])
        with left:
            hero('Big possibilities.\nOne little breakthrough.', 'Meet Buddy, your patient learning companion. Find the missing piece, explore it your way, and see understanding grow.', 'A LEARNING SPACE THAT GROWS WITH YOU')
        with right:
            mascot()
            st.markdown('**Curiosity belongs to everyone.**')
            st.caption('From first discoveries to professional skills.')
        columns = st.columns(3)
        for col,title,text,icon in zip(columns,
            ['Find your starting point','Make it click','See real progress'],
            ['Short checks uncover concept gaps without guessing what you know from your age.',
             'Explore an explanation, a visual prompt or a hands-on activity. Switch whenever it helps.',
             'Verify with new questions. Follow a learning path built from your own answers.'],['01 · DISCOVER','02 · UNDERSTAND','03 · GROW']):
            with col:
                card(title,text,icon)
        with st.expander('Try a 20-second discovery'):
            selected=st.slider('How many of four equal parts will you choose?',0,4,3,key='home_fraction')
            blocks=''.join(f'<span class="fraction-part {"filled" if i<selected else ""}"></span>' for i in range(4))
            st.markdown(f'<div class="playground"><div class="fraction-grid">{blocks}</div><strong>{selected}/4 of the whole</strong></div>',unsafe_allow_html=True)
            st.caption('Move the slider. The whole stays the same; your selected fraction changes.')
        with st.expander('Different learners. Different journeys.'):
            st.caption('Illustrative journeys, not customer testimonials. Explore their persisted synthetic records in the demo.')
            for col,title,description in zip(st.columns(3),['Pip · first discoveries','Alex · deeper connections','River · practical skills'],
                ['Count with visual groups, match pairs, and try a tiny challenge.',
                 'Check a concept gap, ask Buddy a question, and tackle a scenario.',
                 'Build a study rhythm and apply programming foundations to a personal goal.']):
                with col:
                    card(title,description,'EXAMPLE JOURNEY')
        if settings.allow_demo:
            if st.button('Explore the demo',type='primary',use_container_width=True):
                with st.spinner('Creating your private synthetic learning studio…'):
                    with factory.begin() as session:
                        user = create_demo(session)
                sign_in(user)
            st.caption('No API key needed. Five fictional learners, a parent-view preview, and a synthetic classroom. Demo data is separate from real accounts; demo never calls OpenAI.')
    else:
        st.link_button('← Back to home','?page=home')
        hero('Welcome back.' if st.query_params.get('page')=='login' else 'Your next discovery starts here.', 'A personal space to learn at your own pace.', 'COGNIFY')
    if st.query_params.get('page')=='signup':
        create_tab,sign_tab = st.tabs(['Create an account','Sign in'])
    else:
        sign_tab,create_tab = st.tabs(['Sign in','Create an account'])
    with sign_tab:
        with st.form('login'):
            username = st.text_input('Username',max_chars=40,key='login_username')
            password = st.text_input('Password',type='password',max_chars=128,key='login_password')
            st.form_submit_button('Sign in',type='primary',on_click=authenticate,args=('login',))
    with create_tab:
        st.caption('Accounts are for adults. A parent or guardian creates and manages learner profiles for anyone under 18. No email, real name or date of birth is collected.')
        with st.form('register'):
            username = st.text_input('Choose a username',max_chars=40,key='register_username')
            password = st.text_input('Choose a password',type='password',max_chars=128,key='register_password')
            role = st.selectbox('I am joining as',['learner','parent','educator'],format_func=lambda x:{'learner':'Adult / university learner','parent':'Parent / guardian','educator':'Educator'}[x],key='register_role')
            adult = st.checkbox('I am 18 or older; I will manage any child profiles as their parent or guardian',key='register_adult')
            st.form_submit_button('Create account',type='primary',on_click=authenticate,args=('register',))
    if st.session_state.get('auth_error'):
        st.error(st.session_state.pop('auth_error'))
    st.caption('Cognify is a local learning tool. Six reviewed starter concepts across mathematics, science and computing; document recall extends practice to your own sources.')


def workspace(user):
    if time.time()-st.session_state.get('last_active',0)>3600:
        st.session_state.clear()
        st.rerun()
    st.session_state.last_active = time.time()
    with factory() as session:
        profiles = visible_profiles(session,user.id)
    # Shared classroom profiles are read-only and appear only in the educator dashboard.
    owned = [p for p in profiles if p.owner_id==user.id]
    with st.sidebar:
        brand()
        st.caption('YOUR PERSONAL LEARNING SPACE')
        if user.demo:
            st.info('Synthetic demo · offline')
        if owned:
            prior = st.session_state.get('profile_id',owned[0].id)
            ids = [p.id for p in owned]
            selected = st.selectbox('Learning as',ids,index=ids.index(prior) if prior in ids else 0,
                format_func=lambda x:next(f'{p.nickname} · {p.age_group}' for p in owned if p.id==x))
            if selected != st.session_state.get('profile_id'):
                for key in ['attempt_id','quiz_result','lesson','document_lesson','audio_cache','game_id','game_celebration','focus_concept']:
                    st.session_state.pop(key,None)
            st.session_state.profile_id = selected
        menu = ['My learning','Learn','Buddy Chat','Practice','Games','Progress','Achievements','Study plan','Document lab','Profile','Settings']
        if user.role == 'parent' or user.demo:
            menu.append('Parent space')
        if user.role == 'educator':
            menu.append('Educator studio')
        active_profile = next((p for p in owned if p.id == st.session_state.get('profile_id')),None)
        labels = NAVIGATION.get(active_profile.age_group,{}) if active_profile else {}
        sync_route(menu)
        page = st.radio('Explore',menu,format_func=lambda value:labels.get(value,value),key='route',on_change=route_changed)
        st.divider()
        if st.button('Add learner profile',use_container_width=True):
            st.session_state.add_profile = True
        st.button('Sign out',use_container_width=True,on_click=sign_out)
        st.caption('Private by default. Progress is shared only through classroom enrollment. Sessions expire after one hour of inactivity.')
    profile = next((p for p in owned if p.id==st.session_state.get('profile_id')),None)
    exp = EXPERIENCES[profile.age_group] if profile else EXPERIENCES['18–24']
    theme(max(st.session_state.font_size,exp.font_size),st.session_state.contrast,st.session_state.reduce_motion,exp.accent)
    st.caption('COGNIFY / '+ROUTES[page].replace('-',' ').upper())
    if st.session_state.get('flash'):
        st.success(st.session_state.pop('flash'))
    if st.session_state.get('add_profile'):
        if st.button('Back to workspace'):
            st.session_state.add_profile = False
            st.rerun()
        views.profile_form(factory,user)
        return
    if page == 'Educator studio':
        views.educator_dashboard(factory,user)
        return
    if not profile:
        hero('A fresh start for a curious mind.', 'Tell Buddy a little about your goals. A diagnostic will establish your starting point.', 'WELCOME TO COGNIFY')
        views.profile_form(factory,user)
        return
    if page == 'My learning':
        experience.dashboard(factory,user,profile)
    elif page == 'Learn':
        experience.learn(factory,settings,user,profile)
    elif page == 'Games':
        experience.games(factory,user,profile)
    elif page == 'Buddy Chat':
        experience.chat(factory,settings,user,profile)
    elif page == 'Achievements':
        experience.achievements(factory,user,profile)
    elif page == 'Study plan':
        experience.study_plan(factory,user,profile)
    elif page == 'Profile':
        views.profile_form(factory,user,profile)
    elif page == 'Practice':
        views.practice(factory,settings,user,profile)
    elif page == 'Progress':
        views.progress(factory,user,profile)
    elif page == 'Document lab':
        views.document_learning(factory,settings,user,profile)
    elif page == 'Parent space':
        views.parent_dashboard(factory,user,profile)
    elif page == 'Settings':
        views.settings_view(factory,settings,user,profile)

with page_root.container():
    try:
        uid = st.session_state.get('user_id')
        with factory() as session:
            user = session.get(User,uid) if uid else None
        if user:
            workspace(user)
        else:
            landing()
    except (ValueError, SQLAlchemyError) as exc:
        logging.getLogger(__name__).warning('Application operation failed (%s)',type(exc).__name__)
        st.error(str(exc) if isinstance(exc,ValueError) else 'The local database operation could not be completed. Please retry. Check that the database folder is writable if the problem persists.')

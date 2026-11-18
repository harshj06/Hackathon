"""Stable query-string routes supported by Streamlit without a second web framework."""
import streamlit as st

ROUTES={'My learning':'dashboard','Learn':'learn','Buddy Chat':'buddy','Practice':'assessments',
        'Games':'games','Progress':'progress','Achievements':'achievements','Study plan':'study-plan',
        'Document lab':'documents','Parent space':'parent','Educator studio':'educator','Profile':'profile','Settings':'settings'}


def go(page,concept_id=None):
    if page not in ROUTES:
        raise ValueError('Unknown destination.')
    st.session_state.route=page
    slug=ROUTES[page]
    st.query_params['page']=slug
    st.session_state.query_seen=slug
    if concept_id:
        st.session_state.focus_concept=concept_id


def route_changed():
    go(st.session_state.route)


def sync_route(allowed):
    slug=st.query_params.get('page','dashboard')
    if slug!=st.session_state.get('query_seen'):
        page=next((key for key,value in ROUTES.items() if value==slug), 'My learning')
        st.session_state.route=page if page in allowed else 'My learning'
        st.session_state.query_seen=slug
    if st.session_state.get('route') not in allowed:
        st.session_state.route='My learning'

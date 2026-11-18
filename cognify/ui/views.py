import hashlib
from datetime import timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import select
from cognify.adaptive import EXPERIENCES, PREFERENCES, SUBJECTS, INTERESTS, CAREER_PATHS, display_choices
from cognify.models import Profile, Concept, Question, Assessment, Event, Classroom, Enrollment, Document, DocumentAttempt, now
from cognify.services.accounts import (ProfileInput, create_profile, update_profile, require_profile,
    visible_profiles, create_classroom, enroll, leave_classroom)
from cognify.services.learning import (build_path, start_assessment, submit_assessment, get_assessment,
    assessment_feedback, history, report)
from cognify.services.documents import upload_document, get_document, recall_questions, grade_recall
from cognify.services.buddy import BuddyService
from cognify.ui.style import hero, card, mascot
from cognify.ui.routing import go


def save_profile_callback(factory, user_id, profile_id, prefix):
    try:
        data = ProfileInput(**{field: st.session_state[prefix+field] for field in ProfileInput.model_fields})
        with factory.begin() as session:
            saved = update_profile(session,user_id,profile_id,data) if profile_id else create_profile(session,user_id,data)
            build_path(session,user_id,saved.id)
            st.session_state.profile_id = saved.id
        st.session_state.pop('lesson',None)
        st.session_state.flash = 'Your learning space is ready.'
        st.session_state.add_profile = False
    except ValueError as exc:
        st.session_state.profile_error = str(exc)


def profile_form(factory, user, profile=None):
    st.subheader('Shape your learning experience' if not profile else 'Your adaptive profile')
    st.caption('Use a nickname. Preferences can change; they are not a permanent learning-style label.')
    prefix = f'profile_{profile.id if profile else "new"}_'
    with st.form('profile_form'):
        left, right = st.columns(2)
        left.text_input('Learner nickname', value=profile.nickname if profile else '', max_chars=40,key=prefix+'nickname')
        age_choices = list(EXPERIENCES) if user.role == 'parent' or user.demo else ['18–24', '25+']
        right.selectbox('Age group', age_choices, index=age_choices.index(profile.age_group) if profile and profile.age_group in age_choices else 0,key=prefix+'age_group')
        left.text_input('Education level', value=profile.education if profile else '', max_chars=100, placeholder='For example: primary school or professional',key=prefix+'education')
        right.selectbox('Try this explanation format', PREFERENCES, index=PREFERENCES.index(profile.preference) if profile else 0,key=prefix+'preference')
        st.multiselect('Interests', INTERESTS, default=profile.interests if profile else [],key=prefix+'interests')
        st.multiselect('Subjects', SUBJECTS, default=profile.subjects if profile else ['Mathematics'],key=prefix+'subjects')
        st.text_area('What would you like to achieve?', value=profile.goals if profile else '', max_chars=500,key=prefix+'goals')
        st.checkbox('Allow online explanations and narration for this learner', value=profile.ai_enabled if profile else False,key=prefix+'ai_enabled')
        st.caption('When enabled and configured, OpenAI receives age-group guidance, interests, the selected lesson, and document excerpts only when you request them. Buddy Chat also sends your question and up to six recent messages in that concept thread. Names, assessment history and account details are not sent. Parents control this setting for children.')
        st.form_submit_button('Save profile' if profile else 'Create learning space',type='primary',
            on_click=save_profile_callback,args=(factory,user.id,profile.id if profile else None,prefix))
    if st.session_state.get('profile_error'):
        st.error(st.session_state.pop('profile_error'))


def overview(factory, user, profile):
    exp = EXPERIENCES[profile.age_group]
    hero(f'{profile.nickname}, {exp.greeting[0].lower() + exp.greeting[1:]}', exp.motivation, exp.label)
    with factory.begin() as session:
        rows = report(session, user.id, profile.id)
        attempts = history(session, user.id, profile.id)
        path = build_path(session, user.id, profile.id)
        concepts = {c.id:c for c in session.scalars(select(Concept))}
    a,b,c = st.columns(3)
    a.metric('Concepts mastered', sum(r['status'] == 'Mastered' for r in rows))
    b.metric('Completed checks', len(attempts))
    c.metric('Suggested session', f'{exp.plan_minutes} min')
    left, right = st.columns([1.65,1])
    with left:
        st.subheader('Your next steps')
        if not path:
            st.success('Your selected starter concepts are mastered. Use Practice for revision or add a subject in Settings.')
        for index,cid in enumerate(path[:5]):
            with st.container(border=True):
                st.markdown(f'**{index+1}. {concepts[cid].title}**')
                st.caption(f'{concepts[cid].subject} · Prerequisites first · {exp.plan_minutes} minute study block')
        st.caption('Unassessed concepts remain unassessed. Age never sets your starting score.')
    with right:
        mascot()
        if profile.age_group in ['5–8','9–12']:
            st.write(f'✦ {len(attempts)} discovery checks completed · {sum(r["status"] == "Mastered" for r in rows)} mastery stars')
        card('A small step is a real step', 'Open Practice to discover what is clear and what needs another explanation.', 'MEET BUDDY')
        st.markdown('**Your goal**')
        st.write(profile.goals)
        if profile.age_group in ['18–24','25+']:
            st.markdown('**Apply it to work or study**')
            st.write('For each concept, make one example related to your goal, explain the reasoning, and schedule a verification check in your next session.')
            track = st.selectbox('Choose an applied learning path',list(CAREER_PATHS))
            subject, outcome = CAREER_PATHS[track]
            st.caption(outcome)
            if st.button('Use this study path'):
                data = ProfileInput(**{field:getattr(profile,field) for field in ProfileInput.model_fields})
                data.subjects = [subject]
                data.goals = outcome
                with factory.begin() as session:
                    update_profile(session,user.id,profile.id,data)
                    build_path(session,user.id,profile.id)
                st.session_state.flash = 'Study path updated. Open Practice to begin.'
                st.rerun()



def show_lesson(factory, settings, user, profile, concept):
    st.subheader('A little help from Buddy')
    st.caption('Explanations support learning. Your quiz answers alone determine scores.')
    token = f'{profile.id}:{concept.id}'
    if st.button('Explain with Buddy', type='primary'):
        with st.spinner('Preparing your explanation…'):
            cached=st.session_state.get('lesson')
            result = cached[1] if cached and cached[0]==token else BuddyService(settings).explain(concept, profile, demo=user.demo)
        st.session_state.lesson = (token, result)
        with factory.begin() as session:
            require_profile(session, user.id, profile.id, write=True)
            session.add(Event(profile_id=profile.id, kind='Lesson', detail=f'Studied {concept.title} ({result.source}).'))
    saved = st.session_state.get('lesson')
    if not saved or saved[0] != token:
        st.info('Choose a concept and ask Buddy for a guided explanation. A curated lesson is available without an API key.')
        return
    result = saved[1]
    render_lesson(result, profile)
    with st.expander('See a concept illustration',expanded=profile.preference=='Visual'):
        concept_visual(concept.id)
    narration(settings, user, profile, result.lesson.explanation + '\n' + result.lesson.example)


def render_lesson(result, profile):
    st.caption(result.source)
    if result.notice:
        st.info(result.notice)
    lesson = result.lesson
    with st.container(border=True):
        st.subheader(lesson.title)
        st.text(lesson.explanation)
        st.markdown('**Worked example**')
        st.text(lesson.example)
        if profile.preference == 'Visual':
            st.markdown('**Picture it**')
            st.text(lesson.visual)
        elif profile.preference == 'Practical':
            st.markdown('**Try it offline**')
            st.text(lesson.activity)
        else:
            st.markdown('**Make a connection**')
            st.text(lesson.analogy)
        with st.expander('Explore other ways to learn'):
            st.text('Visual: ' + lesson.visual)
            st.text('Practical: ' + lesson.activity)
            st.text('Analogy: ' + lesson.analogy)
        for takeaway in lesson.takeaways:
            st.text('• ' + takeaway)
        st.markdown('**Think it through — unscored**')
        st.text(lesson.reflection)


def narration(settings, user, profile, text):
    st.caption('Optional voice is AI-generated, not a human recording.')
    key = hashlib.sha256(f'{profile.id}:{settings.tts_model}:{settings.voice}:{text}'.encode()).hexdigest()
    audio_cache = st.session_state.setdefault('audio_cache', {})
    if st.button('Listen to this explanation', key='voice_'+key, disabled=user.demo or not profile.ai_enabled or not settings.api_key):
        if key not in audio_cache:
            with st.spinner('Creating narration…'):
                data, error = BuddyService(settings).narrate(text)
            if data:
                if len(audio_cache) >= 5:
                    audio_cache.pop(next(iter(audio_cache)))
                audio_cache[key] = data
            else:
                st.warning(error)
    if key in audio_cache:
        st.audio(audio_cache[key], format='audio/mp3')
    elif user.demo or not settings.api_key or not profile.ai_enabled:
        st.caption('Text-only mode: voice becomes available with credentials and profile permission, outside demo mode.')


def practice(factory, settings, user, profile):
    hero('Understanding starts here.', 'A short check. A useful explanation. Another chance to make it click.', EXPERIENCES[profile.age_group].quiz_label)
    with factory() as session:
        focus=session.get(Concept,st.session_state.get('focus_concept',''))
    subject = st.selectbox('Subject', profile.subjects,index=profile.subjects.index(focus.subject) if focus and focus.subject in profile.subjects else 0)
    with factory() as session:
        concepts = list(session.scalars(select(Concept).where(Concept.subject == subject).order_by(Concept.id)))
    cid = st.selectbox('Concept', [c.id for c in concepts],index=[c.id for c in concepts].index(focus.id) if focus and focus.id in [c.id for c in concepts] else 0, format_func=lambda x: next(c.title for c in concepts if c.id==x))
    concept = next(c for c in concepts if c.id==cid)
    left,right = st.columns(2)
    for column,kind,label in [(left,'diagnostic','Start diagnostic'),(right,'verification','Verify understanding')]:
        if column.button(label, use_container_width=True):
            with factory.begin() as session:
                attempt = start_assessment(session, user.id, profile.id, cid, kind)
                st.session_state.attempt_id = attempt.id
            st.session_state.pop('quiz_result', None)
    aid = st.session_state.get('attempt_id')
    if aid:
        with factory() as session:
            attempt = get_assessment(session, user.id, aid)
            questions = [session.get(Question, qid) for qid in attempt.question_ids]
        if attempt.profile_id == profile.id and not attempt.completed_at:
            st.subheader(f'{attempt.kind.title()} · {len(questions)} questions')
            st.caption('Prerequisite checks are included when needed. Every question must be answered; there is no timer. Early learners see two choices, juniors three, and other learners four. Scores across these formats are not directly comparable.')
            with st.form(f'quiz_{aid}'):
                choices = {}
                for i,q in enumerate(questions):
                    choices[q.id] = st.radio(f'{i+1}. {q.prompt}', display_choices(q,profile.age_group),
                        format_func=lambda choice,q=q:q.options[choice], index=None, key=f'q_{aid}_{q.id}')
                if st.form_submit_button('Check my understanding', type='primary'):
                    try:
                        with factory.begin() as session:
                            submit_assessment(session, user.id, aid, choices)
                        st.session_state.quiz_result = aid
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
        elif attempt.profile_id == profile.id and attempt.completed_at:
            st.session_state.quiz_result = aid
    result_id = st.session_state.get('quiz_result')
    if result_id:
        with factory() as session:
            attempt = get_assessment(session, user.id, result_id)
            feedback = assessment_feedback(session, user.id, result_id)
        if attempt.profile_id == profile.id:
            st.success(f'{attempt.score:.0%} correct. Each answer helps us choose your next step.')
            st.button('Reinforce this with a game',on_click=go,args=('Games',cid))
            for answer,q in feedback:
                with st.expander(('✓ ' if answer.correct else '↻ ') + q.prompt):
                    st.write('Your answer: ' + q.options[answer.selected])
                    st.write('Correct answer: ' + q.options[q.correct])
                    st.write(q.explanation)
                    if answer.misconception:
                        st.info('Possible gap to explore: ' + answer.misconception)
            st.caption('Possible gaps are answer-based suggestions, not diagnoses. Mastery requires at least six distinct questions, including diagnostic and verification evidence, with 80% accuracy.')
    st.divider()
    show_lesson(factory, settings, user, profile, concept)


def progress(factory, user, profile, heading=True):
    if heading:
        hero('See what is taking shape.', 'Progress based on your answers, with room to keep growing.', 'LEARNING EVIDENCE')
    with factory() as session:
        rows = report(session, user.id, profile.id)
        attempts = history(session, user.id, profile.id)
        events = list(session.scalars(select(Event).where(Event.profile_id == profile.id).order_by(Event.created_at.desc()).limit(20)))
        docs = list(session.scalars(select(DocumentAttempt).where(DocumentAttempt.profile_id == profile.id)))
    if not rows:
        st.info('No assessment evidence yet. Complete a diagnostic in Practice to begin your progress record.')
        return
    df = pd.DataFrame(rows)
    st.plotly_chart(px.bar(df, x='mastery', y='concept', color='status', orientation='h', range_x=[0,100],
        color_discrete_map={'Mastered':'#35795D','Developing':'#7963CC','Needs practice':'#AE6F25'},
        labels={'mastery':'Latest distinct-question accuracy (%)','concept':'','status':'Evidence status'},
        template='plotly_white').update_layout(legend=dict(orientation='h',y=1.2),margin=dict(l=0,r=10,t=50,b=10)), use_container_width=True)
    st.dataframe(df.drop(columns='concept_id'), hide_index=True, use_container_width=True)
    st.download_button('Download progress CSV', df.to_csv(index=False).encode(), file_name='cognify-progress.csv', mime='text/csv')
    if len(attempts)>1:
        chart = pd.DataFrame([{'Check':i+1,'Accuracy':a.score*100,'Type':a.kind} for i,a in enumerate(attempts)])
        st.plotly_chart(px.line(chart,x='Check',y='Accuracy',markers=True,hover_data=['Type'],range_y=[0,100],template='plotly_white'),use_container_width=True)
        st.caption('Checks may cover different concepts and difficulty levels; this is assessment history, not a controlled measure of improvement.')
    with st.expander('Assessment history'):
        st.dataframe(pd.DataFrame([{'When (UTC)':a.completed_at,'Type':a.kind,'Questions':len(a.question_ids),'Correct (%)':round(a.score*100)} for a in attempts]),hide_index=True,use_container_width=True)
    if docs:
        st.write(f'Source recall: {sum(d.correct for d in docs)} exact words recalled across {sum(d.total for d in docs)} questions. Tracked separately from concept mastery.')
    from cognify.ui.experience import improvement
    improvement(factory,user,profile)
    with st.expander('Learning activity'):
        for event in events:
            st.write(f'{event.created_at:%d %b %H:%M} UTC · {event.detail}')


def parent_dashboard(factory, user, profile):
    if user.role != 'parent' and not user.demo:
        st.error('Parent access is required.')
        return
    hero(f'Growing with {profile.nickname}.', 'A clear view of practice, strengths and opportunities to learn together.', 'PARENT SPACE')
    with factory() as session:
        require_profile(session,user.id,profile.id,write=True)
        rows = report(session,user.id,profile.id)
        attempts = history(session,user.id,profile.id)
        recent = [a for a in attempts if a.completed_at >= now()-timedelta(days=7)]
        concept_map = {c.id:c for c in session.scalars(select(Concept))}
    from cognify.services.engagement import snapshot
    from cognify.ui.experience import reward_strip
    with factory() as session:
        reward_strip(snapshot(session,user.id,profile.id))
    st.subheader('This week')
    st.write(f'{len(recent)} completed checks in the last seven days. {sum(r["status"]=="Mastered" for r in rows)} concepts currently meet the mastery threshold.')
    strengths = [r['concept'] for r in rows if r['status']=='Mastered']
    st.write('Current strengths: ' + (', '.join(strengths) if strengths else 'Still gathering evidence. Celebrate effort and useful questions.'))
    gaps = [r for r in rows if r['status']!='Mastered']
    if recent:
        weekly=pd.DataFrame([{'When (UTC)':a.completed_at,'Check':a.kind,'Correct (%)':round(a.score*100)} for a in recent])
        st.download_button('Download weekly report',weekly.to_csv(index=False).encode(),file_name='cognify-weekly.csv',mime='text/csv')
    st.subheader('Try something together')
    for row in gaps[:3]:
        card(row['concept'],concept_map[row['concept_id']].lesson['activity'],'OFFLINE ACTIVITY')
    progress(factory,user,profile,heading=False)


def educator_dashboard(factory,user):
    if user.role != 'educator':
        st.error('Educator access is required.')
        return
    hero('A clearer picture of your class.', 'Find common gaps and plan the next useful lesson.', 'EDUCATOR STUDIO')
    with st.expander('Create a classroom'):
        with st.form('classroom'):
            name = st.text_input('Classroom name',max_chars=80)
            if st.form_submit_button('Create classroom'):
                try:
                    with factory.begin() as session:
                        create_classroom(session,user.id,name)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    with factory() as session:
        classes = list(session.scalars(select(Classroom).where(Classroom.educator_id==user.id)))
    if not classes:
        st.info('Create a classroom and share its code with learners or their parents. Records appear only after they join.')
        return
    selected = st.selectbox('Classroom',[c.id for c in classes],format_func=lambda x:next(c.name for c in classes if c.id==x))
    classroom = next(c for c in classes if c.id==selected)
    with st.expander('Invitation code'):
        st.code(classroom.invite,language=None)
        st.caption('Share this code privately. Joining authorizes this educator to view that learner’s profile and progress, but not uploaded documents.')
    with factory() as session:
        profiles = list(session.scalars(select(Profile).join(Enrollment,Enrollment.profile_id==Profile.id).where(Enrollment.classroom_id==selected)))
        all_rows = [{**r,'Learner':p.nickname,'profile_id':p.id} for p in profiles for r in report(session,user.id,p.id)]
    st.metric('Enrolled learners',len(profiles))
    if not all_rows:
        st.info('No assessment evidence yet. Enrolled learners need to complete a check.')
        return
    df = pd.DataFrame(all_rows)
    grouped = df.groupby('concept',as_index=False).agg(Accuracy=('mastery','mean'),Assessed=('profile_id','nunique'))
    st.plotly_chart(px.bar(grouped,x='concept',y='Accuracy',range_y=[0,100],hover_data=['Assessed'],template='plotly_white'),use_container_width=True)
    st.caption('Averages include only assessed learners; unassessed learners are not counted as zero. Choice count varies by age and difficulty varies by performance, so use these results for instructional planning, not cross-learner ranking.')
    st.subheader('Where another explanation could help')
    st.dataframe(df[df.status!='Mastered'][['Learner','concept','mastery','status']],hide_index=True,use_container_width=True)
    with st.expander('Plan the next mini-lesson'):
        common=df[df.status!='Mastered'].groupby('concept_id').size().sort_values(ascending=False).head(3)
        with factory() as session:
            for cid,count in common.items():
                concept=session.get(Concept,cid)
                st.markdown('**'+concept.title+'**')
                st.caption(f'{count} assessed learners may benefit from practice')
                st.write(concept.lesson['activity'])
    learner_id = st.selectbox('Individual progress',[p.id for p in profiles],format_func=lambda x:next(p.nickname for p in profiles if p.id==x))
    progress(factory,user,next(p for p in profiles if p.id==learner_id),heading=False)


def document_learning(factory,settings,user,profile):
    hero('Turn a page into a discovery.', 'Bring a source, explore its ideas, and check what you remember.', 'DOCUMENT LAB')
    st.caption('PDF or UTF-8 TXT · up to 5 MB, 40 PDF pages, 80,000 characters. Files stay in your local database; online explanations send only the first 12,000 characters when requested.')
    uploaded = st.file_uploader('Choose a learning document',type=['pdf','txt'])
    if st.button('Add document',disabled=uploaded is None):
        try:
            with factory.begin() as session:
                doc = upload_document(session,user.id,profile.id,uploaded.name,uploaded.getvalue())
            st.success(f'Added {doc.filename}.')
        except ValueError as exc:
            st.error(str(exc))
    with factory() as session:
        require_profile(session,user.id,profile.id,write=True)
        documents = list(session.scalars(select(Document).where(Document.profile_id==profile.id).order_by(Document.id.desc())))
    if not documents:
        st.info('Your document shelf is empty. Add a source to begin.')
        return
    doc_id = st.selectbox('Your document shelf',[d.id for d in documents],format_func=lambda x:next(d.filename for d in documents if d.id==x))
    with factory() as session:
        doc = get_document(session,user.id,doc_id)
        concept = session.get(Concept,'observation')
    from cognify.services.documents import source_summary,document_plan,complete_document_step
    with st.expander('Source highlights & learning mission',expanded=True):
        st.caption('Extractive summary · exact source sentences, not independently verified facts')
        for sentence in source_summary(doc.text):
            st.text(sentence)
        with factory.begin() as session:
            plan=document_plan(session,user.id,doc.id)
        st.progress(len(plan.completed)/len(plan.steps),text=f'{len(plan.completed)} of {len(plan.steps)} source steps complete')
        next_index=len(plan.completed)
        if next_index<len(plan.steps):
            step=plan.steps[next_index]
            st.write('**'+step['title']+'**')
            if step['evidence']:
                st.text(step['evidence'])
            else:
                st.caption('Complete the word-recall check below with every answer correct, then finish your path.')
            if st.button('Complete this source step',key=f'doc_step_{doc.id}_{next_index}'):
                try:
                    with factory.begin() as session:
                        complete_document_step(session,user.id,doc.id,next_index)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        else:
            st.success('Source mission complete · 15 XP earned once for this path.')
    st.subheader('Source evidence — exact extracted text')
    st.caption('Explanation and recall use the first 12,000 characters. Source claims have not been independently verified.')
    with st.expander('Read the source excerpt',expanded=False):
        st.text(doc.text[:12000])
    if st.button('Explain this excerpt with Buddy'):
        with st.spinner('Preparing a source-based study guide…'):
            result = BuddyService(settings).explain(concept,profile,document_text=doc.text,demo=user.demo)
        st.session_state.document_lesson = (profile.id,doc.id,result)
    saved = st.session_state.get('document_lesson')
    if saved and saved[:2]==(profile.id,doc.id):
        st.subheader('Study guide — separate from source evidence')
        render_lesson(saved[2],profile)
        narration(settings,user,profile,saved[2].lesson.explanation)
    questions = recall_questions(doc.text)
    st.subheader('Source recall check')
    st.caption('Type the missing word exactly as it appears in the source (case does not matter). This checks recall, not concept mastery or whether the source is true.')
    if not questions:
        st.info('No suitable English sentences for automatic word-recall questions. Try a document with complete sentences; the source reader still works.')
        return
    with st.form(f'recall_{doc.id}'):
        responses = [st.text_input(q['prompt'],max_chars=100,key=f'doc{doc.id}_{i}') for i,q in enumerate(questions)]
        if st.form_submit_button('Check source recall'):
            try:
                with factory.begin() as session:
                    flags,qs = grade_recall(session,user.id,doc.id,responses)
                st.success(f'{sum(flags)}/{len(flags)} exact source words recalled.')
                for flag,q in zip(flags,qs):
                    st.write(('✓ ' if flag else '↻ ') + q['answer'] + ' — ' + q['evidence'])
            except ValueError as exc:
                st.error(str(exc))


def settings_view(factory,settings,user,profile):
    hero('Make this space yours.', 'Choose how you learn and who can see your progress.', 'SETTINGS & ACCESSIBILITY')
    left,right = st.columns(2)
    left.slider('Text size',16,24,key='font_size')
    right.checkbox('High contrast',key='contrast')
    right.checkbox('Reduce animation',key='reduce_motion')
    st.caption('Accessibility changes apply on the next interaction and last for this browser session.')
    profile_form(factory,user,profile)
    st.subheader('Classroom sharing')
    with st.form('join_class'):
        invite = st.text_input('Classroom invitation code',max_chars=64)
        consent = st.checkbox('Share this learner’s profile and progress with the classroom educator')
        if st.form_submit_button('Join classroom'):
            if not consent:
                st.error('Confirm sharing before joining.')
            else:
                try:
                    with factory.begin() as session:
                        classroom = enroll(session,user.id,profile.id,invite)
                    st.success(f'Joined {classroom.name}.')
                except ValueError as exc:
                    st.error(str(exc))
    with factory() as session:
        classes = list(session.scalars(select(Classroom).join(Enrollment).where(Enrollment.profile_id==profile.id)))
    for classroom in classes:
        st.write(classroom.name)
        if st.button('Leave classroom',key=f'leave_{classroom.id}'):
            with factory.begin() as session:
                leave_classroom(session,user.id,profile.id,classroom.id)
            st.rerun()
    st.subheader('Connection status')
    if settings.credential_error:
        st.warning(settings.credential_error)
    st.write('API key: configured' if settings.api_key else 'API key: blank — offline lessons available')
    st.caption('Keys are configured in the server environment, never entered into this interface.')
    if st.button('Check API connection',disabled=user.demo):
        with st.spinner('Checking the configured model…'):
            ok,message = BuddyService(settings).connectivity()
        (st.success if ok else st.warning)(message)


def concept_visual(concept_id):
    """Illustrations are curricular examples, never learner analytics."""
    st.caption('Teaching illustration · a worked example, not learner or experimental data')
    if concept_id == 'fractions':
        fig = px.pie(names=['Selected','Remaining'],values=[3,1],color=['Selected','Remaining'],
            color_discrete_map={'Selected':'#7963CC','Remaining':'#E4E2ED'},hole=.45)
        fig.update_layout(annotations=[dict(text='3 / 4',x=.5,y=.5,font_size=26,showarrow=False)],height=300,margin=dict(t=0,b=0,l=0,r=0))
        st.plotly_chart(fig,use_container_width=True)
        st.write('Three of four equal parts are selected.')
    elif concept_id == 'addition':
        a,b,c=st.columns(3)
        a.markdown('### ● ● ●')
        a.caption('First group: 3')
        b.markdown('### + ● ●')
        b.caption('Second group: 2')
        c.markdown('### = 5')
        c.caption('Combined quantity')
    elif concept_id == 'loops':
        st.code('repeat 4 times:\n    draw ● ●\n\n● ● | ● ● | ● ● | ● ●\n4 groups × 2 dots = 8 dots',language=None)
    elif concept_id == 'sequence':
        st.code('OPEN EDITOR  →  WRITE TEXT  →  SAVE FILE',language=None)
        st.write('Each step prepares what the next step needs.')
    elif concept_id == 'observation':
        a,b=st.columns(2)
        with a:
            card('Observation','The plant measures 12 cm.','MEASURE')
        with b:
            card('Explanation to test','Light may have influenced its growth.','INVESTIGATE')
    elif concept_id == 'experiments':
        st.dataframe(pd.DataFrame({'Condition':['Plant type','Water amount','Light'],
            'Group A':['Same','Same','Less'],'Group B':['Same','Same','More']}),hide_index=True,use_container_width=True)
        st.write('Change light; keep other conditions alike. Measure growth in both groups.')

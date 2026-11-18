'use client';
import {useEffect,useState} from 'react';
import {request} from './learning-space';
type Draft={id:string;status:string;pack:{title:string;lesson:string;activity:string;questions:{prompt:string;options:string[];correct:number;hint:string;explanation:string}[];sequence:string[];pairs:[string,string][]}};
export default function ReviewQueue(){
 const [drafts,setDrafts]=useState<Draft[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false),[confirmed,setConfirmed]=useState<Record<string,boolean>>({});
 const refresh=()=>request<Draft[]>('/admin/reviews').then(setDrafts);
 useEffect(()=>{refresh().catch(e=>setError(e.message))},[]);
 async function decide(id:string,decision:string){setBusy(true);setError('');try{await request('/admin/reviews/'+id+'/'+decision,{});await refresh()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <section><h1>Content review</h1><p>Check factual accuracy, age suitability, answer keys, hints and practical safety before publishing. Schema checks do not establish correctness.</p>{error&&<p role="alert" className="error">{error}</p>}{!drafts.length&&<p>No drafts awaiting review.</p>}{drafts.map(d=><article key={d.id}><h2>{d.pack.title}</h2><p>{d.pack.lesson}</p><p>Activity: {d.pack.activity}</p>{d.pack.questions.map((q,i)=><details key={i}><summary>{q.prompt}</summary><p>Answer: {q.options[q.correct]}</p><p>Options: {q.options.join(' · ')}</p><p>Hint: {q.hint}</p><p>{q.explanation}</p></details>)}<p>Sequence: {d.pack.sequence.join(' → ')}</p><p>Pairs: {d.pack.pairs.map(p=>p.join(' = ')).join(' · ')}</p><label className="check"><input type="checkbox" checked={!!confirmed[d.id]} onChange={e=>setConfirmed({...confirmed,[d.id]:e.target.checked})}/>I reviewed the content, answer keys and activity safety.</label><div className="actions"><button disabled={busy||!confirmed[d.id]} onClick={()=>decide(d.id,'publish')}>Publish reviewed pack</button><button disabled={busy} onClick={()=>decide(d.id,'reject')}>Reject draft</button></div></article>)}</section>
}

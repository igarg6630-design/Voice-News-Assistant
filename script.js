const CATS={sports:"sports",business:"business",technology:"technology",tech:"technology",health:"health",entertainment:"entertainment",science:"science"};
const FILLER=["my topic is","tell me about","news about","news on","i want to know about","search for","about","latest","news","please"];
const STOP=["stop","enough","cancel","quiet","exit"];
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const cap=s=>s[0].toUpperCase()+s.slice(1);
let hist=[];try{hist=JSON.parse(localStorage.getItem("vn_hist")||"[]")}catch(e){}
let session=0,rec=null,listening=false,arts=[],rate=1,mode="idle";
const synth=window.speechSynthesis,SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 
/* ----- waveform ----- */
const cv=$("wave"),ctx=cv.getContext("2d"),orb=$("orb");
let amp=.1,target=.1,t=0;
function resize(){const r=devicePixelRatio||1;cv.width=cv.clientWidth*r;cv.height=cv.clientHeight*r;ctx.setTransform(r,0,0,r,0,0)}
addEventListener("resize",resize);
function frame(){
  t+=.04;amp+=(target-amp)*.07;
  const w=cv.clientWidth,h=cv.clientHeight,mid=h/2;
  ctx.clearRect(0,0,w,h);ctx.beginPath();ctx.lineWidth=1.7;ctx.strokeStyle="#7f62ff";ctx.shadowColor="#6c4cff";ctx.shadowBlur=12;ctx.lineJoin="round";
  for(let x=0;x<=w;x+=3){
    const k=x/w;
    const env=.3+.7*Math.pow(Math.abs(Math.sin(k*Math.PI*6+Math.sin(t*.5))),1.5);
    const a=Math.sin(x*.085+t*3.2)*Math.sin(x*.021-t*1.4);
    const n=Math.sign(a)*Math.pow(Math.abs(a),.7)+.35*Math.sin(x*.23+t*5);
    const y=mid+n*env*amp*h*.48;
    x?ctx.lineTo(x,y):ctx.moveTo(x,y);
  }
  ctx.stroke();
  orb.style.transform=`scale(${1+amp*.7+Math.sin(t*2)*.03})`;
  requestAnimationFrame(frame);
}
function setMode(m){mode=m;target={idle:.1,listen:.75,speak:.6}[m];$("stopTop").classList.toggle("show",m==="speak");$("mic").classList.toggle("listening",m==="listen")}
setInterval(()=>{if(mode==="listen")target=.45+Math.random()*.5;else if(mode==="speak")target=.4+Math.random()*.4},180);
 
/* ----- text ----- */
function say(txt,dim){const el=$("text");el.textContent=txt;el.classList.toggle("dim",!!dim)}
 
/* ----- history ----- */
function saveHist(label,params){
  hist=hist.filter(h=>h.label!==label);
  hist.unshift({label,params,time:new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})});
  hist=hist.slice(0,25);try{localStorage.setItem("vn_hist",JSON.stringify(hist))}catch(e){}renderHist();
}
function renderHist(){
  $("history").innerHTML=hist.length?hist.map((h,i)=>`<li tabindex="0" data-i="${i}"><span class="t">${esc(h.label)}</span><span class="m">${esc(h.time)}</span></li>`).join(""):'<div class="none">Abhi kuch nahi. Pehli news sunne ke baad yahan dikhegi.</div>';
}
const openH=e=>{const li=e.target.closest("li");if(li){const h=hist[li.dataset.i];closePanels();loadNews(h.params,h.label)}};
$("history").addEventListener("click",openH);
$("history").addEventListener("keydown",e=>{if(e.key==="Enter")openH(e)});
$("clear").onclick=()=>{hist=[];try{localStorage.removeItem("vn_hist")}catch(e){}renderHist()};
function closePanels(){$("drawer").classList.remove("show");$("set").classList.remove("show");$("scrim").classList.remove("show")}
$("menu").onclick=()=>{$("drawer").classList.add("show");$("scrim").classList.add("show")};
$("scrim").onclick=closePanels;
$("gear").onclick=()=>{const s=$("set");s.classList.toggle("show");$("scrim").classList.toggle("show",s.classList.contains("show"))};
$("rate").oninput=e=>{rate=+e.target.value;$("rv").textContent=rate.toFixed(1)+"x"};
$("chev").onclick=()=>document.body.classList.toggle("open");
 
/* ----- speech out ----- */
function stopSpeaking(){session++;synth.cancel();if(mode==="speak")setMode("idle")}
function speak(text){return new Promise(res=>{
  const u=new SpeechSynthesisUtterance(text);u.lang="en-IN";u.rate=rate;
  const vs=synth.getVoices(),v=vs.find(v=>/en-IN/i.test(v.lang))||vs.find(v=>v.lang.startsWith("en"));
  if(v)u.voice=v;u.onend=u.onerror=()=>res();synth.speak(u);})}
const speakPlain=t=>{setMode("speak");return speak(t).then(()=>setMode("idle"))};
 
/* ----- news ----- */
function showStory(i){
  const a=arts[i];
  $("cur").innerHTML=`<div class="k">Story ${i+1} of ${arts.length}</div><h2>${esc(a.title)}</h2>${a.description?`<p>${esc(a.description)}</p>`:""}<div class="s">${esc(a.source||"")}${a.url?` · <a href="${esc(a.url)}" target="_blank" rel="noopener">Full story</a>`:""}</div>`;
  document.querySelectorAll(".card").forEach((c,j)=>c.classList.toggle("now",j===i));
  document.querySelectorAll(".card")[i]?.scrollIntoView({block:"nearest",inline:"nearest",behavior:"smooth"});
}
$("list").addEventListener("click",e=>{const c=e.target.closest(".card");if(c)readFrom(+c.dataset.i)});
$("list").addEventListener("keydown",e=>{if(e.key==="Enter"){const c=e.target.closest(".card");if(c)readFrom(+c.dataset.i)}});
 
const API_BASE = "http://127.0.0.1:5000";
 
async function loadNews(params, label) {
    stopSpeaking();
    const my = session;
 
    say("Fetching " + label + "…", true);
 
    try {
        // Flask backend ko request bhejo
        const response = await fetch(
            `${API_BASE}/api/news?${new URLSearchParams(params)}`
        );
 
        // Server response validate karo
        const d = await response.json();
 
        if (my !== session) return;
 
        if (!response.ok) {
            throw new Error(
                d.error || `Backend error: ${response.status}`
            );
        }
 
        if (d.error) {
            say(d.error);
            await speakPlain("Sorry. " + d.error);
            return;
        }
 
        // Backend se articles array milni chahiye
        if (!Array.isArray(d.articles)) {
            throw new Error(
                "Backend response mein articles array nahi mili."
            );
        }
 
        if (d.articles.length === 0) {
            say("Is topic pe koi khabar nahi mili. Doosra topic try karo.");
            await speakPlain("Sorry, no news was found for this topic.");
            return;
        }
 
        // News ko existing frontend state mein save karo
        arts = d.articles;
        saveHist(label, params);
 
        // News list display karo
        $("list").innerHTML = arts.map((a, i) => `
            <div class="card" tabindex="0" data-i="${i}">
                <small>${esc(a.source || "News")}</small>
                ${esc(a.title || "Untitled news")}
            </div>
        `).join("");
 
        document.body.classList.add("open");
        say(label);
 
        // Pehli news se reading start karo
        readFrom(0);
 
    } catch (e) {
        if (my !== session) return;
 
        console.error("Backend connection error:", e);
 
        const message =
            e instanceof TypeError
                ? "Flask server connect nahi hua. Check karo ki port 5000 par server running hai."
                : e.message;
 
        say(message);
        await speakPlain(message);
    }
}
async function readFrom(start){
  stopSpeaking();const my=session;setMode("speak");
  for(let i=start;i<arts.length;i++){
    if(my!==session)return;
    showStory(i);
    await speak(`News ${i+1}. ${arts[i].title}. ${arts[i].description||""}`);
  }
  if(my===session){setMode("idle");await speak("That was the latest news.")}
}
 
/* ----- commands ----- */
function clean(c){FILLER.forEach(f=>c=c.split(f).join(" "));return c.split(/\s+/).filter(Boolean).join(" ")}
function handle(cmd){
  cmd=(cmd||"").toLowerCase().trim();if(!cmd)return;say(cmd);
  if(STOP.some(w=>cmd.includes(w))||/quit|goodbye/.test(cmd)){stopSpeaking();return speakPlain("Okay. Stopped.")}
  for(const w in CATS)if(cmd.includes(w))return loadNews({category:CATS[w]},cap(CATS[w])+" news");
  const q=clean(cmd);q?loadNews({q},"“"+q+"”"):loadNews({},"Top headlines");
}
 
/* ----- mic + edit ----- */
function toggleMic(){
  if(!SR){say("Voice ke liye Chrome ya Edge use karo, ya Edit se type karo.");return}
  if(listening){rec.stop();return}
  stopSpeaking();rec=new SR();rec.lang="en-IN";rec.interimResults=true;let final="";
  rec.onstart=()=>{listening=true;setMode("listen");say("Listening…",true)};
  rec.onresult=e=>{let s="";for(const r of e.results){s+=r[0].transcript;if(r.isFinal)final=s}say(s)};
  rec.onerror=e=>say(e.error==="not-allowed"?"Mic permission allow karo.":e.error==="no-speech"?"Kuch sunai nahi diya, phir try karo.":"Mic error: "+e.error,true);
  rec.onend=()=>{listening=false;setMode("idle");if(final)handle(final)};
  rec.start();
}
$("mic").onclick=toggleMic;
$("edit").onclick=()=>{
  const b=$("editbox"),cur=$("text").classList.contains("dim")?"":$("text").textContent;
  $("text").style.display="none";b.style.display="block";b.value=cur;b.focus();
};
function endEdit(){$("editbox").style.display="none";$("text").style.display=""}
$("editbox").addEventListener("keydown",e=>{
  if(e.key==="Enter"){const v=$("editbox").value;endEdit();handle(v)}
  if(e.key==="Escape"){endEdit()}
});
$("editbox").addEventListener("blur",endEdit);
$("stopTop").onclick=()=>{stopSpeaking();setMode("idle")};
$("home").onclick=()=>{stopSpeaking();setMode("idle");document.body.classList.remove("open");say("Say “news”, “cricket” or “tell me about Tesla”",true)};
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&document.activeElement.id!=="editbox"){stopSpeaking();closePanels()}});
 
resize();frame();renderHist();synth.getVoices();
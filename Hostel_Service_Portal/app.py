import streamlit as st, sqlite3, hashlib, os, hmac
from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Hostel Service Portal", page_icon="🏠", layout="wide")
DB=Path(__file__).with_name("hostel_portal.db")
CATS=["Water Cooler","Switch / Regulator","Fan","Tube Light","Furniture","Cleanliness"]
STATUSES=["Submitted","Under Review","Assigned","In Progress","Resolved","Closed","Rejected"]
PRIORITIES=["Low","Normal","High","Urgent"]

def con():
    c=sqlite3.connect(DB,check_same_thread=False); c.row_factory=sqlite3.Row; return c
def hp(p,s=None):
    s=s or os.urandom(16); return s.hex()+"$"+hashlib.pbkdf2_hmac("sha256",p.encode(),s,180000).hex()
def verify(p,stored):
    try:
        s,h=stored.split("$"); return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256",p.encode(),bytes.fromhex(s),180000).hex(),h)
    except: return False
def init():
    now=datetime.now().isoformat(timespec="seconds")
    with con() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE COLLATE NOCASE, password TEXT, role TEXT, roll TEXT, block TEXT, room TEXT);
        CREATE TABLE IF NOT EXISTS complaints(id INTEGER PRIMARY KEY, student_id INTEGER REFERENCES users(id), category TEXT, location TEXT, description TEXT, priority TEXT, status TEXT, assigned TEXT, supervisor_note TEXT, resolution TEXT, created TEXT, updated TEXT);
        CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, complaint_id INTEGER, actor TEXT, action TEXT, note TEXT, created TEXT);
        """)
        if not c.execute("SELECT 1 FROM users WHERE email='warden@hostel.local'").fetchone():
            c.execute("INSERT INTO users(name,email,password,role,roll,block,room) VALUES(?,?,?,?,?,?,?)",("Demo Warden","warden@hostel.local",hp("Warden@123"),"warden","","",""))
        if not c.execute("SELECT 1 FROM users WHERE email='student@hostel.local'").fetchone():
            uid=c.execute("INSERT INTO users(name,email,password,role,roll,block,room) VALUES(?,?,?,?,?,?,?)",("Demo Student","student@hostel.local",hp("Student@123"),"student","DEMO001","A Block","101")).lastrowid
            samples=[("Water Cooler","A Block, Ground Floor","Water cooler is not cooling","High","Submitted"),("Fan","A Block, Room 101","Ceiling fan makes noise","Normal","In Progress"),("Cleanliness","A Block, Washroom","Washroom needs cleaning","High","Resolved")]
            for cat,loc,desc,pri,status in samples:
                cur=c.execute("INSERT INTO complaints(student_id,category,location,description,priority,status,created,updated) VALUES(?,?,?,?,?,?,?,?)",(uid,cat,loc,desc,pri,status,now,now))
                c.execute("INSERT INTO history(complaint_id,actor,action,note,created) VALUES(?,?,?,?,?)",(cur.lastrowid,"student@hostel.local","Complaint submitted","Synthetic demo record",now))
def user_by_email(email):
    with con() as c:
        r=c.execute("SELECT * FROM users WHERE email=?",(email.strip(),)).fetchone(); return dict(r) if r else None
def register(name,email,pw,roll,block,room):
    with con() as c: c.execute("INSERT INTO users(name,email,password,role,roll,block,room) VALUES(?,?,?,?,?,?,?)",(name,email.lower(),hp(pw),"student",roll,block,room))
def complaints(uid=None):
    q="""SELECT x.*,u.name,u.email,u.roll,u.block,u.room FROM complaints x JOIN users u ON x.student_id=u.id"""
    args=()
    if uid is not None: q+=" WHERE x.student_id=?"; args=(uid,)
    q+=" ORDER BY x.created DESC"
    with con() as c: return [dict(r) for r in c.execute(q,args).fetchall()]
def history(cid=None):
    q="SELECT h.*,x.category FROM history h JOIN complaints x ON x.id=h.complaint_id"; args=()
    if cid is not None: q+=" WHERE h.complaint_id=?"; args=(cid,)
    q+=" ORDER BY h.created DESC"
    with con() as c: return [dict(r) for r in c.execute(q,args).fetchall()]
def submit(u,cat,loc,desc,pri):
    now=datetime.now().isoformat(timespec="seconds")
    with con() as c:
        cur=c.execute("INSERT INTO complaints(student_id,category,location,description,priority,status,created,updated) VALUES(?,?,?,?,?,?,?,?)",(u["id"],cat,loc,desc,pri,"Submitted",now,now))
        cid=cur.lastrowid; c.execute("INSERT INTO history(complaint_id,actor,action,note,created) VALUES(?,?,?,?,?)",(cid,u["email"],"Complaint submitted","Sent to supervisor queue",now)); return cid
def update(cid,status,assigned,note,resolution,email):
    now=datetime.now().isoformat(timespec="seconds")
    with con() as c:
        old=c.execute("SELECT status FROM complaints WHERE id=?",(cid,)).fetchone()
        c.execute("UPDATE complaints SET status=?,assigned=?,supervisor_note=?,resolution=?,updated=? WHERE id=?",(status,assigned,note,resolution,now,cid))
        c.execute("INSERT INTO history(complaint_id,actor,action,note,created) VALUES(?,?,?,?,?)",(cid,email,f"Status: {old['status']} → {status}",(note+" "+resolution).strip(),now))
def css():
    st.markdown("""<style>.stApp{background:#f5f8fc} section[data-testid="stSidebar"]{background:#eaf1f8}.hero{background:linear-gradient(110deg,#173a5e,#147d88);color:white;padding:1.2rem 1.5rem;border-radius:16px;margin-bottom:1rem}.hero h1{margin:0;font-size:2rem}.hero p{margin:.4rem 0 0;opacity:.9} div[data-testid="stMetric"]{background:white;border:1px solid #dfe7ef;padding:.8rem;border-radius:12px}</style>""",unsafe_allow_html=True)
def login():
    css(); st.markdown('<div class="hero"><h1>🏠 Hostel Service Portal</h1><p>Report maintenance problems and track resolution.</p></div>',unsafe_allow_html=True)
    a,b=st.tabs(["🎓 Student Login","🛡️ Supervisor / Warden Login"])
    with a:
        x,y=st.columns(2)
        with x:
            with st.form("slogin"):
                e=st.text_input("Student email"); p=st.text_input("Password",type="password"); go=st.form_submit_button("Login as Student")
            if go:
                u=user_by_email(e)
                if u and u["role"]=="student" and verify(p,u["password"]):
                    st.session_state.user=u; st.rerun()
                else: st.error("Invalid student email or password.")
        with y:
            st.subheader("Create student account")
            with st.form("register"):
                n=st.text_input("Full name"); re=st.text_input("Email"); roll=st.text_input("Roll number")
                block=st.selectbox("Hostel block",["A Block","B Block","C Block","D Block","Other"]); room=st.text_input("Room number")
                p1=st.text_input("Create password",type="password"); p2=st.text_input("Confirm password",type="password")
                rg=st.form_submit_button("Register")
            if rg:
                if not all([n.strip(),re.strip(),roll.strip(),room.strip(),p1]): st.error("Complete all fields.")
                elif "@" not in re or len(p1)<8 or p1!=p2: st.error("Check email, use 8+ characters and make passwords match.")
                elif user_by_email(re): st.error("Email already registered.")
                else:
                    try: register(n.strip(),re.strip(),p1,roll.strip(),block,room.strip()); st.success("Account created. Log in now.")
                    except: st.error("Registration failed.")
    with b:
        st.info("Warden accounts are provisioned by the administrator; students cannot register as wardens.")
        with st.form("wlogin"):
            e=st.text_input("Warden email"); p=st.text_input("Password",type="password"); go=st.form_submit_button("Login as Warden")
        if go:
            u=user_by_email(e)
            if u and u["role"]=="warden" and verify(p,u["password"]): st.session_state.user=u; st.rerun()
            else: st.error("Invalid warden email or password.")
    with st.expander("Demo credentials"):
        st.write("Student: `student@hostel.local` / `Student@123`")
        st.write("Warden: `warden@hostel.local` / `Warden@123`")
def student_page(u):
    css(); st.markdown(f'<div class="hero"><h1>Student Dashboard</h1><p>{u["name"]} · {u["block"]} · Room {u["room"]}</p></div>',unsafe_allow_html=True)
    rows=complaints(u["id"]); a,b,c=st.columns(3)
    a.metric("My complaints",len(rows)); b.metric("Active",sum(r["status"] not in ["Closed","Rejected"] for r in rows)); c.metric("Resolved / closed",sum(r["status"] in ["Resolved","Closed"] for r in rows))
    t1,t2,t3=st.tabs(["➕ Raise complaint","📋 My complaints","🕘 How it works"])
    with t1:
        with st.form("new"):
            cat=st.selectbox("Complaint type",CATS); loc=st.text_input("Location",value=f'{u["block"]}, Room {u["room"]}')
            pri=st.selectbox("Priority",PRIORITIES,index=1); desc=st.text_area("Describe the issue")
            ok=st.checkbox("Details are correct"); go=st.form_submit_button("Submit complaint",type="primary")
        if go:
            if not loc.strip() or not desc.strip(): st.error("Location and description are required.")
            elif not ok: st.error("Please confirm details.")
            else:
                cid=submit(u,cat,loc,desc,pri); st.success(f"Complaint HSP-{cid:05d} submitted and sent to the Warden."); st.rerun()
    with t2:
        if rows:
            df=pd.DataFrame(rows); st.dataframe(df[["id","category","location","priority","status","assigned","supervisor_note","resolution","created","updated"]].rename(columns={"id":"Complaint ID","category":"Type","location":"Location","priority":"Priority","status":"Status","assigned":"Assigned staff","supervisor_note":"Warden update","resolution":"Resolution","created":"Submitted","updated":"Updated"}),use_container_width=True,hide_index=True)
            cid=st.selectbox("Select complaint history",[r["id"] for r in rows],format_func=lambda x:f"HSP-{x:05d}")
            hist=history(cid)
            if hist: st.dataframe(pd.DataFrame(hist)[["action","note","actor","created"]],use_container_width=True,hide_index=True)
            selected=next(r for r in rows if r["id"]==cid)
            if selected["status"]=="Resolved" and st.button("Issue is not fixed — reopen"):
                update(cid,"Submitted",selected["assigned"] or "", "Student requested reopening","",u["email"]); st.rerun()
        else: st.info("No complaints yet.")
    with t3:
        st.markdown("**Submit → Warden reviews → Maintenance staff assigned → Work in progress → Resolved → Warden closes.**")
        st.caption("You can view only complaints submitted by your account.")
def warden_page(u):
    css(); st.markdown('<div class="hero"><h1>Supervisor / Warden Portal</h1><p>Review, assign and monitor all hostel maintenance complaints.</p></div>',unsafe_allow_html=True)
    rows=complaints(); a,b,c,d=st.columns(4)
    a.metric("Total",len(rows)); b.metric("Awaiting review",sum(r["status"]=="Submitted" for r in rows)); c.metric("Active",sum(r["status"] not in ["Closed","Rejected"] for r in rows)); d.metric("Resolved / closed",sum(r["status"] in ["Resolved","Closed"] for r in rows))
    t1,t2,t3=st.tabs(["🗂️ Complaint queue","📊 Analytics","🕘 Activity history"])
    with t1:
        sf=st.selectbox("Filter status",["All"]+STATUSES); cf=st.selectbox("Filter complaint type",["All"]+CATS)
        filtered=[r for r in rows if (sf=="All" or r["status"]==sf) and (cf=="All" or r["category"]==cf)]
        if filtered:
            df=pd.DataFrame(filtered); st.dataframe(df[["id","name","roll","block","room","category","location","priority","status","assigned","created"]].rename(columns={"id":"ID","name":"Student","roll":"Roll no.","block":"Block","room":"Room","category":"Type","location":"Location","priority":"Priority","status":"Status","assigned":"Assigned staff","created":"Submitted"}),use_container_width=True,hide_index=True)
            cid=st.selectbox("Manage complaint",[r["id"] for r in filtered],format_func=lambda x:f"HSP-{x:05d} · "+next(r["category"]+" / "+r["name"] for r in filtered if r["id"]==x))
            r=next(r for r in rows if r["id"]==cid)
            x,y=st.columns(2)
            with x:
                st.write("**Student:**",r["name"],"(",r["email"],")"); st.write("**Hostel / Room:**",r["block"],"/",r["room"])
                st.write("**Location:**",r["location"]); st.write("**Description:**",r["description"]); st.write("**Priority:**",r["priority"])
            with y:
                with st.form("update"):
                    assigned=st.text_input("Assign to maintenance staff",value=r["assigned"] or "",placeholder="Electrician / Plumber / Housekeeping")
                    status=st.selectbox("Status",STATUSES,index=STATUSES.index(r["status"]))
                    note=st.text_area("Warden update / instruction",value=r["supervisor_note"] or "")
                    resolution=st.text_area("Resolution note",value=r["resolution"] or "")
                    save=st.form_submit_button("Save update",type="primary")
                if save:
                    if status in ["Assigned","In Progress"] and not assigned.strip(): st.error("Enter the staff member before assigning.")
                    elif status in ["Resolved","Closed"] and not resolution.strip(): st.error("Enter resolution details before resolving or closing.")
                    else:
                        update(cid,status,assigned.strip(),note.strip(),resolution.strip(),u["email"]); st.success("Complaint updated; student can see the status and notes."); st.rerun()
        else: st.info("No complaints match these filters.")
        if rows: st.download_button("Export complaints CSV",pd.DataFrame(rows).to_csv(index=False).encode(), "hostel_complaints.csv","text/csv")
    with t2:
        if rows:
            df=pd.DataFrame(rows); x,y=st.columns(2)
            x.plotly_chart(px.pie(df.groupby("status").size().reset_index(name="Count"),names="status",values="Count",hole=.4,title="Complaint status"),use_container_width=True)
            y.plotly_chart(px.bar(df.groupby("category").size().reset_index(name="Count"),x="category",y="Count",title="Complaints by type"),use_container_width=True)
            st.plotly_chart(px.bar(df.groupby("priority").size().reset_index(name="Count"),x="priority",y="Count",title="Complaints by priority"),use_container_width=True)
        else: st.info("Analytics appear after complaints are submitted.")
    with t3:
        hs=history()
        if hs: st.dataframe(pd.DataFrame(hs)[["complaint_id","category","actor","action","note","created"]].rename(columns={"complaint_id":"Complaint ID","category":"Type","actor":"Actor","action":"Action","note":"Note","created":"Timestamp"}),use_container_width=True,hide_index=True)
        else: st.info("No activity yet.")
def main():
    init()
    if "user" not in st.session_state: login(); return
    u=st.session_state.user
    with st.sidebar:
        st.markdown("## 🏠 HSP"); st.write(u["name"]); st.caption(u["email"]); st.write("Role: "+u["role"].title())
        if st.button("Logout"): st.session_state.pop("user",None); st.rerun()
        st.caption("Academic prototype · SQLite")
    student_page(u) if u["role"]=="student" else warden_page(u)
if __name__=="__main__": main()

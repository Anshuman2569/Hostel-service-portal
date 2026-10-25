# Hostel Service Portal
Run in PowerShell from this folder:
```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
Demo Student: student@hostel.local / Student@123
Demo Warden: warden@hostel.local / Warden@123

Workflow: Student submits complaint -> Warden reviews and assigns maintenance staff -> status progresses through Assigned, In Progress, Resolved and Closed. Students see only their own complaints; wardens see all complaints. Categories: Water Cooler, Switch / Regulator, Fan, Tube Light, Furniture, Cleanliness.

Academic prototype only. Use synthetic data and do not deploy with demo credentials or real sensitive data.

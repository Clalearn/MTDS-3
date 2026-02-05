from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import math
from datetime import date, datetime, timedelta
import io
import pypdf

app = FastAPI()

# --- MODELLI DATI (Input che arrivano dall'App) ---
class UserProfile(BaseModel):
    instincts: list[str]
    focus_quality: str
    emotional_enemy: str
    chronotype: str
    review_mode: str
    exercise_mode: str
    active_days: list[str]  # ["Monday", "Tuesday", ...]

class PlanRequest(BaseModel):
    profile: UserProfile
    speed: float
    total_pages: int
    days_total: int
    daily_hours: int
    start_hour_str: str  # "09:00"
    current_page: int = 0
    days_passed: int = 0

# --- LOGICA DI SUPPORTO (Copiata dal tuo codice) ---
def get_technical_strategy(instincts):
    s1, s2 = "Leggi con attenzione.", "Rielabora mentalmente."
    if any("Evidenziatore" in x for x in instincts): s1 = "🚫 **Mani in Tasca:** Vietato sottolineare alla prima lettura."
    elif any("Lettore Passivo" in x for x in instincts): s1 = "⚡ **Interrogazione:** Trasforma i titoli in domande."
    if any("Trascrittore" in x for x in instincts): s2 = "🛑 **Filtro:** Solo 3 parole chiave per paragrafo."
    elif any("Oratore" in x for x in instincts): s2 = "👶 **Feynman:** Spiega a un bambino."
    return s1, s2

def get_psycho_advice(enemy):
    if "Ansia" in enemy: return "🧘 **Mindset:** Non cercare la perfezione."
    elif "Noia" in enemy: return "🎮 **Gamification:** Usa timer aggressivi."
    return "🔋 **Energy:** Cerca solo i concetti macro."

# --- ENDPOINT 1: CALCOLO PIANO ---
@app.post("/generate_plan")
def generate_plan(req: PlanRequest):
    # Setup variabili
    calendar = {}
    today = date.today()
    prof = req.profile
    
    # Parsing orario
    h, m = map(int, req.start_hour_str.split(':'))
    start_t = datetime.strptime(req.start_hour_str, "%H:%M").time()

    # 1. Calcoli Residui
    remaining_pages = max(0, req.total_pages - req.current_page)
    remaining_days = max(0, req.days_total - req.days_passed)

    if not prof.active_days: return {"error": "Nessun giorno attivo selezionato"}
    if remaining_pages == 0: return {"status": "completed", "msg": "Hai finito!"}
    
    # 2. Calcolo Capacità
    real_speed = (60 / req.speed) * 0.9
    if prof.focus_quality == "Dispersiva": real_speed *= 0.8
    if "Trascrittore" in str(prof.instincts): real_speed *= 0.7

    # Giorni Utili
    valid_days = 0
    for d in range(remaining_days):
        if (today + timedelta(days=d)).strftime("%A") in prof.active_days:
            valid_days += 1
            
    mins_avail = (req.daily_hours * 60 * valid_days)
    if prof.review_mode != "Nessuno": mins_avail -= (20 * valid_days)
    
    capacity_pg = int(mins_avail * (real_speed / 60)) if real_speed > 0 else 0
    is_impossible = capacity_pg < remaining_pages
    
    # 3. Generazione Calendario (Semplificato per JSON)
    cursor = req.current_page
    output_plan = []
    
    cycle_duration = 50
    ex_density = 1.0 if prof.exercise_mode == "Molta Pratica" else 0.5
    if prof.exercise_mode == "Solo Teoria": ex_density = 0
    
    s1, s2 = get_technical_strategy(prof.instincts)

    for d in range(remaining_days):
        curr_date = today + timedelta(days=d)
        day_name = curr_date.strftime("%A")
        date_str = curr_date.strftime("%Y-%m-%d")
        
        day_tasks = []
        
        if day_name not in prof.active_days:
            output_plan.append({"date": date_str, "type": "off", "tasks": []})
            continue

        curr_dt = datetime.combine(curr_date, start_t)
        mins_left = req.daily_hours * 60
        
        # Ripasso
        if prof.review_mode != "Nessuno":
            mins_left -= 20
            day_tasks.append({
                "time": curr_dt.strftime("%H:%M"),
                "title": "Review",
                "desc": "Ripasso spaced repetition"
            })
            curr_dt += timedelta(minutes=20)

        # Cicli
        cycles = math.floor(mins_left / (cycle_duration + 10))
        for _ in range(cycles):
            if cursor >= req.total_pages: break
            
            end_dt = curr_dt + timedelta(minutes=cycle_duration)
            pg_todo = real_speed * (cycle_duration/60)
            if prof.exercise_mode == "Molta Pratica": pg_todo *= 0.7
            
            end_cursor = min(req.total_pages, cursor + pg_todo)
            if is_impossible: end_cursor += 1 # Overdrive
            
            ex_count = math.ceil((end_cursor-cursor) * ex_density)
            
            task_obj = {
                "time_start": curr_dt.strftime("%H:%M"),
                "time_end": end_dt.strftime("%H:%M"),
                "pages_start": int(cursor),
                "pages_end": int(end_cursor),
                "exercises": ex_count,
                "input_strategy": s1,
                "process_strategy": s2,
                "psycho_tip": get_psycho_advice(prof.emotional_enemy)
            }
            day_tasks.append(task_obj)
            
            cursor = end_cursor
            curr_dt = end_dt + timedelta(minutes=10) # Pausa

        output_plan.append({"date": date_str, "type": "study", "tasks": day_tasks})

    return {
        "status": "impossible" if is_impossible else "success",
        "coverage": int((cursor / req.total_pages) * 100),
        "missing_pages": int(remaining_pages - capacity_pg) if is_impossible else 0,
        "plan": output_plan
    }

# --- ENDPOINT 2: ANALISI PDF ---
@app.post("/analyze_pdf")
async def analyze_pdf(file: UploadFile = File(...)):
    try:
        content = await file.read()
        pdf_file = io.BytesIO(content)
        reader = pypdf.PdfReader(pdf_file)
        return {"num_pages": len(reader.pages)}
    except Exception as e:
        return {"error": str(e)}

# Endpoint di base per testare se è online
@app.get("/")
def read_root():
    return {"status": "Cla! Engine is Running 🚀"}
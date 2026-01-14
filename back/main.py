from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from database import Base, engine, SessionLocal
from models import User, WorkSession

app = FastAPI(title="Sistema de Control de Jornada")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# ---- Crear usuarios de prueba ----
@app.on_event("startup")
def seed_users():
    db = SessionLocal()
    if db.query(User).count() == 0:
        for c in ["USR-1234", "USR-5678", "USR-9012", "USR-3456"]:
            db.add(User(code=c))
        db.commit()
    db.close()

# ---- Estado de jornada ----
@app.get("/status")
def status(code: str):
    db = SessionLocal()
    user = db.query(User).filter(User.code == code).first()
    if not user:
        raise HTTPException(404, "Código inválido")

    session = db.query(WorkSession).filter(
        WorkSession.user_id == user.id,
        WorkSession.end_time == None
    ).first()

    if not session:
        return {"working": False}

    elapsed = int((datetime.utcnow() - session.start_time).total_seconds())
    return {
        "working": True,
        "seconds": elapsed
    }

# ---- Iniciar jornada ----
@app.post("/start")
def start(code: str):
    db = SessionLocal()

    user = db.query(User).filter(User.code == code).first()
    if not user:
        raise HTTPException(status_code=404, detail="Código inválido")

    active = db.query(WorkSession).filter(
        WorkSession.user_id == user.id,
        WorkSession.end_time.is_(None)
    ).first()

    if active:
        elapsed = int((datetime.utcnow() - active.start_time).total_seconds())
        return {
            "status": "already_started",
            "seconds": elapsed,
            "message": "La jornada ya está activa"
        }

    session = WorkSession(user_id=user.id)
    db.add(session)
    db.commit()

    return {
        "status": "started",
        "message": "Jornada iniciada correctamente"
    }


# ---- Terminar jornada ----
@app.post("/end")
def end(code: str):
    db = SessionLocal()

    user = db.query(User).filter(User.code == code).first()
    if not user:
        raise HTTPException(status_code=404, detail="Código inválido")

    session = db.query(WorkSession).filter(
        WorkSession.user_id == user.id,
        WorkSession.end_time.is_(None)
    ).order_by(WorkSession.start_time.desc()).first()

    if not session:
        raise HTTPException(
            status_code=400,
            detail="No hay jornada activa para este usuario"
        )

    now = datetime.utcnow()
    session.end_time = now
    session.total_seconds = int((now - session.start_time).total_seconds())

    db.commit()
    db.refresh(session)

    return {
        "message": "Jornada finalizada correctamente",
        "total_seconds": session.total_seconds
    }

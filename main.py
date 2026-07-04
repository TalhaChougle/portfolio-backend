import json
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from models import init_db, get_db, Certification
from schemas import CertificationOut
import storage

app = FastAPI(title="Portfolio Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your Netlify/Vercel domain later
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/certifications", response_model=List[CertificationOut])
def list_certifications(db: Session = Depends(get_db)):
    return db.query(Certification).order_by(Certification.id).all()


@app.post("/certifications", response_model=CertificationOut)
def create_certification(
    title: str = Form(...),
    issuer: str = Form(""),
    category: str = Form(""),
    date: str = Form(""),
    description: str = Form(""),
    credential_url: str = Form(""),
    modules: str = Form("[]"),  # JSON-encoded list of strings
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    file_url = ""
    media_type = ""
    if file:
        content = file.file.read()
        file_url = storage.upload_file(content, file.filename, file.content_type)
        media_type = "pdf" if file.content_type == "application/pdf" else "image"

    cert = Certification(
        title=title,
        issuer=issuer,
        category=category,
        date=date,
        description=description,
        credential_url=credential_url,
        file_url=file_url,
        media_type=media_type,
        modules=json.loads(modules),
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


@app.put("/certifications/{cert_id}", response_model=CertificationOut)
def update_certification(
    cert_id: int,
    title: str = Form(...),
    issuer: str = Form(""),
    category: str = Form(""),
    date: str = Form(""),
    description: str = Form(""),
    credential_url: str = Form(""),
    modules: str = Form("[]"),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    cert = db.query(Certification).get(cert_id)
    if not cert:
        raise HTTPException(404, "Certification not found")

    if file:
        storage.delete_file(cert.file_url)
        content = file.file.read()
        cert.file_url = storage.upload_file(content, file.filename, file.content_type)
        cert.media_type = "pdf" if file.content_type == "application/pdf" else "image"

    cert.title = title
    cert.issuer = issuer
    cert.category = category
    cert.date = date
    cert.description = description
    cert.credential_url = credential_url
    cert.modules = json.loads(modules)

    db.commit()
    db.refresh(cert)
    return cert


@app.delete("/certifications/{cert_id}")
def delete_certification(cert_id: int, db: Session = Depends(get_db)):
    cert = db.query(Certification).get(cert_id)
    if not cert:
        raise HTTPException(404, "Certification not found")
    storage.delete_file(cert.file_url)
    db.delete(cert)
    db.commit()
    return {"ok": True}


@app.delete("/certifications")
def delete_all_certifications(db: Session = Depends(get_db)):
    certs = db.query(Certification).all()
    for c in certs:
        storage.delete_file(c.file_url)
    db.query(Certification).delete()
    db.commit()
    return {"ok": True}

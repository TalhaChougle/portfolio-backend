import json
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from models import init_db, get_db, Certification, Resume, LabReport, Publication, Project
from schemas import CertificationOut, ResumeOut, DocOut, ProjectOut
from pydantic import BaseModel
import storage
import autofill

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


@app.get("/resume", response_model=Optional[ResumeOut])
def get_resume(db: Session = Depends(get_db)):
    return db.query(Resume).first()


@app.post("/resume", response_model=ResumeOut)
def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    existing = db.query(Resume).first()
    if existing:
        storage.delete_file(existing.file_url)

    content = file.file.read()
    file_url = storage.upload_file(content, file.filename, file.content_type)
    media_type = "pdf" if file.content_type == "application/pdf" else "image"

    if existing:
        existing.file_url = file_url
        existing.media_type = media_type
        db.commit()
        db.refresh(existing)
        return existing
    else:
        r = Resume(file_url=file_url, media_type=media_type)
        db.add(r)
        db.commit()
        db.refresh(r)
        return r


@app.delete("/resume")
def delete_resume(db: Session = Depends(get_db)):
    existing = db.query(Resume).first()
    if existing:
        storage.delete_file(existing.file_url)
        db.delete(existing)
        db.commit()
    return {"ok": True}


def _make_doc_routes(model, prefix: str):
    @app.get(f"/{prefix}", response_model=List[DocOut])
    def list_docs(db: Session = Depends(get_db)):
        return db.query(model).order_by(model.id).all()

    @app.post(f"/{prefix}", response_model=DocOut)
    def create_doc(
        title: str = Form(...),
        description: str = Form(""),
        file: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
    ):
        file_url = ""
        media_type = ""
        if file:
            content = file.file.read()
            file_url = storage.upload_file(content, file.filename, file.content_type)
            media_type = file.content_type or ""
        item = model(title=title, description=description, file_url=file_url, media_type=media_type)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @app.put(f"/{prefix}/{{item_id}}", response_model=DocOut)
    def update_doc(
        item_id: int,
        title: str = Form(...),
        description: str = Form(""),
        file: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
    ):
        item = db.query(model).get(item_id)
        if not item:
            raise HTTPException(404, "Not found")
        if file:
            storage.delete_file(item.file_url)
            content = file.file.read()
            item.file_url = storage.upload_file(content, file.filename, file.content_type)
            item.media_type = file.content_type or ""
        item.title = title
        item.description = description
        db.commit()
        db.refresh(item)
        return item

    @app.delete(f"/{prefix}/{{item_id}}")
    def delete_doc(item_id: int, db: Session = Depends(get_db)):
        item = db.query(model).get(item_id)
        if not item:
            raise HTTPException(404, "Not found")
        storage.delete_file(item.file_url)
        db.delete(item)
        db.commit()
        return {"ok": True}

    @app.delete(f"/{prefix}")
    def delete_all_docs(db: Session = Depends(get_db)):
        items = db.query(model).all()
        for i in items:
            storage.delete_file(i.file_url)
        db.query(model).delete()
        db.commit()
        return {"ok": True}


_make_doc_routes(LabReport, "lab-reports")
_make_doc_routes(Publication, "publications")


class ProjectIn(BaseModel):
    title: str
    description: str = ""
    long_description: str = ""
    category: str = ""
    github: str = ""
    link: str = ""
    tech_stack: List[str] = []
    highlights: List[str] = []


@app.get("/projects", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.id).all()


@app.post("/projects", response_model=ProjectOut)
def create_project(body: ProjectIn, db: Session = Depends(get_db)):
    p = Project(**body.dict())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@app.put("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, body: ProjectIn, db: Session = Depends(get_db)):
    p = db.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Not found")
    for k, v in body.dict().items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@app.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    p = db.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Not found")
    db.delete(p)
    db.commit()
    return {"ok": True}


@app.delete("/projects")
def delete_all_projects(db: Session = Depends(get_db)):
    db.query(Project).delete()
    db.commit()
    return {"ok": True}


class GithubUrlRequest(BaseModel):
    github_url: str


@app.post("/extract/project")
def extract_project(req: GithubUrlRequest):
    try:
        repo = autofill.fetch_github_repo(req.github_url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    description = autofill.rewrite_project_description(
        repo["raw_description"], repo["languages"], repo["topics"]
    )
    return {"name": repo["name"], "description": description, "tech_stack": repo["languages"]}


@app.post("/extract/cert")
def extract_cert(file: UploadFile = File(...)):
    content = file.file.read()
    is_pdf = file.content_type == "application/pdf" or file.filename.lower().endswith(".pdf")
    if is_pdf:
        pages = autofill.extract_pdf_page_texts(content)
        if len(pages) <= 1:
            text = pages[0] if pages else ""
            return autofill.extract_cert_info(text)
        return {"multi": True, "results": autofill.extract_multi_cert_info(pages)}
    # images: no OCR configured, return empty so the field stays manual
    return {"date": "", "description": ""}


@app.post("/extract/document")
def extract_document(file: UploadFile = File(...)):
    content = file.file.read()
    text = autofill.extract_text_from_file(content, file.content_type, file.filename)
    return {"description": autofill.extract_doc_description(text)}

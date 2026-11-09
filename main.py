import datetime
import json
import os
from io import BytesIO

import docx
import faiss
import numpy as np
import ollama
import PyPDF2
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sentence_transformers import SentenceTransformer
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

import courseKnowledgeBase
import wellbeingMonitor
from database import (
    Conversation,
    Document,
    FlaggedEvent,
    SessionLocal,
    Student,
    hash_content,
    init_db,
)

app = FastAPI(title="Student Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize models
sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
sentiment_analyzer = SentimentIntensityAnalyzer()

# Initialize modules
wellbeing_monitor = wellbeingMonitor.WellbeingMonitor()
knowledge_base = courseKnowledgeBase.CourseKnowledgeBase()

# Create DB tables on startup
init_db()


def _extract_text(content: bytes, filename: str) -> str:
    if filename.endswith('.pdf'):
        pdf_reader = PyPDF2.PdfReader(BytesIO(content))
        return "".join(page.extract_text() for page in pdf_reader.pages)
    elif filename.endswith('.docx'):
        document = docx.Document(BytesIO(content))
        return "".join(p.text for p in document.paragraphs)
    else:
        return content.decode('utf-8')


@app.post("/upload_syllabus")
async def upload_syllabus(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = _extract_text(content, file.filename)
        knowledge_base.add_document(text, file.filename)

        db = SessionLocal()
        try:
            db.add(Document(filename=file.filename, course_id=None, content_hash=hash_content(text)))
            db.commit()
        finally:
            db.close()

        return {"message": f"Successfully uploaded {file.filename}"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/uploadAssignment")
async def upload_assignment(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = _extract_text(content, file.filename)
        knowledge_base.add_document(text, file.filename)

        db = SessionLocal()
        try:
            db.add(Document(filename=file.filename, course_id=None, content_hash=hash_content(text)))
            db.commit()
        finally:
            db.close()

        return {"message": f"Successfully uploaded {file.filename}"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/wellbeing_dashboard")
async def get_wellbeing_dashboard():
    db = SessionLocal()
    try:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        total_flags = db.query(FlaggedEvent).count()
        recent_events = db.query(FlaggedEvent).filter(FlaggedEvent.timestamp >= cutoff).all()

        all_flags = db.query(FlaggedEvent).all()
        student_summary = {}
        for flag in all_flags:
            sid = flag.student_id
            if sid not in student_summary:
                student_summary[sid] = {"flag_count": 0, "last_flagged": None, "reviewed_count": 0}
            student_summary[sid]["flag_count"] += 1
            if (
                student_summary[sid]["last_flagged"] is None
                or flag.timestamp > datetime.datetime.fromisoformat(student_summary[sid]["last_flagged"])
            ):
                student_summary[sid]["last_flagged"] = flag.timestamp.isoformat()
            if flag.reviewed:
                student_summary[sid]["reviewed_count"] += 1

        return {
            "total_flags": total_flags,
            "recent_flags": [
                {
                    "id": e.id,
                    "student_id": e.student_id,
                    "timestamp": e.timestamp.isoformat(),
                    "reason": e.reason,
                    "severity": e.severity,
                    "reviewed": e.reviewed,
                }
                for e in recent_events
            ],
            "student_summary": student_summary,
        }
    finally:
        db.close()


@app.websocket("/ws/{student_id}")
async def websocket_endpoint(websocket: WebSocket, student_id: str):
    await websocket.accept()

    db = SessionLocal()
    try:
        if not db.query(Student).filter(Student.student_id == student_id).first():
            db.add(Student(student_id=student_id))
            db.commit()
    finally:
        db.close()

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get('message', '')
            now = datetime.datetime.utcnow()

            db = SessionLocal()
            try:
                db.add(Conversation(
                    student_id=student_id,
                    timestamp=now,
                    message=user_message,
                    role='user',
                    wellbeing_score=None,
                ))
                db.commit()
            finally:
                db.close()

            wellbeing_analysis = wellbeing_monitor.analyze_message(user_message, student_id)

            if wellbeing_analysis['flag_for_review']:
                stress = wellbeing_analysis['stress_indicators']
                confusion = wellbeing_analysis['confusion_indicators']
                reason = f"stress_indicators={stress}, confusion_indicators={confusion}"
                severity = round(10 - wellbeing_analysis['wellbeing_score'], 2)

                db = SessionLocal()
                try:
                    db.add(FlaggedEvent(
                        student_id=student_id,
                        timestamp=now,
                        reason=reason,
                        severity=severity,
                        reviewed=False,
                    ))
                    db.commit()
                finally:
                    db.close()

            relevant_docs = knowledge_base.search_similar(user_message)
            context = "\n".join([doc['content'] for doc in relevant_docs[:2]])

            prompt = f"""You are a helpful academic assistant for undergraduate students in C++ programming and algorithms courses.

Context from course materials:
{context}

Student question: {user_message}

Please provide a helpful, encouraging response. If the question is about course content, use the context provided. If it's about programming, provide clear explanations and examples. Always be supportive and understanding of student stress.

Response:"""

            try:
                response = ollama.generate(model='llama3.1:8b', prompt=prompt, stream=False)
                bot_response = response['response']
            except Exception:
                bot_response = (
                    "I'm sorry, I'm having trouble processing your request right now. "
                    "Please try again or contact your instructor."
                )

            db = SessionLocal()
            try:
                db.add(Conversation(
                    student_id=student_id,
                    timestamp=datetime.datetime.utcnow(),
                    message=bot_response,
                    role='bot',
                    wellbeing_score=wellbeing_analysis['wellbeing_score'],
                ))
                db.commit()
            finally:
                db.close()

            await websocket.send_text(json.dumps({
                'message': bot_response,
                'wellbeing_score': wellbeing_analysis['wellbeing_score'],
                'flagged': wellbeing_analysis['flag_for_review'],
            }))

    except WebSocketDisconnect:
        print(f"Student {student_id} disconnected")


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def get_homepage():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

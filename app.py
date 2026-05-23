import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from duckduckgo_search import DDGS
import jinja2
from weasyprint import HTML
from datetime import datetime
import re

app = FastAPI()

class QueryRequest(BaseModel):
    query: str
    category: str = "particular"

@app.get("/", response_class=HTMLResponse)
async def index():
    return open("static/index.html").read()

@app.post("/api/generate")
async def generate(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(400, "Campo vacío")
    
    # Recolección
    web = list(DDGS().text(req.query, max_results=6))
    news = list(DDGS().news(req.query, max_results=4))
    
    data = {
        "query": req.query,
        "category": req.category,
        "timestamp": datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"),
        "web": [{"title": r["title"], "url": r["href"], "snippet": r["body"][:150]} for r in web],
        "news": [{"title": r["title"], "url": r["url"], "source": r.get("source",""), "date": r.get("date","")} for r in news],
        "summary": f"Investigación finalizada. {len(web)} fuentes web y {len(news)} noticias analizadas. Datos obtenidos exclusivamente de fuentes públicas."
    }

    # PDF
    os.makedirs("reports", exist_ok=True)
    fid = str(uuid.uuid4())[:8]
    path = f"reports/osint_{req.category}_{fid}.pdf"
    
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("static"))
    html = env.get_template("template.html").render(data=data, cat_label={"particular":"👤 Informe Particular","empresa":"🏢 Informe Corporativo","gobierno":"🏛️ Informe Gubernamental"}[req.category])
    HTML(string=html).write_pdf(path)
    
    return {"pdf_url": f"/api/download/{path.split('/')[-1]}"}

@app.get("/api/download/{filename}")
async def download(filename: str):
    return FileResponse(f"reports/{filename}", media_type="application/pdf", filename=filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

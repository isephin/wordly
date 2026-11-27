import csv, io, json, zipfile
from pathlib import Path

SUPPORTED={'.txt','.md','.csv','.xlsx','.pdf','.docx','.json'}

def extract(name,data,column=''):
    ext=Path(name).suffix.lower()
    if ext not in SUPPORTED: raise ValueError('Unsupported file type: '+ext)
    if ext in {'.docx', '.xlsx'}:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > 150 * 1024 * 1024:
                raise ValueError('Document expands beyond the supported size.')
    if ext in {'.txt','.md'}: return data.decode('utf-8-sig').splitlines(),[]
    if ext=='.pdf':
        from pypdf import PdfReader
        reader=PdfReader(io.BytesIO(data)); lines=[]
        for page in reader.pages: lines.extend((page.extract_text() or '').splitlines())
        if not any(x.strip() for x in lines): raise ValueError('No extractable PDF text; scanned PDFs require OCR.')
        return lines,[]
    if ext=='.docx':
        from docx import Document
        doc=Document(io.BytesIO(data)); lines=[p.text for p in doc.paragraphs]
        lines.extend(c.text for t in doc.tables for r in t.rows for c in r.cells)
        return lines,[]
    if ext=='.json':
        def strings(v):
            if isinstance(v,str): yield v
            elif isinstance(v,list):
                for x in v: yield from strings(x)
            elif isinstance(v,dict):
                for x in v.values(): yield from strings(x)
        return list(strings(json.loads(data.decode('utf-8-sig')))),[]
    if ext=='.csv': rows=csv.reader(io.StringIO(data.decode('utf-8-sig')))
    else:
        from openpyxl import load_workbook
        book=load_workbook(io.BytesIO(data),read_only=True,data_only=True)
        try: return table(book.active.values,column)
        finally: book.close()
    return table(rows,column)

def table(rows,column):
    rows=iter(rows); header=next(rows,[])
    names=[f'{i+1}: {str(v or "Column "+str(i+1))}' for i,v in enumerate(header)]
    index=int(column) if column else None
    if index is not None and not 0<=index<len(names): raise ValueError('Invalid column')
    lines=[]
    for row in rows:
        values=row if index is None else row[index:index+1]
        lines.extend(str(v) for v in values if v is not None and str(v).strip())
    return lines,names

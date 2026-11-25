from advanced_analyzer import options,run,terms
from file_reader import extract
from io import BytesIO
from docx import Document
from openpyxl import Workbook

def main():
    lines=['Apple apple banana 42', 'banana apple and pear', 'running runs runner']
    for raw in [{},{'case':True},{'numbers':True},{'stem':True},{'ngram':2},{'ngram':3,'workers':3},{'exclude':'apple'},{'include':'banana'}]:
        opt=options(raw); a,_=run(lines,opt); b,_=run(lines,opt,True); assert a==b,raw
    assert terms('apple and pear',options({'ngram':2}))==[]
    assert extract('x.csv',b'name,comment\na,hello\nb,world','1')[0]==['hello','world']
    assert extract('x.json',b'{"text":"hello"}')[0]==['hello']
    assert extract('x.md',b'hello\nworld')[0]==['hello','world']
    doc=Document();doc.add_paragraph('hello');buf=BytesIO();doc.save(buf);assert extract('x.docx',buf.getvalue())[0]==['hello']
    book=Workbook();book.active.append(['name','comment']);book.active.append(['a','hello']);buf=BytesIO();book.save(buf);assert extract('x.xlsx',buf.getvalue(),'1')[0]==['hello']
    print('Advanced engine and readers passed')
if __name__=='__main__':main()

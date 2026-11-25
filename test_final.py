import json
from advanced_analyzer import options,run,terms,tokens
from pathlib import Path
from file_reader import extract

from io import BytesIO

def main():
 lines=['Apple apple banana 42','banana apple and pear','running runs runner']; cases=[({}, {'apple':3,'banana':2,'pear':1,'running':1,'runs':1,'runner':1}),({'case':True},{'Apple':1,'apple':2,'banana':2,'pear':1,'running':1,'runs':1,'runner':1}),({'include':'banana'},{'banana':2}),({'exclude':'apple','length':5},{'banana':2,'running':1,'runner':1}),({'ngram':2},{'apple apple':1,'apple banana':1,'banana apple':1,'running runs':1,'runs runner':1})]
 for raw,expected in cases:
  o=options(raw); a,_=run(lines,o);b,_=run(lines,o,True);assert a==b==expected,(raw,a,expected)
 o=options({'numbers':True,'stem':True,'workers':3});a,_=run(lines,o);b,_=run(lines,o,True);assert a==b and a['run']==2 and a['42']==1
 assert extract('x.txt',b'hello\nworld')[0]==['hello','world']
 # PDF fixture is generated separately for the review.
 print('Exact counts, TXT and worker tests passed')
if __name__=='__main__':main()

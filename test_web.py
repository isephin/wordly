import io,json
from app import app

def main():
    with app.test_client() as c:
        assert c.get('/').status_code==200
        assert c.get('/static/favicon.svg').status_code==200
        assert c.get('/api/benchmarks').status_code==200
        r=c.post('/api/analyze',data={'text':'apple apple banana\nbanana pear','options':json.dumps({'exclude':'pear'})})
        assert r.status_code==200,r.get_json()
        d=r.get_json(); assert d['identical'] and d['words']==[{'word':'apple','count':2},{'word':'banana','count':2}]
        r=c.post('/api/columns',data={'file':(io.BytesIO(b'name,comment\na,apple'), 'test.csv')});assert r.get_json()==['1: name','2: comment']
        r=c.post('/api/analyze',data={'file':[(io.BytesIO(b'name,comment\na,apple'), 'test.csv'),(io.BytesIO(b'banana banana'),'test.txt')],'column_0':'1'})
        assert r.status_code==200,r.get_json();d=r.get_json();assert d['identical'] and len(d['comparison'])==2 and d['comparison'][0]['counts']=={'apple':1} and d['comparison'][1]['counts']=={'banana':2}
        assert c.post('/api/analyze',data={'text':' '}).status_code==400
    print('Web routes and file comparison passed')
if __name__=='__main__':main()

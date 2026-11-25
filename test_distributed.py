import threading
from collections import Counter
from http.server import HTTPServer
from urllib.error import HTTPError
from advanced_analyzer import options, count_chunk
from distributed import distributed_run, call
from worker import Handler

def main():
    servers=[]; token='test-secret-not-for-real-use-123'
    try:
        for _ in range(2):
            server=HTTPServer(('127.0.0.1',0),Handler);server.token=token;servers.append(server)
            threading.Thread(target=server.serve_forever,daemon=True).start()
        urls=['http://127.0.0.1:'+str(s.server_port) for s in servers]
        assert call(urls[0],token,'/health')['name']
        try: call(urls[0],'wrong','/health'); raise AssertionError('Accepted wrong token')
        except HTTPError as e: assert e.code==401
        lines=['Apple apple banana','banana pear','apple pear','banana banana']
        for opt in [options({}),options({'case':True}),options({'ngram':2}),options({'exclude':'banana'})]:
            counts,elapsed,details=distributed_run(lines,opt,urls,token)
            assert counts==count_chunk((lines,opt)) and sum(d['lines'] for d in details)==len(lines)
        assert distributed_run(lines,options({}),urls,token)[0]==Counter({'apple':3,'banana':4,'pear':2})
        print('HTTP worker, authentication and distributed count tests passed (loopback).')
    finally:
        for s in servers: s.shutdown();s.server_close()
if __name__=='__main__': main()

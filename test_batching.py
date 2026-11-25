import threading
from http.server import HTTPServer
from advanced_analyzer import options,count_chunk
import distributed
from worker import Handler

def main():
    servers=[]; token='test-secret-not-for-real-use-123'
    try:
        for _ in range(2):
            s=HTTPServer(('127.0.0.1',0),Handler); s.token=token; servers.append(s)
            threading.Thread(target=s.serve_forever,daemon=True).start()
        urls=['http://127.0.0.1:'+str(s.server_port) for s in servers]
        distributed.MAX_BYTES=1024
        lines=['apple banana café "quoted" \\ path '+str(i) for i in range(1000)]
        for opt in [options({}),options({'ngram':2})]:
            counts,_,details=distributed.distributed_run(lines,opt,urls,token)
            assert counts==count_chunk((lines,opt))
            assert sum(d['lines'] for d in details)==len(lines)
            assert all(d['batches']>1 for d in details)
        print('Multi-batch HTTP counting and exact count checks passed.')
    finally:
        for s in servers: s.shutdown();s.server_close()
if __name__=='__main__':main()

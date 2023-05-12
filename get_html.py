#!/usr/bin/env python3
# -*- coding:utf-8 -*- 

import sys
import http.client 
import json
import time
import traceback
import random

def scraping(url):
    b_idx = url.find("://")
    e_idx = url.find("/", b_idx+len("://"))

    host = url[b_idx+len("://"):e_idx]
    uri = url[e_idx:]

    conn = http.client.HTTPSConnection(host)

    conn.request("GET", uri, 
        headers={
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Content-type': 'text/html; charset=utf-8',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'max-age=0',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36',
        })
    rslt = conn.getresponse()

    data = rslt.read()
    conn.close()

    utf_data = str(data, encoding='utf-8')
    return utf_data
## end

def main():
    if len(sys.argv) < 2:
        print("Usage: python f.py meta_data")
        return

    fd = open(sys.argv[-1], 'r')
    for line in fd:
        line = line.strip()
        j = json.loads(line)

        try:
            html = scraping(j['web_url'])
            fname = 'data_html/%s.html' % j['doc_id']
            with open(fname, 'w', encoding='utf8') as w_fd:
                w_fd.write(html)

            print('%s done' % fname)
        except Exception:
            print('%s failed' % j['doc_id'])
            traceback.print_exc()

        r = random.random()
        time.sleep(int(r * 6 + 5))
    ## end

    fd.close()
## end

if __name__ == '__main__':
    main()


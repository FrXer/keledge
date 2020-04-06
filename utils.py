#!/usr/bin/env python3
import os
import time
import random
import re
import json
import requests
import subprocess
import shlex
from datetime import datetime

h = '''
accept-encoding: gzip, deflate, br
user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36
'''

gheaders = dict([i.strip().split(': ', 1) for i in h.split('\n') if i != ''])

def dowloadSplitFileUrl(d, obj, t=0, overwrite=0, headers=None, token=None):
    os.makedirs(d, exist_ok=True)
    
    page = obj.get('NumberOfPage')
    if not page:
        page = obj.get('Page')
    if not page:
        return "Can't get page number.{}".format(obj)
    name = os.path.join(d, "{}.pdf".format(page))
    if os.path.exists(name) and os.path.getsize(name) < 2000:
        os.remove(name)
    if os.path.exists(name) and overwrite==0:
        return "已存在！{}".format(name)
    url = obj['Url']
    if not headers:
        headers = gheaders
    if token is not None:
        url = url+"&Token={}".format(token)
    # print(url, headers)
    r = requests.get(url, headers=headers)
    if r.status_code >= 300:
        time.sleep(max(5, t))

        return "下载失败：{} {}".format(name, r.status_code)
    if len(r.content) < 2000:
        try:
            r.content.decode()
        except UnicodeDecodeError:
            # 空白页
            with open(name, 'wb') as f:
                f.write(r.content)
            return "下载成功！空白页{} http_status:{}".format(name, r.status_code)
        time.sleep(max(30, t))
        return "下载失败：{} {} {} size:{}Bytes\n{}".format(name, r.status_code, url, len(r.content), r.text)
    with open(name, 'wb') as f:
        f.write(r.content)

    time.sleep(max(random.randint(10,20), t))
    return "下载成功！{} http_status:{}".format(name, r.status_code)

def Guess51zhyFull(SplitFiles, increment=64, t=0, headers=None):
    left_page = SplitFiles[-1]['NumberOfPage']
    url = SplitFiles[-1]['Url']
    base_url = os.path.dirname(url)
    template_url = os.path.join(base_url, '{}.pdf')
    re_p = re.match(r'(\d+).pdf', os.path.basename(url))
    try:
        int(re_p.group(1))
    except Exception as e:
        print('error:{}'.format(e))
        return
    if not headers:
        headers = gheaders
    while True:
        right_page = left_page + increment
        r = requests.get(template_url.format(right_page), headers=headers)
        time.sleep(max(5,t))
        print("try page: {}".format(template_url.format(right_page)))
        if r.status_code == 404:
            break
        if r.text.find("操作过快") > 0:
            print('error:操作过快\n{}'.format(r.text))
            time.sleep(60)
            continue
        left_page = right_page
    
    def find(left, right):
        if right-left == 1:
            return left
        mid = (left+right)//2
        r = requests.get(template_url.format(mid))
        print("try page: {}".format(template_url.format(mid)))
        time.sleep(max(15,t))
        if r.status_code == 404:
            return find(left, mid)
        else:
            if r.text.find("操作过快") > 0:
                print('error:操作过快\n{}'.format(r.text))
                time.sleep(60)
            return find(mid, right)
    
    start = SplitFiles[-1]['NumberOfPage']
    end = find(left_page, right_page)
    for i in range(start+1, end+1):
        SplitFiles.append({"NumberOfPage":i,"Url":template_url.format(i)})

def decSplitFile(p, i, o):
    d = os.path.dirname(o)
    os.makedirs(d, exist_ok=True)

    if os.path.exists(o):
        return
    cmd = 'openssl enc -d -aes-128-ecb -K "{}" -in "{}" -out "{}"'.format(p, i, o)
    
    cmd = shlex.split(cmd)
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        if os.path.exists(o):
            os.remove(o)
    return r


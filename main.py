#!/usr/bin/env python3
import requests
import json
import os
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import dowloadSplitFileUrl, decSplitFile, Guess51zhyFull
from inputimeout import inputimeout, TimeoutOccurred


FORMAT = '%(levelname)-4s: %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)

def dowloadSplitFiles(SplitFiles, time=0):
    enc_dir = os.path.join(base_dir, book_prefix+'_enc')
    os.makedirs(enc_dir, exist_ok=True)

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(dowloadSplitFileUrl, enc_dir, obj, time): obj for obj in SplitFiles}
        for future in as_completed(future_to_url):
            obj = future_to_url[future]
            try:
                ret = future.result()
            except Exception as exc:
                logging.warning('%r generated an exception: %s' % (obj, exc))
            else:
                logging.info(ret)


def dowloadSplitFilesByLoop(SplitFiles):
    enc_dir = os.path.join(base_dir, book_prefix+'_enc')
    os.makedirs(enc_dir, exist_ok=True)
    for obj in SplitFiles:
        ret = dowloadSplitFileUrl(enc_dir,  obj)
        logging.info(ret)

def decSplitFiles(enc_dir, dec_dir):
    os.makedirs(dec_dir, exist_ok=True)
    ok = 0
    with ThreadPoolExecutor(max_workers=16) as executor:
        for root,_,files in os.walk(enc_dir):
            future_to_url = {
                executor.submit(
                    decSplitFile,
                    passwd,
                    os.path.join(root,f),
                    os.path.join(dec_dir, f)): f for f in files
                }
        for future in as_completed(future_to_url):
            obj = future_to_url[future]
            try:
                ret = future.result()
            except Exception as exc:
                logging.warning('%r generated an exception: %s' % (obj, exc))
            else:
                if ret == None:
                    ok+=1
                    logging.info("file {} already decrypt.".format(obj))

                elif ret.returncode == 0:
                    ok+=1
                    logging.info("page {} decrypt ok. {}".format(obj, ret.stdout.decode()))
                else:
                    logging.error("page {} error:{}".format(obj, ret.stderr.decode()))
    print("总共：{}页\n成功：{}页".format(len(SplitFiles), ok))
    return ok



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', dest='authorize_file', required=True, action='store',
                    help='authorize file')
    parser.add_argument('-p', dest='passwd_file', action='store',
                    help='passwd file')
    parser.add_argument('-t', dest='sleep',type=int, default=0, action='store',
                    help='sleep time in second')
    parser.add_argument('--no-guess',dest='guess', action='store_false', help="Don't guess 51zhy.cn Full pages")
    args = parser.parse_args()
    authorize_file = args.authorize_file
    base_dir = os.path.dirname(authorize_file)
    book_prefix = os.path.basename(authorize_file).replace('_authorize.txt','')
    passwd_file = args.passwd_file
    if args.passwd_file is None:
        passwd_file = os.path.join(base_dir, book_prefix+"_passwd.txt")
        if not os.path.exists(passwd_file):
            logging.warning("[未找到passwd文件，请使用-p指定]")
            parser.print_help()
            exit(1)

    with open(authorize_file) as authorize:
        result = json.load(authorize)
    with open(passwd_file, 'rt') as pwd:
        passwd = pwd.read(1024)

    if not result['Data'].get('SplitFiles'):
        result['Data']['SplitFiles']=[]
        for i,u in enumerate(result['Data']['SplitFileUrls']):
            result['Data']['SplitFiles'].append({"NumberOfPage":i+1,"Url":u})
    
    SplitFiles = result['Data']['SplitFiles']
    if not result['Data'].get('NumberOfPages'):
        print("全书页数未知")
        result['Data']['NumberOfPages'] = len(SplitFiles)
    else:
        print("全书共{}页".format(result['Data']['NumberOfPages']))
    print("authorize_file获取{}页".format(len(SplitFiles)))
    if args.guess and SplitFiles[0]['Url'].find('51zhy')>0:
        Guess51zhyFull(SplitFiles)
        print("Guess51zhyFull后获取{}页".format(len(SplitFiles)))

    if(len(SplitFiles)<result['Data']['NumberOfPages']):
        logging.warning("authorize_file未获取全文，请确保你的帐号拥有阅读全文的权限！\n(tip:获取到的页数比总页数少1页，实际上已经是全文了，可忽略！)")

    while True:
        dowloadSplitFiles(SplitFiles, args.sleep)
        # dowloadSplitFilesByLoop(SplitFiles)
        enc_dir = os.path.join(base_dir, book_prefix+'_enc')
        dec_dir = os.path.join(base_dir, book_prefix+'_dec')
        ok = decSplitFiles(enc_dir, dec_dir)
        if ok < len(SplitFiles)-1:
            retry = 'Y'
            try:
                retry = inputimeout(prompt='再次尝试？[Y/n]', timeout=60)
            except TimeoutOccurred:
                retry = 'Y'
            if retry not in ['N', 'n', 'Not', 'not']:
                continue
            else:
                break
        else:
            break

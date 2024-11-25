import os, sys, zipfile
import requests
from bs4 import BeautifulSoup

chrome_stable_link = 'https://googlechromelabs.github.io/chrome-for-testing/#stable'

def getLink(link=chrome_stable_link):
    down_link = None
    # os.environ['https_proxy'] = 'http://proxy.vmware.com:3128'
    ret = requests.get(link)
    soup = BeautifulSoup(ret.text, 'html.parser')
    stable_sec = soup.find('section', id='stable')
    all_codes = stable_sec.find_all('code')
    # print(all_codes)
    for x in all_codes:
        if 'chromedriver-win64.zip' in x.text:
            down_link = x.text
            break
    return down_link

def download_chromedrive():
    chrome_loc = r'd:\miniconda3'
    chromedrive_old = os.path.join(chrome_loc, 'chromedriver_old.exe')
    chromedrive_cur = os.path.join(chrome_loc, 'chromedriver.exe')
    chromedrive_zip = os.path.join(chrome_loc, 'chromedriver-win64.zip')
    chromedrive_dir = os.path.join(chrome_loc, 'chromedriver-win64')
    chromedrive_new = os.path.join(chromedrive_dir, 'chromedriver.exe')
    try:
        if os.path.exists(chromedrive_old):
            os.remove(chromedrive_old)
    except:
        pass
    if os.path.exists(chromedrive_zip):
        os.remove(chromedrive_zip)
    try:
        if os.path.exists(chromedrive_cur):
            os.rename(chromedrive_cur, chromedrive_old)
    except:
        pass


    url = getLink()
    if not url:
        return
    with open(chromedrive_zip, 'wb') as h:
        resp = requests.get(url, stream=True)
        if not resp.ok:
            pass
        total = resp.headers.get('Content-Length')
        if total is None:
            h.write(resp.content)
        else:
            downloaded = 0
            total = int(total)
            for block in resp.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
                if not block:
                    break
                downloaded += len(block)
                h.write(block)
                done = int(50*downloaded/total)
                sys.stdout.write(f'\r[{"█"*done}{"."*(50-done)}]')
                sys.stdout.flush()
    sys.stdout.write('\n')

    if os.path.exists(chromedrive_zip):
        with zipfile.ZipFile(chromedrive_zip) as z:
            z.extractall(path=chrome_loc)
        if os.path.exists(chromedrive_new):
            os.rename(chromedrive_new, chromedrive_cur)
        if os.path.exists(chromedrive_cur):
            print('update complete')
    else:
        print('download failure')

if __name__ == '__main__':
    download_chromedrive()

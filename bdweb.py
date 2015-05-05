import argparse
import requests
import urlparse
import logging
import sys
import os
import re
import xml.etree.ElementTree as ET
import multiprocessing


class BuildWeb:
    '''class for buildweb.eng.vmware.com'''

    global logPool

    def __init__(self,
                 sb=False,
                 product='rde-sdk-rel',
                 branch='cart-dev',
                 buildType='release'):
        self.product = product
        self.branch = branch
        self.buildType = buildType
        if sb:
            self.buildapi = 'http://buildapi.eng.vmware.com/sb'
            self.buildweb = 'http://buildweb.eng.vmware.com/sb'
        else:
            self.buildapi = 'http://buildapi.eng.vmware.com/ob'
            self.buildweb = 'http://buildweb.eng.vmware.com/ob'
        qfilter = 'buildstate__in=succeeded,storing&_limit=1&_order_by=-id'
        qstr = '/build/?product=%s&branch=%s&buildtype=%s&' % (product,
                                                               branch,
                                                               buildType)
        self.queryurl = self.buildapi + qstr + qfilter

    def getBuildNum(self):
        resp = requests.get(self.queryurl)
        if not resp.ok:
            print 'can not get result from url: %s' % self.queryurl
            return False
        json = resp.json()
        build = json['_list'][0]
        self.buildid = build['id']
        return self.buildid

    def getQueryStr(self, buildid):
        qstr = '/api/legacy/build_info/?build=%s' % buildid
        self.qidstr = self.buildweb + qstr
        logPool.info(self.qidstr)
        return self.qidstr

    def printLatestInfo(self):
        self.getBuildNum()
        sepa = '*' * 20
        print sepa
        print "Product: %s " % self.product
        print "Branch: %s " % self.branch
        print "Build Type: %s " % self.buildType
        print "Build Number: %s " % self.buildid
        print sepa

    def getFileUrl(self, dlfilter=None, buildnum=None):
        buildid = buildnum
        if not buildid:
            buildid = self.getBuildNum()
        qidstr = self.getQueryStr(buildid)
        resp = requests.get(qidstr)
        if not resp.ok:
            print 'query buildweb with %s failed' % qidstr
            return False

        et = ET.fromstring(resp.text)
        product = et[0]
        if not len(product):
            print 'no product found !'
            return False

        urls = [x.attrib['url'] for x in product.iter(tag='file')]
        dlurls = urls
        if dlfilter:
            logPool.info("regular expression filter : %s" % dlfilter)
            p = re.compile(dlfilter)
            dlurls = [x for x in urls if p.search(x)]
        furls = {os.path.basename(urlparse.urlsplit(x).path): x
                 for x in dlurls}
        logPool.info(furls)
        return furls


def dlItems(urltuple=None):
    global logPool
    if not urltuple:
        return
    name = multiprocessing.current_process().name
    (f, url) = urltuple
    logPool.info("\tProcess:%s\n\tdownload file : %s\n\tdownload link : %s"
                 % (name, f, url))
    with open(f, 'wb') as h:
        resp = requests.get(url, stream=True)
        if not resp.ok:
            pass
        for block in resp.iter_content(1024):
            if not block:
                break
            h.write(block)


def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--branch',
                        dest='branch',
                        action='store',
                        help='branch on buildweb',
                        default='cart-dev')
    parser.add_argument('-c', '--type',
                        dest='buildType',
                        action='store',
                        help='build type on buildweb',
                        default='release')
    parser.add_argument('-p', '--product',
                        dest='product',
                        action='store',
                        help='product on buildweb',
                        default='rde-sdk-rel')
    parser.add_argument('-n', '--num',
                        dest='buildnum',
                        help='buildNumber on buildweb',
                        default=None,
                        action='store')
    parser.add_argument('-l', '--list',
                        dest='list',
                        help='list deliverable files',
                        default=False,
                        action='store_true')
    parser.add_argument('-i', '--info',
                        dest='info',
                        help='list latest build number',
                        default=False,
                        action='store_true')
    parser.add_argument('-d', '--dir',
                        dest='downloadDirectory',
                        help='download directory',
                        default='',
                        action='store')
    parser.add_argument('-f', '--filter',
                        dest='reFilter',
                        help='regular expression filter',
                        default=None,
                        action='store')
    parser.add_argument('-s', '--sanbox',
                        dest='sandbox',
                        help='is sandbox build',
                        action='store_true',
                        default=False)
    args = parser.parse_args()
    return args


# Top-level script environment
if __name__ == '__main__':
    # delete http_proxy first if exist
    if 'http_proxy' in os.environ:
        del os.environ['http_proxy']

    # get command line options
    args = getArgs()
    if args.downloadDirectory:
        if not os.path.exists(args.downloadDirectory):
            print '%s is no exist' % args.downloadDirectory
            try:
                os.makedirs(args.downloadDirectory)
            except:
                pass
        else:
            os.chdir(args.downloadDirectory)

    # log name : bdweb.out
    logging.basicConfig(filename='bdweb.out',
                        level=logging.DEBUG)
    logPool = logging.getLogger('buildweb')

    # instance of Buildweb
    dl = BuildWeb(args.sandbox,
                  args.product,
                  args.branch,
                  args.buildType)
    dlurls = []
    if args.buildnum:
        dlurls = dl.getFileUrl(args.reFilter, args.buildnum)
    else:
        dlurls = dl.getFileUrl(args.reFilter)

    # just list deliverable files for -l | --list options
    if args.list:
        if not dlurls:
            print 'no files found !'
            sys.exit(-1)
        files = [x for x in dlurls.keys()]
        for x in files:
            print x
        sys.exit(0)
    elif args.info:
        dl.printLatestInfo()
        sys.exit(0)

    print 'download directory %s' % os.getcwd()
    # pool size would be the minimum of available cpu core and download link
    poolSize = min(multiprocessing.cpu_count() * 4, len(dlurls))
    pool = multiprocessing.Pool(processes=poolSize)
    fileToDls = [(dlfile, dlurl) for dlfile, dlurl in dlurls.items()]
    pool.map(dlItems, fileToDls)
    pool.close()
    pool.join()

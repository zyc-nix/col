import re
import collections
from datetime import datetime
import argparse


class LBPTools():

    def group(self, lst, n):
        for i in range(0, len(lst), n):
            val = lst[i:i+n]
            if len(val) == n:
                yield tuple(val)

    def _getSessionInfo(self, tpacLog):
        txt = collections.defaultdict(lambda: collections.defaultdict(list))
        outs = ""
        with open(tpacLog, 'r') as f:
            outs = f.read()
        self.contents = outs
        mp = re.compile('''
                    (?P<datebegin>^\d\d\.\d\d\.\d{4}\s+?\d\d:\d\d:\d\d)
                    (?:[^\n\r]+?)
                    (WTS_REMOTE_CONNECT\sfor\sSession\sId=::)
                    (?P<sessionid>\d{1,3})
                    (?P<other>.+?)
                    ((?=\Z)|(?=(^[^\n\r]+?WTS_REMOTE_CONNECT\sfor\sSession\sId=)))
                    ''', re.M|re.S|re.X)
        f = mp.finditer(outs)

        for idx, info in enumerate(f):
            txt[idx]['datebegin'] = info.group('datebegin')
            txt[idx]['sessionid'] = info.group('sessionid')
            txt[idx]['other'] = info.group('other')

        return txt

    def _delayAddPrinter(self, txt):
        ret = []
        mp = re.compile('''
                    (?P<datebegin>^\d\d\.\d\d\.\d{4}\s+?\d\d:\d\d:\d\d)  # time
                    (?P<secondbegin>:\d{3})
                    \s+?(?:[^\n\r]+?Try\sto\scall.+?)
                    (?P<dateend>^\d\d\.\d\d\.\d{4}\s+?\d\d:\d\d:\d\d)    # time
                    (?P<secondend>:\d{3})
                    \s+?
                    (?:[^\n\r]+?AddPrinter)
                    \s
                    (?P<status>succeeded|failed)
                    (?:[^<]+)
                    (?P<name>[^>]+?>)
                    (?:.+?)
                    (?:pPortName\s<)
                    (?P<type>[^>]+)
                    ''', re.S | re.M | re.X)

        for m in mp.finditer(txt):
            fmt = '%d.%m.%Y %H:%M:%S'
            if m.group('name'):
                lbpName = m.group('name')[1:-1]
                printType = 'Thinprint'
                if not 'TPVM' in m.group('type'):
                    printType = 'LBP'
                tdelta = datetime.strptime(m.group('dateend'), fmt) - datetime.strptime(m.group('datebegin'), fmt)
                if tdelta.days < 0:
                    tdelta = datetime.timedelta(days=0,
                                    seconds=tdelta.seconds,
                                    microseconds=tdelta.microseconds)
                ret.append([lbpName,
                            printType,
                            tdelta,
                            m.group('type'),
                            m.group('status'),
                            m.group('datebegin')])
        return sorted(ret, key=lambda x: x[2])

    def _delayVCOpen(self, txt):
        ret = []
        mp = re.compile('''
                    (?P<datebegin>^\d\d\.\d\d\.\d{4}\s+?\d\d:\d\d:\d\d)             # time
                    (?P<secondbegin>:\d{3})
                    \s+?
                    (?:[^\n\r]+?Trying\sto\s(open|read\sfrom)\sVChannel.+?)
                    (?P<dateend>^\d\d\.\d\d\.\d{4}\s+?\d\d:\d\d:\d\d)               # time
                    (?P<secondend>:\d{3})
                    \s+?
                    (?P<ops>[^\n\r]+?VChannel(Open|Read)\(\))
                    \s
                    (?P<status>succeeded|failed)
                    ''', re.S | re.M | re.X )
        if not mp:
            print 'failed'
        for m in mp.finditer(txt):
            fmt = '%d.%m.%Y %H:%M:%S'
            tdelta = datetime.strptime(m.group('dateend'), fmt) - datetime.strptime(m.group('datebegin'), fmt)
            if tdelta.days < 0:
                tdelta = datetime.timedelta(days=0,
                                seconds=tdelta.seconds,
                                microseconds=tdelta.microseconds)
            ops = 'Open'
            if 'Read' in m.group('ops'):
                ops = 'Read'
            ret.append(['VChannel %s' % ops,
                        '%s' % tdelta,
                        m.group('datebegin')])
        return ret


    def listInfo(self, log):
        allInfo = self._getSessionInfo(log)
        if not allInfo:
            allInfo = self.contents
            allPrinters = self._delayAddPrinter(self.contents)
            if not allPrinters:
                return
            for idx in allPrinters:
                lbpName = idx[0]
                print '%-16s %-24s %-10s %-10s %-16s' \
                    % (lbpName,
                    idx[3],
                    idx[2],
                    idx[4],
                    idx[5])
        else:
            for idx, x in enumerate(allInfo):
                allPrinters = self._delayAddPrinter(allInfo[idx]['other'])
                if not allPrinters:
                    continue
                print 'session:%s time:%s ------' % (allInfo[idx]['sessionid'],
                                                    allInfo[idx]['datebegin'])
                for idx in allPrinters:
                    lbpName = idx[0]
                    print '%-16s %-24s %-10s %-10s %-16s' \
                        % (lbpName,
                        idx[3],
                        idx[2],
                        idx[4],
                        idx[5])


    def calcDelays(self, log):
        allInfo = self._getSessionInfo(log)
        if not allInfo:
            otherInfo = self.contents
            allPrinters = self._delayAddPrinter(otherInfo)
            if not allPrinters:
                return
            delayOpens = self._delayVCOpen(otherInfo)
            for i in delayOpens:
                print 'delays on %-28s %-10s : %-16s' % (i[0], i[1], i[2])

            for idx in allPrinters:
                lbpName = idx[0]
                print 'delays on printer %-20s %-10s : %-24s %-16s' \
                    % (lbpName,
                    idx[2],
                    idx[5],
                    idx[3])


        else:
            for idx, x in enumerate(allInfo):
                otherInfo = allInfo[idx]['other']
                allPrinters = self._delayAddPrinter(otherInfo)
                if not allPrinters:
                    continue
                print 'session:%s time:%s ------' % (allInfo[idx]['sessionid'],
                                                    allInfo[idx]['datebegin'])
                delayOpens = self._delayVCOpen(otherInfo)
                for i in delayOpens:
                    print 'delays on %-28s %-10s : %-16s' % (i[0], i[1], i[2])

                for idx in allPrinters:
                    lbpName = idx[0]
                    print 'delays on printer %-20s %-10s : %-24s %-16s' \
                        % (lbpName,
                        idx[2],
                        idx[5],
                        idx[3])


def getOptions():
    parser = argparse.ArgumentParser('version=1.0')
    parser.add_argument('-l', '--list',
                      dest='listInfo',
                      action='store_true',
                      help='list LBP/Thinprint printers',
                      default=False)
    parser.add_argument('-c',
                      dest='calc',
                      action='store_true',
                      help='calculate printer creation time',
                      default=False)
    parser.add_argument('-f', '--logs',
                      dest='logFiles',
                      nargs='+',
                      help='TP auto connect Logs',
                      default=[])
    args = parser.parse_args()
    return (args)

def main():
    opts = getOptions()
    lbp = LBPTools()

    # main logic
    if not len(opts.logFiles):
        print('no TP auto connect logs specified')
    else:
        for i in opts.logFiles:
            print 'Informations from file %s ------' % i
            if opts.listInfo:
                lbp.listInfo(i)
            elif opts.calc:
                lbp.calcDelays(i)

if __name__ == '__main__':
    main()

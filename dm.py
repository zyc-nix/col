import sys
import re
import time
import subprocess
import optparse
import math


class ConnectedMonitor():
    def __init__(self, display):
        self.name = display[0]
        self.presolution = display[1]
        self.online = display[2]
        if self.online:
            self.cresolution = display[3]
            self.rotation = display[4]
            self.position = display[5]
            # only interest in resolutions
            p = re.compile(r'\d{3,5}x\d{3,5}')
            self.other = p.findall(display[6])


class DisplayTools():

    def __init__(self):
        self.refresh()
        self.dirTable = {'right': '--right-of', 'left': '--left-of',
                         'below': '--below', 'above': '--above'}

    def refresh(self):
        ret = self.__getInfo()
        self.connected = [ConnectedMonitor(x) for x in ret]
        self.online = [x for x in self.connected if x.online]
        self.offline = [x for x in self.connected if not x.online]

    def __getInfo(self):
        outs = ""
        if sys.platform == "darwin":
            with open("output.txt", 'r') as f:
                outs = f.read()
        else:
            # must support xrandr command
            cmd = "xrandr -q"
            outs, err = subprocess.Popen(cmd,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         shell=True).communicate()
            if err:
                raise 'Test Environment Error: we must support xrandr command!'

        ret = []
        mp = re.compile('''
                    (?P<name>^\S+?)             # name
                    \s
                    connected
                    \s
                    (primary)?
                    \s?
                    ((?P<cresolution>\d+x\d+)   # current resolution
                    \+
                    (?P<pos>\d+\+\d+))?         # position
                    \s??
                    (?P<rotate>\S+)?            # rotation
                    \s?
                    (?:\(.+?$)
                    \s+?
                    (?P<presolution>\d+x\d+)    # preferred resolution
                    \s+?
                    (?:[^*+]+\*?\+?.*?\s*)      # optional */+
                    (?P<other>^\s{2,}.+?)       # remaining resolutions
                    (?=^\w+|\Z)                 # another beginning or EOF
                    ''', re.S | re.M | re.X)

        for m in mp.finditer(outs):
            if not m.group('cresolution'):
                ret.append([m.group('name'), m.group('presolution'), False])
                continue
            position = m.group('pos').replace('+', ',')
            other = m.group('other')
            if m.group('rotate'):
                rotate = m.group('rotate')
                ret.append([m.group('name'), m.group('presolution'), True,
                            m.group('cresolution'), rotate, position, other])
            else:
                ret.append([m.group('name'), m.group('presolution'), True,
                            m.group('cresolution'), 'normal', position, other])

        return ret

    def listMonitorInfo(self):
        namelen = max([len(x.name) for x in self.online])
        fstr = '%-*s%-12s%-8s%-12s%-10s%-12s'
        print fstr % (namelen+2, 'Name', 'preferred', 'online?',
                      'position', 'rotation', 'current')
        for x in self.connected:
            if x.online:
                info = fstr % (namelen+2, x.name, x.presolution, 'YES',
                               x.position, x.rotation, x.cresolution)
            else:
                info = '%-*s%-12s%-8s' % (namelen+2, x.name,
                                          x.presolution, 'NO')
            print info

    def listOnlineMonitors(self):
        for x in self.online:
            print x.name

    def listOfflineMonitors(self):
        if len(self.offline):
            for x in self.offline:
                print x.name
        else:
            print 'all connected monitors are active'

    def toggleMonitor(self, name=None, off=False):
        if off:
            cmd = 'xrandr --output %s --off' % name
        else:
            cmd = 'xrandr --output %s --auto' % name
        subprocess.call(cmd, shell=True)
        time.sleep(5)

    def getCubeNum(self):
        cubeRange = [x*x for x in xrange(2, 7)]  # 4 ~ 36 monitors total,
        nconnected = len(self.connected)
        nonline = len(self.online)               # 2 ~ 6 per row and column
        onlineRange = [x for x in xrange(4, nonline + 1)]
        connectedRange = [x for x in xrange(4, nconnected + 1)]
        possibleOnlineRange = set(onlineRange) & set(cubeRange)
        possibleConnectedRange = set(connectedRange) & set(cubeRange)
        if len(possibleConnectedRange) < 1:
            msg = '%s monitors are not support the cube layout ' % nconnected
            e = Exception(msg)
            raise e
        elif len(possibleConnectedRange) == 1:
            return list(possibleConnectedRange)[0]
        elif len(possibleConnectedRange) > 1 and len(possibleOnlineRange) == 1:
            return list(possibleOnlineRange)[0]
        elif len(possibleConnectedRange) > 1 and len(possibleOnlineRange) == 0:
            return list(possibleConnectedRange)[0]
        else:
            return 0

    def setNumOnline(self, number):
        # make sure we have the right number of active monitor
        ntotal = len(self.connected)
        nonline = len(self.online)
        if number != nonline:  # from command line
            if number > ntotal:
                msg = 'you have connected %s monitors totally, but ask for %s'\
                    % (ntotal, number)
                e = Exception(msg)
                raise e
            diff = []
            if nonline < number:
                diff = self.offline[:number - nonline]
                map((lambda t: self.toggleMonitor(t.name, off=False)), diff)
            elif nonline > number:
                diff = self.online[number - nonline:]
                map((lambda t: self.toggleMonitor(t.name, off=True)), diff)
            else:
                pass
            # refresh all informations after change
            self.refresh()

    def setlayout(self, opts):
        cmd = ''
        if opts.layout in ('cube', '2'):
            cmd = self.getCubeCmd(opts)
        else:
            cmd = self.getCmd(opts)
        print '*************'
        print 'cmd : --> \n%s' % cmd
        print '*************'
        if sys.platform == "linux2":
            err = subprocess.call(cmd, shell=True)
            time.sleep(10)
            if err:
                print 'error in execute cmd : %s' % cmd
                return False
            return True

    def __chunks(self, l, n):
        return [l[i:i+n] for i in xrange(0, len(l), n)]

    def getCubeCmd(self, opts):

        dlen = int(math.sqrt(len(self.online)))
        d2 = self.__chunks(self.online, dlen)
        v1 = self.online[::dlen]
        if opts.size == 'best':
            opts.size = min(x.presolution for x in self.online)
        cmd = ''
        pre = ''
        for i, monitor in enumerate(v1):
            if i > 0:
                cmd += ' --output %s --mode %s --rotate %s %s %s ' % \
                        (monitor.name, opts.size, opts.rotation, '--below', pre.name)
            else:
                cmd = 'xrandr --output %s --pos 0x0 --primary --mode %s --rotate %s' % \
                        (monitor.name, opts.size, opts.rotation)
            prev = monitor
            for j, m in enumerate(d2[i][1:]):
                cmd += ' --output %s --mode %s --rotate %s %s %s' % \
                        (m.name, opts.size, opts.rotation, '--right-of', prev.name)
                prev = m
            pre = monitor
        return cmd

    def getCmd(self, opts):
        if not opts.direction:
            if opts.layout in ('landscape', '0'):
                opts.direction = '0'
            elif opts.layout in ('portrait', '1'):
                opts.direction = '1'

        str4 = [str(i) for i in xrange(4)]
        directionTable = {'0': 'right', '1': 'below', '2': 'left', '3': 'above'}
        if opts.direction in str4:
            opts.direction = directionTable[opts.direction]
        else:
            print 'invalid direction for layout, 0,1,2,3 are valid value'
            sys.exit(-1)

        cmd = ''
        if opts.layout in ('landscape', '0') and opts.direction not in ('right', 'left'):
            msg = '%s direction not supported in Landscape mode' % opts.direction
            e = Exception(msg)
            raise e
        elif opts.layout in ('portrait', '1') and opts.direction not in ('below', 'above'):
            msg = '%s direction not supported in Portrait mode' % opts.direction
            e = Exception(msg)
            raise e

        number = len(self.online)
        if opts.number:
            number = opts.number
        if number in xrange(3, 36):   # only rectangle supported
            pre = ''
            direction = self.dirTable[opts.direction]
            lrotation = opts.lrotation
            if not len(lrotation):
                lrotation = [x.rotation for x in self.online]
            for i, monitor in enumerate(self.online):
                if i > 0:
                    cmd += ' --output %s --mode %s --rotate %s %s %s ' % \
                            (monitor.name, opts.size, lrotation[i], direction, pre.name)
                else:
                    cmd = 'xrandr --output %s --pos 0x0 --primary --mode %s --rotate %s' % \
                            (monitor.name, opts.size, lrotation[i])
                pre = monitor
        elif number == 2:      # can have different resolution and rotation
            if len(self.online) != 2:
                msg = 'fatal error in this script'
                e = Exception(msg)
                raise e

            m0, m1 = self.online
            r0 = opts.lrotation[0]
            r1 = opts.lrotation[1]
            if not opts.align:
                # relative position
                direction = self.dirTable[opts.direction]
                s0 = opts.lsize[0]
                s1 = opts.lsize[1]
                cmd = 'xrandr --output %s --primary --mode %s --rotate %s ' % \
                    (m0.name, s0, r0)
                cmd += ' --output %s --mode %s --rotate %s %s %s ' % \
                    (m1.name, s1, r1, direction, m0.name)

            else:
                # absolute position
                if opts.align not in ('lts', 'lms', 'lbs', 'pls', 'pms', 'prs', 'ltb', 'lmb', 'lbb', 'plb', 'pmb', 'prb'):
                    print "%s is not a valid value" % opts.align
                    sys.exit(-1)
                if False:'''
                    1, select monitor with smaller resolution first
                    2, re-position according to requirement:
                        lts : smaller one top-left most, Landscape, top aligned
                        lms : smaller one top-left most, Landscape, middle aligned
                        lbs : smaller one top-left most, Landscape, bottom aligned
                        pls : smaller one top-left most, Portrait, left aligned
                        pms : smaller one top-left most, Portrait, middle aligned
                        prs : smaller one top-left most, Portrait, right aligned
                        ltb : bigger one top-left most, Landscape, top aligned
                        lmb : bigger one top-left most, Landscape, middle aligned
                        lbb : bigger one top-left most, Landscape, bottom aligned
                        plb : bigger one top-left most, Portrait, left aligned
                        pmb : bigger one top-left most, Portrait, middle aligned
                        prb : bigger one top-left most, Portrait, right aligned
                '''
                sml = m0
                big = m1
                # select a monitor with smaller resolution
                if int(m0.presolution.split('x')[0]) > int(m1.presolution.split('x')[0]):
                    sml, big = big, sml

                # will use 1280x1024 at worst
                smlw, smlh = 1280, 1024
                smlResolutionTestingList = ('1680x1050', '1600x1200', '1440x900', '1600x900')
                if sml.presolution in smlResolutionTestingList:
                    smlw, smlh = map(int, sml.presolution.split('x'))
                else:
                    for x in smlResolutionTestingList:
                        if x in sml.other:
                            smlw, smlh = map(int, x.split('x'))
                            break
                bigw, bigh = map(int, m1.presolution.split('x'))
                smlp, bigp = '0x0', '0x0'
                # default the smaller on top-left most
                if opts.align == 'lts':
                    if r0 in ('left', 'right'):
                        bigp = "%dx%d" % (smlh, 0)
                    else:
                        bigp = "%dx%d" % (smlw, 0)
                elif opts.align == 'lms':
                    if r0 in ('left', 'right'):
                        if r1 in ('left', 'right'):
                            smlp = "%dx%d" % (0, (bigw - smlw) / 2)
                        else:
                            smlp = "%dx%d" % (0, (bigh - smlw) / 2 if bigh > smlw else 0)
                        bigp = "%dx%d" % (smlh, 0)
                    else:
                        if r1 in ('left', 'right'):
                            smlp = "%dx%d" % (0, (bigw - smlh) / 2)
                        else:
                            smlp = "%dx%d" % (0, (bigh - smlw) / 2)
                        bigp = "%dx%d" % (smlw, 0)
                elif opts.align == 'lbs':
                    if r0 in ('left', 'right'):
                        if r1 in ('left', 'right'):
                            smlp = "%dx%d" % (0, bigw - smlw)
                        else:
                            smlp = "%dx%d" % (0, bigh - smlw if bigh > smlw else 0)
                        bigp = "%dx%d" % (smlh, 0)
                    else:
                        if r1 in ('left', 'right'):
                            smlp = "%dx%d" % (0, bigh - smlw if bigh > smlw else 0)
                        else:
                            smlp = "%dx%d" % (0, bigh - smlh)
                        bigp = "%dx%d" % (smlw, 0)
                elif opts.align == 'pls':
                    if r0 in ('left', 'right'):
                        bigp = "%dx%d" % (0, smlw)
                    else:
                        bigp = "%dx%d" % (0, smlh)
                elif opts.align == 'pms':
                    if r0 in ('left', 'right'):
                        if r1 in ('left', 'right'):
                            smlp = "%dx%d" % ((bigh - smlh) / 2, 0)
                        else:
                            smlp = "%dx%d" % ((bigw - smlh) / 2, 0)
                        bigp = "%dx%d" % (0, smlw)
                    else:
                        if r1 in ('left', 'right'):
                            smlp = "%dx%d" % ((bigh - smlw) / 2 if bigh > smlw else 0, 0)
                        else:
                            smlp = "%dx%d" % ((bigw - smlw) / 2, 0)
                        bigp = "%dx%d" % (0, smlh)
                elif opts.align == 'prs':
                    if r0 in ('left', 'right'):
                        if r1 in ('left', 'right'):
                            smlp = "%dx%d" % (bigh - smlh, 0)
                        else:
                            smlp = "%dx%d" % (bigw - smlh, 0)
                        bigp = "%dx%d" % (0, smlw)
                    else:
                        if r1 in ('left', 'right'):
                            smlp = "%dx%d" % (bigh - smlw if bigh > smlw else 0, 0)
                        else:
                            smlp = "%dx%d" % (bigw - smlw, 0)
                        bigp = "%dx%d" % (0, smlh)
                # the bigger one on top-left most
                elif opts.align == 'ltb':
                    if r1 in ('left', 'right'):
                        smlp = "%dx%d" % (bigh, 0)
                    else:
                        smlp = "%dx%d" % (bigw, 0)
                elif opts.align == 'lmb':
                    if r1 in ('left', 'right'):
                        smlp = "%dx%d" % (bigh, (bigw - smlw) / 2 if r0 in ('left', 'right') else (bigw - smlh) / 2)
                    else:
                        if r0 in ('left', 'right'):
                            smlp = "%dx%d" % (bigw, (bigh - smlw) / 2 if bigh > smlw else 0)
                        else:
                            smlp = "%dx%d" % (bigw, (bigh - smlh) / 2)
                elif opts.align == 'lbb':
                    if r1 in ('left', 'right'):
                        smlp = "%dx%d" % (bigh, bigw - smlw if r0 in ('left', 'right') else bigw - smlh)
                    else:
                        if r0 in ('left', 'right'):
                            smlp = "%dx%d" % (bigw, bigh - smlw if bigh > smlw else 0)
                        else:
                            smlp = "%dx%d" % (bigw, bigh - smlh)
                elif opts.align == 'plb':
                    if r1 in ('left', 'right'):
                        smlp = "%dx%d" % (0, bigw)
                    else:
                        smlp = "%dx%d" % (0, bigh)
                elif opts.align == 'pmb':
                    if r1 in ('left', 'right'):
                        if r0 in ('left', 'right'):
                            smlp = "%dx%d" % ((bigh - smlh) / 2, bigw)
                        else:
                            smlp = "%dx%d" % ((bigh - smlw) / 2 if bigh > smlw else 0, bigw)
                    else:
                        smlp = "%dx%d" % ((bigw - smlh if r0 in ('left', 'right') else bigw - smlw) / 2, bigh)
                elif opts.align == 'prb':
                    if r1 in ('left', 'right'):
                        if r0 in ('left','right'):
                            smlp = "%dx%d" % (bigh - smlh, bigw)
                        else:
                            smlp = "%dx%d" % (bigh - smlw if bigh > smlw else 0, bigw)
                    else:
                        smlp = "%dx%d" % (bigw - smlh if r0 in ('left','right') else bigw - smlw, bigh)
                else:
                    print 'un-supported layout'
                    sys.exit(-1)

                cmd = 'xrandr --output %s --primary --mode %s --rotate %s --pos %s ' % \
                    (sml.name, "%sx%s" % (smlw, smlh), r0, smlp)
                cmd += ' --output %s --mode %s --rotate %s --pos %s ' % \
                    (big.name, "%sx%s" % (bigw, bigh), r1, bigp)

        elif number == 1:      # can have different resolution and rotation
                m = self.online[0]
                size = m.cresolution
                if opts.size != 'best':
                    size = opts.size
                cmd = 'xrandr --output %s --mode %s --rotate %s ' % \
                    (m.name, size, opts.rotation)
        return cmd


def getOptions():
    parser = optparse.OptionParser(version='1.0')
    parser.add_option('-l', '--list',
                      dest='listconnected',
                      action='store_true',
                      help='list all connected monitor informations',
                      default=False)
    parser.add_option('--List',
                      dest='listonline',
                      action='store_true',
                      help='list all online monitors',
                      default=False)
    parser.add_option('--LIST',
                      dest='listoffline',
                      action='store_true',
                      help='list all inactive monitors',
                      default=False)
    parser.add_option('-a', '--all',
                      dest='activeall',
                      action='store_true',
                      default=False)
    parser.add_option('-r', '--reorder',
                      dest='reorder',
                      help='reorder monitor sequence')
    parser.add_option('--off',
                      action='append',
                      help='de-active online monitor',
                      default=[],
                      dest='offlist')
    parser.add_option('-n', '--number',
                      dest='number',
                      type=int,
                      help='active monitor number ...',
                      action='store')
    parser.add_option('-o', '--rotation',
                      dest='rotation',
                      help='0 : normal, do not rotate,\
                            1 : right , counter clockwise 90 degree,\
                            2 : inverted , counter clockwise 180 degree,\
                            3 : left, counter clockwise 270 degree',
                      default='0')
    parser.add_option('-s', '--size',
                      dest='size',
                      help='supported resolution like 1920x1200, 1024x768 ...',
                      default='best',
                      action='store')
    parser.add_option('-d', '--direction',
                      help='0 : right , next monitor connected to the right of the previous one ,\
                            1 : below , next monitor connect below of the previous one,\
                            2 : left , next monitor connect to the left of the previous one,\
                            3 : top , next monitor connect on top of the previous one',
                      dest='direction')
    parser.add_option('--layout',
                      dest='layout',
                      type='choice',
                      choices=['0', 'landscape', '1', 'portrait', '2', 'cube'],
                      help='0 or landscape: 2x1, 3x1, 4x1 ...\
                            1 or portrait : 1x2, 1x3, 1x4 ...\
                            2 or cube : 2x2, 3x3 ...',
                      default='landscape'),
    parser.add_option('--align',
                      help='lts : Landscape, with smaller one top-left most, top aligned, \
                            lms : Landscape, with smaller one top-left most, middle aligned, \
                            lbs : Landscape, with smaller one top-left most, bottom aligned, \
                            pls : Portrai, with smaller one top-left most,, left aligned, \
                            pms : Portrai, with smaller one top-left most,, middle aligned, \
                            prs : Portrai, with smaller one top-left most,, right aligned, \
                            ltb : Landscape, with bigger one top-left most, top aligned, \
                            lmb : Landscape, with bigger one top-left most, middle aligned, \
                            lbb : Landscape, with bigger one top-left most, bottom aligned, \
                            plb : Portrait, with bigger one top-left most, left aligned, \
                            pmb : Portrait, with bigger one top-left most, middle aligned, \
                            prb : Portrait, with bigger one top-left most, right aligned',
                      default=None,
                      dest='align')
    opts, args = parser.parse_args()
    return (opts, args)

def main():
    opts, args = getOptions()
    dm = DisplayTools()

    # main logic
    if opts.listconnected:
        dm.listMonitorInfo()
        return
    if opts.listonline:
        dm.listOnlineMonitors()
        return
    if opts.listoffline:
        dm.listOfflineMonitors()
        return
    if opts.activeall:
        dm.setNumOnline(len(dm.connected))
        return
    if len(opts.offlist):
        dm.toggleMonitor(opts.listoffline, off=True)
        return

    # make sure we have the right number of active monitor
    number = 1
    if opts.number:
        dm.setNumOnline(opts.number)
        number = opts.number
    elif not opts.number and opts.layout in ('cube', '2'):
        cubeNum = dm.getCubeNum()
        if cubeNum:
            dm.setNumOnline(cubeNum)
        else:
            print "please specify the number of monitor for cube layout"
            sys.exit(-1)
        number = cubeNum
    else:
        number = len(dm.online)

    # same resolutions and rotations for 3 or 4 monitors
    # can have different resolutions and rotations for 2 monitors
    if opts.size == 'best':
        if number in (3, 4):
            opts.size = min([x.presolution for x in dm.online])
        elif number == 2:
            opts.lsize = [x.presolution for x in dm.online]
    else:
        opts.lsize = re.split(',', opts.size)
        opts.size = opts.lsize[0]
        if number == 2 and len(opts.lsize) == 1:
            opts.lsize.append(dm.online[1].presolution)

    rotateTable = {'0': 'normal', '1': 'right', '2': 'inverted', '3': 'left'}
    if ',' in opts.rotation:
        opts.lrotation = re.split(',', opts.rotation)
    else:
        opts.lrotation = [opts.rotation]
    opts.lrotation = [rotateTable[x] for x in opts.lrotation]
    # use default rotation if not specified
    if len(opts.lrotation) < number:
        diff = dm.online[len(opts.lrotation) - number:]
        for m in diff:
            opts.lrotation.append(m.rotation)

    opts.rotation = opts.lrotation[0]

    # lets do some reorder based on --reorder options
    if opts.reorder:
        lorder = opts.reorder.split(',')
        if len(lorder) != len(dm.online):
            print "please specify the exact order"
            sys.exit(-1)
        dm.online = [dm.online[int(x)] for x in lorder]

    dm.setlayout(opts)

if __name__ == '__main__':
    main()

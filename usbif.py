import subprocess
import collections
import copy
import re

class UsbInf:
    """ USB interface """

    def __init__(self, interfaceInfo):
        self.bus      = interfaceInfo[0]
        self.dev      = interfaceInfo[1]
        self.usbclass = interfaceInfo[2]
        self.speed    = interfaceInfo[3]
        self.If       = interfaceInfo[4]
        self.port     = interfaceInfo[5]
    def __str__(self):
        return "Bus %s Device %s: subclass %s" % (self.bus, self.dev, self.usbclass)

class UsbDev:
    """ USB Device """

    def __init__(self, devInfo):
        self.vendor       = devInfo[0]
        self.bus          = devInfo[1]
        self.dev          = devInfo[2]
        self.vid          = devInfo[3]
        self.pid          = devInfo[4]
        self.interfaces   = []
        self.composite    = False
        self.storage      = False
        self.manufacturer = None
        self.port         = None
        self.path         = None
        self.disk         = None
        self.mountInfo    = {}

    def updateInterfaces(self, usbInf):
        if usbInf.bus == self.bus and usbInf.dev == self.dev:
            self.interfaces.append(usbInf)
            self.port = usbInf.port

    def update(self, clientSide=True):
        if len(self.interfaces) > 1:
            self.composite = True
        if any('stor' in x.usbclass for x in self.interfaces):
            self.storage = True
            p = collections.OrderedDict(self.port.items())
            self.path = str(list(p)[0])
            if len(self.port) > 1:
                p.popitem(last=False)
                for k,v in p.items():
                    self.path += ".%s" % v
            self.path = "%s-%s" % (self.bus, self.path)
            cmd = "ls /sys/bus/usb/drivers/usb-storage/*%s*/*/*/*/block" % self.path
            if clientSide:
                outs = subprocess.Popen(cmd,
                                        shell=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE).communicate()[0].decode()
                self.disk = outs


class UsbInfo:

    def parseUsbTree(self, outs):
        ret = []
        busp = re.compile('''
                          (?:^/:.+?Bus\s+)
                          (?P<bus>\d+)
                          \.
                          (?P<other>.+?)
                          (?=^/|\Z)
                          ''', re.M | re.X | re.S)
        devp = re.compile('''
                          (?P<tree>.*?)
                          Port\s+
                          (?P<port>\d+?)
                          :
                          (?:\s+Dev\s+)
                          (?P<dev>\d+)
                          ,
                          (?:\s+If\s+)?
                          (?P<If>\d+)?
                          ,?
                          (?:\s+Class=)
                          (?P<class>.+?)
                          ,
                          (?:\s+Driver=.*?)
                          ,
                          \s+
                          (?P<speed>.+$)
                          ''', re.X | re.M )

        for m in busp.finditer(outs):
            if m.group('other'):
                devs = [x.groupdict() for x in devp.finditer(m.group('other'))]
                port = {}
                cport = {}
                for x in devs:
                    depth = x['tree'].count(' ') / 4
                    if depth == 0:
                        port = {}
                    elif depth > 0:
                        port[depth - 1] = x['port']
                        cport = copy.copy(port)
                    item = []
                    item.append(int(m.group('bus')))
                    item.append(int(x['dev']))
                    item.append(x['class'])
                    item.append(x['speed'])
                    item.append(x['If'])
                    item.append(cport)
                    ret.append(item)
        return ret

    def parseUsbDevs(self, outs):

        ret = []
        devp = re.compile('''
                          (?:^Bus\s+?)
                          (?P<bus>\d+)
                          \s
                          (?:Device\s+?)
                          (?P<dev>\d+?)
                          :\s+ID\s+
                          (?P<vid>[^:]+)
                          :
                          (?P<pid>\S+)
                          \s+
                          (?P<name>.+?$)
                          ''', re.M | re.X)
        for m in devp.finditer(outs):
            if m.group('name'):
                item = []
                item.append(m.group('name'))
                item.append(int(m.group('bus')))
                item.append(int(m.group('dev')))
                item.append(m.group('vid'))
                item.append(m.group('pid'))
            ret.append(item)

        return ret


usbDisk = collections.namedtuple('usbDisk', ('part', 'type', 'mountpoint'))

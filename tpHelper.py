#!/bin/env python
import optparse
import cups
import random

class PDFPrinter:
    def __init__(self, device='cups-pdf:/', prefix='testpdf', minindex=1, number=30):
        self.device = device
        self.prefix = prefix
        self.index = minindex
        self.num = number
        self.conn = cups.Connection()
        devs = self.conn.getDevices()
        if device not in devs:
            raise "you don't have %s device installed" % device
        self.pdfppd = self.__getPdfPpd()

    def __getPdfPpd(self):
        ppds = self.conn.getPPDs()
        for i in ppds.keys():
            if i.find('CUPS-PDF.ppd') != -1:
                return i

    def listPrinter(self):
        self.printers = self.conn.getPrinters()
        for p in self.printers:
            print p

    def addPrinter(self):
        for i in xrange(self.index, self.num+self.index):
            pname = "%s%s" % (self.prefix, i)
            print "adding %s" % pname
            self.conn.addPrinter(name=pname, \
                            device=self.device, ppdname=self.pdfppd)
            self.conn.enablePrinter(pname)
            self.conn.acceptJobs(pname)

    def delPrinter(self):
        for i in xrange(self.index, self.num+self.index):
            pname = "%s%s" % (self.prefix, i)
            print "deleting %s" % pname
            try:
                self.conn.deletePrinter(pname)
            except:
                pass

    def setDefault(self, name='testpdf'):
        self.conn.setDefault(name)

    def getDefault(self):
        return self.conn.getDefault()

    def togglePrinter(self, printer_list, enable=True):
        for i in printer_list:
            if enable:
                self.conn.enablePrinter(i)
            else:
                self.conn.disablePrinter(i)

    def testPrinter(self, printer_list):
        for i in printer_list:
            try:
                self.conn.printTestPage(i)
            except:
                pass

    def changeDefaultPrinter(self):
        self.oldDefault = self.GetDefault()
        idx = random.choice(range(1, 6))
        self.newDefault = "%s%d" % (self.prefix, idx)
        while(self.oldDefault):
           if self.newDefault != self.oldDefault:
               break
           else:
               idx = random.choice(range(1, 6))
               self.newDefault = "%s%d" % (self.prefix, idx)

        self.SetDefault(self.newDefault)


def getOptions():
    parser = optparse.OptionParser(version='1.0')
    parser.add_option('-l', '--list',
                      dest='list_printer',
                      action='store_true',
                      help='list all printers',
                      default=False)
    parser.add_option('-a', '--add',
                      dest='add_printer',
                      action='store_true',
                      help='add printers ',
                      default=False)
    parser.add_option('-d', '--del',
                      dest='del_printer',
                      action='store_true',
                      default=False)
    parser.add_option('-n', '--num',
                      dest='number',
                      type=int,
                      action='store',
                      default=30)
    parser.add_option('--min',
                      dest='minindex',
                      type=int,
                      action='store',
                      default=1)
    parser.add_option('--enable',
                      action='append',
                      help='enable printers',
                      default=[],
                      dest='enable_list')
    parser.add_option('--disable',
                      action='append',
                      help='disable printers',
                      default=[],
                      dest='disable_list')
    parser.add_option('-t', '--test',
                      action='append',
                      help='test printers',
                      default=[],
                      dest='test_list')
    parser.add_option('-s', '--set_default',
                      dest='set_printer',
                      default=None,
                      help='set default printer',
                      action='store'),
    parser.add_option('-g', '--get_default',
                      dest='get_printer',
                      help='get default printer',
                      default=False,
                      action='store_true'),
    opts, args = parser.parse_args()
    return (opts, args)


def main():
    opts, args = getOptions()
    pdfprinter = PDFPrinter(minindex=opts.minindex, number=opts.number)

    # main logic
    if opts.list_printer:
        pdfprinter.listPrinter()
        return
    if opts.add_printer:
        pdfprinter.addPrinter()
        return
    if opts.del_printer:
        pdfprinter.delPrinter()
        return
    if opts.get_printer:
        defP = pdfprinter.getDefault()
        print "The default printer is %s" % defP
        return
    if opts.set_printer:
        pdfprinter.setDefault(opts.set_printer)
        return
    if opts.enable_list:
        pdfprinter.togglePrinter(opts.enable_list, enable=True)
    if opts.disable_list:
        pdfprinter.togglePrinter(opts.disable_list, enable=False)
    if opts.test_list:
        pdfprinter.testPrinter(opts.test_list)

# Top-level script environment
if __name__ == '__main__':
    main()



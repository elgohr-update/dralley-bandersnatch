from xml.etree import ElementTree
import pep381client
import sys, os, shutil, optparse, hashlib, time

def main():
    opts = optparse.OptionParser(usage="Usage: pep381checkfiles <targetdir>")
    options, args = opts.parse_args()

    if len(args) != 1:
        opts.error("You have to specify a target directory")

    targetdir = args[0]
    incomplete_packages = set()
    for package in os.listdir(os.path.join(targetdir, 'web', 'simple')):
        dir = os.path.join(targetdir, 'web', 'simple', package)
        if not os.path.isdir(dir):
            continue
        try:
            f = open(os.path.join(dir, 'index.html'))
        except IOError:
            print "Missing index.html for", dir
            incomplete_packages.add(package)
            continue
        tree = ElementTree.fromstring(f.read())
        for a in tree.findall(".//a"):
            url = a.attrib['href']
            if not url.startswith('../../packages/'):
                continue
            url, md5 = url.split('#')
            url = url[len('../../'):]
            fn = os.path.join(targetdir, 'web', url)
            if not os.path.exists(fn):
                incomplete_packages.add(package)
                print "Missing file", fn
                continue
            if "md5="+hashlib.md5(open(fn,'rb').read()).hexdigest() != md5:
                print "Bad md5", fn
                continue

    if incomplete_packages:
        s = pep381client.Synchronization.load(targetdir)
        for i in range(10):
            if s.storage.find_running():
                print "Synchronization in progress, waiting"
                time.sleep(10)
            else:
                break
        s.storage.start_running(os.getpid())
        s.storage.commit()
        try:
            # Reload pickled state
            s = pep381client.Synchronization.load(targetdir)
            s.projects_to_do.update(incomplete_packages)
            # claim that a synchronization was aborted and 
            # needs to be restarted
            s.last_started = s.last_completed
            s.store()
        finally:
            s.storage.end_running()
            s.storage.commit()
        print "Todo list updated; run pep381run now"

#
# rpmhelper.py - rpm helper functions
#
# Levin Du <zsdjw@21cn.com>
#
# Copyright 2007 Magic Linux Group
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import os
from misclib import *

def compare_version(ver1, ver2):
    """Compare version ver1 and ver2.
    version can cotain non-digitals."""
    def _split_verion(ver):
        r = []
        pos = -1
        for i in range(len(ver)):
            if ver[i]>="0" and ver[i]<="9":
                if pos < 0:
                    pos = i
            else:
                if pos >= 0:
                    r.append(ver[pos:i])
                    pos = -1
                r.append(ver[i])

        if pos >= 0:
            r.append(ver[pos:])
        return r

    if ver1 is None:
        if ver2 is None:
            return 0
        else:
            return -1
    else:
        if ver2 is None:
            return 1

    vlist1 = _split_verion(ver1)
    vlist2 = _split_verion(ver2)
    n = min(len(vlist1), len(vlist2))
    for i in range(n):
        try:
            int_ver1 = int(vlist1[i])
            int_ver2 = int(vlist2[i])
            r = cmp(int(vlist1[i]), int(vlist2[i]))
            if r != 0:
                return r
        except ValueError:
            r = cmp(vlist1[i], vlist2[i])
            if r != 0:
                return r
    r = cmp(len(vlist1), len(vlist2))
    return r

class RpmHelperError(Exception):
    pass

class RpmBasicInfo:
    """Basic info about rpm, contains (name, epoch, version, release, arch, fullname)"""
    _attrs = {"name":0, "epoch":1, "version":2, "release":3, "arch":4, "fullname":5}

    def __init__(self, nevra = None):
        """ @nevra = (name, epoch, version, release, arch, fullname) """
        self.nevra = nevra

    def __getattr__(self, k):
        """ handy use like basic_info.name, basic_info.arch."""
        if self.nevra == None:
            raise RuntimeError, "nevra not initialized yet."
        if k in RpmBasicInfo._attrs:
            return self.nevra[RpmBasicInfo._attrs[k]]
        raise AttributeError, k

    def __str__(self):
        return self.fullname

    def __cmp__(self, other):
        if other==None:
            return 1
        if self.name != other.name:
            raise RpmHelperError, \
                  "Cannot compare rpms with different names: %s and %s." \
                  % (self.name, other.name)
        r = compare_version(self.version, other.version)
        if r != 0:
            return r
        r = compare_version(self.release, other.release)
        if r != 0:
            return r
        return 0

def parseFilename(rpm_fullname):
    """Parse full rpm filename and return RpmBasicInfo object. """
    def _getPrevToken(str, sep):
        pos = str.rfind(sep)
        if pos != -1:
            return (str[:pos], str[pos+1:])
        else:
            return (str, None)

    rest = rpm_fullname
    (rest, part) = _getPrevToken(rest, ".")
    if part != "rpm":
        return None
    (rest, part) = _getPrevToken(rest, ".")
    is_src = part == "src"
    if is_src:
        arch = None
    else:
        arch = part
    (rest, release) = _getPrevToken(rest, "-")
    (rest, version) = _getPrevToken(rest, "-")
    name = rest
    return RpmBasicInfo((name, None, version, release, arch, rpm_fullname))

def make_rpmlist_from_html(html_str):
    from HTMLParser import HTMLParser
    class MyHTMLParser(HTMLParser):
        def __init__(self):
            self.href_list = []
            HTMLParser.__init__(self)

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                for attr, val in attrs:
                    if attr=="href":
                        self.href_list.append(val)

    parser = MyHTMLParser()
    parser.feed(html_str)
    rpmfn_list = []
    for link in parser.href_list:
        if link.endswith(".rpm"):
            rpmfn_list.append(link)
    del parser
    return rpmfn_list

def make_rpmlist_from_text(txt_str):
    rpmfn_list = []
    for fn in txt_str.split("\n"):
        if fn.endswith(".rpm"):
            rpmfn_list.append(os.path.basename(fn))
    return rpmfn_list

def make_rpmlist_from_dir(dir):
    rpmfn_list = []
    import glob
    dir = os.path.expanduser(dir)
    for fn in glob.glob(os.path.join(dir, "*.rpm")):
        rpmfn_list.append(os.path.basename(fn))
    return rpmfn_list

def make_rpmlist_from_rpm(root):
    import rpm
    ts = rpm.TransactionSet(root)
    mi = ts.dbMatch()
    rpmfn_list = []
    for hdr in mi:
        rpmfn_list.append("%s-%s-%s.%s.rpm" % \
                          (hdr["name"],
                           hdr["version"],
                           hdr["release"],
                           hdr["arch"]))
    del mi
    del ts
    return rpmfn_list

def sort_rpmlist(rpmlist):
    d = {}
    for rpm_item in rpmlist:
        if type(rpm_item) == tuple:
            o = parseFilename(rpm_item[0])
            d.setdefault(o.name, []).append((o, rpm_item[1]))
        else:
            o = parseFilename(rpm_item)
            d.setdefault(o.name, []).append(o)
    for k in d.keys():
        if len(d[k]) > 1:
            d[k].sort(reverse=True)
    return d

def diff_rpmlist(rpmlist1, rpmlist2, full_sync = True):
    """ Compare rpm list 1 & 2.
    rpmlist1 - [ "rpm filename", ... ]
    rpmlist2 - [ "rpm filename", ... ]

    Return [(rpm1, rpm2), ...]. rpm1 and rpm2 is object of RpmBasicInfo.
    (rpm1, None) - rpm1 shall be deleted (not exists in rpmlist2).
    (rpm1, rpm2) - rpm1 shall be updated to rpm2.
    (None, rpm2) - rpm2 shall be added. """
    d1 = sort_rpmlist(rpmlist1)
    d2 = sort_rpmlist(rpmlist2)

    r = []
    for rpm_name in unique(d1.keys(), d2.keys()):
        if rpm_name in d1:
            r1 = d1[rpm_name][0]
        else:
            r1 = None
        if rpm_name in d2:
            r2 = d2[rpm_name][0]
        else:
            if not full_sync:
                continue
            else:
                r2 = None

        if not (r1 is not None and r2 is not None and r1 == r2):
            r.append((r1, r2))
    return r

def diff_rpmlist_with_data(rpmlist1, rpmlist2):
    """ Compare rpm list 1 & 2.
    rpmlist1 - [ ("rpm filename1", data1), ... ]
    rpmlist2 - [ ("rpm filename2", data2), ... ]

    Return [((rpm1, data1), (rpm2, data2)), ...]. rpm1 and rpm2 is object of RpmBasicInfo.

    ((rpm1, data1), (None, None )) - rpm1 shall be deleted (not exists in rpmlist2).
    ((rpm1, data1), (rpm2, data2)) - rpm1 shall be updated to rpm2.
    ((None, None ), (rpm2, data2)) - rpm2 shall be added. """
    d1 = sort_rpmlist(rpmlist1)
    d2 = sort_rpmlist(rpmlist2)

    r = []
    for rpm_name in unique(d1.keys(), d2.keys()):
        if rpm_name in d1:
            r1 = d1[rpm_name][0]
        else:
            r1 = (None, None)
        if rpm_name in d2:
            r2 = d2[rpm_name][0]
        else:
            r2 = (None, None)
        if not (r1[0] is not None and r2[0] is not None and r1[0] == r2[0]):
            r.append((r1, r2))
    return r

def read_from_location(location):
    """location can be directory, url, html, plain text file, or even stdin "-"
    """
    content_type = "text"
    if location == "-":
        s = sys.stdin.read()

    elif location.startswith("http://"):
        import urllib
        try:
            s = urllib.urlopen(location).read()
        except:
            print "Error reading from %s." % location
            raise
        content_type = "html"

    elif os.path.isdir(location):
        s = make_rpmlist_from_dir(location)
        content_type = "list"

    elif os.path.isfile(location):
        s = open(location, "r").read()
        if os.path.splitext(location)[1].lower() in (".htm",".html"):
            content_type = "html"

    elif location.startswith("rpm:"):
        location = location[len("rpm:"):]
        if not location:
            location = '/'
        s = make_rpmlist_from_rpm(location)
        content_type = "list"

    else:
        raise RuntimeError, "Unknown location %s." % location

    if content_type == "html":
        s = make_rpmlist_from_html(s)

    elif content_type == "text":
        s = make_rpmlist_from_text(s)

    return s

def get_location_type(location):
    loc_type = "unknown"
    if location.startswith("http://"):
        loc_type = "http"
    elif location.startswith("rpm:"):
        loc_type = "rpm"
    elif os.path.isdir(location):
        loc_type = "dir"
    return loc_type

## magicrpm.py
### Imports
import snack
import os
import shutil
import ConfigParser
import types
import time
import subprocess

### Global variables
backup_path = ""
pull_repos = {}
local_repo = os.getcwd()

### Utility
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

def unique(*s):
    """Return a list of the elements in s, but without duplicates.

    For example, unique([1,2,3,1,2,3]) is some permutation of [1,2,3],
    unique("abcabc") some permutation of ["a", "b", "c"], and
    unique(([1, 2], [2, 3], [1, 2])) some permutation of
    [[2, 3], [1, 2]].

    For best speed, all sequence elements should be hashable.  Then
    unique() will usually work in linear time.

    If not possible, the sequence elements should enjoy a total
    ordering, and if list(s).sort() doesn't raise TypeError it's
    assumed that they do enjoy a total ordering.  Then unique() will
    usually work in O(N*log2(N)) time.

    If that's not possible either, the sequence elements must support
    equality-testing.  Then unique() will usually work in quadratic
    time.
    """
    if len(s) == 0:
        return []

    # Try using a dict first, as that's the fastest and will usually
    # work.  If it doesn't work, it will usually fail quickly, so it
    # usually doesn't cost much to *try* it.  It requires that all the
    # sequence elements be hashable, and support equality comparison.
    u = {}
    try:
        for y in s:
            for x in y:
                u[x] = 1
    except TypeError:
        del u  # move on to the next method
    else:
        return u.keys()

    # We can't hash all the elements.  Second fastest is to sort,
    # which brings the equal elements together; then duplicates are
    # easy to weed out in a single pass.
    # NOTE:  Python's list.sort() was designed to be efficient in the
    # presence of many duplicate elements.  This isn't true of all
    # sort functions in all languages or libraries, so this approach
    # is more effective in Python than it may be elsewhere.
    try:
        t = []
        for y in s:
            t.extend(list(y))
        t.sort()
    except TypeError:
        del t  # move on to the next method
    else:
        n = len(t)
        assert n > 0
        last = t[0]
        lasti = i = 1
        while i < n:
            if t[i] != last:
                t[lasti] = last = t[i]
                lasti += 1
            i += 1
        return t[:lasti]

    # Brute force is all that's left.
    u = []
    for y in s:
        for x in y:
            if x not in u:
                u.append(x)
    return u

def run_cmd_silent(*args):
#     f = open("/dev/null", "rw")
#     null_fd = f.fileno()
#     result = subprocess.call(args, stdin = null_fd,
#                              stdout = null_fd,
#                              stderr = null_fd)
#     f.close()
    result = subprocess.call(args)
    return result

### Rpm helper
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

def make_rpmlist_from_rpm():
    import rpm
    ts = rpm.TransactionSet()
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
        s = make_rpmlist_from_rpm()
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

### Common UI code
class BaseUI:                           # Base UI class
    MB_OK = "ok"
    MB_CANCEL = "cancel"
    MB_YES = "yes"
    MB_NO = "no"
    MB_OKCANCEL = [MB_OK, MB_CANCEL]
    MB_YESNO = [MB_YES, MB_NO]
    MB_YESNOCANCEL = [MB_YES, MB_NO, MB_CANCEL]

    _MB_DISP = {
        MB_OK: "Ok",
        MB_CANCEL: "Cancel",
        MB_YES: "Yes",
        MB_NO: "No",
        }

    _MB_HOTKEY = {
        MB_CANCEL: "ESC",
        }

    def _NormalizeButtons(self, raw_buttons):
        "Formalize to [(key, disp), ...]"
        if type(raw_buttons) not in (types.ListType, types.TupleType):
            raw_buttons = [raw_buttons]
        result = []
        for button in raw_buttons:
            if type(button) is types.TupleType:
                result.append((button[0], button[1]))
            else:
                try:
                    disp_value = self._MB_DISP[button]
                except KeyError:
                    disp_value = button
                    button = button.lower()
                try:
                    hot_key = self._MB_HOTKEY[button]
                except KeyError:
                    hot_key = None
                if hot_key:
                    result.append((disp_value, button, hot_key))
                else:
                    result.append((disp_value, button))
        return result

    def MessageBox(self, title, prompt, buttons = MB_OK):
        pass

    def ProgressWindow(self, title, prompt):
        """Return a progress window instance, with methods of:
            def update(self, progress, prompt)
            def popup(self)
            """
        raise NotImplemented()

    def ListboxChoiceWindow(self, title, prompt,
                            list_items, # [("Display", "key"), ("Clean", "clean")]
                            buttons = MB_OKCANCEL):
        raise NotImplemented()

    def InputBox(self, title, prompt, label_value_list):
        raise NotImplemented()

    def ErrorBox(self, prompt, buttons = MB_OK):
        return self.MessageBox("Error", prompt, buttons)

    def WarningBox(self, prompt, buttons = MB_OK):
        return self.MessageBox("Warning", prompt, buttons)

    def InfoBox(self, prompt, buttons = MB_OK):
        return self.MessageBox("Info", prompt, buttons)

    def ConfirmBox(self, prompt):
        return self.MessageBox("Confirm", prompt, self.MB_YESNO) == self.MB_YES

    def debug(self, arg):
        print arg

# Some injection to snack
snack.hotkeys["ESC"] = 27        # Esc key
snack.hotkeys[27] = "ESC"

class TextUI(BaseUI):
    screen = None

    def __init__(self):
        if not TextUI.screen:
            TextUI.screen = snack.SnackScreen()

    def cleanup(self):
        if TextUI.screen:
            TextUI.screen.finish()
            TextUI.screen = None

    def MessageBox(self, title, text, buttons = BaseUI.MB_OK, width=30):
        buttons = self._NormalizeButtons(buttons)
        return snack.ButtonChoiceWindow(self.screen, title, text,
                                        buttons, width)

    def ListboxChoiceWindow(self, title, prompt,
                            list_items, # [("Clean", "clean"), ("Display", "key")]
                            buttons = BaseUI.MB_OKCANCEL,
                            width = 30):
        buttons = self._NormalizeButtons(buttons)
        return snack.ListboxChoiceWindow(self.screen, title, prompt,
                                         list_items, buttons, width, default = 0)

    def InputBox(self, title, prompt, label_value_list, entryWidth = 20):
        label_entry = []
        for label, value in label_value_list:
            label_entry.append((label, value))
        buttons = self._NormalizeButtons(self.MB_OKCANCEL)
        return snack.EntryWindow(self.screen, title, prompt,
                                 label_entry,
                                 buttons = buttons,
                                 entryWidth = entryWidth)

    def ProgressWindow(self, title, prompt, width=0):
        class _ProgressWindow:
            def __init__(self, screen, title, prompt,
                         width = 40):
                self.screen = screen
                self.label = snack.Label(prompt)
                self.scale = snack.Scale(width - 4, 100)
                self.grid = snack.GridFormHelp(screen, title, help, 1, 2)
                self.grid.add(self.label, 0, 0, anchorLeft = 1)
                self.grid.add(self.scale, 0, 1)
                self.grid.draw()
                self.screen.refresh()

            def update(self, progress, text = None):
                self.scale.set(progress)
                if text:
                    self.label.setText(text)
                self.screen.refresh()

            def popup(self):
                self.screen.popWindow()

        if not width:
            width = self.screen.width * 3 / 4
        return _ProgressWindow(self.screen, title, prompt, width)

    def debug(self, arg):
        self.screen.suspend()
        print arg
        time.sleep(5)
        self.screen.resume()

### App Logic code
def get_rpm_clean_list():
    result = []
    rpmfn_list = make_rpmlist_from_dir(local_repo)
    rpmfn_map = sort_rpmlist(rpmfn_list)
    for li in rpmfn_map.values():
        if len(li) > 1:
            result.append((li[0].fullname, 0))
            for i in range(1, len(li)):
                result.append((li[i].fullname, 1))
    return result

def check_backup_path(path, ui, edit_mode = False):
    if not path.strip() or edit_mode:
        result = ui.InputBox("Backup path",
                                  "Please input backup path:",
                                  (("Path:", path),))
        if result[0] != ui.MB_OK:
            return (False, path)

        path = result[1][0].strip()
        if not path:
            ui.ErrorBox("Input empty!")
            return (False, path)

    path = path.strip()
    if os.path.exists(path):
        if not os.path.isdir(path):
            ui.ErrorBox("'%s' is not a directory!" % path)
            return (False, path)

    else:
        result = ui.MessageBox("Confirm",
                                  "Directory '%s' not exists. Create?" % path,
                                  ui.MB_YESNO)
        if result != "yes":
            return (False, path)

        try:
            os.makedirs(path)
        except OSError, e:
            ui.ErrorBox("Make directory failed: %s" % str(e))
            return (False, path)

    return (True, path)

def check_repo_url(url, ui):
    url = url.strip()
    if not url:
        ui.ErrorBox("Input empty!")
        return False

    loc_type = get_location_type(url)

    if loc_type not in ("http", "dir"):
        ui.ErrorBox("Directory not exists or URL is invalid.")
        return False

    return True

def fetch_rpm_update_list(repo1_path, repo2_path, ui):
    progress_win = ui.ProgressWindow("Get update list",
                                     "Fetching rpm list from %s..." % repo2_path,
                                     width = ui.screen.width * 3 / 4)
    try:
        rpm_list2 = read_from_location(repo2_path)
    except Exception, e:
        progress_win.popup()
        ui.ErrorBox(("Pull error: %s" % str(e)))
        return None

    progress_win.update(50, "Fetching rpm list from %s..." % repo1_path)
    rpm_list1 = make_rpmlist_from_dir(repo1_path)

    progress_win.update(60, "Caculating difference...")
    diff_list = diff_rpmlist(rpm_list1, rpm_list2, full_sync = False)

    progress_win.update(80)
    result = {}
    for local, remote in diff_list:
        if local:
            if local < remote:
                result[remote.fullname] = local.fullname
        else:
            result[remote.fullname] = None
    del diff_list
    progress_win.popup()

    return result

### App UI
class CleanRpmWindow(TextUI):
    def __init__(self):
        TextUI.__init__(self)

    def __call__(self):
        global backup_path
        clean_list = get_rpm_clean_list()
        if not clean_list:
            self.InfoBox("No files need cleaning.")
            return

        screen = self.screen
        chktree = snack.CheckboxTree(height = screen.height - 10,
                                     scroll = 1)
        for rpm, sel in clean_list:
            chktree.append(rpm, selected = sel)

        grid = snack.GridForm(screen, "Clean Rpm Old Files", 1, 2)
        grid.add(chktree, 0, 0, growx = 1, growy = 1)

        buttons = snack.ButtonBar(screen, self._NormalizeButtons(["Clean", self.MB_CANCEL]))
        grid.add(buttons, 0, 1, growx = 1)

        while True:
            result = grid.run()

            if buttons.buttonPressed(result) != "clean":
                screen.popWindow()
                return

            selection = chktree.getSelection()

            if not selection:
                self.WarningBox("No files selected. Please select some.")
                continue

            result, backup_path = check_backup_path(backup_path, self)
            if not result:
                continue

            break

        screen.popWindow()

        self.do_backup(selection)

    def do_backup(self, selection):
        progress_win = self.ProgressWindow("Moving files to %s" % backup_path,
                                           "Preparing...")
        num = len(selection)
        for i, fn in enumerate(selection):
            progress_win.update(i * 100 / num,
                                "(%d/%d) %s" % (i+1, num, fn))
            shutil.move(fn, os.path.join(backup_path, fn))
            time.sleep(0.01)
        progress_win.popup()

        self.screen.refresh()
        self.InfoBox("All Done!")

class PullRpmWindow(TextUI):
    def __init__(self):
        TextUI.__init__(self)

    def __call__(self):
        if not pull_repos:
            self.ErrorBox("Please define pull repos in Option first.")
            return

        while True:
            repos = pull_repos.keys()
            choose = self.ListboxChoiceWindow("Pull Rpms", "Please select repos:",
                                              repos,
                                              buttons = (("Pull", "pull"),
                                                         self.MB_CANCEL),
                                              width = 30)
            if choose[0] == "cancel":
                break

            self.pull_repo(repos[choose[1]])

    def pull_repo(self, repo):
        global backup_path
        screen = self.screen

        update_list = fetch_rpm_update_list(local_repo, pull_repos[repo], self)
        if not update_list:
            self.InfoBox("%s is already up to date." % local_repo)
            return

        chktree = snack.CheckboxTree(height = screen.height - 12,
                                     scroll = 1)
        item_list = []
        for k, v in update_list.items():
            if v:
                chktree.append("U %s" % k, selected = 1)
                item_list.append("U %s" % k)
                chktree.append("D %s" % v, selected = 1)
                item_list.append("D %s" % v)
            else:
                chktree.append("N %s" % k, selected = 1)
                item_list.append("N %s" % k)

        grid = snack.GridForm(screen, "Clean Rpm Old Files", 1, 2)
        grid.add(chktree, 0, 0, growx = 1, growy = 1)

        buttons = snack.ButtonBar(screen,
                                  self._NormalizeButtons(["Update",
                                                          "SelectAll", 
                                                          "SelectNone", 
                                                          "SelectUpdate", 
                                                          self.MB_CANCEL]))
        grid.add(buttons, 0, 1, growx = 1)

        while True:
            result = grid.run()

            button = buttons.buttonPressed(result)
            if button in ("selectall", "selectnone"):
                for i in item_list:
                    chktree.setEntryValue(i, button == "selectall")
                continue
            
            elif button == "selectupdate":
                for i in item_list:
                    chktree.setEntryValue(i, i[0] != 'N')
                continue
            
            elif button == "cancel":
                screen.popWindow()
                return

            selection = chktree.getSelection()

            if not selection:
                self.WarningBox("No files selected. Please select some.")
                continue

            result, backup_path = check_backup_path(backup_path, self)
            if not result:
                continue

            break

        screen.popWindow()

        self.do_update_repo(repo, selection)

    def do_update_repo(self, repo, selection):
        loc = pull_repos[repo]
        loc_type = get_location_type(loc)

        progress_win = self.ProgressWindow("Updating File",
                                           "")
        num = len(selection)
        for i, k in enumerate(selection):
            act = k[0]
            fn = k[2:]
            if act in ("U", "N"):
                msg = "Downloading %s"
            else:
                msg = "Removing %s"
            progress_win.update(i * 100 / num,
                                ("(%d/%d) " + msg) % (i+1, num, fn))
            if act in ("U", "N"):
                if loc_type == "dir":
                    shutil.copy(os.path.join(loc, fn), local_repo)
                elif loc_type == "http":
                    self.screen.suspend()
                    status = run_cmd_silent("wget",
                                            os.path.join(loc, fn))
                    self.screen.resume()
                    if status:
                        os.unlink(fn)
                        if not self.ConfirmBox("Wget '%s' failed. Continue?" % fn):
                            break
            else:
                shutil.move(fn, os.path.join(backup_path, fn))

            time.sleep(0.01)

        progress_win.popup()
        self.screen.refresh()
        self.InfoBox("All Done!")

class OptionWindow(TextUI):
    def __init__(self):
        TextUI.__init__(self)

    def __call__(self):
        while True:
            choose = self.ListboxChoiceWindow("Option Menu", "Please select:",
                                              [("Pull Repos", "pull_repos"),
                                               ("Backup Path", "backup_path")],
                                              width = 30)
            if choose[0] == self.MB_CANCEL:
                break

            if choose[1] == "backup_path":
                check_backup_path(backup_path, self, edit_mode = True)

            elif choose[1] == "pull_repos":
                self.edit_repos()

    def edit_repos(self):
        """
List box

Add Edit Delete Cancel
        """
        screen = self.screen

        while True:
            listbox = snack.CListbox(screen.height - 10,
                                     2,
                                     (20, 40),
                                     scroll = 1,
                                     returnExit = 1,
                                     col_labels = ("Name", "Path"),
                                     adjust_width = 1)
            for name, path in pull_repos.items():
                listbox.append((name, path), name)

            grid = snack.GridForm(screen, "Repos Setup", 1, 2)
            grid.add(listbox, 0, 0, growx = 1, growy = 1)

            buttons = snack.ButtonBar(screen, self._NormalizeButtons([("Add", "add"),
                                               ("Edit", "edit"),
                                               ("Remove", "remove"),
                                               self.MB_CANCEL]))
            grid.add(buttons, 0, 1, growx = 1)

            result = grid.runOnce()

            button = buttons.buttonPressed(result)
            if not pull_repos:
                repo = None
            else:
                repo = listbox.current()

            if button == "cancel":
                break

            elif repo and button in (None, "edit"):
                self.edit_repo(repo)

            elif repo is None or button == "add":
                self.add_repo()

            elif repo and button == "remove":
                self.remove_repo(repo)

    def edit_repo(self, repo):
        result = self.InputBox("Edit repo %s" % repo,
                                  "Please input repo url:",
                                  (("Url:", pull_repos[repo]),))
        if result[0] == self.MB_OK:
            url = result[1][0].strip()
            if check_repo_url(url, self):
                pull_repos[repo] = url

    def add_repo(self):
        result = self.InputBox("Add repo",
                                  "Please input repo name and url:",
                                  (("Name:", ""),
                                   ("Url:", "")))
        if result[0] == self.MB_OK:
            repo = result[1][0]
            url = result[1][1]
            if repo in pull_repos:
                result = self.MessageBox("Confirm",
                                            "Repo '%s' already exists, replace?" % repo,
                                            self.MB_OKCANCEL)
                if result[0] != self.MB_OK:
                    return

            if check_repo_url(url, self):
                pull_repos[repo] = url


    def remove_repo(self, repo):
        result = self.MessageBox("Confirm",
                                 "Really remove repo '%s'?" % repo,
                                 self.MB_OKCANCEL)

        if result == self.MB_OK:
            del pull_repos[repo]

def load_config():
    global backup_path, pull_repos
    if os.path.exists(".magicrpm.rc"):
        parser = ConfigParser.ConfigParser()
        parser.read(".magicrpm.rc")
        try:
            backup_path = parser.get("clean", "backup_path")
        except (ConfigParser.NoSectionError,
                ConfigParser.NoOptionError), e:
            backup_path = ""
            raise
        try:
            pull_repos = dict(parser.items("pull"))
        except ConfigParser.NoSectionError, e:
            pull_repos = {}
            raise

def save_config():
    parser = ConfigParser.ConfigParser()
    parser.add_section("clean")
    parser.set("clean", "backup_path", backup_path)
    parser.add_section("pull")
    for k, v in pull_repos.items():
        parser.set("pull", k, v)
    try:
        f = open(".magicrpm.rc", "wb")
        parser.write(f)
    except Exception, e:
        print "Save config error."
        raise
    f.close()

def main():
    load_config()
    ui = TextUI()

    try:
        while True:
            choose = ui.ListboxChoiceWindow("Main Menu", "Please select: ",
                                            [("Pull", "pull"),
                                             ("Clean", "clean"),
                                             ("Option", "option")],
                                            buttons = [("Run", "run"),
                                                       ui.MB_CANCEL],
                                            width = 30)

            if choose[0] == ui.MB_CANCEL:
                break

            elif choose[1] == "clean":
                CleanRpmWindow()()

            elif choose[1] == "pull":
                PullRpmWindow()()

            elif choose[1] == "option":
                OptionWindow()()

    except Exception, e:
        ui.cleanup()
        raise
        save_config()
    else:
        ui.cleanup()
        save_config()

if __name__ == "__main__":
    main()

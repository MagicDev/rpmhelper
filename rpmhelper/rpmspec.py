import re
import subprocess

'''
 - [X] parse defines of `rpmbuild --showrc`
 - [X] %{PACKAGE_VERSION} # logrotate.spec
 - [X] %{!?_prefix:/usr} # rpm.spec
 - [X] %{?_prefix:%{_prefix}} will failed, use %{?_prefix} instead
 - [X] %define pythonver %(%{__python} -c "import sys; print sys.version[:3]") # newt.spec
 - [X] %{SOURCE999} # samba.spec
 - [X] %define cytune_archs %{ix86} alpha armv4l  # util-linux.spec
 - [X] %{!?kernel: %{expand: %%define kernel %(uname -r)}}  # union.spec
 - [X] %{expand:%%global optflags %{optflags} -D_GNU_SOURCE=1} # coreutils.spec

'''

tag_re      = re.compile(r'%\{(?P<cond>[?!]*)(?P<tag>[^:}{]+)(?::(?P<body>[^}{]+))?\}')
cond_tag_re = re.compile(r'%\{(?P<cond>[?!]*)(?P<tag>[^:%{}]+).*')
define_re = re.compile(r'\s*%%?(?:define|global)\s+(\S+)\s+(.*)')

def parse_define(line, defines):
    m = define_re.match(line)
    if m:
        name, value = m.group(1, 2)
        defines[name.lower()] = value
        #print '%define', name, '->', value
        return value
    else:
        return ''

def _subst_func(match, defines):
    '''The condition macros:
%{?dist}
{dist} if dist is defined

%{?_buildshell:%{_buildshell}}%
%{_buildshell} if _buildshell is defined

{!?_buildshell:/bin/sh}
/bin/sh if _buildshell is NOT defined
    '''
    cond, tag, body = match.group('cond', 'tag', 'body')
    tag = tag.lower()
    if tag == 'expand':
        val = body
    else:
        try:
            val = defines[tag]
        except KeyError:
            if not cond:
                raise KeyError('%%{%s} not defined' % tag)
            elif cond == '?':
                val = ''
            elif cond in ('!?', '?!'):
                val = '1'
            else:
                raise RuntimeError('%%{%s%s} not support' % \
                                       (cond, tag))
        else:
            if cond == '!?':
                val = ''
        if body is not None and val:
            val = body
    # {?def:%%define x 1}
    return parse_define(val, defines) or val

def subst_define(value, defines):
    orig_value = value
    stack = []                  #  (pos, left, cond)
    i = 0
    expand_count = 0
    while i < len(value) and expand_count < 100:
        # print 'I, C, Stack: ', i, value[i], stack

        if value[i] == '"':
            i += 1
            while i < len(value) and value[i] != '"':
                i += 1
            i += 1
            continue
            
        elif value[i] == '%' \
                and i + 1 < len(value) \
                and value[i+1] in '({':
            if value[i+1] == '{':
                match = cond_tag_re.match(value[i:])
                if match:
                    cond, tag = match.group('cond', 'tag')
                    tag = tag.lower()
                    if not cond:
                        stack.append((i, '{', True))
                    elif cond == '?':
                        stack.append((i, '{', tag in defines))
                    elif cond in ('!?', '?!'):
                        stack.append((i, '{', tag not in defines))
                    else:
                        raise RuntimeError('%%{%s%s...} not support' % \
                                               (cond, tag))
            else:
                stack.append((i, '(', True))
        
        elif value[i] in ')}' and stack:
            # check if a match
            pos, left, cond = stack[-1]
            right = value[i]
            if left == '(' and right == ')':
                shell_cmd = value[pos+2:i]
                # print 'Shell command:', shell_cmd
                result = subprocess.Popen(shell_cmd,
                                          stdout = subprocess.PIPE,
                                          shell = True). \
                                          communicate()[0]
                result = result.rstrip('\r\n')
                value = value[:pos] + result + value[i+1:]
                i = pos + len(result)
                stack.pop()
                continue

            elif left == '{' and right == '}':
                part = value[pos:i+1]
                # print 'Macro:', part
                for _pos, _left, _cond in stack:
                    if _left == '{' and not _cond:
                        # do not expand, let's make it empty
                        value = value[:pos] + value[i+1:]
                        i = pos
                        break
                else:
                    result = tag_re.sub(lambda match: \
                                            _subst_func(match, defines),
                                        part)
                    value = value[:pos] + result + value[i+1:]
                    i = pos         # recursive expand
                    expand_count += 1
                stack.pop()
                continue
        i += 1

    return value

def parse_rpmrc():
    lines = subprocess.Popen(['/bin/rpm', '--showrc'],
                             stdout=subprocess.PIPE).communicate()[0]

    pattern = re.compile('^-1[14]: (\S+)\s+(\S+)')
    result = {}
    for line in lines.split('\n'):
        m = pattern.match(line)
        if m:
            name, value = m.group(1, 2)
            if '%(' in value or '%{expand' in value:
                pass
            elif name == 'nil':
                result[name] = ''
            else:
                result[name] = value
    return result

def parse_spec(spec_file):
    show_tag = ('name', 'url', 'version', 'release',
                'source', 'patch', 'license', 'group')
    result = {}
    defines = parse_rpmrc()
    # strange, PACKAGE_VERSION is defined nowhere
    defines['package_version'] = '%{version}'

    for line in file(spec_file).readlines():
        line = line.strip()
        if not line or line[0] in '#*-':
            continue
        
        if parse_define(line, defines):
           pass
        
        elif line.startswith('%{?') \
                or line.startswith('%{!?') \
                or line.startswith('%{expand:'):
            subst_define(line, defines)

        elif line[0] != '%' and ':' in line:
            name, value = line.split(':', 1)
            name = name.strip().lower()
            value = value.strip()
            for t in show_tag:
                if name.startswith(t):
                    value = subst_define(value, defines)
                    result[name] = value
                    # append to define if not in
                    if name not in defines:
                        defines[name] = value
    return result

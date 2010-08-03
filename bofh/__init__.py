#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2010 University of Oslo, Norway
#
# This file is part of PyBofh.
#
# PyBofh is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBofh is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyBofh; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

import xmlrpclib as _rpc

version = u"0.1"

def get_default_url():
    return "https://cerebrum-uio.uio.no:8000"

def get_default_cert():
    return {}

def connect(username, password, url=None, cert=None):
    """Return a new Bofh() object."""
    return Bofh(username, password, url or get_default_url(), cert or get_default_cert())

class BofhTransport(_rpc.SafeTransport):
    def __init__(self, cert, *rest, **kw):
        _rpc.SafeTransport.__init__(self, *rest, **kw)
        # XXX: do our own cert checking

def _sdt2strftime(format):
    """Simple thing to convert java's simple date format to strftime"""
    reps = (#subst  with
            (u"yyyy", u"%Y"),
            (u"MM", u"%m"),
            (u"dd", u"%d"),
            (u"HH", u"%H"),
            (u"mm", u"%M"))
    return reduce(lambda form, rep: form.replace(*rep), reps, format)

def _washresponse(resp):
    if isinstance(resp, basestring):
        if resp and resp[0] == ':':
            return None if resp == ':None' else resp[1:]
        return unicode(resp, "ISO-8859-1") if isinstance(resp, str) else resp
    elif isinstance(resp, (list, tuple)):
        return [_washresponse(x) for x in resp]
    elif isinstance(resp, dict):
        for i in resp.keys():
            resp[i] = _washresponse(resp[i])
        return resp
    else:
        return resp

def parse_format_suggestion(bofh_response, format_sugg):
    def get_formatted_field(map, field):
        field = field.split(":", 2)
        val = map[field[0]]
        if len(field) == 3:
            if field[1] == 'date':
                format = _sdt2strftime(field[2])
            else:
                raise KeyError(field[1])
            if val is not None:
                return val.strftime(format.encode("ASCII"))
        if val is None:
            return u"<not set>"
        return val

    lst = []
    if "hdr" in format_sugg:
        lst.append(format_sugg["hdr"])
    st = format_sugg['str_vars']
    if isinstance(st, basestring):
        lst.append(st)
    else:
        for row in st:
            if len(row) == 3:
                format, vars, sub_hdr = row
                if u"%" in sub_hdr:
                    format, sub_hdr = sub_hdr, None
            else:
                format, vars  = row
                sub_hdr = None
            if sub_hdr:
                lst.append(sub_hdr)
            if not isinstance(bofh_response, (list, tuple)):
                bofh_response = [bofh_response]
            for i in bofh_response:
                if isinstance(i, basestring):
                    lst.append(i)
                    continue
                try:
                    positions = tuple(get_formatted_field(i, j) for j in vars)
                except KeyError:
                    continue
                lst.append(format % positions)
    return u"\n".join(lst)

class _Argument(object):
    def __init__(self, bofh, map):
        self._bofh = bofh
        self.optional = map.get('optional', False)
        self.repeat = map.get('repeat', False)
        self.default = map.get('default')
        self.type = map.get('type')
        self.help_ref = map.get('help_ref', False)
        self.prompt = map.get('prompt')

    @property
    def help(self):
        if hasattr(self, '_help'):
            return self._help
        else:
            help = self._help = self._bofh.arg_help(self.help_ref)
            return help

#XXX: make a metaclass for commands
class _Command(object):
    def __init__(self, group, name, fullname, args):
        self._group = group
        self._bofh = group._bofh
        self._args = args
        self._format_suggestion = None
        self._help = None
        self._fullname = fullname

    def _get_help(self):
        hlp = self._help
        if hlp is None:
            try:
                hlp = self._help = self._bofh._run_raw_sess_command(
                        "help", self._group._name, self._name)
            except:
                pass
            return hlp
    help = property(_get_help, doc=u"Get help string for command")

    def _get_format_suggestion(self):
        if self._format_suggestion is None:
            self._format_suggestion = self._bofh.get_format_suggestion(self._fullname)
        return self._format_suggestion
    format_suggestion = property(_get_format_suggestion, doc=u"Get format suggestion")

    def __call__(self, *rest, **kw):
        ret = self._bofh.run_command(self._fullname, *rest)
        with_format = not ('with_format' in kw and not kw['with_format'])
        if with_format and not isinstance(ret, basestring):
            return parse_format_suggestion(ret, self.format_suggestion)
        return ret

    @property
    def args(self):
        """Return information about each arg
        Returns a list of dicts: {
            optional: True if optional
            repeat: True if arg is repeatable
            default: string or True if get_default_param should be called
            type: arg type
            help_ref: string to send to help_ref
            prompt: Text to send to prompter for arg
        }"""
        if hasattr(self, '_fixed_args'):
            return self._fixed_args
        ret = self._fixed_args = []
        for arg in self._args:
            ret.append(_Argument(self._bofh, arg))
        return ret

class _CommandGroup(object):
    def __init__(self, bofh, name):
        self._name = name
        self._bofh = bofh
        self._cmds = dict()

    def _add_command(self, cmd, full_cmd, args):
        command = _Command(self, cmd, full_cmd, args)
        self._cmds[cmd] = command
        setattr(self, cmd, command)

    def get_bofh_command_keys(self):
        u"""Get the list of group keys"""
        return self._cmds.keys()

    def get_bofh_command_value(self, key):
        return self._cmds.get(key)

class Bofh(object):
    def __init__(self, username, password, url, cert):
        self._connection = None
        self._groups = dict()
        self._connect(url, cert)
        self._session = self._run_raw_command("login", username, password)
        self._init_commands()

    def _connect(self, url, cert):
        self._connection = _rpc.Server(url, transport=BofhTransport(cert, use_datetime=True), 
                encoding="ISO-8859-1", use_datetime=True)

    def _run_raw_command(self, name, *args):
        fn = getattr(self._connection, name)
        return _washresponse(fn(*args))

    def _run_raw_sess_command(self, name, *args):
        fn = getattr(self._connection, name)
        return _washresponse(fn(self._session, *args))

    # XXX: There are only a handfull of bofhd commands:
    # motd = get_motd(client_name, version)
    # session = login(user, pass)
    # logout(session)
    # get_commands(session) -- see _init_commands
    # help(session) -- general help
    # help(session, "arg_help", ref) -- help on arg type, ref found in arg['help_ref']
    # help(session, group) -- help on group
    # help(session, group, cmd) -- help on command
    # run_command(session, command, args)  # command = group_cmd
    # call_prompt_func(session, command, args) =>
    #   {prompt: string, help_ref: key, last_arg: bool, default: value,
    #    map: [[["Header", None], value], [[format, *args], value], ...],
    #    raw: bool}
    # get_default_param(session, command, args)
    # get_format_suggestion(command)

    def get_motd(self, client=u"PyBofh", version=version):
        "Get message of the day from server"
        return _washresponse(self._connection.get_motd(client, version))

    def login(self, user, password):
        "Log in to server"
        self._session = self._run_raw_command("login", username, password)

    def logout(self):
        self._run_raw_sess_command("logout")
        self._session = None
        #XXX bring down all commands

    def get_commands(self):
        return self._run_raw_sess_command("get_commands")

    def help(self, *args):
        return self._run_raw_sess_command("help", *args)

    def arg_help(self, help_ref):
        return self.help("arg_help", help_ref)

    def run_command(self, command, *args):
        return self._run_raw_sess_command("run_command", command, *args)

    def call_prompt_func(self, command, *args):
        return self._run_raw_sess_command("call_prompt_func", command, *args)

    def get_default_param(self, command, *args):
        return self._run_raw_sess_command("get_default_param", command, *args)

    def get_format_suggestion(self, command):
        return self._run_raw_command("get_format_suggestion", command)

    @property
    def motd(self):
        u"""Get message of the day from bofh server"""
        return _washresponse(self._connection.get_motd(u"pybofh", version))

    def _init_commands(self, reset=False):
        #XXX: reset is set to true if server is restarted, and commands
        # might have changed. It should mean: delete commands not in response
        cmds = _washresponse(self._connection.get_commands(self._session))
        for key, value in cmds.items():
            # key will typically be a string, e.g. "person_info"
            # value is a list,
            # its first element is a list with the splitted command name,
            # e.g. ["person", "info"]
            group, cmd = value[0]
            args = value[1] if len(value) == 2 else []
            if group in self._groups:
                self._groups[group]._add_command(cmd, key, args)
            else:
                grp = _CommandGroup(self, group)
                self._groups[group] = grp
                setattr(self, group, grp)
                grp._add_command(cmd, key, args)

    def get_bofh_command_keys(self):
        u"""Get the list of group keys"""
        return self._groups.keys()

    def get_bofh_command_value(self, key):
        return self._groups.get(key)

def repl(bofh):
    import sys, locale
    while True:
        print "pybofh >>> ",
        line = sys.stdin.readline().decode(locale.getpreferredencoding()).strip().split()
        cmd = bofh
        while line and hasattr(cmd, line[0]):
            cmd = getattr(cmd, line.pop(0))
        try:
            print cmd(*line)
        except:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import getpass
    a = connect(getpass.getuser(), getpass.getpass())
    repl(a)


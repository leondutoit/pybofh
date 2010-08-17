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


__all__ = ['internal_commands', 'parser', 'proto', 'readlineui',
        'version', 'get_default_url', 'get_default_cert', 'connect']
import xmlrpclib as _rpc
from . import proto

def get_default_url():
    return "https://cerebrum-uio.uio.no:8000"

def get_default_cert():
    return {}

def connect(username, password, url=None, cert=None):
    """Return a new Bofh() object."""
    return proto.Bofh(username, password, url or get_default_url(), cert or get_default_cert())


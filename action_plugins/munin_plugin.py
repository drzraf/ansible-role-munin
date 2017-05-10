#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# An Ansible action plugin to manage Munin plugins
# (c) 2016, 2017 Raphaël Droz <raphael.droz@gmail.com>
#
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#
# Examples:

# Symlink a plugin
# - munin_plugin:
#     name: port
#     instance: port_http
#   notify: restart munin-node

# Create a configuration for a named plugin
# - munin_plugin
#     name: multips_memory
#     instance: multips_memory_memcache
#     config: |
#       env.names memcached

# Create a configuration for a class of plugins
# - munin_plugin
#     name: memcached
#     instance: 'default_memcached_multi_*'
#     config: |
#       group www-data
#       env.host unix:///var/run/memcached/memcached.sock

import os, re
from ansible.plugins.action import ActionBase

class ActionModule(ActionBase):

    TRANSFERS_FILES = True

    def run(self, tmp=None, task_vars=None):
        result = super(ActionModule, self).run(tmp, task_vars)

        name = self._task.args.get('name')
        instance = self._task.args.get('instance', name)
        src = self._task.args.get('src', None)
        # must be a directory
        dest = self._task.args.get('dest', None)
        config = self._task.args.get('config', None)
        changed = False

        # Copy plugin file: TODO (dest)
        if src and dest:
            result.update(self._execute_module(module_name='copy',
                                               module_args=dict(src=src, dest=dest),
                                               task_vars=task_vars))
        # Symlink
        if name and not '*' in instance:
            # Intend to "activate" (symlink) the plugin providing a src (but no dest)
            # use it as the plugin source on the remote host
            if src and not dest:
                plugin_path = src
            elif src and dest:
                plugin_path = os.path.join(dest, name)
            else:
                plugin_path = os.path.join(task_vars.get('munin_pluginsdir'), name)

            # Create symlink to plugin.
            path = os.path.join(task_vars.get('munin_activepluginsdir'), instance)
            result.update(self._execute_module(module_name='file',
                                               module_args=dict(state='link', path=path, src=plugin_path),
                                               task_vars=task_vars))

        # Set plugin configuration
        if config:
            plugin_conf = '''# Managed by Ansible

[%s]
%s
''' % (instance, config)
            if not tmp:
                tmp = self._make_tmp_path()
            src = self._transfer_data(self._connection._shell.join_path(tmp, 'source'), plugin_conf)
            dest = os.path.join(task_vars.get('munin_pluginsconfdir'), '%s.conf' % (re.sub(ur"\*", "", instance)))
            result.update(self._execute_module(module_name='copy',
                                               module_args=dict(mode='0600', owner='root', group='root', src=src, dest=dest),
                                               task_vars=task_vars,
                                               tmp=tmp))
        return result

import os

from Pymacs import lisp

import rope.refactor.rename
import rope.refactor.extract
import rope.refactor.inline
from rope.base import project, libutils
from rope.ide import codeassist


class interactive(object):

    def __init__(self, mode=''):
        self.mode = mode

    def __call__(self, func):
        func.interaction = self.mode
        return func

class RopeInterface(object):

    def __init__(self):
        self.project = None
        self.old_content = None

    def init(self):
        """Initialize rope mode"""
        lisp.add_hook(lisp.before_save_hook,
                      lisp.rope_before_save_actions)
        lisp.add_hook(lisp.after_save_hook,
                      lisp.rope_after_save_actions)
        lisp.add_hook(lisp.kill_emacs_hook,
                      lisp.rope_exiting_actions)
        lisp.global_set_key('\x03g', lisp.rope_goto_definition)
        lisp.global_set_key('\x03rr', lisp.rope_rename)
        lisp.global_set_key('\x03rl', lisp.rope_extract_variable)
        lisp.global_set_key('\x03rm', lisp.rope_extract_method)
        lisp.global_set_key('\x03ri', lisp.rope_inline)

    def before_save_actions(self):
        if self.project is not None:
            resource = self._get_resource()
            if resource is not None:
                self.old_content = resource.read()
            else:
                self.old_content = ''

    def after_save_actions(self):
        if self.project is not None:
            libutils.report_change(self.project, lisp.buffer_file_name(),
                                   self.old_content)
            self.old_content = None

    def exiting_actions(self):
        if self.project is not None:
            self.close_project()

    @interactive('DRope Project Root Folder: ')
    def set_project(self, root):
        if self.project is not None:
            self.close_project()
        self.project = project.Project(root)

    @interactive()
    def close_project(self):
        self.project.close()
        self.project = None

    @interactive('sNew Name: ')
    def rename(self, newname):
        self._check_project()
        lisp.save_some_buffers()
        resource, offset = self._get_location()
        renamer = rope.refactor.rename.Rename(self.project, resource, offset)
        changes = renamer.get_changes(newname, docs=True)
        self._perform(changes)

    def _do_extract(self, extractor, newname):
        self._check_project()
        lisp.save_buffer()
        resource = self._get_resource()
        start, end = self._get_region()
        extractor = extractor(self.project, resource, start, end)
        changes = extractor.get_changes(newname)
        self._perform(changes)

    @interactive('sNew Variable Name: ')
    def extract_variable(self, newname):
        self._do_extract(rope.refactor.extract.ExtractVariable, newname)

    @interactive('sNew Method Name: ')
    def extract_method(self, newname):
        self._do_extract(rope.refactor.extract.ExtractMethod, newname)

    @interactive('')
    def inline(self):
        self._check_project()
        lisp.save_some_buffers()
        resource, offset = self._get_location()
        inliner = rope.refactor.inline.create_inline(
            self.project, resource, offset)
        self._perform(inliner.get_changes())

    def _perform(self, changes):
        self.project.do(changes)
        self._reload_buffers(changes.get_changed_resources())

    def _get_region(self):
        offset1 = self._get_offset()
        lisp.exchange_point_and_mark()
        offset2 = self._get_offset()
        lisp.exchange_point_and_mark()
        return min(offset1, offset2), max(offset1, offset2)

    def _get_offset(self):
        return lisp.point() - 1

    @interactive('')
    def goto_definition(self):
        self._check_project()
        resource, offset = self._get_location()
        definition = codeassist.get_definition_location(
            self.project, lisp.buffer_string(), offset, resource)
        if definition[0]:
            lisp.find_file(definition[0].real_path)
        lisp.goto_line(definition[1])

    def _get_location(self):
        resource = self._get_resource()
        offset = self._get_offset()
        return resource, offset

    def _get_resource(self):
        filename = lisp.buffer_file_name()
        resource = libutils.path_to_resource(self.project, filename)
        return resource

    def _check_project(self):
        if self.project is None:
            lisp.call_interactively(lisp.rope_set_project)

    def _reload_buffers(self, changed_resources):
        for resource in changed_resources:
            buffer = lisp.find_buffer_visiting(resource.real_path)
            if buffer and resource.exists():
                lisp.set_buffer(buffer)
                lisp.revert_buffer(None, 1)


interface = RopeInterface()

init = interface.init
set_project = interface.set_project
close_project = interface.close_project

rename = interface.rename
extract_variable = interface.extract_variable
extract_method = interface.extract_method
inline = interface.inline

before_save_actions = interface.before_save_actions
after_save_actions = interface.after_save_actions
exiting_actions = interface.exiting_actions

goto_definition = interface.goto_definition

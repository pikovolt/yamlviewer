# yamlviewer.py, Copyright (c) 2016, Patrick O'Grady.
#
# MIT License
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

#
# Read-only tree viewer for Yaml scripts written in PyQt4.  Trees are displayed
# in a lazy manner, meaning that the child contents of an item are added only
# when the user opens the item.  This way the viewer avoids problems with
# trees that have circular dependencies.

# Usage:
#   python -m yamlviewer [yamlfile]

#
# Pressing <F5> reloads the currently displayed file.
#


from PySide2 import QtCore, QtGui, QtWidgets
from .ui import Ui_MainWindow
import os
import sys
import yaml

def debug(msg):
    if False:
        print("DEBUG %s" % msg)

class YamlViewer(QtCore.QObject):

    def __init__(self, view, controller, configuration, filename=None):
        super(YamlViewer, self).__init__()
        self._view = view
        self._controller = controller
        self._configuration = configuration
        self._fname = None
        view.action_Open.triggered.connect(self.file_open)
        view.action_Save.triggered.connect(self.file_save)
        view.action_Reload.triggered.connect(self.re_load)
        view.action_Reload.setShortcut(QtGui.QKeySequence("F5"))
        self._root = view.yaml.invisibleRootItem()
        self._item_map = { }
        self._marker = QtWidgets.QTreeWidgetItem(["marker"])
        view.yaml.itemExpanded.connect(self.expanded)
        if filename:
            self.load(filename)

    def file_open(self):
        results = QtWidgets.QFileDialog.getOpenFileName(
                    self._controller,
                    'Open file',
                    self._configuration["directory"]
                )
        fname = results[0]
        debug("fname=%s." % fname)
        self._configuration["directory"] = os.path.dirname(fname)
        self.load(fname)

    def file_save(self):
        results = QtWidgets.QFileDialog.getSaveFileName(
                    self._controller,
                    'Save file',
                    self._configuration["directory"]
                )
        fname = results[0]
        debug("fname=%s." % fname)
        self._configuration["directory"] = os.path.dirname(fname)
        self.save(fname)

    def re_load(self):
        if self._fname:
            self.load(self._fname)

    def expand_all_items(self, item):
        item.setExpanded(True)
        for i in range(item.childCount()):
            self.expand_all_items(item.child(i))

    def populate(self, content, item, ch):
        item.removeChild(ch)
        self._item_map[item] = self.good
        def add(k, v):
            debug("type(v)=%s." % (type(v),))
            if type(v) == dict:
                x = QtWidgets.QTreeWidgetItem([k,])
                x.setFlags(x.flags() | QtCore.Qt.ItemIsEditable)  # Make item editable
                z = QtWidgets.QTreeWidgetItem(["marker"])
                self._item_map[x] = lambda item, x=x, v=v: self.populate(v, x, z)
                x.addChild(z)
                item.addChild(x)
                return
            if type(v) == list:
                x = QtWidgets.QTreeWidgetItem([k, "(list with %u item%s)" % (len(v), "" if len(v)==1 else "s")])
                x.setFlags(x.flags() | QtCore.Qt.ItemIsEditable)  # Make item editable
                z = QtWidgets.QTreeWidgetItem(["marker"])
                self._item_map[x] = lambda item, x=x, v=v: self.populate(v, x, z)
                x.addChild(z)
                item.addChild(x)
                return
            debug("type(k)=%s, type(v)=%s." % (type(k), type(v)))
            x = QtWidgets.QTreeWidgetItem([k, "%s" % v])
            x.setFlags(x.flags() | QtCore.Qt.ItemIsEditable)  # Make item editable
            self._item_map[x] = self.good
            item.addChild(x)
        if type(content) == dict:
            for k, v in content.items():
                add(k, v)
            return
        if type(content) == list:
            for n, datum in enumerate(content):
                add("%u" % n, datum)
            return

    def load(self, fname):
        with open(fname, "rt") as f:
            s = f.read()
        self._content = yaml.load(s, Loader=MapLoader)
        self._root.takeChildren()
        self.populate(self._content, self._root, self._marker)
        self._fname = fname
        self.expand_all_items(self._root)

    def good(self, item):
        pass

    def expanded(self, item):
        debug("expanded, item=%s, map=%s" % (item, self._item_map.get(item, "N/A")))
        h = self._item_map[item]
        h(item)

    def save(self, filename):
        with open(filename, "wt") as f:
            f.write(tree_to_yaml(self._root))

def tree_to_yaml(item):

    def item_to_dict(item):
        if item.childCount() == 0:
            return item.text(1)
        result = {}
        for i in range(item.childCount()):
            child = item.child(i)
            key = child.text(0)
            value = item_to_dict(child)
            result[key] = value
        return result

    # root is a dictionary
    root_dict = {}
    for i in range(item.childCount()):
        child = item.child(i)
        key = child.text(0)
        value = item_to_dict(child)
        root_dict[key] = value

    return yaml.dump(root_dict, default_flow_style=False)


# MapLoader makes all object/python instances into maps.
class MapLoader(yaml.SafeLoader):
    def construct_x(self, tag_suffix, node):
        debug("node.tag=%s, tag_suffix=%s." % (node.tag, tag_suffix))
        return self.construct_mapping(node)
MapLoader.add_multi_constructor(
        "tag:yaml.org,2002:python/object",
        MapLoader.construct_x)


def main():
    configuration = {
        "directory": os.path.expanduser("~"),
    }
    try:
        with open(os.path.expanduser("yamlviewer.yaml"), "rt") as f:
            s = f.read()
            c = yaml.load(s, Loader=yaml.SafeLoader)
            configuration.update(c)
    except IOError:
        # file not found
        pass
    try:
        app = QtWidgets.QApplication(sys.argv)
        controller = QtWidgets.QMainWindow(parent=None)
        view = Ui_MainWindow()
        view.setupUi(controller)
        filename = None
        if len(sys.argv) > 1:
            filename = sys.argv[1]
        yaml_viewer = YamlViewer(view, controller, configuration, filename)
        controller.show()
        sys.exit(app.exec_())
    finally:
        s = yaml.dump(configuration)
        with open(os.path.expanduser("yamlviewer.yaml"), "wt") as f:
            f.write(s)

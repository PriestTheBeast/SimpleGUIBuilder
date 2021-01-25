import inspect
import sys
import ast

import PySimpleGUI as sg
import layout_parser as ps

CONTAINER_ELEMENTS = (sg.Column, sg.Frame, sg.Tab, sg.TabGroup)
CONTAINER_LAYOUT_ARG = {sg.Column: 0, sg.Frame: 1, sg.Tab: 1, sg.TabGroup: 0}

GUI_CLASSES = dict(inspect.getmembers(sys.modules["PySimpleGUI"], inspect.isclass))


# This custom structure is core of the whole thing
# It's my centralized way of storing a layout, built it, modify it, modify its initial parameters
# String layouts are translated into the Tree structure and vice-versa through the layout_parser
# 	which could also be called string_layout_interpreter? anyway
class TreeNode:

	def __init__(self, element, parent=None):
		# element class
		self.element = element
		self.parent = parent

		self.container = []
		if element in CONTAINER_ELEMENTS:
			self.container.append(TreeNode("Root"))

		self.necessary_args_name = []
		self.necessary_args = {}
		self.optional_args = {}
		# this exists so it can compare and not print all optional args when creating the string layout
		# optional args in export
		self.default_optional_args = {}
		# this exists so the user can give first optional args without key
		# Example: Button("OMG") instead of Button(button_text="less omg")
		self.default_optional_args_name = []
		self.args_docs = {}

		if self.element not in ("Row", "Root"):
			self.set_properties()

	# If element is ("Row", "Root") give, else give the Class name
	def __str__(self):
		if isinstance(self.element, str):
			return self.element

		return self.element.__name__

	# If the element is a container Element, i.e. can contain other elements
	def is_container(self):
		return self.element in ("Row", "Root") + CONTAINER_ELEMENTS

	# Adds a child node to this node, creates Row element if necessary
	def add_tree_node(self, tree_node):
		# how does this work with container elements - it has logic outside it
		# and if someone wants to add something and self is not a container then nothing happens
		if self.is_container():
			if self.element == "Row" or tree_node.element == "Row":
				self.container.append(tree_node)
				tree_node.parent = self
				return self

			row = TreeNode("Row", parent=self).add_tree_node(tree_node)
			tree_node.parent = row
			self.container.append(row)
		else:
			sg.popup("Target element is not a Container/Root/Row")

	# Removes itself from parent node
	def remove_tree_node(self):
		if self.parent is None:
			sg.popup("Cannot remove Root element")
		else:
			self.parent.container.remove(self)

	# Moves tree node location in parent node
	def move_tree_node(self, direction):
		if self.parent is None:
			sg.popup("Cannot move Root element")
		else:
			container = self.parent.container
			position = container.index(self)
			if direction == "back":
				container[position], container[position - 1] = container[position - 1], container[position]
			else:
				next_pos = position + 1 if position + 1 != len(container) else 0
				# if next_pos == len(container):
				# 	next_pos = 0
				container[position], container[next_pos] = container[next_pos], container[position]

	# Returns the layout object of the Tree, which is given to the Preview window to render
	def get_layout(self):
		# if self.element in ("Root", "Row"):
		if self.container:
			if self.element in ("Root", "Row"):
				return [x.get_layout() for x in self.container]

			return self.element(*[self.necessary_args[x] if x != "layout" else self.container[0].get_layout()
								  for x in self.necessary_args_name], **self.optional_args)

		# if element is empty root or row
		if self.element in ("Root", "Row"):
			if self.element == "Root":
				raise Exception("Root cannot be empty")
			return []

		return self.element(*[self.necessary_args[x] for x in self.necessary_args_name], **self.optional_args)

	# Returns the tree data representation of the Tree,
	# 	which is given to the TreeElement for visualization and element picking
	def get_tree_data(self, treedata=None, parent=""):
		if treedata is None:
			treedata = sg.TreeData()

		treedata.Insert(parent, self, str(self),
						[self.optional_args["visible"], self.optional_args["key"]]
						if self.element not in ("Row", "Root") else ["_", "_"])

		for x in self.container:
			x.get_tree_data(treedata, self)

		return treedata

	# Builds and returns a Tree structure from a previously parsed layout
	# It is separate from the parse_string_layout for recursion purposes
	@staticmethod
	def make_tree_from_parsed_layout(parsed_layout):
		tree = TreeNode("Root")

		for parsed_row in parsed_layout:
			row = TreeNode("Row")
			tree.add_tree_node(row)
			for parsed_elem in parsed_row:
				print(parsed_elem)
				elem = TreeNode(GUI_CLASSES[parsed_elem[0]])
				row.add_tree_node(elem)
				for i in range(len(elem.necessary_args_name)):
					elem.necessary_args[elem.necessary_args_name[i]] = parsed_elem[1][i]
				necessary_to_optional = parsed_elem[1][len(elem.necessary_args_name):]
				if necessary_to_optional:
					for i in range(len(necessary_to_optional)):
						elem.optional_args[elem.default_optional_args_name[i]] = necessary_to_optional[i]
				for key in parsed_elem[2]:
					elem.optional_args[key] = parsed_elem[2][key]
				if GUI_CLASSES[parsed_elem[0]] in CONTAINER_ELEMENTS:
					elem.container = [TreeNode.make_tree_from_parsed_layout(elem.necessary_args["layout"])]

		return tree

	# Builds and returns a Tree structure from a string layout
	# The magic parsing of the string layout has it's own file to be able to contain all the fun xD
	@staticmethod
	def parse_string_layout(string_layout):
		parsed_layout = ps.parse_string_layout(string_layout)

		tree = TreeNode.make_tree_from_parsed_layout(parsed_layout)

		return tree

	# Converts value to string, needs its own function because string needs quotations to "string"
	@staticmethod
	def convert_to_str(value):
		if isinstance(value, str):
			return '"{}"'.format(value)
		else:
			return str(value)

	# Builds and returns a string layout from a Tree structure
	def layout_to_string(self):
		string_layout = ""

		if self.element in ("Root", "Row"):
			string_layout = "[{}]".format(", ".join([x.layout_to_string() for x in self.container]))
		else:
			args = [TreeNode.convert_to_str(
				self.necessary_args[arg_name]) if self.element not in CONTAINER_ELEMENTS or arg_name != "layout"
					else self.container[0].layout_to_string()
					for arg_name in self.necessary_args_name]

			kargs = ["{0}={1}".format(arg_name, TreeNode.convert_to_str(arg_value))
					 for arg_name, arg_value in self.optional_args.items()
					 if self.optional_args[arg_name] != self.default_optional_args[arg_name]]

			string_layout = "sg.{elem_name}({args})".\
				format(elem_name=self.element.__name__, args=", ".join((args + kargs)))

		return string_layout

	# Gets and creates all the necessary data structures with the argument info of the element
	# Also does that to get property tooltips from the Element's docs
	def set_properties(self):
		args_c = self.element.__init__.__code__.co_argcount
		args = self.element.__init__.__code__.co_varnames
		defaults = self.element.__init__.__defaults__

		# parse argument tooltips from docs
		docs = self.element.__init__.__doc__
		current_text = ""
		inside_param = False
		have_name = False
		current_name = ""
		for char in docs:
			if not inside_param:
				if char not in [" ", "\n", "\t", "\r"]:
					current_text += char
					if current_text == ":param":
						inside_param = True
						current_text = ""
				if char == "\n":
					current_text = ""
			else:
				current_text += char
				if not have_name:
					if char == ":":
						current_name = current_text[1:-1]
						current_text = ""
						have_name = True
				else:
					if char == "\n":
						self.args_docs[current_name] = current_text[:-1]
						current_text = ""
						inside_param = False
						have_name = False
						current_name = ""

		# print(self.args_docs)

		real_args = args[1:args_c]

		if not defaults:
			necessary_args = real_args
			def_args = []
		else:
			necessary_args = real_args[:-len(defaults)]
			def_args = real_args[-len(defaults):]

		# print(real_args)
		# print(necessary_args)
		# print(def_args)

		for arg in necessary_args:
			self.necessary_args_name.append(arg)
			self.necessary_args[arg] = None

		for i, arg in enumerate(def_args):
			self.optional_args[arg] = defaults[i]
			self.default_optional_args_name.append(arg)

		# print(self.necessary_args)
		# print(self.optional_args)
		self.default_optional_args = {k: v for k, v in self.optional_args.items()}

	# Returns the layout that is shown on the right, with all the properties available for change for the element
	def get_properties_layout(self, elem_size, property_count):
		layout = []

		layout.append([sg.Text(text="Necessary Args")])

		for arg_name in self.necessary_args_name:
			if arg_name == "layout":
				continue
			value = str(self.necessary_args[arg_name] if not isinstance(self.necessary_args[arg_name], str)
						else '"' + self.necessary_args[arg_name] + '"')
			layout.append([sg.Text(text=arg_name,
								   tooltip=(self.args_docs[arg_name] if arg_name in self.args_docs else None)),
						   sg.Input(default_text=value, key=str(property_count) + "_" + arg_name)])

		layout.append([sg.Text(text="Optional Args")])

		for arg_name, arg_value in self.optional_args.items():
			value = str(arg_value if not isinstance(arg_value, str)
						else '"' + arg_value + '"')
			layout.append([sg.Text(text=arg_name,
								   tooltip=(self.args_docs[arg_name] if arg_name in self.args_docs else None)),
						   sg.Input(default_text=value, key=str(property_count) + "_" + arg_name)])

		return sg.Column(layout, scrollable=True, vertical_scroll_only=True, size=elem_size)

	# Applies the properties
	# Some day this might be automatic or provide a notice like "hey, you have unsaved properties, save?"
	# But today is not that day
	def apply_properties(self, values, property_count):
		for arg_name in self.necessary_args:
			key = str(property_count) + "_" + arg_name
			if key in values:
				self.necessary_args[arg_name] = ast.literal_eval(values[key])

		for arg_name in self.optional_args:
			key = str(property_count) + "_" + arg_name
			if key in values:
				self.optional_args[arg_name] = ast.literal_eval(values[key])

	# Receives a file and writes to it the template file with in layout in it
	# Dunno if this belongs here or in main, but it's here for now
	def write_to_file(self, file):
		file_text = '''import PySimpleGUI as sg

# Template file taken from here https://pysimplegui.trinket.io/demo-programs#/demo-programs/the-basic-pysimplegui-program
sg.theme('DarkAmber')  # No gray windows please!

# STEP 1 define the layout
layout = ''' + self.layout_to_string() + '''

#STEP 2 - create the window
window = sg.Window('Template Window', layout, resizable=True)
# If you don't want to start with the window maximized comment this bellow vvv
#window.maximize()

# STEP3 - the event loop
while True:
    event, values = window.read()   # Read the event that happened and the values dictionary
    print(event, values)
    if event == sg.WIN_CLOSED or event == 'Exit':     # If user closed window with X or if user clicked "Exit" button then exit
        break

window.close()'''
		file.write(file_text)

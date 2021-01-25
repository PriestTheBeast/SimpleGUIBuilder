import inspect
import sys
import ast

import PySimpleGUI as sg

CONTAINER_ELEMENTS = (sg.Column, sg.Frame, sg.Tab)
CONTAINER_LAYOUT_ARG = {sg.Column: 0, sg.Frame: 1, sg.Tab: 1}

GUI_CLASSES = dict(inspect.getmembers(sys.modules["PySimpleGUI"], inspect.isclass))


# This file is one I don't wish to revisit so soon, but it does all the hard work of
# 	taking a layout in string format and interpret it, making possible creating a Tree structure from it
# 	all I have to say is, god damn handling strings in parsing the string layout xD

# Parses info into a list of something, start and end are the delimiters,
# save_all I think makes it also save the beginning b4 the start delimiter
# filter_beginning allows it to ignore some chars at the start of the info, like " " and ","
def parse_with_delimiters(info, start, end, save_all=False, filter_beginning=None):
	rows = []
	row = []
	quote = None
	escaped = False
	deep_lvl = 0
	in_beginning = True
	for letter in info:
		if in_beginning:
			if filter_beginning is None or letter not in filter_beginning:
				in_beginning = False
			else:
				continue

		if escaped:
			escaped = False
			row.append(letter)
			continue
		if letter in ("'", '"'):
			if quote is None:
				quote = letter
			elif letter == quote:
				quote = None
			row.append(letter)
			continue
		if quote is not None:
			if letter == "\\":
				escaped = True
			row.append(letter)
			continue

		if letter == start:
			if save_all or deep_lvl > 0:
				row.append(letter)
			deep_lvl += 1
		elif letter == end:
			if deep_lvl == 1:
				if save_all:
					row.append(letter)
				rows.append("".join(row))
				row = []
				in_beginning = True
			else:
				row.append(letter)
			deep_lvl -= 1
		elif save_all or deep_lvl > 0:
			row.append(letter)

	return rows


def parse_with_single_char(info, ch, filter_beginning=None):
	if not info:
		return []
	rows = []
	row = []
	quote = None
	escaped = False
	collection_start = {"(": ")", "{": "}", "[": "]"}
	collection_char = None
	deep_lvl = 0
	in_beginning = True
	for letter in info:
		if in_beginning:
			if filter_beginning is None or letter not in filter_beginning:
				in_beginning = False
			else:
				continue

		if escaped:
			escaped = False
			row.append(letter)
			continue
		if letter in ("'", '"'):
			if quote is None:
				quote = letter
			elif letter == quote:
				quote = None
			row.append(letter)
			continue
		if quote is not None:
			if letter == "\\":
				escaped = True
			row.append(letter)
			continue

		if collection_char is not None:
			if letter == collection_start[collection_char]:
				deep_lvl -= 1
				if deep_lvl == 0:
					collection_char = None
			elif letter == collection_char:
				deep_lvl += 1
		else:
			if letter in collection_start:
				collection_char = letter
				deep_lvl += 1
			elif letter == ch:
				rows.append("".join(row))
				row = []
				in_beginning = True
				continue
		row.append(letter)

	rows.append("".join(row))
	return rows


def strip_except_inside_quote(info):
	new_info = ""

	quote = None
	escaped = False
	for letter in info:
		if escaped:
			escaped = False
			new_info += letter
			continue
		if letter in ("'", '"'):
			if quote is None:
				quote = letter
			elif letter == quote:
				quote = None
			new_info += letter
			continue
		if quote is not None:
			if letter == "\\":
				escaped = True
			new_info += letter
			continue

		if letter not in (" ", "\n", "\t"):
			new_info += letter

	return new_info


def parse_string_layout(string_layout):
	# remove first "[ ]"
	rows_string = strip_except_inside_quote(string_layout)[1:-1]

	# separate into rows
	rows = parse_with_delimiters(rows_string, "[", "]")

	# separate each row into list of elements
	tree = []
	for row in rows:
		tree.append(parse_with_delimiters(row, "(", ")", save_all=True, filter_beginning=(" ", ",")))

	# for row in tree:
	# 	for element in row:
	# 		print(element, end=" - ")
	# 	print()

	# separate each element into the element name and list of evaluated args
	new_tree = []
	for row in tree:
		new_row = []
		new_tree.append(new_row)
		for element in row:
			element_name_ended = False
			element_name = ""
			args = ""
			for letter in element:
				if element_name_ended:
					args += letter
				elif letter == "(":
					element_name_ended = True
					args += letter
				else:
					element_name += letter

			args_list = parse_with_single_char(args[1:-1], ",")
			are_kargs = False
			args_values = []
			kargs_values = {}
			for i, arg in enumerate(args_list):
				container_with_args = (GUI_CLASSES[element_name[3:]] in CONTAINER_ELEMENTS
									   and i == CONTAINER_LAYOUT_ARG[GUI_CLASSES[element_name[3:]]])
				if not are_kargs and "=" in arg and not container_with_args:
					eq_pos = arg.index("=")
					if ("'" not in arg or eq_pos < arg.index("'")) and ('"' not in arg or eq_pos < arg.index('"')):
						are_kargs = True

				if not are_kargs:
					if container_with_args:
						args_values.append(parse_string_layout(arg))
					else:
						try:
							args_values.append(ast.literal_eval(arg))
						except Exception as e:
							print(arg)
							raise Exception(str(e), arg) from e
				else:
					kargs_values[arg[:arg.index("=")]] = ast.literal_eval(arg[arg.index("=") + 1:])

			new_row.append((element_name[3:], args_values, kargs_values))

	# for row in new_tree:
	# 	for element in row:
	# 		print(element, end=" - ")
	# 	print()

	return new_tree


# Test a very bad case scenario
def main():
	test_layout = '[ \n \t  ' \
				  '[  sg.Text  (  "  This is a very \\" sure then \\" \' right \' ][ basic PySimpleGUI layout")],' \
				  '[sg.Input()],' \
				  '[   sg.Button(  \'  Button "right" \\\' maybe \\\'  \'), sg.Button( "Exit", 4, 6, key= "-nope-", visible=True)]' \
				  ']'

	print(parse_string_layout(test_layout))


if __name__ == "__main__":
	main()

import inspect
import sys
import time

import PySimpleGUI as sg
from tree_node import TreeNode

GUI_CLASSES = dict(inspect.getmembers(sys.modules["PySimpleGUI"], inspect.isclass))

ELEMB_KEY = "ELEMB-"


# Function that returns the layout of the middle Elements Frame, where you choose the an element
# It's lists made by hand, but any Element that is not in any list will be added at the last list (Others)
def make_elements_frame():
	layout = []

	elements = set(GUI_CLASSES.values())
	elements_names = [e.__name__ for e in elements if
					  issubclass(e, sg.Element) and e not in (sg.Element, sg.ErrorElement)]

	# Makes a button for each string in the given list of strings
	make_button_row = (lambda element_list: [sg.Button(button_text=e, key=ELEMB_KEY + e) for e in element_list])

	layout.append([sg.Button(button_text="Delete Element", button_color=("black", "darkred"), key="DeleteElement"),
				   sg.Button('Move Element Up', key="MoveUp"), sg.Button('Move Element Down', key="MoveDown")])

	layout.append([sg.Text(text="Main Elements")])
	main_elements = ["Text", "InputText", "Output", "Button", "Combo", "Listbox", "Radio", "Checkbox"]
	layout.append(make_button_row(main_elements))

	layout.append([sg.Text(text="Containers")])
	container_elems = ["TabGroup", "Tab", "Frame", "Column"]
	layout.append(make_button_row(container_elems))

	layout.append([sg.Text(text="Separators")])
	design_elems = ["HorizontalSeparator", "VerticalSeparator"]
	layout.append(make_button_row(design_elems))

	layout.append([sg.Text(text="Menus")])
	organization_elems = ["Menu", "MenuButton", "OptionMenu", "ButtonMenu"]
	layout.append(make_button_row(organization_elems))

	layout.append([sg.Text(text="Structured Info")])
	structured_info_elems = ["Tree", "Table"]
	layout.append(make_button_row(structured_info_elems))

	layout.append([sg.Text(text="Images/Drawing")])
	drawing_elems = ["Image", "Graph", "Canvas"]
	layout.append(make_button_row(drawing_elems))

	layout.append([sg.Text(text="Others")])
	other_elements = ["Slider", "Spin", "Multiline", "ProgressBar", "StatusBar"]
	for e in elements_names:
		if e not in (main_elements + container_elems + design_elems + organization_elems +
					 structured_info_elems + drawing_elems + other_elements + ["Pane"]):
			other_elements.append(e)
	# print(e)
	layout.append(make_button_row(other_elements))

	return layout


# Creates the main window layout from scratch. Necessary to reset the window.
def make_main_window(tree):

	# STEP 1 define the layout
	tree_elem = sg.Tree(tree.get_tree_data(), ["Visible", "Key"],
						key="-TREE-", enable_events=True, show_expanded=True, col0_width=30,
						auto_size_columns=False, col_widths=[5, 10])

	frame_elem = sg.Frame("Elements", make_elements_frame())

	frame_prop = sg.Frame("Properties", [])

	stuff_row = [tree_elem, frame_elem, frame_prop]

	layout = [
		[sg.Text('M.M. - Welcome to a layout builder for PySimpleGUI, made with PySimpleGUI!'),
		 sg.Button("About"), sg.Button('Preview'), sg.Button('Import'), sg.Button('Export'),
		 sg.Button("Save"), sg.Button("Load"), sg.Button("Setup"), sg.Button('Apply Properties'),
		 sg.Text(size=(20, 1), auto_size_text=True, key="Status_text", text_color="Light Green")],
		stuff_row
	]

	# STEP 2 - create the window
	# print(location, size)
	w = sg.Window('My new window', layout, finalize=True, resizable=True)
	w.maximize()

	# Resizes the Main 3 elements according to the window size
	size = tuple(w.Size)
	padded_size = (size[0], size[1] - 50)
	elem_w, elem_h = padded_size[0] // len(stuff_row), padded_size[1]
	for elem in stuff_row:
		elem.set_size((elem_w, elem_h))

	return w, tree_elem, frame_elem, frame_prop, (elem_w, elem_h)


# Main Function :)
def main():
	print("Hello World!")
	sg.theme('DarkAmber')  # No gray windows please!

	# auto_load from file if it exists
	try:
		f = open("autosave.txt")
		template_string_layout = f.read()
		f.close()
	except:
		print("There is no autosave file. Giving template layout.")
		template_string_layout = "[" \
								 "[sg.Text(text='This is a very basic PySimpleGUI layout')], " \
								 "[sg.InputText()], " \
								 "[sg.Button('Button', key='-ExampleKey-'), sg.Button(button_text='Exit')] " \
								 "]"

	# Create tree structure from the string layout
	# This tree structure is different from the TreeElement,
	# 	the TreeElement shows a simplified visual representation of this Tree
	tree = TreeNode.parse_string_layout(template_string_layout)

	# Create window
	window, tree_element, frame_elements, frame_properties, elem_size = make_main_window(tree)

	# Initial variable setup
	current_tree_node, current_property = None, None
	property_count = 0
	win2 = None
	win2_active = False
	current_time = time.time()

	# The event loop
	while True:
		# Read the event that happened and the values dictionary
		event, values = window.read()

		# print(event, values)
		window["Status_text"].update(value="")

		# If user closed window with X or if user clicked "Exit" button then exit
		if event in (sg.WIN_CLOSED, 'Exit'):
			break

		# I don't remember why this is here
		if event is None:
			continue

		# If user clicked button on an element in the tree
		if event == "-TREE-":
			tree_node = values[event][0]
			if tree_node != current_tree_node:
				if current_tree_node is not None:
					current_property.update(visible=False)

				if property_count > 50:
					window.close()
					window, tree_element, frame_elements, frame_properties, elem_size = make_main_window(tree)
					property_count = 0

				current_tree_node = tree_node
				current_property = tree_node.get_properties_layout(elem_size, property_count + 1)
				window.extend_layout(frame_properties, [[sg.pin(current_property)]])
				property_count += 1

		# If user clicked button on an element in the tree
		if event == "Apply Properties":
			selected_tree_element = values["-TREE-"]
			if current_tree_node is None:
				sg.popup("No element selected")
			else:
				try:
					if selected_tree_element:
						current_tree_node = selected_tree_element[0]
					if current_tree_node.element in ("Root", "Row"):
						sg.popup("Root/Row have no properties to apply.")
					else:
						current_tree_node.apply_properties(values, property_count)
						# sg.popup_auto_close("Properties Applied", auto_close_duration=3)
						window["Status_text"].update(value='Properties Applied')
						tree_element.update(values=tree.get_tree_data())
				except Exception as e:
					sg.popup_error("Error: " + str(e) +
								   "\nError applying properties. Prob tried to enter a bad value to a property.")

		# If user clicked on an element to add
		if event[:6] == ELEMB_KEY:
			element_name = event[6:]
			selected_tree_element = values["-TREE-"]
			if not selected_tree_element:
				sg.popup("No element selected")
			else:
				selected_tree_element[0].add_tree_node(TreeNode(GUI_CLASSES[element_name]))
				tree_element.update(values=tree.get_tree_data())

		# If user clicked on the DeleteElement button
		if event == "DeleteElement":
			selected_tree_element = values["-TREE-"]
			if not selected_tree_element:
				sg.popup("No element selected")
			else:
				response = sg.popup_ok_cancel("Confirm deletion?", selected_tree_element[0])
				if response == "OK":
					selected_tree_element[0].remove_tree_node()
					tree_element.update(values=tree.get_tree_data())

		# If user clicked on the MoveUp element button
		if event == "MoveUp":
			selected_tree_element = values["-TREE-"]
			if not selected_tree_element:
				sg.popup("No element selected")
			else:
				selected_tree_element[0].move_tree_node("back")
			tree_element.update(values=tree.get_tree_data())

		# If user clicked on the MoveDown element button
		if event == "MoveDown":
			selected_tree_element = values["-TREE-"]
			if not selected_tree_element:
				sg.popup("No element selected")
			else:
				selected_tree_element[0].move_tree_node("forward")
			tree_element.update(values=tree.get_tree_data())

		# If user clicked on the Import button
		# This allows the user to import a layout to SimpleGUIBuilder from a string layout
		if event == "Import":
			text = sg.popup_get_text("ATTENTION! Importing will replace current layout.\n"
									 "Also, importing '[]' is a great way to clear if you want to.")
			if text == "":
				sg.popup_auto_close("Text is empty. Importing cancelled.", auto_close_duration=3)
			elif text is None:
				# sg.popup_auto_close("Import cancelled.", auto_close_duration=3)
				pass
			else:
				try:
					tree = TreeNode.parse_string_layout(text)
					tree_element.update(values=tree.get_tree_data())
				except Exception as e:
					sg.popup_error(("Error: " + str(e) if len(e.args) == 1
									else "Error: " + str(e.args[0]) + "\n, in this place: " + str(e.args[1])) +
								   "\n Importing cancelled or Error in importing (mistake in the text given).")

		# If user clicked on the Export button
		# Shows the correspondent string layout for the GUI being built
		if event == "Export":
			sg.popup_get_text("Current layout:", default_text=tree.layout_to_string())

		# If user clicked on the Save button
		# Export button but string layout goes to file
		if event == "Save":
			try:
				file_path = sg.popup_get_file("Where do you want to save your file?", save_as=True)
				if file_path is not None:
					with open(file_path, "w") as f:
						f.write(tree.layout_to_string())
			except Exception as e:
				sg.popup_error("Error: " + str(e) +
							   "\nError in writing to file.")

		# If user clicked on the Load button
		# Import button but string layout comes from file
		if event == "Load":
			try:
				file_path = sg.popup_get_file("ATTENTION! Loading will replace current layout.\n"
											  "Where is the file you want to load?")
				if file_path is not None:
					with open(file_path, "r") as f:
						text = f.read()
					if text == "":
						sg.popup_auto_close("Text is empty. Loading cancelled.", auto_close_duration=3)
					elif text is None:
						# sg.popup_auto_close("Import cancelled.", auto_close_duration=3)
						pass
					else:
						try:
							tree = TreeNode.parse_string_layout(text)
							tree_element.update(values=tree.get_tree_data())
						except Exception as e:
							sg.popup_error(("Error: " + str(e) if len(e.args) == 1
											else "Error: " + str(e.args[0]) + "\n, in this place: " + str(e.args[1])) +
										   "\n Loading cancelled or Error in Loading (mistake in the text given).")
			except Exception as e:
				sg.popup_error("Error: " + str(e) +
							   "\nError in reading from file.")

		# If user clicked on the Setup button
		# This button will create a file from the template in here
		# https://pysimplegui.trinket.io/demo-programs#/demo-programs/the-basic-pysimplegui-program
		# Except with the layout switched to the exported string layout
		# Most of it is in "tree.write_to_file" function
		if event == "Setup":
			try:
				file_path = sg.popup_get_file("Where do you want to save your Setup file?", save_as=True)
				if file_path is not None:
					with open(file_path, "w") as f:
						tree.write_to_file(f)
			except Exception as e:
				sg.popup_error("Error: " + str(e) +
							   "\nError in writing to file.")

		# If user clicked on the About button
		# This button will show info I want to show for people to see if anyone wants to see xD
		if event == "About":
			sg.popup("I don't really like frontend but I really like the idea of giving my backend/terminal programs "
					 "something more pleasurable to interact with.\n\n"
					 "That's when I came across PySimpleGUI, a simple solution to quickly give my programs an interactive front. "
					 "But in checking out PySimpleGUI I found I wanted more and had an idea: \n"
					 "It would be nice if PySimpleGUI and therefore GUI making/designing was in itself more interactive.\n\n"
					 "And that's how SimpleGUIBuilder came to be:\n"
					 "A GUI for creating/designing GUI's for PySimpleGUI, made with PySimpleGUI.\n"
					 "I hope this will be useful to people :)\n\n"
					 "Made by Miguel Martins.\n\n"
					 "If you want to support me: https://www.buymeacoffee.com/MMartins\n\n"
					 "Version - 1.0.2")

		# Handle window preview
		# Check if in the meantime if the window was closed
		# Have to see if I need timeout and win2_active variable with the window being modal
		if win2_active:
			ev, v = win2.read(timeout=100)
			if ev == sg.WIN_CLOSED:
				win2_active = False
				win2.close()

		if not win2_active and event == "Preview":
			try:
				win2 = sg.Window('Preview', tree.get_layout(), finalize=True, modal=True)
				win2_active = True
			except Exception as e:
				sg.popup_error("Error: " + str(e) +
							   "\nError in preview (mistake in the layout). You can try finding it with export")

		# autosave
		if time.time() - current_time > 180:
			try:
				with open("autosave.txt", "w") as f:
					f.write(tree.layout_to_string())
				current_time = time.time()
			except Exception as e:
				sg.popup_error("Error: " + str(e) +
							   "\nError in autosaving to file")

	window.close()
	# autosave
	try:
		with open("autosave.txt", "w") as f:
			f.write(tree.layout_to_string())
	except Exception as e:
		sg.popup_error("Error: " + str(e) +
					   "\nError in autosaving to file")


if __name__ == "__main__":
	try:
		main()
	except Exception as e:
		sg.popup_error("Error: " + str(e) +
					   "\nGeneral error. This error exists so the program doesn't just crash." +
					   "\nAn error happened that I didn't catch properly, so no good message to help in what's wrong" +
					   " except the prob bluberish above :(" +
					   "\nI hope no one sees this, but you know how it is, it will happen ¯\_(ツ)_/¯")

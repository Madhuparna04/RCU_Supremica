#!/usr/bin/env python3

import sys

if sys.argv.__len__() != 2:
    print("Usage:", sys.argv[0], "file.dot")
    sys.exit()

def open_dot(file_path):
    cursor = 0
    dot_lines = []
    try:
        dot_file = open(file_path)
    except OSError:
        print("Cannot open:", file_path)
        sys.exit()

    dot_lines = dot_file.read().splitlines()
    dot_file.close()

    # checking the first line:
    line = dot_lines[cursor].split()

    if (line[0] != "digraph") and (line[1] != "state_automaton"):
        print("format error")
    else:
        cursor = cursor + 1
    return dot_lines

def get_cursor_begin_states(dot_lines):
    cursor = 0
    while dot_lines[cursor].split()[0] != "{node":
        cursor += 1
    return cursor

def get_cursor_begin_events(dot_lines):
    cursor = 0
    while dot_lines[cursor].split()[0] != "{node":
       cursor += 1
    while dot_lines[cursor].split()[0] == "{node":
        cursor += 1
    # skip initial state transition
    cursor += 1
    return cursor

def fill_state_variables(dot_lines):
    # wait for node declaration
    states = []
    final_states=[]
    cursor = get_cursor_begin_states(dot_lines)

    # process nodes
    while dot_lines[cursor].split()[0] == "{node":
        line = dot_lines[cursor].split()
        raw_state = line[-1]

        #  "enabled_fired"}; -> enabled_fired
        state = raw_state.replace('"', '').replace('};', '').replace(',','_')
        if state[0:7] == "__init_":
            initial_state = state[7:]
        else:
            states.append(state)
            if dot_lines[cursor].__contains__("doublecircle") == True:
                final_states.append(state)

        cursor = cursor + 1

    states = sorted(set(states))
    states.remove(initial_state)

    # Insert the initial state at the bein og the states
    states.insert(0, initial_state)

    return states, initial_state, final_states

def fill_event_variables(dot_lines):
    # here we are at the begin of transitions, take a note, we will return later.
    cursor = get_cursor_begin_events(dot_lines)

    events = []
    while dot_lines[cursor][1] == '"':
        # transitions have the format:
        # "all_fired" -> "both_fired" [ label = "disable_irq" ];
        #  ------------ event is here ------------^^^^^
        if dot_lines[cursor].split()[1] == "->":
            line = dot_lines[cursor].split()
            event = line[-2].replace('"','')

            # when a transition has more than one lables, they are like this
            # "local_irq_enable\nhw_local_irq_enable_n"
            # so split them.

            event = event.replace("\\n", " ")
            for i in event.split():
                events.append(i)
        cursor = cursor + 1

    return sorted(set(events))

def print_states_enum(initial_state, states):
    # print all states, the first is the initial, the last is the
    # "state_max", which is the number of states.
    print("enum states {")
    print("\t", initial_state, " = 0,", sep = '')
    for i in states:
        if i != initial_state:
            print("\t", i, ",", sep = '')
    print('\tstate_max')
    print("};")

    print("")

def print_events_enum(events):
    # print events:
    first = 1
    print("enum events { ")
    for i in events:
        if first:
            print("\t", i, " = 0,", sep = '')
            first = 0
        else:
            print("\t", i, ",", sep = '')
    print('\tevent_max')
    print("};\n")

def get_state_type(states):
    min_type="char"
    if states.__len__() > 255:
        min_type="short"
    if states.__len__() > 65535:
        min_type="int"
    return min_type

def print_struct_automaton_definition(states):
    min_type = get_state_type(states)
    print("struct automaton {")
    print("\tchar *state_names[state_max];")
    print("\tchar *event_names[event_max];")
    print("\t", min_type, " function[state_max][event_max];", sep = '')
    print("\t", min_type, " initial_state;", sep = '')
    print("\tchar final_states[state_max];")
    print("};\n")

def create_matrix(dot_lines, events, states):
    # transform the array into a dictionary
    events_dict = {}
    states_dict = {}
    nr_event = 0
    for event in events:
        events_dict[event] = nr_event
        nr_event += 1

    nr_state = 0
    for state in states:
        states_dict[state] = nr_state
        nr_state = nr_state + 1

    # declare the matrix....
    matrix = [['-1' for x in range(nr_event)] for y in range(nr_state)]

    # and we are back! Let's fill the matrix
    cursor = get_cursor_begin_events(dot_lines)

    while dot_lines[cursor][1] == '"':
        if dot_lines[cursor].split()[1] == "->":
            line = dot_lines[cursor].split()
            origin_state = line[0].replace('"','').replace(',','_')
            dest_state = line[2].replace('"','').replace(',','_')
            possible_events = line[-2].replace('"','').replace("\\n", " ")
            for event in possible_events.split():
                matrix[states_dict[origin_state]][events_dict[event]] = dest_state
        cursor = cursor + 1
    return matrix

def print_automaton_struct_header():
    print("struct automaton aut = {")

def print_names_per_line(states_or_events):
    first = 1
    for i in states_or_events:
        if first:
            print("\t\t\"", i, sep = '', end = '')
            first = 0;
        else:
            print("\",\n\t\t\"", i, sep = '', end = '')
    print("\"\n\t},")

def print_event_names_vector(events):
    print("\t.event_names = { ")
    print_names_per_line(events)

def print_state_names_vector(states):
    print("\t.state_names = { ")
    print_names_per_line(states)

def get_max_strlen_state(states):
    return max(states, key=len).__len__()

def matrix_columns_per_line(states):
    prefix=24 #'\t\t\t'
    overhead_per_entry=2 #', '
    strlen=get_max_strlen_state(states)
    max_lenght=80 # Linux code
    columns_per_line=int((max_lenght - prefix)/(strlen + overhead_per_entry))
    return(columns_per_line)

def get_state_string_format(states):
    maxlen = get_max_strlen_state(states)
    return "%" + str(maxlen) + "s"

def print_function_matrix_single_line(events, states, matrix):
    nr_states=states.__len__()
    nr_events=events.__len__()
    strformat = get_state_string_format(states)
    print("\t.function = {")
    for x in range(nr_states):
        print("\t\t{ ", end = '')
        for y in range(nr_events):
            if y != nr_events-1:
                print(strformat % matrix[x][y], ", ", sep = '', end = '')
            else:
                print(strformat % matrix[x][y], " },", sep = '')
    print('\t},')

def print_function_matrix_multi_lines(events, states, matrix):
    elem_per_line = matrix_columns_per_line(states)
    nr_states=states.__len__()
    nr_events=events.__len__()

    strformat = get_state_string_format(states)

    print("\t.function = {")
    for x in range(nr_states):
        print("\t\t{ ")
        nr_elem=0
        for y in range(nr_events):
            if nr_elem == 0:
                print("\t\t\t", end = '')

            if y != nr_events-1:
                print(strformat % matrix[x][y], ", ", sep = '', end = '')
            else:
                print(strformat % matrix[x][y], "\n\t\t},", sep = '')

            nr_elem += 1
            if (elem_per_line == nr_elem):
                nr_elem = 0
                print("");
    print('\t},')



def print_function_matrix(events, states, matrix):
    nr_elem = matrix_columns_per_line(states)
    if nr_elem > states.__len__():
        print_function_matrix_single_line(events, states, matrix)
    else:
        print_function_matrix_multi_lines(events, states, matrix)
    
def print_inital_state(states):
    print("\t.initial_state = ", states[0], ",", sep = '')

def print_final_states_vector(states, final_states):
    print("\t.final_states = { ", sep = '', end = '')
    first = 1
    for i in states:
        if first == 0:
            print(', ', sep = '', end='')
        else:
            first = 0

        if final_states.__contains__(i):
            print('1', sep = '', end='')
        else:
            print('0', sep = '', end='')
    print(" }")

def print_automaton_struct_footer():
    print("};")

dot_lines = open_dot(sys.argv[1])
states, initial_state, final_states = fill_state_variables(dot_lines)
events = fill_event_variables(dot_lines)
matrix = create_matrix(dot_lines, events, states)

matrix_columns_per_line(states)

print_states_enum(initial_state, states)
print_events_enum(events)
print_struct_automaton_definition(states)

print_automaton_struct_header()
print_event_names_vector(events)
print_state_names_vector(states)
print_function_matrix(events, states, matrix)
print_inital_state(states)
print_final_states_vector(states, final_states)
print_automaton_struct_footer()


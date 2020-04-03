enum states {
	rcu = 0,
	state_max
};

enum events { 
	rcu_dyntick = 0,
	event_max
};

struct automaton {
	char *state_names[state_max];
	char *event_names[event_max];
	char function[state_max][event_max];
	char initial_state;
	char final_states[state_max];
};

struct automaton aut = {
	.event_names = { 
		"rcu_dyntick"
	},
	.state_names = { 
		"rcu"
	},
	.function = {
		{ rcu },
	},
	.initial_state = rcu,
	.final_states = { 0 }
};


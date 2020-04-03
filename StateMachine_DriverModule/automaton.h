#include <linux/percpu.h>
#include "rcu.h"

#ifdef DEBUG
#define debug 		trace_printk
#define error 		trace_printk
#define stack 		trace_dump_stack
#define snapshot 	tracing_snapshot
#else
#define debug(...) 	do {} while (0)
#define error		trace_printk
#define stack		trace_dump_stack
	#ifdef SNAPSHOT
	#define snapshot	tracing_snapshot
	#else
	#define snapshot(...)	do {} while (0)
	#endif
#endif

struct verification {
	struct automaton *aut;
	char curr_state;
	char verifying;
};

DEFINE_PER_CPU(struct verification, per_cpu_ver);

struct verification *this_cpu_ver(void)
{
	return this_cpu_ptr(&per_cpu_ver);
}

void verification_init(void)
{
	struct verification *ver;
	int cpu;
	for_each_cpu(cpu, cpu_online_mask) {
		ver = per_cpu_ptr(&per_cpu_ver, cpu);
		ver->aut = &aut;
		ver->curr_state = ver->aut->initial_state;
		ver->verifying = 0;
	}
}

void verification_reset(struct verification *ver)
{
	ver->verifying = 0;
	ver->curr_state = ver->aut->initial_state;
}

void verification_start(struct verification *ver)
{
	ver->verifying = 1;
}

int verifying(struct verification *ver)
{
	return ver->verifying;
}

char *get_state_name(struct verification *ver, enum states state)
{
	return ver->aut->state_names[state];
}

char *get_event_name(struct verification *ver, enum events event)
{
	return ver->aut->event_names[event];
}

char get_next_state(struct verification *ver, enum states curr_state, enum events event)
{
	return ver->aut->function[curr_state][event];
}

char get_curr_state(struct verification *ver)
{
	return ver->curr_state;

}

void set_curr_state(struct verification *ver, enum states state)
{
	ver->curr_state = state;
}

char process_event(struct verification *ver, enum events event)
{
	int curr_state = get_curr_state(ver);
	int next_state = get_next_state(ver, curr_state, event);

	//printk(KERN_INFO "In process event");
	if (next_state >= 0) {
		set_curr_state(ver, next_state);

		debug("%s -> %s = %s %s\n",
			     get_state_name(ver, curr_state),
			     get_event_name(ver, event),
			     get_state_name(ver, next_state),
			     next_state ? "" : "safe!");

		return true;
	}

	error("event %s not expected in the state %s\n",
		get_event_name(ver, event),
		get_state_name(ver, curr_state));

	stack(0);

	return false;
}

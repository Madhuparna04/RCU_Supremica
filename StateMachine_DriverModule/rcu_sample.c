#include <linux/ftrace.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/init.h>

#define SNAPSHOT 1

#include <trace/events/rcu.h>
#include <trace/events/sched.h>
#include "automaton.h"

#define MODULE_NAME "rcu_sample"

int trace = 0;

void __handle_event(enum events event)
{

	struct verification *ver = this_cpu_ver();
	int retval;

	if (!verifying(ver) || !trace)
		return;

	retval = process_event(ver, event);

	if (!retval) {
		snapshot();
		verification_reset(ver);
	}
}
void handle_rcu_dyntick(void *data, const char *polarity, long oldnesting, long newnesting, int dynticks)
{
	struct verification *ver = this_cpu_ver();
	if (!verifying(ver)) {
		if (!trace)
			return;
		verification_start(ver);
		debug("starting trace\n");
		return;
	}
	__handle_event(rcu_dyntick);
}

struct tp_and_name {
	int registered;
	struct tracepoint *tp;
	void *probe;
	char *name;
};

void fill_tp_by_name(struct tracepoint *ktp, void *priv)
{
	struct tp_and_name *tp  = priv;
	if (!strcmp(ktp->name, tp->name))
		tp->tp = ktp;
}

struct tracepoint *get_struct_tracepoint(char *name)
{
	struct tp_and_name tp = {
		.name = name,
		.tp = NULL
	};

	for_each_kernel_tracepoint(fill_tp_by_name, &tp);

	return tp.tp;
}

struct tp_and_name tps[1] = {
	{
		.probe = handle_rcu_dyntick,
		.name = "rcu_dyntick",
		.registered = 0
	},

};

static int __init wip_init(void)
{
	int i;
	int retval;

	printk(KERN_INFO "Initializing " MODULE_NAME);

	verification_init();
	
	for (i = 0; i < 1; i++) {

	
		tps[i].tp = get_struct_tracepoint(tps[i].name);
	
		if (!tps[i].tp)
			goto out_err;

		tps[i].registered = 1;
	
		retval = tracepoint_probe_register(tps[i].tp, tps[i].probe, NULL);

		if (retval)
			goto out_err;
	}
	
	trace = 1;
	return 0;

out_err:
	for (i = 0; i < 1; i++) {
		if (tps[i].registered)
			tracepoint_probe_unregister(tps[i].tp, tps[i].probe, NULL);
	}
	return -EINVAL;
	return 0;
}

static void __exit wip_exit(void)
{
	int i;
	trace = 0;
	for (i = 0; i < 1; i++) {
		if (tps[i].registered)
			tracepoint_probe_unregister(tps[i].tp, tps[i].probe, NULL);
	}
	
	return;
}

module_init(wip_init);
module_exit(wip_exit);

MODULE_LICENSE("GPL v2");
MODULE_AUTHOR("Madhuparna Bhowmik");
MODULE_DESCRIPTION("rcu dynticks");

#include <linux/perf_event.h>
#include <stddef.h>

#ifndef EVENTS_INIT
    #define EVENTS_INIT

    #define EVENTS_EXCLUDE_KERNEL 1
    #define EVENTS_EXCLUDE_HV     1
typedef struct _perf_event_config_t {
    unsigned int type;
    unsigned long long config;
    char* name;
} perf_event_config_t;

    #define A72_PC_BRANCH_PRED 0x12

perf_event_config_t events[] = {
    //{PERF_TYPE_HARDWARE, PERF_COUNT_HW_BRANCH_INSTRUCTIONS, "branches"},
    {PERF_TYPE_HARDWARE, PERF_COUNT_HW_BRANCH_MISSES, "missed_branches"},
    {PERF_TYPE_HARDWARE, PERF_COUNT_HW_CACHE_BPU, "cache_BPU"},
    {PERF_TYPE_HARDWARE, PERF_COUNT_SW_CPU_CLOCK, "cpu_clock"},
    {PERF_TYPE_HARDWARE, PERF_COUNT_HW_INSTRUCTIONS, "instructions"},
    {PERF_TYPE_RAW, A72_PC_BRANCH_PRED, "predicted_branches"}};

size_t events_len = sizeof(events) / sizeof(*events);
#endif

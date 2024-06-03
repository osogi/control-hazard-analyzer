#define _GNU_SOURCE
#include <asm/unistd.h>
#include <linux/perf_event.h>
#include <sched.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

void test_fun();

#define EXIT_SIGNAL 2

int* perf_fd;
size_t perf_fd_len = 0;

#ifndef EVENTS_INIT
    #define EVENTS_INIT

    #define EVENTS_EXCLUDE_KERNEL 1
    #define EVENTS_EXCLUDE_HV     1
typedef struct _perf_event_config_t {
    unsigned int type;
    unsigned long long config;
    char* name;
} perf_event_config_t;

perf_event_config_t events[] = {};
size_t events_len = 0;

#endif

long perf_event_open(struct perf_event_attr* hw_event, pid_t pid, int cpu, int group_fd, unsigned long flags) {
    int ret;
    ret = syscall(__NR_perf_event_open, hw_event, pid, cpu, group_fd, flags);
    return ret;
}

int set_up_perf_event(perf_event_config_t* event, int cpu) {
    int fd;
    struct perf_event_attr* pe = malloc(sizeof(struct perf_event_attr));
    pe->type = event->type;
    pe->size = sizeof(struct perf_event_attr);
    pe->config = event->config;
    pe->disabled = 1;
    pe->exclude_kernel = EVENTS_EXCLUDE_KERNEL;
    pe->exclude_hv = EVENTS_EXCLUDE_HV;

    fd = perf_event_open(pe, 0, cpu, -1, 0);
    if (fd == -1) {
        fprintf(stderr, "Error opening leader %llx\n", pe->config);
    }
    free(pe);
    return fd;
}

static void init(int cpu) {
    perf_fd_len = events_len;
    perf_fd = calloc(events_len, sizeof(*perf_fd));
    for (size_t i = 0; i < events_len; i++) {
        perf_fd[i] = set_up_perf_event(&events[i], cpu);
    }

    for (size_t i = 0; i < events_len; i++) {
        if (perf_fd[i] != -1)
            ioctl(perf_fd[i], PERF_EVENT_IOC_RESET, 0);
    }

    for (size_t i = 0; i < events_len; i++) {
        if (perf_fd[i] != -1)
            ioctl(perf_fd[i], PERF_EVENT_IOC_ENABLE, 0);
    }
}

static void fin() {
    signal(SIGINT, SIG_IGN);
    if (perf_fd != NULL) {
        for (size_t i = 0; i < perf_fd_len; i++) {
            if (perf_fd[i] != -1)
                ioctl(perf_fd[i], PERF_EVENT_IOC_DISABLE, 0);
        }

        long long value_result = -1;
        for (size_t i = 0; i < perf_fd_len; i++) {
            if (perf_fd[i] != -1) {
                if (read(perf_fd[i], &value_result, sizeof(long long)) <= 0) {
                    fprintf(stderr, "Can't read value of '%s'\n", events[i].name);
                }
                close(perf_fd[i]);
            } else {
                value_result = -1;
            }
            printf("%s: %lld\n", events[i].name, value_result);
        }
    }
}

static void sigint_handler() { exit(EXIT_SIGNAL); }

int main(int argc, char* argv[]) {
    atexit(fin);
    signal(SIGINT, sigint_handler);

    struct sched_param sp;
    sp.sched_priority = sched_get_priority_max(SCHED_FIFO);
    sched_setscheduler(0, SCHED_FIFO, &sp);

    cpu_set_t cpuset;
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <cpu>\n", argv[0]);
        exit(EXIT_FAILURE);
    }
    int cpu = atoi(argv[1]);
    CPU_ZERO(&cpuset);
    CPU_SET(cpu, &cpuset);
    if (sched_setaffinity(0, sizeof(cpuset), &cpuset) == -1) {
        fprintf(stderr, "Can't set test to %d CPU core\n", cpu);
    }

    init(cpu);
    test_fun();
    return 0;
}

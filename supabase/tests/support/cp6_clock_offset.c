/* CP6 disposable PostgreSQL clock fixture. Never used by the application.
 * Shift only wall-clock reads; preserve the kernel's monotonic clock and
 * timeout behavior. The controller may choose an offset within two days.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

static int64_t offset_us(void) {
    const char *path = getenv("CP6_CLOCK_OFFSET_FILE");
    if (path == NULL) return 0;
    if (strcmp(path, "/tmp/cp6-aa-clock.offset") != 0) _exit(78);
    int saved_errno = errno;
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) _exit(78);
    char buf[64];
    ssize_t n = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (n <= 0 || n >= (ssize_t)sizeof(buf) - 1) _exit(78);
    buf[n] = '\0';
    char *end;
    errno = 0;
    long long value = strtoll(buf, &end, 10);
    if (errno != 0 || end == buf || (*end != '\0' && !(*end == '\n' && end[1] == '\0'))
        || value < -172800000000LL || value > 172800000000LL) _exit(78);
    errno = saved_errno;
    return (int64_t)value;
}

int gettimeofday(struct timeval *tv, void *tz) {
    int result = (int)syscall(SYS_gettimeofday, tv, tz);
    if (result == 0) {
        int64_t value = (int64_t)tv->tv_sec * 1000000 + tv->tv_usec + offset_us();
        tv->tv_sec = (time_t)(value / 1000000);
        tv->tv_usec = (suseconds_t)(value % 1000000);
    }
    return result;
}

int clock_gettime(clockid_t id, struct timespec *tp) {
    int result = (int)syscall(SYS_clock_gettime, id, tp);
    if (result == 0 && (id == CLOCK_REALTIME || id == CLOCK_REALTIME_COARSE)) {
        int64_t value = (int64_t)tp->tv_sec * 1000000000 + tp->tv_nsec + offset_us() * 1000;
        tp->tv_sec = (time_t)(value / 1000000000);
        tp->tv_nsec = (long)(value % 1000000000);
    }
    return result;
}

time_t time(time_t *out) {
    struct timespec tp;
    if (syscall(SYS_clock_gettime, CLOCK_REALTIME, &tp) != 0) return (time_t)-1;
    int64_t value = (int64_t)tp.tv_sec * 1000000 + tp.tv_nsec / 1000 + offset_us();
    time_t result = (time_t)(value / 1000000);
    if (out != NULL) *out = result;
    return result;
}

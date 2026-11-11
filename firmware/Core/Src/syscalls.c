/*
 * syscalls.c - minimal newlib stubs (no file system, printf goes to serial.c)
 */
#include <sys/stat.h>
#include <errno.h>

int _close(int fd)                 { (void)fd; return -1; }
int _fstat(int fd, struct stat *s) { (void)fd; s->st_mode = S_IFCHR; return 0; }
int _isatty(int fd)                { (void)fd; return 1; }
int _lseek(int fd, int p, int d)   { (void)fd; (void)p; (void)d; return 0; }
int _read(int fd, char *b, int n)  { (void)fd; (void)b; (void)n; return 0; }
int _write(int fd, char *b, int n) { (void)fd; (void)b; return n; }
int _getpid(void)                  { return 1; }
int _kill(int pid, int sig)        { (void)pid; (void)sig; errno = EINVAL; return -1; }

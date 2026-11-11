/*
 * serial.h - USART2 (ST-LINK virtual COM port): line input, printf output
 */
#ifndef SERIAL_H
#define SERIAL_H

#include <stdbool.h>

void serial_start(void);                 /* start interrupt reception */
bool serial_get_line(char *dst, int max); /* true when a full line arrived */
void serial_printf(const char *fmt, ...); /* waits if the previous send is busy */
bool serial_try_printf(const char *fmt, ...); /* drops the line if busy (telemetry) */

#endif /* SERIAL_H */

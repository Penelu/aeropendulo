/*
 * serial.c - non-blocking UART for the console and the telemetry
 */
#include "serial.h"
#include "board.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#define RX_LINE_MAX 64
#define TX_BUF_MAX  160

static uint8_t rx_byte;
static char rx_buf[RX_LINE_MAX];
static int  rx_len;
static char line[RX_LINE_MAX];
static volatile bool line_ready;

static char tx_buf[TX_BUF_MAX];

void serial_start(void)
{
    HAL_UART_Receive_IT(&huart2, &rx_byte, 1);
}

/* called by the HAL for every received byte */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *h)
{
    if (h != &huart2)
        return;

    char c = (char)rx_byte;
    if (c == '\n' || c == '\r') {
        if (rx_len > 0 && !line_ready) {
            rx_buf[rx_len] = '\0';
            strcpy(line, rx_buf);
            line_ready = true;
        }
        rx_len = 0;
    } else if (rx_len < RX_LINE_MAX - 1) {
        rx_buf[rx_len++] = c;
    }
    HAL_UART_Receive_IT(&huart2, &rx_byte, 1);
}

/* restart reception after an overrun or framing error */
void HAL_UART_ErrorCallback(UART_HandleTypeDef *h)
{
    if (h == &huart2)
        HAL_UART_Receive_IT(&huart2, &rx_byte, 1);
}

bool serial_get_line(char *dst, int max)
{
    if (!line_ready)
        return false;
    strncpy(dst, line, max - 1);
    dst[max - 1] = '\0';
    line_ready = false;
    return true;
}

static bool tx_busy(void)
{
    return huart2.gState != HAL_UART_STATE_READY;
}

static void send(const char *fmt, va_list ap)
{
    int n = vsnprintf(tx_buf, sizeof tx_buf, fmt, ap);
    if (n < 0)
        return;
    if (n >= (int)sizeof tx_buf)
        n = sizeof tx_buf - 1;
    HAL_UART_Transmit_IT(&huart2, (uint8_t *)tx_buf, (uint16_t)n);
}

void serial_printf(const char *fmt, ...)
{
    uint32_t t0 = HAL_GetTick();
    while (tx_busy() && HAL_GetTick() - t0 < 50) {
        /* wait for the previous line (max ~14 ms at 115200 baud) */
    }
    va_list ap;
    va_start(ap, fmt);
    send(fmt, ap);
    va_end(ap);
}

bool serial_try_printf(const char *fmt, ...)
{
    if (tx_busy())
        return false;
    va_list ap;
    va_start(ap, fmt);
    send(fmt, ap);
    va_end(ap);
    return true;
}

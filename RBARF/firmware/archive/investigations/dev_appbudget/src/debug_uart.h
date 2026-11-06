#ifndef DEBUG_UART_H
#define DEBUG_UART_H

#include <stdint.h>

void debug_uart_init(void);
void debug_uart_byte(uint8_t b);
void debug_uart_buf(const volatile uint8_t *buf, uint8_t len);
void debug_uart_hex(uint8_t b);
void debug_uart_send_report(void);

#endif

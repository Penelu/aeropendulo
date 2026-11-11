/*
 * board.h - peripheral handles shared between modules
 */
#ifndef BOARD_H
#define BOARD_H

#include "stm32l4xx_hal.h"

extern UART_HandleTypeDef huart2;   /* ST-LINK virtual COM port */
extern I2C_HandleTypeDef  hi2c1;    /* IMU */
extern TIM_HandleTypeDef  htim3;    /* fan PWM */

void board_init(void);
void error_handler(void);

#endif /* BOARD_H */

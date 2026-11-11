/*
 * stm32l4xx_it.c - interrupt handlers
 */
#include "board.h"

void SysTick_Handler(void)
{
    HAL_IncTick();
}

void USART2_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart2);
}

void HardFault_Handler(void)
{
    error_handler();
}

void NMI_Handler(void) {}
void MemManage_Handler(void) { error_handler(); }
void BusFault_Handler(void)  { error_handler(); }
void UsageFault_Handler(void) { error_handler(); }
void SVC_Handler(void) {}
void DebugMon_Handler(void) {}
void PendSV_Handler(void) {}

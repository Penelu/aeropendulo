/*
 * imu.h - Grove IMU 9DOF (ICM20600 + AK09918, or older MPU-9250 version)
 */
#ifndef IMU_H
#define IMU_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    float acc[3];        /* g   (X, Y, Z of the chip) */
    float gyro[3];       /* deg/s, bias removed */
} imu_raw_t;

typedef struct {
    float theta_acc;     /* angle from the accelerometer only (deg, 90 = vertical) */
    float rate;          /* angular rate about the pivot (deg/s) */
    float theta_gyro;    /* integrated gyro only (deg), for the consistency test */
    float theta;         /* complementary filter output (deg) */
} imu_angle_t;

typedef struct {
    int axis_up, sign_up;
    int axis_side, sign_side;
    int axis_gyro, sign_gyro;
} imu_axes_t;

extern imu_axes_t imu_axes;

bool imu_init(void);                       /* detect and configure, true if found */
uint8_t imu_address(void);                 /* 7-bit address found (0 if none) */
uint8_t imu_whoami(void);
const char *imu_name(void);
bool imu_read(imu_raw_t *r);               /* one burst read of accel + gyro */
void imu_calibrate_gyro(int samples);      /* keep the rod still while it runs */
void imu_angle_reset(imu_angle_t *a, const imu_raw_t *r);
void imu_angle_update(imu_angle_t *a, const imu_raw_t *r, float dt);

#endif /* IMU_H */

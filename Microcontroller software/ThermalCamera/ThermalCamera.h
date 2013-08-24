#ifndef _THERMALCAMERA_H_
#define _THERMALCAMERA_H_

	// Includes:
	#include "bit_manipulation.h"
	
	#include <avr/io.h>
	#include <avr/wdt.h>
	#include <avr/power.h>
	#include <avr/interrupt.h>
	#include <stdlib.h>
	#include <stdio.h>

	#include "USB.h"
	#include <LUFA/Drivers/Peripheral/TWI.h>


	// Function Prototypes: 
	void SetupHardware(void);

#endif


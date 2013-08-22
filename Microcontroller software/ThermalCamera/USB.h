/*
 * USB.h
 *
 * Created: 1.07.2013 15:58:08
 *  Author: Mark
 */ 


#ifndef USB_H_
#define USB_H_
	
	#define USB_RX_CMD_START_CHAR	'<'		// Character, that indicates the start of a command
	#define USB_RX_CMD_END_CHAR		'>'		// Character, that indicates the end of a command
	#define USB_RX_CMD_LENGTH		32		// Size of input buffer (maximum command length)

	//includes
	#include "Descriptors.h"
	#include <LUFA/Drivers/USB/USB.h>
	
	//function prototypes:
	void USB_send_debug(const char *message);
	void USB_send_warning(const char *message);
	void USB_send_error(const char *message);
	void USB_send_cmd(const char *cmd, const char *message);
	
	void EVENT_USB_Device_Connect(void);
	void EVENT_USB_Device_Disconnect(void);
	void EVENT_USB_Device_ConfigurationChanged(void);
	void EVENT_USB_Device_ControlRequest(void);

#endif /* USB_H_ */
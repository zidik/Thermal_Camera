#define DEBUG					1		// Should debug messages be sent

#define SERVO_MAX				608		// Maximal output compare register value (maximal servo angle)
#define SERVO_MIN				175		// Minimal output compare register value (minimal servo angle)

#define MLX_ADDRESS				0x5A	// I2C slave address of Thermal sensor
#define MLX_OBJ_TEMP_ADDRESS	0x07	// Internal address of thermal sensor that contains object temperature
#define MLX_AMB_TEMP_ADDRESS	0x06	// Internal address of thermal sensor that contains ambient temperature

#include "ThermalCamera.h"

static inline bool readMLX(uint8_t address, uint16_t *temperature, uint8_t *pec);

static inline void recieve_incoming_characters();
static inline void parse_command(uint8_t *command);
static inline bool parse_info(uint8_t *command);
static inline bool parse_abs_pos(uint8_t *command);
static inline bool parse_rel_pos(uint8_t *command);
static inline bool parse_servo_pos(uint8_t *command, uint8_t servoNr);
static inline bool parse_csv_u16(uint8_t *char_array, uint8_t start, uint8_t length, uint8_t count, uint16_t *values);
static inline bool parse_temp(uint8_t *command);

static inline void send_datapoint( uint8_t posX, uint8_t posY, uint16_t temp);

static inline uint16_t getServoValue(uint8_t servoNr);
static inline void setServoValue(uint8_t servoNr, uint16_t servoValue);

static inline void scanStep();
static inline void scanInit();
static inline void scanMoveServos();


uint8_t USB_RX_data[USB_RX_CMD_LENGTH];	// array of received bytes
uint8_t USB_RX_data_count = 0;	// number of received bytes
bool USB_RX_CMD_started;	// true if command start sign has been received but end sign not yet



extern USB_ClassInfo_CDC_Device_t VirtualSerial_CDC_Interface;
/** Standard file stream for the CDC interface when set up, so that the virtual CDC COM port can be
 *  used like any regular character stream in the C APIs
 */
static FILE USBSerialStream;

int8_t scanServoDir = 1;	// scanning servo direction - changes between 1 and -1
// TODO: replace counter with timer
uint16_t scanCounter = 0;	//counter for timing
bool scanning = false;	//Current scanning state
bool scanInitialisation = false;	//True if scanning is about to begin (Servos are moving to starting position)
//Current position
uint8_t scanPosX = 0;				
uint8_t scanPosY = 0;

uint8_t scanStepSize = 3;	// Step size
uint8_t scanResolution = 64;	// scanning resolution

int main(void)
{
	SetupHardware();

	// Create a regular character stream for the interface so that it can be used with the stdio.h functions
	CDC_Device_CreateStream(&VirtualSerial_CDC_Interface, &USBSerialStream);
	// Set USB as an standard input and output
	stdin	= &USBSerialStream;
	stdout	= &USBSerialStream;

	GlobalInterruptEnable();
	uint16_t heartBeatCounter = 0;
	uint8_t counter2 = 0;
	
	
	for (;;)
	{
		//Scanning part
		if(scanning){
			scanCounter++;
			if(scanInitialisation){
				if(scanCounter == 0){
					//wait 0xFFFF cycles - so servo would have time to move to initial position
					scanInitialisation = false;
				}
			}
			else{
				if(scanCounter == 6000){
					scanCounter = 0;
					scanStep();
				}
			}
		}
		
		
		// Heartbeat LED
		heartBeatCounter++;
		if(heartBeatCounter == 0){
			SETBIT(PINE,PE6);
			
			//TODO: USB Reconnection on connection loss
			counter2++;
			if(counter2 == 20){
				counter2 = 0;
				/*USB_Disable();
				//_delay_ms(500);
				USB_Init();*/
				
			}
		}
		
		recieve_incoming_characters();

		CDC_Device_USBTask(&VirtualSerial_CDC_Interface);
		USB_USBTask();
	}
}

static inline void scanInit(){
	scanning = true;
	scanInitialisation = true;
	scanCounter = 0;
	scanServoDir = 1;
	scanPosX = 0;
	scanPosY = 0;
	scanMoveServos();
}

static inline void scanStep(){
	uint16_t temperature;
	uint8_t pec;
	
	//Take a reading
	if(readMLX(MLX_OBJ_TEMP_ADDRESS, &temperature, &pec)){
		send_datapoint(scanPosX, scanPosY, temperature);
	}
	else{
		//ERROR
		//TODO: - retry?
		USB_send_cmd("Scan","0");
	}
	
	//Calculate a new position
	//If next step would make Y go over maximum
	if(scanServoDir == 1 && scanPosY >= scanResolution-1){
		scanPosY = scanResolution-1;
		scanPosX++;
		scanServoDir = -1;
	}
	//If next step would make Y go below 0 (and underflow)
	else if(scanServoDir == -1 && scanPosY == 0){
		scanPosX++;
		scanServoDir = 1;
	}
	//Normal step
	else{
		scanPosY += scanServoDir;
	}
	
	if(scanPosX >= scanResolution){
		//end scanning
		scanning = false;
		return;
	}
	
	//Set up the new position
	scanMoveServos();
}

static inline void scanMoveServos(){
	//Padding should be around 100.., so reasonable sizes for
	//step - resolution
	//6 - 39
	//5 - 47
	//4 - 58
	//3 - 78
	uint8_t padding = ((SERVO_MAX-SERVO_MIN) - scanResolution*scanStepSize) / 2;
	
	OCR1B = SERVO_MAX - padding - scanPosY*scanStepSize; //Flipped up-down
	OCR1A = SERVO_MIN + padding + scanPosX*scanStepSize;
}

static inline void send_datapoint( uint8_t posX, uint8_t posY, uint16_t temp )
{
	char output_string[16];
	int cx = snprintf(	output_string, sizeof(output_string),
						"%u:%u:%u",
						posX, posY, temp);
						
	if(cx == -1)
		USB_send_warning("snprintf error");
	if(cx >= sizeof(output_string))
		USB_send_warning("snprintf error - buffer is not large enough");
	USB_send_cmd("Scan",output_string);
}

static inline void recieve_incoming_characters(){
	int8_t recieved_char;
	while(EOF != (recieved_char = getchar())){
		if(recieved_char == USB_RX_CMD_START_CHAR){
			if(USB_RX_CMD_started){
				USB_send_warning("Command already started!");
			}
			else{
				USB_RX_CMD_started = true;
			}
			USB_RX_data_count = 0;
			memset(USB_RX_data, 0, USB_RX_CMD_LENGTH);
		}
		else if(recieved_char == USB_RX_CMD_END_CHAR && USB_RX_CMD_started){
			USB_RX_CMD_started = false;
			parse_command(USB_RX_data);
		}
		else if(USB_RX_CMD_started){
			if(USB_RX_data_count==USB_RX_CMD_LENGTH){
				USB_RX_CMD_started = false;
				USB_send_warning("Input buffer overflow - command ignored");
			}
			else{
				//let's add characters to data
				USB_RX_data[USB_RX_data_count] = recieved_char;
				USB_RX_data_count++;
			}
		}
		else{
			USB_send_warning("Command has not started! - ignoring..");
		}
	}	
}

static inline void parse_command(uint8_t *command){
	uint8_t cmd_parsed = 0;
	switch(command[0]){
		
		//Information
		case 'i':
		cmd_parsed = parse_info(command);
		break;
		
		//Move servos together
		case 'a':
			cmd_parsed = parse_abs_pos(command);
		break;
		
		case 'r':
			cmd_parsed = parse_rel_pos(command);
		break;
		
		case 's':
			cmd_parsed = true;
			scanInit();
		break;
		
		//Move servos separately
		case 'A':
			cmd_parsed = parse_servo_pos(command, 0);
		break;
		
		case 'B':
			cmd_parsed = parse_servo_pos(command, 1);
		break;
		
		//Read temperature
		case 't':
			cmd_parsed = parse_temp(command);
		break;
		
		default:
			USB_send_warning("Unknown command.");
		break;
	}
	if(!cmd_parsed){
		USB_send_warning("Command could not be parsed.");
	}
}

static inline bool parse_info(uint8_t *command){
	if(command[1] == '?'){
		USB_send_cmd("INFO", "dev=ThermalCamera");
		return true;
	}
	return false;
}
static inline bool parse_abs_pos(uint8_t *command){
	if(command[1] == '?'){
		//combine results into string
		char output_string[12];
		int cx = snprintf(output_string, sizeof(output_string), "%u,%u", OCR1A, OCR1B);
		if(cx == -1){
			USB_send_warning("snprintf error");
		}
		if(cx >= sizeof(output_string)){
			USB_send_warning("snprintf error - buffer is not large enough");
		}
		USB_send_cmd("ABSPOS", output_string);
		return true;
	}
	else if(command[1] == '='){
		uint16_t values[2];
		if(parse_csv_u16(command, 2, USB_RX_CMD_LENGTH, 2, values)){
			setServoValue(0, values[0]);
			setServoValue(1, values[1]);
			return true;
		}
	}
	return false;
	
}
static inline bool parse_rel_pos(uint8_t *command){
	if(command[1] == '='){
		uint16_t values[2];
		if(parse_csv_u16(command, 2, USB_RX_CMD_LENGTH, 2, values)){
			setServoValue(0, getServoValue(0)+values[0]);
			setServoValue(1, getServoValue(1)+values[1]);
			return true;
		}
	}
	return false;
}
static inline bool parse_servo_pos(uint8_t *command, uint8_t servoNr){
	if(command[1] == '?'){
		char buffer[6] = "";
		itoa (getServoValue(servoNr), buffer, 10);
		USB_send_cmd("OCRA",buffer);
		return true;
	}
	else if(command[1] == '='){
		setServoValue(servoNr, atoi((char*)command+2));
		return true;
	}
	return false;
}
static inline bool parse_temp( uint8_t *command )
{
	uint8_t choice = -1;
	// read object temperature
	if(command[1] == 'o')
		choice = 0;
	// read ambient temperature
	if(command[1] == 'a')
		choice = 1;
	
	if(choice != -1 && command[2] == '?')
	{
		uint16_t temperature;
		uint8_t pec;
		bool success = false;
		if(choice == 0)
		{
			success = readMLX(MLX_OBJ_TEMP_ADDRESS, &temperature, &pec);
		}
		else if(choice == 1){
			success = readMLX(MLX_AMB_TEMP_ADDRESS, &temperature, &pec);
		}
		
		if(success){
			char output_string[6] = "";
			utoa(temperature, output_string, 10);
			//send result to USB
			if(choice == 0)
				USB_send_cmd("OBJECT",output_string);
			else if(choice == 1)
				USB_send_cmd("AMBIENT",output_string);
			return true;
		}
	}
	return false;
}

/*
//gets comma separated numeric values from char_array, starting from "start" and with length "length".
//
// char_array	- array to parse
// start		- point, from where start parsing char_array
// length		- char_array length
// count		- how many values to get
// values		- pointer to array where to store found values.
*/
static inline bool parse_csv_u16( uint8_t *char_array, uint8_t start, uint8_t length, uint8_t count, uint16_t *values )
{
	//get first value
	values[0] = (uint16_t)atoi((char*)char_array+start);
	//get all other values (all sepparated by comma)
	for(uint8_t i = 1; i < count; i++){
		bool found = false;
		while(start < length){
			//find next comma
			if(char_array[start] == ','){
				start++;
				values[i] = (uint16_t)atoi((char*)char_array+start);
				found = true;					
				break;
			}
			start++;
		}
		if(!found){
			//If not enough numbers were found
			return false;
		}
	}
	return true;
}

static inline bool readMLX(uint8_t address, uint16_t *temperature, uint8_t *pec){
	bool success = false;
	// Start a read session to device at address 0x5A, internal address 0x07 with a 1ms timeout
	uint8_t temp_l, temp_h;
	//Start writing
	if (TWI_StartTransmission((MLX_ADDRESS<<1) | TWI_ADDRESS_WRITE, 1) == TWI_ERROR_NoError){
		//send adress to read
		if(TWI_SendByte(address)){
			//start reading
			if (TWI_StartTransmission((MLX_ADDRESS<<1) | TWI_ADDRESS_READ, 1) == TWI_ERROR_NoError){
				// Read three bytes, acknowledge after the third byte is received
				if(TWI_ReceiveByte(&temp_l, false)){
					if(TWI_ReceiveByte(&temp_h, false)){
						if(TWI_ReceiveByte(pec, true)){
							// TODO: use pec too
							// This masks off the error bit of the high byte, then moves it left 8 bits and adds the low byte.
							if(BITVAL(temp_h,7)){
								USB_send_warning("Temp sensor errorbit high");
							}
							*temperature = (((uint16_t)(temp_h & 0x7F))<<8)+temp_l;
							success = true;
						}
					}
				}
				
			}
		}
	}
	TWI_
	// Must stop transmission afterwards to release the bus
	TWI_StopTransmission();
	return success;
}

static inline uint16_t getServoValue(uint8_t servoNr){
	if(servoNr == 0)
		return OCR1A;
	else if(servoNr == 1)
		return OCR1B;
	else{
		return -1;
		USB_send_warning("Invalid servoNr - (getServoValue)");
	}
	
}
static inline void setServoValue(uint8_t servoNr, uint16_t servoValue){
	
	if(servoValue < SERVO_MIN || servoValue > SERVO_MAX){
		char output_string[72];
		int cx = snprintf(output_string, sizeof(output_string),
			"Servo position value has to be between %u and %u. (%u was set)",
			SERVO_MIN, SERVO_MAX, servoValue);
		if(cx == -1)
			USB_send_warning("snprintf error");
		if(cx >= sizeof(output_string))
			USB_send_warning("snprintf error - buffer is not large enough");
		USB_send_warning(output_string);
	}
	else if(servoNr == 0){
		OCR1A = servoValue;
	}
	else if(servoNr == 1){
		OCR1B = servoValue;
	}
	else{
		USB_send_warning("Invalid servoNr - (setServoValue)");
	}
}



void SetupHardware(void)
{
	// Remove CLKDIV8
	CLKPR = 0x80;
	CLKPR = 0x00;
	// Disable WDT
	CLEARBIT(MCUSR,WDRF);
	wdt_disable();
	// Disable JTAG
	SETBIT(MCUCR,JTD);
	SETBIT(MCUCR,JTD);
	
	// Setup debug LED
	SETBIT(DDRE,PE6);
	
	servo_setup();
	TWI_setup();
	USB_Init();
}

void servo_setup()
{
	// Setup servo timer
	TCCR1A|=(1<<COM1A1)|(1<<COM1B1)|(1<<WGM11);			//NON Inverted PWM
	TCCR1B|=(1<<WGM13)|(1<<WGM12)|(1<<CS11)|(1<<CS10);	//PRESCALER=64 MODE 14(FAST PWM)
	ICR1=4999;											//fPWM=50Hz (Period = 20ms Standard).
	SETBIT(DDRB,PB5);
	SETBIT(DDRB,PB6);
}

void TWI_setup()
{
	// Initialize the TWI driver before first use at 100KHz
	TWI_Init(TWI_BIT_PRESCALE_1, TWI_BITLENGTH_FROM_FREQ(1, 100000));
	SETBIT(DDRD,PD0);
	SETBIT(DDRD,PD1);
}



/*
* EasyDaqRelay simulator
*
* See http://www.easydaq.biz/Datasheets/Data%20Sheet%2034%20%20(Using%20Linux%20with%20EasyDAQ%20USB%20Products).pdf
*
* This sketch simulates the behaviour of an EasyDaq USB Relay ESB8PR2,
* as follows:
*
* We read from serial port on 9600. This occupies digital pins 0 and 1
*
* We map EasyDaq relays 1 to 8 to Arduino pins 2 to 9.
*
* ASCII'B' (42H),X 
* Initialises the card (sets the port & channel I/O directions). Set direction of Port B, 
1=Input, 0= output. (i.e. where X=10111111 (AFH) = sets bit 7 as an output, the rest as inputs).  
* 
* This maps to setting the pinMode for Arduino pins 2 to 9
*
* ASCII'C' (43H), X
* Write data X to Port B (i.e. X=00000001 (01H), sets channel 1 to active). Valid data bytes 
are latched by the card until a further valid data byte is written to it.
*
*
* ASCII ‘A’ (41H), X 
* Read Port B (Char X=don’t care. Device sends 1 byte of returned data).
*
*/

char easyDaqCommand;
int easyDaqValue;
const int outputDiagnostics = false;

const int firstGPIOPin = 2;


void setup()
{
  // EasyDaq serial port operates at 9600
  Serial.begin(9600);
  
  //if (outputDiagnostics) {
    Serial.println("Starting up...");
  //}
  
}

void executeCommand(char command,int value) {
  if (outputDiagnostics) {
    Serial.print("Executing command: ");
    Serial.print(command);
    Serial.print(" with value: ");
    Serial.print(value,HEX);
    Serial.println("H");
  }
  
  if (command=='B') {
    // set the pinMode to be out on pins 2 to 9
    //tone(13, 1000, 500);
    for (int bitPosition = 0; bitPosition <= 8; bitPosition++) {

      if (bitRead(value,bitPosition) == 0) {
        
        pinMode(firstGPIOPin+bitPosition, OUTPUT);
      } else {
        pinMode(firstGPIOPin+bitPosition, INPUT);
      }
    }  
  } else if (command=='C') {

    for (int bitPosition = 0; bitPosition <= 8; bitPosition++) {
    //tone(13, 2000, 500);
      if (bitRead(value,bitPosition) == 1) {
        digitalWrite(firstGPIOPin+bitPosition, HIGH);
      } else {
        digitalWrite(firstGPIOPin+bitPosition, LOW);
      }
    }
  } else if (command=='A') {
    Serial.write(lowByte(31));    
  }
}
void loop()
{
 

 

  if (Serial.available()>=2) // check to see that we have at least two bytes to read
  {
    
    easyDaqCommand = Serial.read();
    
    // determine if the character is a command or a value
    if (easyDaqCommand  == 'A' || easyDaqCommand =='B' || easyDaqCommand =='C') {
      easyDaqValue = Serial.read();
      executeCommand(easyDaqCommand, easyDaqValue);
    }
      
    
  }

}

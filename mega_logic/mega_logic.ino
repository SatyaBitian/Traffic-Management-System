int lanePins[4][3] = {{2,3,4}, {6,7,8}, {9,10,11}, {12,13,44}}; // R, Y, G
int lastGreenLane = 0;

void setup() {
  Serial.begin(9600);
  for(int i=0; i<4; i++) {
    for(int j=0; j<3; j++) pinMode(lanePins[i][j], OUTPUT);
    digitalWrite(lanePins[i][0], HIGH); // All Red
  }
  // Initial Green on Lane 1
  digitalWrite(lanePins[0][0], LOW);
  digitalWrite(lanePins[0][2], HIGH);
}

void loop() {
  if (Serial.available() > 0) {
    int targetLane = Serial.readStringUntil('\n').toInt();

    if(targetLane != lastGreenLane) {
      // 1. Current to Red
      digitalWrite(lanePins[lastGreenLane][2], LOW); 
      digitalWrite(lanePins[lastGreenLane][0], HIGH);

      // 2. Target Yellow (0.5s)
      digitalWrite(lanePins[targetLane][0], LOW);   
      digitalWrite(lanePins[targetLane][1], HIGH);  
      delay(500);                                   
      digitalWrite(lanePins[targetLane][1], LOW);   

      // 3. Target Green
      digitalWrite(lanePins[targetLane][2], HIGH);  
      lastGreenLane = targetLane;
    }
  }
}

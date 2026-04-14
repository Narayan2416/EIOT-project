#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "WIFI_NAME";
const char* password = "WIFI_PASSWORD";

int led = 5;
int count = 0;

unsigned long lastSend = 0;

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.print("ESP IP: ");
  Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);
  pinMode(led, OUTPUT);

  connectWiFi();
}
  
void loop() {

  // Reconnect WiFi if needed
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Reconnecting WiFi...");
    connectWiFi();
  }

  // Send every 10 seconds
  if (WiFi.status() == WL_CONNECTED && millis() - lastSend >= 10000) {

    lastSend = millis();

    HTTPClient http;

    http.begin("http://<SERVER_IP>/data");
    http.addHeader("Content-Type", "application/json");

    String jsonData = "{\"count\": " + String(count++) + "}";

    Serial.println("Sending data...");

    int httpResponseCode = http.POST(jsonData);

    if (httpResponseCode > 0) {
      Serial.print("Response Code: ");
      Serial.println(httpResponseCode);
      Serial.println(http.getString());
    } else {
      Serial.print("HTTP Error: ");
      Serial.println(http.errorToString(httpResponseCode));
    }

    http.end();

    // Optional LED blink
    digitalWrite(led, HIGH);
    delay(100);
    digitalWrite(led, LOW);
  }
}

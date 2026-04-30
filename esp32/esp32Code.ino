#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// WiFi credentials
const char* ssid = "WIFI_NAME";
const char* password = "WIFI_PASSWORD";

// DHT setup
#define DHTPIN 4
#define soilPin 34    // Connect DHT11 DATA pin to GPIO 4
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// Timer
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

  dht.begin();   // Initialize DHT sensor

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

    // Read sensor
    float temperature = dht.readTemperature();  // Celsius
    float humidity = dht.readHumidity();
    int soil =  analogRead(soilPin);

    // Check if reading failed
    if (isnan(temperature) || isnan(humidity)) {
      Serial.println("Failed to read from DHT sensor!");
      return;
    }

    Serial.println("Sending data...");
    Serial.print("Temp: ");
    Serial.print(temperature);
    Serial.print(" °C | Humidity: ");
    Serial.print(humidity);
    Serial.print(" | Soil: ");
    Serial.print(soil);
    Serial.println(" %");

    HTTPClient http;
    http.begin("http://10.148.200.92:5000/api/esp32/reading");
    http.addHeader("Content-Type", "application/json");

    // JSON payload
    String jsonData = "{";
    jsonData += "\"temperature\": " + String(temperature) + ",";
    jsonData += "\"humidity\": " + String(humidity) + ",";
    jsonData += "\"soil\": " + String(soil);
    jsonData += "}";

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
  }
}
#include <WiFi.h>
#include <HTTPClient.h>
#include <Arduino_GFX_Library.h>
#include "AudioFileSourceICYStream.h"
#include "AudioFileSourceBuffer.h"
#include "AudioGeneratorMP3.h"
#include "AudioOutputI2S.h"
#include "MjpegClass_tsk.h"
#define SPI_FREQUENCY 240000000  // Set the SPI frequency to 80 MHz
#define FPS 60
#define MJPEG_BUFFER_SIZE (160 * 128 * 2 / 4) // Adjusted based on display resolution
#define I2S_DOUT 25
#define I2S_BCLK 27
#define I2S_LRC 26

const char* ssid = "Rickswifi";
const char* password = "ricksuvo101";
const char* serverIP = "192.168.1.18";

int LCD_SCK = 18;
int LCD_MISO = 19;
int LCD_MOSI = 23;
int LCD_DC_A0 = 2;
int LCD_RESET = 15;
int LCD_CS = 5;

Arduino_ESP32SPI *bus = new Arduino_ESP32SPI(LCD_DC_A0, LCD_CS, LCD_SCK, LCD_MOSI, LCD_MISO);
Arduino_GFX *gfx = new Arduino_ST7735(bus, LCD_RESET, 3, false, ST7735_TFTWIDTH, ST7735_TFTHEIGHT, 0, 0, 0, 0, false);

MjpegClass mjpeg;

// Audio
AudioFileSourceICYStream *file;
AudioFileSourceBuffer *buff;
AudioGeneratorMP3 *mp3;
AudioOutputI2S *out;

uint8_t *mjpeg_buf;

static int drawMCU(JPEGDRAW *pDraw) {
  gfx->draw16bitBeRGBBitmap(pDraw->x, pDraw->y, pDraw->pPixels, pDraw->iWidth, pDraw->iHeight);
  return 1;
}

void setup() {
  Serial.begin(115200);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");

  gfx->begin();
  gfx->fillScreen(BLACK);
  
  // Initialize I2S output
  out = new AudioOutputI2S();
  out->SetPinout(I2S_BCLK, I2S_LRC, I2S_DOUT);
  out->SetGain(0.5);

  // Allocate MJPEG buffer
  mjpeg_buf = (uint8_t *)malloc(MJPEG_BUFFER_SIZE);
  if (!mjpeg_buf) {
    Serial.println(F("mjpeg_buf malloc failed!"));
    return;
  }

  // Initialize audio components
  mp3 = new AudioGeneratorMP3();
}

void playVideoAndAudio(String videoURL, String audioURL) {
  HTTPClient http;

  // Fetch and play video
  http.begin(videoURL.c_str());
  int httpCode = http.GET();
  
  if (httpCode == HTTP_CODE_OK) {
    WiFiClient* stream = http.getStreamPtr();
    
    mjpeg.setup(
      stream,               // Stream for video
      mjpeg_buf,            // Buffer for MJPEG data
      drawMCU,              // Callback for drawing MJPEG frames
      true,                 // Use Big Endian
      0,                    // x position
      0,                    // y position
      gfx->width(),         // Width limit
      gfx->height()         // Height limit
    );

    // Start audio playback
    file = new AudioFileSourceICYStream(audioURL.c_str());
    buff = new AudioFileSourceBuffer(file, 2048);
    mp3->begin(buff, out);
    
    unsigned long lastVideoFrameTime = 0;
    const unsigned long frameInterval = 1000 / FPS; // Time between frames in milliseconds

    while (stream->connected()) {
      unsigned long currentTime = millis();

      // Process audio
      if (mp3->isRunning()) {
        if (!mp3->loop()) mp3->stop();
      }

      // Process video frame if it's time for a new frame
      if (currentTime - lastVideoFrameTime >= frameInterval) {
        if (mjpeg.readMjpegBuf()) {
          mjpeg.drawJpg();
          lastVideoFrameTime = currentTime;
        } else {
          Serial.println(F("MJPEG read error"));
          break;
        }
      }

      // Small delay to prevent tight looping
      delay(1);
    }
    
    mp3->stop();
    delete file;
    delete buff;
  } else {
    Serial.println(F("ERROR: Failed to fetch video file"));
  }

  http.end();
}


void loop() {
  String videoURL = String("http://") + serverIP + ":5000/video";
  String audioURL = String("http://") + serverIP + ":5000/audio"; // Use /aac for AAC audio
  playVideoAndAudio(videoURL, audioURL);
  delay(1000);  // Wait a bit before trying to play again
}

void audio_info(const char *info) {
  Serial.print("audio_info: "); Serial.println(info);
}

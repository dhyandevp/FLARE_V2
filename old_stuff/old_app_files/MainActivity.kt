
package com.flare.mobile

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioManager
import android.media.ToneGenerator
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "FLARE"
        private const val CUTOFF = 70.0
        private const val CHANNEL_ID = "flare_sos_wifi_v1"
        private const val NOTIFICATION_ID = 1001
        private const val NOTIFICATION_PERMISSION_REQUEST = 100
    }

    private lateinit var connectionStatus: TextView
    private lateinit var threatStatus: TextView
    private lateinit var waterValue: TextView
    private lateinit var rainValue: TextView
    private lateinit var soilValue: TextView
    private lateinit var riskValue: TextView
    private lateinit var sosStatus: TextView
    private lateinit var alarmStatus: TextView

    private lateinit var esp32IpInput: EditText
    private lateinit var connectButton: Button
    private lateinit var testSosButton: Button
    private lateinit var stopAlarmButton: Button

    private val mainHandler = Handler(Looper.getMainLooper())

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private var toneGenerator: ToneGenerator? = null

    private var alarmRunning = false

    // SOS state
    private var sosTriggered = false
    private var alarmAcknowledged = false

    // Sensor values
    private var water: Double? = null
    private var rain: Double? = null
    private var soil: Double? = null

    private val alarmRunnable = object : Runnable {
        override fun run() {
            if (!alarmRunning) return

            try {
                toneGenerator?.startTone(
                    ToneGenerator.TONE_PROP_BEEP2,
                    450
                )
            } catch (e: Exception) {
                Log.e(TAG, "Alarm sound error", e)
            }

            mainHandler.postDelayed(this, 1200)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        initializeViews()
        createNotificationChannel()
        requestNotificationPermission()

        connectButton.setOnClickListener {
            connectToEsp32()
        }

        testSosButton.setOnClickListener {
            triggerSos("FLARE MANUAL TEST SOS")
        }

        stopAlarmButton.setOnClickListener {
            acknowledgeSos()
        }

        connectionStatus.text = "ESP32: DISCONNECTED"
        threatStatus.text = "THREAT: WAITING FOR DATA"
        sosStatus.text = "SOS: STANDBY"
        alarmStatus.text = "ALARM: OFF"

        updateSensorDisplay()
    }

    private fun initializeViews() {
        connectionStatus = findViewById(R.id.connectionStatus)
        threatStatus = findViewById(R.id.threatStatus)

        waterValue = findViewById(R.id.waterValue)
        rainValue = findViewById(R.id.rainValue)
        soilValue = findViewById(R.id.soilValue)
        riskValue = findViewById(R.id.riskValue)

        sosStatus = findViewById(R.id.sosStatus)
        alarmStatus = findViewById(R.id.alarmStatus)

        testSosButton = findViewById(R.id.testSosButton)
        stopAlarmButton = findViewById(R.id.stopAlarmButton)
        connectButton = findViewById(R.id.connectButton)

        esp32IpInput = findViewById(R.id.esp32IpInput)
    }

    // -----------------------------------------
    // ESP32 WEBSOCKET CONNECTION
    // -----------------------------------------

    private fun connectToEsp32() {
        val ip = esp32IpInput.text.toString().trim()

        val ipPattern = Regex(
            "^((25[0-5]|2[0-4][0-9]|1?[0-9]?[0-9])\\.){3}" +
                    "(25[0-5]|2[0-4][0-9]|1?[0-9]?[0-9])$"
        )

        if (!ip.matches(ipPattern)) {
            connectionStatus.text = "INVALID ESP32 IP ADDRESS"
            return
        }

        webSocket?.cancel()
        webSocket = null

        connectionStatus.text = "CONNECTING TO ESP32..."

        val url = "ws://$ip:81/"

        Log.d(TAG, "Connecting to $url")

        val request = Request.Builder()
            .url(url)
            .build()

        webSocket = httpClient.newWebSocket(
            request,
            webSocketListener
        )
    }

    private val webSocketListener = object : WebSocketListener() {

        override fun onOpen(
            webSocket: WebSocket,
            response: Response
        ) {
            Log.d(TAG, "WebSocket connected: ${response.code}")

            runOnUiThread {
                connectionStatus.text = "ESP32: CONNECTED"
            }
        }

        override fun onMessage(
            webSocket: WebSocket,
            text: String
        ) {
            Log.d(TAG, "Received ESP32 data: $text")

            try {
                val json = JSONObject(text)

                val newWater = readSensorValue(json, "water")
                val newRain = readSensorValue(json, "rain")
                val newSoil = readSensorValue(json, "soil")

                runOnUiThread {
                    water = newWater
                    rain = newRain
                    soil = newSoil

                    updateSensorReadings()
                }

            } catch (e: Exception) {
                Log.e(TAG, "Invalid sensor JSON: $text", e)
            }
        }

        override fun onClosing(
            webSocket: WebSocket,
            code: Int,
            reason: String
        ) {
            Log.w(TAG, "WebSocket closing: $code - $reason")
            webSocket.close(code, reason)
        }

        override fun onClosed(
            webSocket: WebSocket,
            code: Int,
            reason: String
        ) {
            Log.w(TAG, "WebSocket closed: $code - $reason")

            runOnUiThread {
                markDisconnected("CONNECTION CLOSED: $reason")
            }
        }

        override fun onFailure(
            webSocket: WebSocket,
            t: Throwable,
            response: Response?
        ) {
            Log.e(TAG, "WebSocket failure: ${t.message}", t)

            runOnUiThread {
                markDisconnected(
                    "CONNECTION FAILED: ${t.message ?: "Unknown error"}"
                )
            }
        }
    }

    // -----------------------------------------
    // SENSOR DATA
    // -----------------------------------------

    private fun readSensorValue(
        json: JSONObject,
        key: String
    ): Double? {

        if (!json.has(key) || json.isNull(key)) {
            return null
        }

        val value = json.optDouble(key, Double.NaN)

        return if (value.isFinite() && value in 0.0..100.0) {
            value
        } else {
            null
        }
    }

    private fun updateSensorReadings() {

        updateSensorDisplay()

        val validValues = listOfNotNull(
            water,
            rain,
            soil
        )

        if (validValues.isEmpty()) {
            threatStatus.text = "THREAT: WAITING FOR DATA"
            riskValue.text = "RISK SCORE: UNAVAILABLE"
            return
        }

        // Combined demonstration risk score.
        // All three sensors must be valid for this calculation.

        if (water != null && rain != null && soil != null) {

            val calculatedRisk =
                water!! * 0.40 +
                        soil!! * 0.30 +
                        rain!! * 0.30

            riskValue.text =
                "RISK SCORE: ${calculatedRisk.toInt()}%"

        } else {
            riskValue.text = "RISK SCORE: INCOMPLETE DATA"
        }

        // Any valid sensor reaching 70% triggers SOS.

        val anySensorCritical = validValues.any {
            it >= CUTOFF
        }

        if (anySensorCritical) {

            threatStatus.text = "THREAT: CRITICAL SENSOR READING"

            if (!sosTriggered) {
                triggerSos("FLARE: SENSOR CUTOFF REACHED")
            }

        } else {

            // Only reset when ALL THREE sensors are valid
            // and every reading is below the cutoff.

            val allSensorsValid =
                water != null &&
                        rain != null &&
                        soil != null

            val allSensorsSafe =
                allSensorsValid &&
                        water!! < CUTOFF &&
                        rain!! < CUTOFF &&
                        soil!! < CUTOFF

            if (allSensorsSafe) {

                threatStatus.text = "THREAT: BELOW CUTOFF"

                if (sosTriggered) {
                    resetSosCondition()
                }

            } else {

                threatStatus.text = "THREAT: INCOMPLETE SENSOR DATA"
            }
        }
    }

    private fun updateSensorDisplay() {

        waterValue.text = water?.let {
            "Water: ${it.toInt()}%"
        } ?: "Water: N/A"

        rainValue.text = rain?.let {
            "Rain: ${it.toInt()}%"
        } ?: "Rain: N/A"

        soilValue.text = soil?.let {
            "Soil: ${it.toInt()}%"
        } ?: "Soil: N/A"
    }

    // -----------------------------------------
    // SOS SYSTEM
    // -----------------------------------------

    private fun triggerSos(message: String) {

        if (sosTriggered) return

        sosTriggered = true
        alarmAcknowledged = false

        sosStatus.text = "SOS: ACTIVE"

        threatStatus.text = "THREAT: CRITICAL"

        startSosAlarm()

        showSosNotification(message)

        Log.w(TAG, "SOS TRIGGERED: $message")
    }

    // User presses STOP ALARM.
    // This acknowledges the SOS but does not clear
    // the underlying critical sensor condition.

    private fun acknowledgeSos() {

        if (!sosTriggered) {
            stopAlarmSound()
            sosStatus.text = "SOS: STANDBY"
            return
        }

        alarmAcknowledged = true

        stopAlarmSound()

        sosStatus.text = "SOS: ACTIVE - ACKNOWLEDGED"

        Log.d(TAG, "SOS acknowledged by user")
    }

    // Reset only after all three valid readings
    // have fallen below the cutoff.

    private fun resetSosCondition() {

        stopAlarmSound()

        sosTriggered = false
        alarmAcknowledged = false

        sosStatus.text = "SOS: STANDBY"

        Log.d(TAG, "SOS condition reset")
    }

    // -----------------------------------------
    // ALARM SOUND
    // -----------------------------------------

    private fun startSosAlarm() {

        if (alarmRunning || alarmAcknowledged) return

        alarmRunning = true

        try {
            toneGenerator = ToneGenerator(
                AudioManager.STREAM_ALARM,
                65
            )

            alarmStatus.text = "ALARM: ACTIVE"

            mainHandler.removeCallbacks(alarmRunnable)
            mainHandler.post(alarmRunnable)

        } catch (e: Exception) {

            alarmStatus.text = "ALARM: SOUND UNAVAILABLE"

            Log.e(TAG, "Could not start alarm", e)
        }
    }

    // Stops only the sound. Does not reset SOS.

    private fun stopAlarmSound() {

        alarmRunning = false

        mainHandler.removeCallbacks(alarmRunnable)

        try {
            toneGenerator?.stopTone()
            toneGenerator?.release()

        } catch (e: Exception) {
            Log.e(TAG, "Error stopping alarm", e)
        }

        toneGenerator = null

        alarmStatus.text = "ALARM: OFF"
    }

    // -----------------------------------------
    // NOTIFICATIONS
    // -----------------------------------------

    private fun createNotificationChannel() {

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {

            val channel = NotificationChannel(
                CHANNEL_ID,
                "FLARE SOS Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "FLARE sensor warning notifications"
            }

            val manager = getSystemService(
                Context.NOTIFICATION_SERVICE
            ) as NotificationManager

            manager.createNotificationChannel(channel)
        }
    }

    private fun requestNotificationPermission() {

        if (
            Build.VERSION.SDK_INT >= 33 &&
            ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) {

            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                NOTIFICATION_PERMISSION_REQUEST
            )
        }
    }

    private fun showSosNotification(message: String) {

        if (
            Build.VERSION.SDK_INT >= 33 &&
            ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) {

            Log.w(TAG, "Notification permission not granted")
            return
        }

        val notification = NotificationCompat.Builder(
            this,
            CHANNEL_ID
        )
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("FLARE SOS ALERT")
            .setContentText(message)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(true)
            .build()

        NotificationManagerCompat.from(this).notify(
            NOTIFICATION_ID,
            notification
        )
    }

    // -----------------------------------------
    // CONNECTION STATUS
    // -----------------------------------------

    private fun markDisconnected(
        message: String = "ESP32: DISCONNECTED"
    ) {
        connectionStatus.text = message
        Log.w(TAG, message)
    }

    // -----------------------------------------
    // CLEANUP
    // -----------------------------------------

    override fun onDestroy() {

        mainHandler.removeCallbacks(alarmRunnable)

        stopAlarmSound()

        webSocket?.cancel()
        webSocket = null

        httpClient.dispatcher.executorService.shutdown()

        super.onDestroy()
    }
}

package com.flare.mobile

import android.Manifest
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.media.AudioManager
import android.media.ToneGenerator
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log
import android.view.View
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * FLARE V2 app.
 * UI   = assets/dashboard.html in a WebView (same design as the ESP32 website).
 * Kotlin = WebSocket to the ESP32, SOS alarm sound, vibration, notification.
 */
class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "FLARE"
        private const val DEFAULT_LIMIT = 70.0
        private const val CHANNEL_ID = "flare_sos_v2"
        private const val NOTIFICATION_ID = 1001
        private const val NOTIFICATION_PERMISSION_REQUEST = 100
        private const val PREFS = "flare_prefs"
        private const val KEY_IP = "esp32_ip"
        private const val ACTION_STOP = "com.flare.mobile.STOP_ALARM"
        private const val RECONNECT_DELAY_MS = 3000L
        private val SENSOR_NAMES = listOf("Water", "Rain", "Soil")
        private val IP_PATTERN = Regex(
            "^((25[0-5]|2[0-4][0-9]|1?[0-9]?[0-9])\\.){3}" +
                    "(25[0-5]|2[0-4][0-9]|1?[0-9]?[0-9])$"
        )
    }

    private lateinit var root: View
    private lateinit var webView: WebView
    private var pageReady = false

    private val mainHandler = Handler(Looper.getMainLooper())

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(6, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(20, TimeUnit.SECONDS)
        .build()

    // Connection
    private var webSocket: WebSocket? = null
    private var targetIp: String? = null
    private var connState = "disconnected"
    private var connText = "Enter ESP32 IP"

    // Sensors (0..100, null = invalid)
    private var water: Double? = null
    private var rain: Double? = null
    private var soil: Double? = null
    private val limits = doubleArrayOf(DEFAULT_LIMIT, DEFAULT_LIMIT, DEFAULT_LIMIT)

    // SOS
    private var sosTriggered = false
    private var alarmAcknowledged = false
    private var manualTest = false
    private var alarmRunning = false
    private var toneGenerator: ToneGenerator? = null

    private val alarmRunnable = object : Runnable {
        override fun run() {
            if (!alarmRunning) return
            try {
                toneGenerator?.startTone(ToneGenerator.TONE_PROP_BEEP2, 450)
            } catch (e: Exception) {
                Log.e(TAG, "Alarm sound error", e)
            }
            vibrate()
            mainHandler.postDelayed(this, 1200)
        }
    }

    private val reconnectRunnable = Runnable {
        targetIp?.let { openSocket(it) }
    }

    // ---------------------------------------------------------------
    // LIFECYCLE
    // ---------------------------------------------------------------

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        root = findViewById(R.id.root)
        webView = findViewById(R.id.webView)

        // keep the page clear of status bar / nav bar / keyboard
        ViewCompat.setOnApplyWindowInsetsListener(root) { v, insets ->
            val bars = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.ime()
            )
            v.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            WindowInsetsCompat.CONSUMED
        }

        applySystemBars(dark = true)
        createNotificationChannel()
        requestNotificationPermission()
        setupWebView()

        val saved = prefs().getString(KEY_IP, null)
        if (!saved.isNullOrBlank()) connectToEsp32(saved)

        handleIntent(intent)
    }

    // "Stop alarm" button inside the notification lands here
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        if (intent != null && intent.action == ACTION_STOP) {
            intent.action = null
            acknowledgeSos()
        }
    }

    override fun onDestroy() {
        mainHandler.removeCallbacksAndMessages(null)
        stopAlarmSound()
        targetIp = null
        webSocket?.cancel()
        webSocket = null
        httpClient.dispatcher.executorService.shutdown()
        webView.destroy()
        super.onDestroy()
    }

    private fun prefs() = getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    // ---------------------------------------------------------------
    // WEBVIEW (UI)
    // ---------------------------------------------------------------

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        webView.setBackgroundColor(Color.TRANSPARENT)
        webView.overScrollMode = View.OVER_SCROLL_NEVER
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.addJavascriptInterface(Bridge(), "Android")

        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView, url: String) {
                pageReady = true
                pushStatus()
                pushAlarm()
            }

            // page has no links; never navigate away
            override fun shouldOverrideUrlLoading(
                view: WebView,
                request: WebResourceRequest
            ): Boolean = true
        }

        webView.loadUrl("file:///android_asset/dashboard.html")
    }

    private fun js(code: String) {
        if (pageReady) webView.evaluateJavascript(code, null)
    }

    private fun pushStatus() {
        js("window.FLARE&&FLARE.onStatus(${JSONObject.quote(connState)},${JSONObject.quote(connText)})")
    }

    private fun pushAlarm() {
        js("window.FLARE&&FLARE.onAlarm($sosTriggered,$alarmAcknowledged,$manualTest)")
    }

    private fun setConn(state: String, text: String) {
        connState = state
        connText = text
        pushStatus()
    }

    private fun applySystemBars(dark: Boolean) {
        root.setBackgroundColor(if (dark) 0xFF22100B.toInt() else Color.WHITE)
        WindowCompat.getInsetsController(window, window.decorView).apply {
            isAppearanceLightStatusBars = !dark
            isAppearanceLightNavigationBars = !dark
        }
    }

    /** Functions the dashboard page can call as window.Android.xxx() */
    inner class Bridge {
        @JavascriptInterface
        fun connect(ip: String) {
            mainHandler.post { connectToEsp32(ip) }
        }

        @JavascriptInterface
        fun disconnect() {
            mainHandler.post { disconnectFromEsp32() }
        }

        @JavascriptInterface
        fun stopAlarm() {
            mainHandler.post { acknowledgeSos() }
        }

        @JavascriptInterface
        fun testSos() {
            mainHandler.post { triggerSos("FLARE manual SOS test", manual = true) }
        }

        @JavascriptInterface
        fun savedIp(): String = prefs().getString(KEY_IP, "") ?: ""

        @JavascriptInterface
        fun setDark(dark: Boolean) {
            mainHandler.post { applySystemBars(dark) }
        }
    }

    // ---------------------------------------------------------------
    // ESP32 WEBSOCKET
    // ---------------------------------------------------------------

    private fun connectToEsp32(rawIp: String) {
        val ip = rawIp.trim()
            .removePrefix("http://").removePrefix("ws://")
            .substringBefore("/").substringBefore(":")

        if (!ip.matches(IP_PATTERN)) {
            setConn("error", "Invalid IP address")
            return
        }

        prefs().edit().putString(KEY_IP, ip).apply()
        targetIp = ip
        openSocket(ip)
    }

    private fun openSocket(ip: String) {
        mainHandler.removeCallbacks(reconnectRunnable)
        webSocket?.cancel()

        setConn("connecting", "Connecting to $ip…")
        Log.d(TAG, "Connecting to ws://$ip:81/")

        val request = Request.Builder().url("ws://$ip:81/").build()
        webSocket = httpClient.newWebSocket(request, socketListener)
    }

    private fun disconnectFromEsp32() {
        targetIp = null
        mainHandler.removeCallbacks(reconnectRunnable)
        webSocket?.close(1000, "bye")
        webSocket = null
        setConn("disconnected", "Not connected")
    }

    private val socketListener = object : WebSocketListener() {

        override fun onOpen(ws: WebSocket, response: Response) {
            mainHandler.post {
                if (ws !== webSocket) return@post
                setConn("connected", targetIp ?: "Connected")
            }
        }

        override fun onMessage(ws: WebSocket, text: String) {
            mainHandler.post {
                if (ws !== webSocket) return@post
                handleMessage(text)
            }
        }

        override fun onClosing(ws: WebSocket, code: Int, reason: String) {
            ws.close(1000, null)
        }

        override fun onClosed(ws: WebSocket, code: Int, reason: String) {
            mainHandler.post { onSocketLost(ws) }
        }

        override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
            Log.w(TAG, "WebSocket failure: ${t.message}")
            mainHandler.post { onSocketLost(ws) }
        }
    }

    private fun onSocketLost(ws: WebSocket) {
        if (ws !== webSocket) return
        webSocket = null

        if (targetIp != null) {
            setConn("retry", "Offline · retrying")
            mainHandler.postDelayed(reconnectRunnable, RECONNECT_DELAY_MS)
        } else {
            setConn("disconnected", "Not connected")
        }
    }

    // ---------------------------------------------------------------
    // SENSOR DATA
    // ---------------------------------------------------------------

    private fun handleMessage(text: String) {
        // UI gets every message as-is
        js("window.FLARE&&FLARE.onMessage(${JSONObject.quote(text)})")

        try {
            val json = JSONObject(text)
            if (json.optString("t") != "live") return

            json.optJSONArray("lim")?.let { arr ->
                for (i in 0 until minOf(3, arr.length())) {
                    val v = arr.optDouble(i, DEFAULT_LIMIT)
                    limits[i] = if (v.isFinite() && v > 0) v else DEFAULT_LIMIT
                }
            }

            water = readSensorValue(json, "water")
            rain = readSensorValue(json, "rain")
            soil = readSensorValue(json, "soil")

            evaluateSos()
        } catch (e: Exception) {
            Log.e(TAG, "Invalid sensor JSON: $text", e)
        }
    }

    private fun readSensorValue(json: JSONObject, key: String): Double? {
        if (!json.has(key) || json.isNull(key)) return null
        val value = json.optDouble(key, Double.NaN)
        return if (value.isFinite() && value in 0.0..100.0) value else null
    }

    private fun evaluateSos() {
        val values = listOf(water, rain, soil)

        val critical = values.indices.filter { i ->
            val v = values[i]
            v != null && v >= limits[i]
        }

        if (critical.isNotEmpty()) {
            if (manualTest) manualTest = false        // test became a real alarm
            if (!sosTriggered) {
                val detail = critical.joinToString(", ") { i ->
                    "${SENSOR_NAMES[i]} ${values[i]!!.toInt()}%"
                }
                triggerSos("$detail above the safe limit", manual = false)
            } else {
                pushAlarm()
            }
            return
        }

        // reset only when all three are valid and safe
        if (values.all { it != null } && sosTriggered && !manualTest) {
            resetSosCondition()
        }
    }

    // ---------------------------------------------------------------
    // SOS
    // ---------------------------------------------------------------

    private fun triggerSos(message: String, manual: Boolean) {
        if (sosTriggered) return

        sosTriggered = true
        alarmAcknowledged = false
        manualTest = manual

        startSosAlarm()
        showSosNotification(
            title = if (manual) "FLARE SOS test" else "FLARE SOS — move to higher ground",
            message = message,
            active = true
        )
        pushAlarm()
        Log.w(TAG, "SOS TRIGGERED: $message")
    }

    /** "Stop alarm" button. Real SOS stays active (acknowledged) until sensors drop. */
    private fun acknowledgeSos() {
        when {
            manualTest -> resetSosCondition()
            sosTriggered -> {
                alarmAcknowledged = true
                stopAlarmSound()
                showSosNotification(
                    title = "FLARE — alarm silenced",
                    message = "Danger is still present. Stay alert.",
                    active = false
                )
                pushAlarm()
            }
            else -> stopAlarmSound()
        }
    }

    private fun resetSosCondition() {
        stopAlarmSound()
        sosTriggered = false
        alarmAcknowledged = false
        manualTest = false
        NotificationManagerCompat.from(this).cancel(NOTIFICATION_ID)
        pushAlarm()
    }

    private fun startSosAlarm() {
        if (alarmRunning || alarmAcknowledged) return
        alarmRunning = true
        try {
            toneGenerator = ToneGenerator(AudioManager.STREAM_ALARM, 80)
        } catch (e: Exception) {
            Log.e(TAG, "Could not create tone generator", e)
        }
        mainHandler.removeCallbacks(alarmRunnable)
        mainHandler.post(alarmRunnable)
    }

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
    }

    private fun vibrate() {
        try {
            val vibrator: Vibrator =
                if (Build.VERSION.SDK_INT >= 31) {
                    getSystemService(VibratorManager::class.java).defaultVibrator
                } else {
                    legacyVibrator()
                }
            vibrator.vibrate(
                VibrationEffect.createOneShot(400, VibrationEffect.DEFAULT_AMPLITUDE)
            )
        } catch (e: Exception) {
            Log.e(TAG, "Vibrate failed", e)
        }
    }

    @Suppress("DEPRECATION")
    private fun legacyVibrator(): Vibrator =
        getSystemService(Context.VIBRATOR_SERVICE) as Vibrator

    // ---------------------------------------------------------------
    // NOTIFICATIONS
    // ---------------------------------------------------------------

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "FLARE SOS Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "FLARE flood & landslide warnings"
            }
            getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }
    }

    private fun requestNotificationPermission() {
        if (
            Build.VERSION.SDK_INT >= 33 &&
            ActivityCompat.checkSelfPermission(
                this, Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                NOTIFICATION_PERMISSION_REQUEST
            )
        }
    }

    /**
     * active = true  -> loud heads-up, pinned, with a "Stop alarm" button
     * active = false -> quiet, swipe-away reminder after the alarm is silenced
     */
    private fun showSosNotification(title: String, message: String, active: Boolean) {
        if (
            Build.VERSION.SDK_INT >= 33 &&
            ActivityCompat.checkSelfPermission(
                this, Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            Log.w(TAG, "Notification permission not granted")
            return
        }

        val openApp = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val stopAlarm = PendingIntent.getActivity(
            this, 1,
            Intent(this, MainActivity::class.java)
                .setAction(ACTION_STOP)
                .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val builder = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_warning)
            .setContentTitle(title)
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setColor(0xFFDC2626.toInt())
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setContentIntent(openApp)
            .setOngoing(active)
            .setAutoCancel(!active)
            .setSilent(!active)

        if (active) {
            builder.addAction(0, "Stop alarm", stopAlarm)
        }

        NotificationManagerCompat.from(this).notify(NOTIFICATION_ID, builder.build())
    }
}

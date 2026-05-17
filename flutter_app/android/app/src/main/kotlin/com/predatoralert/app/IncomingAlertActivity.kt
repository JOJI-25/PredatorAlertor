package com.predatoralert.app

import android.app.KeyguardManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.view.WindowManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * Full-screen alert activity that appears over the lock screen.
 * This activity displays the alert UI and provides the ACKNOWLEDGE button.
 * 
 * Security: This activity does NOT bypass lock screen security.
 * The lock screen remains active underneath.
 */
class IncomingAlertActivity : FlutterActivity() {
    
    companion object {
        private const val CHANNEL = "com.predatoralert.app/incoming_alert"
    }
    
    private var wakeLock: PowerManager.WakeLock? = null
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Configure window to show over lock screen
        configureWindowFlags()
        
        // Acquire wake lock to keep screen on
        acquireWakeLock()
    }
    
    private fun configureWindowFlags() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            // Modern API (Android 8.1+)
            setShowWhenLocked(true)
            setTurnScreenOn(true)
            
            // Keep screen on while alert is showing
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            // Legacy API
            @Suppress("DEPRECATION")
            window.addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
            )
        }
        
        // NOTE: We intentionally do NOT use FLAG_DISMISS_KEYGUARD
        // to ensure lock screen security is preserved
    }
    
    private fun acquireWakeLock() {
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.SCREEN_BRIGHT_WAKE_LOCK or PowerManager.ACQUIRE_CAUSES_WAKEUP,
            "predatoralert:alertactivity"
        )
        wakeLock?.acquire(5 * 60 * 1000L) // 5 minutes max
    }
    
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "getAlertData" -> {
                    // Return alert data to Flutter
                    val animal = intent.getStringExtra(AlertForegroundService.EXTRA_ANIMAL) ?: "Unknown"
                    val confidence = intent.getStringExtra(AlertForegroundService.EXTRA_CONFIDENCE) ?: "0"
                    result.success(mapOf(
                        "animal" to animal,
                        "confidence" to confidence
                    ))
                }
                "acknowledgeAlert" -> {
                    // Stop the alert service and close this activity
                    stopAlertService()
                    finish()
                    result.success(true)
                }
                else -> result.notImplemented()
            }
        }
    }
    
    private fun stopAlertService() {
        val stopIntent = Intent(this, AlertForegroundService::class.java).apply {
            action = "com.predatoralert.app.STOP_ALERT"
        }
        startService(stopIntent)
    }
    
    override fun onBackPressed() {
        // Disable back button to prevent accidental dismissal
        // User must tap ACKNOWLEDGE to stop the alert
    }
    
    override fun onDestroy() {
        super.onDestroy()
        
        // Release wake lock
        try {
            if (wakeLock?.isHeld == true) {
                wakeLock?.release()
            }
        } catch (e: Exception) {
            // Ignore
        }
    }
    
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
    }
    
    // Use the main Dart entrypoint for the alert UI
    override fun getDartEntrypointFunctionName(): String = "main"
    
    // Use a special route for the alert screen
    override fun getInitialRoute(): String = "/incoming_alert"
}

package com.predatoralert.app

import android.app.*
import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import android.os.*
import android.util.Log
import androidx.core.app.NotificationCompat

/**
 * Foreground service for persistent siren and vibration playback.
 * This service cannot be killed by the system and will continue playing
 * until explicitly stopped by user action (ACKNOWLEDGE button).
 */
class AlertForegroundService : Service() {
    
    companion object {
        private const val TAG = "AlertForegroundService"
        private const val NOTIFICATION_ID = 1001
        private const val CHANNEL_ID = "predator_alert_service"
        private const val ACTION_STOP = "com.predatoralert.app.STOP_ALERT"
        
        // Keys for intent extras
        const val EXTRA_ANIMAL = "animal"
        const val EXTRA_CONFIDENCE = "confidence"
    }
    
    private var mediaPlayer: MediaPlayer? = null
    private var vibrator: Vibrator? = null
    private var wakeLock: PowerManager.WakeLock? = null
    
    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "AlertForegroundService created")
        createNotificationChannel()
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "onStartCommand received: ${intent?.action}")
        
        when (intent?.action) {
            ACTION_STOP -> {
                stopAlert()
                return START_NOT_STICKY
            }
        }
        
        val animal = intent?.getStringExtra(EXTRA_ANIMAL) ?: "Unknown"
        val confidence = intent?.getStringExtra(EXTRA_CONFIDENCE) ?: "0"
        
        // Start as foreground service immediately
        val notification = createNotification(animal, confidence)
        startForeground(NOTIFICATION_ID, notification)
        
        // Acquire wake lock to keep CPU running
        acquireWakeLock()
        
        // Start siren and vibration
        startSiren()
        startVibration()
        
        // Launch the full-screen alert activity
        launchAlertActivity(animal, confidence)
        
        return START_STICKY
    }
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "AlertForegroundService destroyed")
        stopAlert()
    }
    
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Predator Alert",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Critical predator detection alerts"
                setSound(null, null) // Sound is handled by MediaPlayer
                enableVibration(false) // Vibration is handled separately
                lockscreenVisibility = Notification.VISIBILITY_PUBLIC
            }
            
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }
    
    private fun createNotification(animal: String, confidence: String): Notification {
        // Create stop action intent
        val stopIntent = Intent(this, AlertForegroundService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPendingIntent = PendingIntent.getService(
            this, 0, stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        // Create full-screen intent for the alert activity
        val fullScreenIntent = Intent(this, IncomingAlertActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or 
                    Intent.FLAG_ACTIVITY_CLEAR_TOP or
                    Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra(EXTRA_ANIMAL, animal)
            putExtra(EXTRA_CONFIDENCE, confidence)
        }
        val fullScreenPendingIntent = PendingIntent.getActivity(
            this, 0, fullScreenIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("🚨 PREDATOR ALERT")
            .setContentText("${animal.uppercase()} detected! Tap to view.")
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_CALL)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setOngoing(true)
            .setAutoCancel(false)
            .setFullScreenIntent(fullScreenPendingIntent, true)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "STOP", stopPendingIntent)
            .build()
    }
    
    private fun acquireWakeLock() {
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "predatoralert:alertservice"
        )
        wakeLock?.acquire(10 * 60 * 1000L) // 10 minutes max
    }
    
    private fun startSiren() {
        try {
            mediaPlayer?.release()
            mediaPlayer = MediaPlayer.create(this, R.raw.siren).apply {
                isLooping = true
                
                // Use alarm stream to bypass silent mode
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                    setAudioAttributes(
                        AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_ALARM)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                            .build()
                    )
                } else {
                    @Suppress("DEPRECATION")
                    setAudioStreamType(AudioManager.STREAM_ALARM)
                }
                
                // Set volume to max
                val audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
                val maxVolume = audioManager.getStreamMaxVolume(AudioManager.STREAM_ALARM)
                audioManager.setStreamVolume(AudioManager.STREAM_ALARM, maxVolume, 0)
                
                start()
            }
            Log.d(TAG, "Siren started")
        } catch (e: Exception) {
            Log.e(TAG, "Error starting siren: ${e.message}")
        }
    }
    
    private fun startVibration() {
        try {
            vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vibratorManager = getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
                vibratorManager.defaultVibrator
            } else {
                @Suppress("DEPRECATION")
                getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            }
            
            // Vibration pattern: 0ms delay, 500ms on, 200ms off, repeat
            val pattern = longArrayOf(0, 500, 200, 500, 200, 500)
            
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator?.vibrate(VibrationEffect.createWaveform(pattern, 0))
            } else {
                @Suppress("DEPRECATION")
                vibrator?.vibrate(pattern, 0)
            }
            Log.d(TAG, "Vibration started")
        } catch (e: Exception) {
            Log.e(TAG, "Error starting vibration: ${e.message}")
        }
    }
    
    private fun launchAlertActivity(animal: String, confidence: String) {
        val intent = Intent(this, IncomingAlertActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_CLEAR_TOP or
                    Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra(EXTRA_ANIMAL, animal)
            putExtra(EXTRA_CONFIDENCE, confidence)
        }
        startActivity(intent)
    }
    
    fun stopAlert() {
        Log.d(TAG, "Stopping alert...")
        
        // Stop and release media player
        try {
            mediaPlayer?.stop()
            mediaPlayer?.release()
            mediaPlayer = null
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping media player: ${e.message}")
        }
        
        // Stop vibration
        try {
            vibrator?.cancel()
            vibrator = null
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping vibration: ${e.message}")
        }
        
        // Release wake lock
        try {
            if (wakeLock?.isHeld == true) {
                wakeLock?.release()
            }
            wakeLock = null
        } catch (e: Exception) {
            Log.e(TAG, "Error releasing wake lock: ${e.message}")
        }
        
        // Stop foreground service
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }
}

package com.predatoralert.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.PowerManager
import android.util.Log

/**
 * Receiver to launch the app when a predator alert is received
 */
class AlertReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        Log.d("AlertReceiver", "Predator alert received - launching app")
        
        // Wake up the device
        val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
        val wakeLock = powerManager.newWakeLock(
            PowerManager.FULL_WAKE_LOCK or 
            PowerManager.ACQUIRE_CAUSES_WAKEUP or 
            PowerManager.ON_AFTER_RELEASE,
            "predatoralert:wakelock"
        )
        wakeLock.acquire(10000) // 10 seconds
        
        // Launch the main activity
        val launchIntent = Intent(context, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)
            addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
            addFlags(Intent.FLAG_FROM_BACKGROUND)
            putExtra("predator_alert", true)
            putExtra("animal", intent.getStringExtra("animal") ?: "unknown")
        }
        
        context.startActivity(launchIntent)
        
        // Release wake lock after a delay
        android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
            if (wakeLock.isHeld) {
                wakeLock.release()
            }
        }, 5000)
    }
}

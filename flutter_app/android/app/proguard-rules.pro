# Flutter/Firebase ProGuard Rules
# Keep Flutter classes
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }
-dontwarn io.flutter.embedding.**

# Keep Firebase classes
-keep class com.google.firebase.** { *; }
-keep class com.google.android.gms.** { *; }
-dontwarn com.google.firebase.**
-dontwarn com.google.android.gms.**

# Keep Google Sign-In
-keep class com.google.android.gms.auth.** { *; }

# Keep Kotlin Coroutines
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}

# Keep serialization
-keepattributes *Annotation*
-keepattributes Signature

# Fix R8 missing class warning
-dontwarn com.google.android.play.core.splitcompat.SplitCompatApplication

"""
PredatorAlert SMS & Phone Call Notification Module
Sends instant phone call alerts + SMS via Twilio when predators are detected.
Phone calls ring immediately (2-3s), SMS follows as backup.
"""
import threading
import time
from config import Config
from logger import detection_logger

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False


class SMSNotifier:
    """Sends instant phone call + SMS alerts via Twilio when predators are detected."""
    
    # Cooldown period per animal class to avoid alert spam (seconds)
    DEFAULT_COOLDOWN = 60
    
    def __init__(self):
        self.enabled = Config.SMS_ENABLED
        self.account_sid = Config.TWILIO_ACCOUNT_SID
        self.auth_token = Config.TWILIO_AUTH_TOKEN
        self.from_number = Config.TWILIO_NUMBER
        self.to_number = Config.SMS_DESTINATION_NUMBER
        self.cooldown = Config.SMS_COOLDOWN_SECONDS
        self.call_enabled = Config.CALL_ENABLED
        
        self._client = None
        self._initialized = False
        # Track last alert time per animal to avoid spamming
        self._last_alert_time: dict[str, float] = {}
        self._lock = threading.Lock()
    
    def initialize(self) -> bool:
        """Initialize Twilio client. Returns True if successful."""
        if not self.enabled:
            detection_logger.log_api_status("SMS/Call notifications disabled")
            return True
        
        if not TWILIO_AVAILABLE:
            detection_logger.log_error(
                "Twilio package not installed. Run: pip install twilio"
            )
            return False
        
        if not all([self.account_sid, self.auth_token, self.from_number, self.to_number]):
            detection_logger.log_error(
                "Twilio config incomplete. Check TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
                "TWILIO_NUMBER, SMS_DESTINATION_NUMBER in .env"
            )
            return False
        
        try:
            self._client = TwilioClient(self.account_sid, self.auth_token)
            self._initialized = True
            detection_logger.log_api_status(
                "Twilio notifier initialized",
                f"to={self.to_number} | call={self.call_enabled} | cooldown={self.cooldown}s"
            )
            return True
        except Exception as e:
            detection_logger.log_error("Failed to initialize Twilio client", e)
            return False
    
    def send_predator_alert(
        self,
        animal: str,
        confidence: float,
        priority_label: str = "unknown"
    ) -> bool:
        """
        Send instant alert for a predator detection.
        1. Phone call (instant — rings in 2-3 seconds)
        2. SMS (backup — may take 10-30s via carrier)
        Respects cooldown to avoid spamming.
        """
        if not self.enabled or not self._initialized:
            return False
        
        # Check cooldown for this animal class
        with self._lock:
            now = time.time()
            last_sent = self._last_alert_time.get(animal, 0)
            if now - last_sent < self.cooldown:
                return False  # Still in cooldown
            self._last_alert_time[animal] = now
        
        # Fire both call and SMS in parallel background threads for speed
        threading.Thread(
            target=self._send_call,
            args=(animal, confidence, priority_label),
            daemon=True
        ).start()
        
        threading.Thread(
            target=self._send_sms,
            args=(animal, confidence, priority_label),
            daemon=True
        ).start()
        
        return True
    
    def _send_call(self, animal: str, confidence: float, priority_label: str) -> None:
        """Make an instant phone call via Twilio (rings phone in 2-3 seconds)."""
        if not self.call_enabled:
            return
            
        try:
            # TwiML: speaks the alert message when the call is answered
            twiml = (
                '<Response>'
                '<Say voice="alice" language="en-IN">'
                f'Warning! Predator Alert! A {animal} has been detected '
                f'with {confidence:.0%} confidence. '
                f'Priority level: {priority_label}. '
                'Please check the camera feed immediately. '
                'Repeating: '
                f'A {animal} has been detected near your area.'
                '</Say>'
                '<Pause length="1"/>'
                '<Say voice="alice" language="en-IN">'
                f'This is an automated alert from Predator Alert device {Config.DEVICE_ID}.'
                '</Say>'
                '</Response>'
            )
            
            call = self._client.calls.create(
                twiml=twiml,
                from_=self.from_number,
                to=self.to_number
            )
            
            detection_logger.log_api_status(
                "Phone call initiated",
                f"animal={animal} | sid={call.sid}"
            )
        except Exception as e:
            detection_logger.log_error(f"Phone call failed for {animal}", e)
    
    def _send_sms(self, animal: str, confidence: float, priority_label: str) -> None:
        """Send SMS via Twilio (backup, may take 10-30s via carrier)."""
        try:
            body = (
                f"⚠️ PREDATOR ALERT ⚠️\n"
                f"Animal: {animal.upper()}\n"
                f"Confidence: {confidence:.0%}\n"
                f"Priority: {priority_label}\n"
                f"Device: {Config.DEVICE_ID}\n"
                f"Action Required: Check camera feed immediately!"
            )
            
            message = self._client.messages.create(
                body=body,
                from_=self.from_number,
                to=self.to_number
            )
            
            detection_logger.log_api_status(
                "SMS sent",
                f"animal={animal} | sid={message.sid}"
            )
        except Exception as e:
            detection_logger.log_error(f"SMS send failed for {animal}", e)
    
    def is_ready(self) -> bool:
        """Check if notifier is ready."""
        return self._initialized or not self.enabled

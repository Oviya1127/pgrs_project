"""Application constants."""

class Roles:
    USER = "USER"
    ADMIN = "ADMIN"


class GrievanceStatus:
    SUBMITTED = "SUBMITTED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    
    ALL = [SUBMITTED, IN_PROGRESS, RESOLVED]


class PriorityLevel:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    
    ALL = [LOW, MEDIUM, HIGH, CRITICAL]
    
    ORDER = {
        LOW: 1,
        MEDIUM: 2,
        HIGH: 3,
        CRITICAL: 4
    }


class SentimentThreshold:
    CRITICAL = -0.6
    HIGH = -0.3
    MEDIUM = 0.0
    LOW = 0.3


class PeerThreshold:
    CRITICAL = 50
    HIGH = 20
    MEDIUM = 5


class Messages:
    LOGIN_SUCCESS = "Login successful"
    REGISTER_SUCCESS = "Registration successful"
    GRIEVANCE_SUBMITTED = "Grievance submitted successfully"
    GRIEVANCE_UPDATED = "Grievance updated successfully"
    FEEDBACK_SUBMITTED = "Feedback submitted successfully"
    VALIDATION_SUCCESS = "Peer validation recorded"
    
    INVALID_CREDENTIALS = "Invalid email or password"
    EMAIL_EXISTS = "Email already exists"
    PHONE_EXISTS = "Phone number already exists"
    USER_NOT_FOUND = "User not found"
    GRIEVANCE_NOT_FOUND = "Grievance not found"
    UNAUTHORIZED = "Unauthorized access"
    FORBIDDEN = "Access forbidden"
    ALREADY_VALIDATED = "You have already validated this grievance"
    OWN_GRIEVANCE = "Cannot validate your own grievance"
